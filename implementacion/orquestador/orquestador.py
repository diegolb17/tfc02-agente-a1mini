"""Orquestador (seccion 5.1.3).

Atiende tres clases de evento en un solo bucle: los cambios de estado de la
impresora, el reloj de supervision y los mensajes del operador. Ademas recibe
los eventos del microcontrolador durante el ciclo de remocion. Es el unico que
llama al modelo de lenguaje, y la decision sobre la confianza la toma aqui, no
el modelo (R-SEG-01).
"""
import logging
import queue
import time
import unicodedata
import uuid

from . import mensajes as M
from .impresora import EN_CURSO, EN_PAUSA, TERMINADA

log = logging.getLogger("orquestador")


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip(" ?!.¿¡")


# Ordenes de rutina reconocidas por palabras clave, sin llamar al modelo (5.3.3).
PALABRAS = {
    "ayuda": ("/start", "/ayuda", "ayuda"),
    "estado": ("/estado", "estado", "cuanto falta", "como va", "como vamos"),
    "foto": ("/foto", "foto"),
    "pausa": ("/pausa", "pausa", "pausar", "pausa la impresion"),
    "reanudar": ("/reanudar", "reanuda", "reanudar", "continua", "continuar"),
    "luz": ("/luz", "luz"),
    "referencia": ("/referencia", "referencia"),
    "detener": ("/detener", "deten todo", "detener", "detenla", "cancela la impresion"),
}


class Orquestador:
    def __init__(self, config, impresora, camara, telegram, registro, micro, agente, funciones):
        self.config = config
        self.impresora = impresora
        self.camara = camara
        self.telegram = telegram
        self.registro = registro
        self.micro = micro
        self.agente = agente
        self.f = funciones
        self.cola: queue.Queue = queue.Queue()
        self.proxima_supervision = None
        self.recordatorio = None
        self.pendientes: dict[str, dict] = {}     # confirmaciones en espera
        self.cancelada_por_falla = False
        self.sin_red = False
        self.esperando_verificacion = None         # intento en duda, a la espera del operador
        self.inicio_espera_falla = None
        self._parar = False
        impresora.al_cambiar_estado(lambda n, a: self.cola.put(("impresora", n, a)))

    # Bucle principal ----------------------------------------------------------
    def ejecutar(self, duracion: float | None = None) -> None:
        fin = time.monotonic() + duracion if duracion else None
        self.telegram.escuchar(self.cola)
        while not self._parar and (fin is None or time.monotonic() < fin):
            if hasattr(self.impresora, "avanzar"):
                self.impresora.avanzar()
            try:
                evento = self.cola.get(timeout=0.2)
            except queue.Empty:
                evento = None
            if evento:
                try:
                    self._atender(evento)
                except Exception:
                    log.exception("Error al atender %s", evento[:2])
            self._relojes()

    def detener(self) -> None:
        self._parar = True
        self.telegram.detener()

    def _atender(self, evento) -> None:
        tipo = evento[0]
        if tipo == "impresora":
            self._cambio_impresora(evento[1], evento[2])
        elif tipo == "mensaje":
            self._mensaje(evento[1])
        elif tipo == "boton":
            self._boton(*evento[1:])
        elif tipo == "micro":
            self._micro(evento[1], evento[2])

    def evento_micro(self, tipo, detalle) -> None:
        """Lo llama el microcontrolador desde su hilo; se atiende en el bucle."""
        self.cola.put(("micro", tipo, detalle))

    def _relojes(self) -> None:
        ahora = time.monotonic()
        if self.proxima_supervision and ahora >= self.proxima_supervision:
            self.proxima_supervision = ahora + self.config.periodo_supervision
            self._supervisar()
        if self.recordatorio and ahora >= self.recordatorio:
            if self.impresora.estado()["fase"] == EN_PAUSA:
                self.telegram.enviar(M.recordatorio_pausa(), self._botones_falla())
                self.recordatorio = ahora + self.config.recordatorio_pausa
            else:
                self.recordatorio = None
        for clave, p in list(self.pendientes.items()):
            if ahora >= p["vence"]:
                del self.pendientes[clave]
                self.telegram.quitar_botones(p["mensaje"])
                self.telegram.enviar(M.SIN_RESPUESTA)
                self.registro.intervencion("sin respuesta", None)
                self.registro.evento("confirmacion vencida", p["accion"])

    # Impresora ----------------------------------------------------------------
    def _cambio_impresora(self, nuevo: str, anterior: str | None) -> None:
        self.registro.evento("cambio de estado", f"{anterior} a {nuevo}")
        log.info("Impresora: %s a %s", anterior, nuevo)
        if nuevo in EN_CURSO and anterior not in EN_CURSO and anterior != EN_PAUSA:
            self.registro.nuevo_trabajo(self.impresora.estado().get("archivo"))
            self.proxima_supervision = time.monotonic() + self.config.periodo_supervision
        elif nuevo in EN_CURSO and anterior == EN_PAUSA:
            self.proxima_supervision = time.monotonic() + self.config.periodo_supervision
        elif nuevo == EN_PAUSA:
            self.proxima_supervision = None
        elif nuevo == TERMINADA:
            self.proxima_supervision = None
            self._fin_de_impresion()
        elif nuevo == "FAILED":
            self.proxima_supervision = None
            self.recordatorio = None
            if self.cancelada_por_falla:
                self.cancelada_por_falla = False
                self.f.ciclo.remocion_autorizada = True       # el operador eligio cancelar
                self.telegram.enviar(M.REMOCION_FALLIDA)
                self.f.iniciar_remocion()

    # Supervision durante la impresion (Figura 28) ------------------------------
    def _supervisar(self) -> None:
        if self.impresora.estado()["fase"] not in EN_CURSO:
            return
        estado = self.impresora.estado()
        self.f.capturar_imagen("supervision")
        captura = self.f.ciclo.capturas["supervision"]
        v = self.agente.inspeccionar("supervision", [captura], estado)
        self._registrar_captura("supervision", "800x600", captura, v)
        if not v.valido:
            if not self.sin_red:
                self.sin_red = True
                self.telegram.enviar(M.SIN_RED)
                self.registro.evento("sin red", v.error)
            return
        if self.sin_red:
            self.sin_red = False
            self.telegram.enviar(M.RED_RECUPERADA)
        if v.clase != "falla" or v.confianza < self.config.umbral_falla:
            return
        # Segunda consulta con la imagen completa antes de pausar.
        self.f.capturar_imagen("verificacion")
        completa = self.f.ciclo.capturas["verificacion"]
        v2 = self.agente.inspeccionar("confirmacion_falla", [completa], estado)
        self._registrar_captura("confirmacion de falla", f"{completa.ancho}x{completa.alto}", completa, v2)
        if not (v2.valido and v2.clase == "falla" and v2.confianza >= self.config.umbral_falla):
            self.registro.evento("falla no confirmada", v2.descripcion or v2.error)
            return
        self.f.ciclo.falla_confirmada = True
        r = self.f.pausar_impresion(v2.descripcion)
        self.telegram.enviar_foto(completa.jpeg, M.falla_confirmada(estado.get("archivo"),
                                  v2.descripcion, r.get("pausada", False)), self._botones_falla())
        self.inicio_espera_falla = time.time()
        self.recordatorio = time.monotonic() + self.config.recordatorio_pausa

    @staticmethod
    def _botones_falla():
        return [[("Reanudar", "falla:reanudar"), ("Cancelar trabajo", "falla:cancelar")]]

    def _registrar_captura(self, tipo, resolucion, captura, v) -> None:
        self.registro.captura(tipo, resolucion, v.clase, v.confianza, v.descripcion or v.error,
                              v.tokens_entrada, str(captura.ruta))
        log.info("Consulta %s: %s %.2f (%s tokens) %s", tipo, v.clase, v.confianza,
                 v.tokens_entrada, v.descripcion or v.error)

    # Fin de la impresion: escalado por confianza (R-SEG-01) ---------------------
    def _fin_de_impresion(self) -> None:
        estado = self.impresora.estado()
        archivo = estado.get("archivo")
        if not self.config.referencia.exists():
            self.f.capturar_imagen("verificacion")
            self.telegram.enviar(M.SIN_REFERENCIA)
            self._solicitar("iniciar_remocion", "sin imagen de referencia")
            return
        self.f.capturar_imagen("verificacion")
        captura = self.f.ciclo.capturas["verificacion"]
        referencia = self.camara_referencia()
        v = self.agente.inspeccionar("fin", [referencia, captura], estado)
        self._registrar_captura("fin de impresion", f"{captura.ancho}x{captura.alto}", captura, v)
        umbral = self.config.umbral_confianza
        if v.valido and v.clase == "libre" and v.confianza >= umbral:
            self.registro.cerrar_trabajo("sin pieza")
            self.telegram.enviar_foto(captura.jpeg, M.PLATAFORMA_YA_LIBRE)
        elif v.valido and v.clase == "pieza" and v.confianza >= umbral:
            # La decision la toma el orquestador al comparar con el umbral.
            self.f.ciclo.remocion_autorizada = True
            self.telegram.enviar_foto(captura.jpeg, M.fin_confianza_alta(archivo, v.descripcion, v.confianza))
            self.f.iniciar_remocion()
        elif v.valido and v.clase == "anomala":
            self._solicitar("iniciar_remocion", M.fin_anomalia(archivo, v.descripcion), texto_directo=True)
        elif v.valido:
            self._solicitar("iniciar_remocion", M.fin_confirmar(archivo, v.descripcion, v.confianza, umbral),
                            texto_directo=True)
        else:
            self._solicitar("iniciar_remocion", M.fin_sin_veredicto(v.error), texto_directo=True)

    def camara_referencia(self):
        from .camara import _desde_bytes
        return _desde_bytes(self.config.referencia.read_bytes(), "referencia", "plataforma_vacia")

    def _solicitar(self, accion: str, motivo: str, texto_directo: bool = False) -> None:
        """Pregunta con botones; sin respuesta en el plazo, la accion no se ejecuta."""
        clave = uuid.uuid4().hex[:8]
        texto = motivo if texto_directo else f"Propuesta: {accion.replace('_', ' ')}. Motivo: {motivo}. ¿La confirmas?"
        etiqueta = "Confirmar remoción" if accion == "iniciar_remocion" else "Confirmar"
        botones = [[(etiqueta, f"conf:{clave}:si"), ("Cancelar", f"conf:{clave}:no")]]
        captura = self.f.ciclo.ultima_captura
        if captura is not None:
            mensaje = self.telegram.enviar_foto(captura.jpeg, texto, botones)
        else:
            mensaje = self.telegram.enviar(texto, botones)
        self.pendientes[clave] = {"accion": accion, "vence": time.monotonic() + self.config.plazo_confirmacion,
                                  "mensaje": mensaje, "inicio": time.time()}
        self.registro.evento("confirmacion solicitada", f"{accion}: {motivo}")

    # Botones ------------------------------------------------------------------
    def _boton(self, dato: str, consulta_id, mensaje_id) -> None:
        self.telegram.responder_boton(consulta_id)
        self.telegram.quitar_botones(mensaje_id)
        partes = dato.split(":")
        if partes[0] == "conf":
            self._respuesta_confirmacion(partes[1], partes[2] == "si")
        elif dato == "falla:reanudar":
            self._intervencion("reanudar", self.inicio_espera_falla)
            self.recordatorio = None
            self.f.ciclo.reanudar_autorizado = True
            r = self.f.reanudar_impresion()
            self.telegram.enviar("Reanudé la impresión." if r.get("reanudada")
                                 else f"No se pudo reanudar: {r}")
        elif dato == "falla:cancelar":
            self._intervencion("cancelar", self.inicio_espera_falla)
            self.recordatorio = None
            self.cancelada_por_falla = True
            self.impresora.detener()
        elif dato == "verif:libre":
            self._intervencion("confirmar plataforma libre", None)
            self.esperando_verificacion = None
            self.micro.resultado_verificacion(True)
        elif dato == "verif:pieza":
            self._intervencion("plataforma con pieza", None)
            self.esperando_verificacion = None
            self.micro.resultado_verificacion(False)
        elif dato == "retenida:reintentar":
            self._intervencion("reintentar", None)
            self.f.ciclo.remocion_autorizada = True
            self.f.iniciar_remocion()
        elif dato == "retenida:retirada":
            self._intervencion("retirada manual", None)
            self.registro.cerrar_trabajo("retirada manual")
            self.telegram.enviar("Gracias. El equipo queda disponible.")
        elif dato == "parada:reanudar":
            self._intervencion("reanudar tras parada", None)
            self.micro.reanudar()
            self.telegram.enviar("Rearme registrado. El ciclo queda en espera de una orden nueva.")
        elif dato == "detener:si":
            self._intervencion("detener", None)
            self.impresora.detener()
            self.telegram.enviar("Detuve la impresión.")
        elif dato == "detener:no":
            self.telegram.enviar("De acuerdo, la impresión sigue.")

    def _intervencion(self, accion: str, desde: float | None) -> None:
        self.registro.intervencion(accion, round(time.time() - desde, 1) if desde else None)

    def _respuesta_confirmacion(self, clave: str, si: bool) -> None:
        p = self.pendientes.pop(clave, None)
        if p is None:
            self.telegram.enviar("Esa pregunta ya venció o fue respondida.")
            return
        self._intervencion("confirmar" if si else "cancelar", p["inicio"])
        if not si:
            self.telegram.enviar(M.REMOCION_CANCELADA if p["accion"] == "iniciar_remocion"
                                 else "Entendido, no lo hago.")
            return
        if p["accion"] == "iniciar_remocion":
            self.f.ciclo.remocion_autorizada = True
            r = self.f.iniciar_remocion()
            self.telegram.enviar(M.REMOCION_CONFIRMADA if r.get("iniciada")
                                 else f"No se pudo iniciar: {r.get('rechazada', r)}")
        elif p["accion"] == "reanudar_impresion":
            self.f.ciclo.reanudar_autorizado = True
            self.f.reanudar_impresion()
            self.telegram.enviar("Reanudé la impresión.")
        else:
            self.telegram.enviar("Anotado.")

    # Microcontrolador ---------------------------------------------------------
    def _micro(self, tipo: str, detalle) -> None:
        if tipo == "etapa":
            self.registro.evento("etapa", detalle)
        elif tipo == "verificar":
            self._verificar(detalle)
        elif tipo == "fin":
            self.registro.cerrar_trabajo(detalle["resultado"], detalle["intentos"], detalle["tiempo_ciclo_s"])
            captura = self.f.ciclo.capturas.get("verificacion")
            if detalle["resultado"] == "retirada":
                texto = M.retirada(detalle["intentos"])
                if captura is not None:
                    self.telegram.enviar_foto(captura.jpeg, texto)
                else:
                    self.telegram.enviar(texto)
            else:
                botones = [[("Reintentar", "retenida:reintentar"), ("Ya la retiré", "retenida:retirada")]]
                self.telegram.enviar_foto(captura.jpeg, M.RETENIDA, botones) if captura is not None \
                    else self.telegram.enviar(M.RETENIDA, botones)
        elif tipo == "falla":
            self.registro.evento("parada", detalle)
            self.telegram.enviar(M.parada(detalle), [[("Reanudar", "parada:reanudar")]])

    def _verificar(self, intento: int) -> None:
        """Etapa 4: captura completa contra la referencia; el orquestador decide."""
        estado = self.impresora.estado()
        self.f.capturar_imagen("verificacion")
        captura = self.f.ciclo.capturas["verificacion"]
        if not self.config.referencia.exists():
            self.esperando_verificacion = intento
            self.telegram.enviar_foto(captura.jpeg, M.SIN_REFERENCIA + " ¿La plataforma quedó libre?",
                                      [[("Sí, está libre", "verif:libre"), ("No, reintentar", "verif:pieza")]])
            return
        v = self.agente.inspeccionar("verificacion", [self.camara_referencia(), captura], estado)
        self._registrar_captura(f"verificacion, intento {intento}", f"{captura.ancho}x{captura.alto}", captura, v)
        umbral = self.config.umbral_confianza
        if v.valido and v.clase == "libre" and v.confianza >= umbral:
            self.micro.resultado_verificacion(True)
        elif v.valido and v.clase == "libre":
            # Libre con confianza baja: decide el operador, no el modelo.
            self.esperando_verificacion = intento
            self.telegram.enviar_foto(captura.jpeg, M.verificacion_dudosa(v.descripcion, v.confianza, umbral),
                                      [[("Sí, está libre", "verif:libre"), ("No, reintentar", "verif:pieza")]])
        else:
            self.micro.resultado_verificacion(False)

    # Mensajes del operador ----------------------------------------------------
    def _mensaje(self, texto: str) -> None:
        clave = _normalizar(texto)
        orden = next((o for o, palabras in PALABRAS.items() if clave in palabras), None)
        self.registro.evento("mensaje del operador", texto)
        if clave in ("/simular_impresion", "/simular_falla") and hasattr(self.impresora, "iniciar_impresion"):
            # Solo con la impresora simulada: recorre el ciclo completo desde Telegram.
            self.camara.escena = "espagueti" if clave == "/simular_falla" else "pieza_presente"
            self.impresora.iniciar_impresion("pieza_prueba.3mf")
            self.telegram.enviar("Inicié una impresión simulada de 20 minutos (dura unos 20 s).")
            return
        if orden == "ayuda":
            self.telegram.enviar(M.AYUDA)
        elif orden == "estado":
            self.telegram.enviar(M.estado(self.f.consultar_estado()))
        elif orden == "foto":
            r = self.f.capturar_imagen("verificacion")
            self.telegram.enviar_foto(self.f.ciclo.ultima_captura.jpeg,
                                      f"Captura de {r['ancho']} x {r['alto']} píxeles ({r['origen']}).")
        elif orden == "pausa":
            r = self.impresora.pausar()
            self._intervencion("pausar", None)
            self.telegram.enviar("Pausé la impresión a tu pedido." if r.get("aceptada", True)
                                 else "La impresora rechazó la pausa: revisa el modo desarrollador.")
        elif orden == "reanudar":
            self._intervencion("reanudar", None)
            self.f.ciclo.reanudar_autorizado = True
            r = self.f.reanudar_impresion()
            self.recordatorio = None
            self.telegram.enviar("Reanudé la impresión." if r.get("reanudada")
                                 else "La impresora rechazó la reanudación: revisa el modo desarrollador.")
        elif orden == "luz":
            encender = not self.impresora.luz_encendida
            self.impresora.luz(encender)
            self.telegram.enviar("Luz encendida." if encender else "Luz apagada.")
        elif orden == "referencia":
            if self.impresora.estado()["fase"] in EN_CURSO:
                self.telegram.enviar(M.REFERENCIA_EN_IMPRESION)
                return
            self.f.capturar_imagen("verificacion")
            captura = self.f.ciclo.ultima_captura
            self.config.referencia.write_bytes(captura.jpeg)
            self.registro.evento("referencia", str(self.config.referencia))
            self.telegram.enviar_foto(captura.jpeg, f"Guardé la referencia de la plataforma vacía "
                                                    f"({captura.ancho} x {captura.alto}).")
        elif orden == "detener":
            self.telegram.enviar(M.CONFIRMAR_DETENER, [[("Sí, detener", "detener:si"), ("No", "detener:no")]])
        else:
            contexto = (f"Estado actual: {self.f.consultar_estado()}\n"
                        f"Ultimos eventos: {self.registro.ultimos_eventos()}")
            try:
                respuesta = self.agente.conversar(texto, contexto)
            except Exception as error:
                log.warning("Conversacion fallida: %s", error)
                respuesta = "No pude consultar al agente ahora. Las órdenes de rutina siguen disponibles: /ayuda."
            self.telegram.enviar(respuesta)
