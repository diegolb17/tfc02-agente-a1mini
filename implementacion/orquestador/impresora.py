"""Comunicacion con la Bambu Lab A1 mini por MQTT local (seccion 5.1.5).

El equipo publica su estado en device/{serie}/report y recibe instrucciones en
device/{serie}/request, sobre TLS en el puerto 8883, con el usuario bblp y el
codigo de acceso del modo LAN como contrasena. La A1 mini envia el estado por
partes, por eso el cliente funde cada mensaje sobre el ultimo estado conocido.

Las ordenes de pausa, reanudacion y detencion exigen el modo desarrollador
desde el firmware 01.05.00.00; la lectura de estado y la luz no (tesis, 5.1.5).
Referencias: OpenBambuAPI y TFC01/Proyecto/bambumcp/bambu-mcp.
"""
import json
import logging
import ssl
import threading
import time

log = logging.getLogger("impresora")

# Estados de gcode_state que informa el equipo.
EN_CURSO = {"PREPARE", "RUNNING", "SLICING"}
TERMINADA = "FINISH"
EN_PAUSA = "PAUSE"


class ImpresoraBase:
    """Interfaz comun de la impresora real y de la simulada."""

    def __init__(self):
        self._estado: dict = {}
        self._cerrojo = threading.Lock()
        self._al_cambiar = []          # funciones f(nuevo, anterior)
        self.luz_encendida = False
        self.luz_reportada = None          # lo que dice el propio equipo en lights_report
        self.instante_luz = 0.0
        self.ultimo_reporte: dict = {}     # ultimo mensaje de estado tal como llego
        self.instante_reporte = 0.0
        self.ultima_respuesta: dict = {}

    def al_cambiar_estado(self, funcion) -> None:
        self._al_cambiar.append(funcion)

    def estado(self) -> dict:
        with self._cerrojo:
            e = dict(self._estado)
        return {
            "fase": e.get("gcode_state", "DESCONOCIDO"),
            "avance_pct": e.get("mc_percent"),
            "minutos_restantes": e.get("mc_remaining_time"),
            "temp_plataforma": e.get("bed_temper"),
            "temp_boquilla": e.get("nozzle_temper"),
            "archivo": e.get("subtask_name") or e.get("gcode_file"),
            "capa": e.get("layer_num"),
            "capas_totales": e.get("total_layer_num"),
            "luz": "encendida" if self.luz_encendida else "apagada",
        }

    def _fundir(self, parcial: dict) -> None:
        with self._cerrojo:
            anterior = self._estado.get("gcode_state")
            self._estado.update(parcial)
            nuevo = self._estado.get("gcode_state")
        if "lights_report" in parcial:
            for luz in parcial["lights_report"]:
                if luz.get("node") == "chamber_light":
                    self.luz_encendida = self.luz_reportada = luz.get("mode") == "on"
                    self.instante_luz = time.time()
        if nuevo and nuevo != anterior:
            for funcion in self._al_cambiar:
                funcion(nuevo, anterior)

    # Ordenes; cada implementacion las envia a su manera.
    def pedir_estado(self): raise NotImplementedError
    def pausar(self): raise NotImplementedError
    def reanudar(self): raise NotImplementedError
    def detener(self): raise NotImplementedError
    def luz(self, encender: bool): raise NotImplementedError
    def cerrar(self): pass


class ImpresoraMQTT(ImpresoraBase):
    """Cliente MQTT real de la A1 mini."""

    def __init__(self, ip: str, serie: str, codigo_acceso: str):
        super().__init__()
        import paho.mqtt.client as mqtt

        self.ip, self.serie = ip, serie
        self._secuencia = 0
        self._respuestas: dict[str, dict] = {}
        self._evento_respuesta = threading.Condition()
        self.conectada = threading.Event()
        self.cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"tfc02-orquestador-{int(time.time())}",
        )
        self.cliente.username_pw_set("bblp", codigo_acceso)
        # El equipo usa un certificado propio: se cifra sin verificarlo.
        self.cliente.tls_set(cert_reqs=ssl.CERT_NONE)
        self.cliente.tls_insecure_set(True)
        self.cliente.on_connect = self._conectado
        self.cliente.on_message = self._mensaje
        self.cliente.on_disconnect = lambda *a: (self.conectada.clear(), log.warning("MQTT desconectado"))

    def conectar(self, espera: float = 10.0) -> bool:
        self.cliente.connect(self.ip, 8883, keepalive=60)
        self.cliente.loop_start()
        if not self.conectada.wait(espera):
            raise ConnectionError(f"Sin respuesta MQTT de {self.ip}:8883 en {espera:.0f} s")
        self.pedir_estado()
        self.pedir_version()
        return True

    def _conectado(self, cliente, _datos, _banderas, codigo, _propiedades=None):
        if codigo != 0:
            log.error("Conexion MQTT rechazada: %s (revisa el codigo de acceso)", codigo)
            return
        cliente.subscribe(f"device/{self.serie}/report")
        self.conectada.set()
        log.info("Conectado a la impresora %s", self.ip)

    def _mensaje(self, _cliente, _datos, mensaje):
        try:
            datos = json.loads(mensaje.payload)
        except ValueError:
            return
        for seccion in ("print", "system", "info", "pushing"):
            parte = datos.get(seccion)
            if not isinstance(parte, dict):
                continue
            if seccion == "print":
                self.ultimo_reporte, self.instante_reporte = dict(parte), time.time()
                self._fundir(parte)
            if seccion == "info" and parte.get("command") == "get_version":
                self.version = {m.get("name"): m.get("sw_ver") for m in parte.get("module", [])}
            secuencia = str(parte.get("sequence_id", ""))
            if secuencia and parte.get("command") not in (None, "push_status"):
                with self._evento_respuesta:
                    self._respuestas[secuencia] = parte
                    self.ultima_respuesta = parte
                    self._evento_respuesta.notify_all()

    def _enviar(self, seccion: str, orden: str, espera: float = 5.0, **extra) -> dict:
        self._secuencia += 1
        secuencia = str(self._secuencia)
        carga = {seccion: {"sequence_id": secuencia, "command": orden, **extra}}
        self.cliente.publish(f"device/{self.serie}/request", json.dumps(carga))
        if espera <= 0:
            return {"enviado": True}
        fin = time.monotonic() + espera
        with self._evento_respuesta:
            while secuencia not in self._respuestas:
                restante = fin - time.monotonic()
                if restante <= 0:
                    return {"enviado": True, "respuesta": None}
                self._evento_respuesta.wait(restante)
            respuesta = self._respuestas.pop(secuencia)
        # Sin modo desarrollador la orden vuelve con result distinto de success.
        return {"enviado": True, "respuesta": respuesta,
                "aceptada": str(respuesta.get("result", "")).lower() in ("", "success", "ok")}

    def pedir_estado(self):
        # OpenBambuAPI recomienda no pedir el estado completo mas de una vez cada 5 min.
        return self._enviar("pushing", "pushall", espera=0, version=1, push_target=1)

    def pedir_version(self):
        return self._enviar("info", "get_version", espera=3)

    def pausar(self):
        return self._enviar("print", "pause", param="")

    def reanudar(self):
        return self._enviar("print", "resume", param="")

    def detener(self):
        return self._enviar("print", "stop", param="")

    def luz(self, encender: bool):
        r = self._enviar("system", "ledctrl", led_node="chamber_light",
                         led_mode="on" if encender else "off",
                         led_on_time=500, led_off_time=500, loop_times=0, interval_time=0)
        self.luz_encendida = encender
        return r

    def cerrar(self):
        self.cliente.loop_stop()
        self.cliente.disconnect()


class ImpresoraSimulada(ImpresoraBase):
    """Impresora simulada para probar el flujo sin el equipo.

    Recorre IDLE, PREPARE, RUNNING y FINISH; la plataforma calienta a 65 grados
    durante la impresion y se enfria despues. La escala de tiempo acelera la
    simulacion: con escala 60, un minuto simulado dura un segundo.
    """

    def __init__(self, duracion_min: float = 20.0, escala: float = 60.0):
        super().__init__()
        self.duracion_min = duracion_min
        self.escala = escala
        self._inicio = None
        self._pausada_desde = None
        self._pausa_acumulada = 0.0
        self.version = {"ota": "01.05.00.00 (simulada)"}
        self._fundir({"gcode_state": "IDLE", "bed_temper": 26.0, "nozzle_temper": 25.0,
                      "mc_percent": 0, "mc_remaining_time": 0})

    def iniciar_impresion(self, archivo: str = "pieza_prueba.3mf") -> None:
        self._inicio = time.monotonic()
        self._pausa_acumulada = 0.0
        self._fundir({"gcode_state": "PREPARE", "subtask_name": archivo, "mc_percent": 0,
                      "total_layer_num": 120, "layer_num": 0})

    def minutos_transcurridos(self) -> float:
        if self._inicio is None:
            return 0.0
        ahora = self._pausada_desde or time.monotonic()
        return (ahora - self._inicio - self._pausa_acumulada) * self.escala / 60.0

    def avanzar(self) -> None:
        """Actualiza el estado simulado; el orquestador lo llama en su bucle."""
        fase = self._estado.get("gcode_state")
        if fase in ("PREPARE", "RUNNING"):
            m = self.minutos_transcurridos()
            if fase == "PREPARE" and m >= 1.0:
                self._fundir({"gcode_state": "RUNNING"})
            avance = min(100, int(100 * m / self.duracion_min))
            self._fundir({"mc_percent": avance, "layer_num": int(1.2 * avance),
                          "mc_remaining_time": max(0, round(self.duracion_min - m)),
                          "bed_temper": 65.0, "nozzle_temper": 220.0})
            if avance >= 100:
                self._fin = time.monotonic()
                self._fundir({"gcode_state": TERMINADA, "nozzle_temper": 60.0})
        elif fase in (TERMINADA, "FAILED") and self._estado.get("bed_temper", 26) > 26:
            # Enfriamiento natural aproximado: unos 10 minutos de 65 a 38.7 grados.
            m = (time.monotonic() - self._fin) * self.escala / 60.0
            natural = round(26 + 39 * 0.9 ** m, 1)
            self._fundir({"bed_temper": min(self._estado["bed_temper"], natural)})

    def enfriar_forzado(self) -> None:
        """Lo usa el microcontrolador simulado cada 20 s: con el ventilador la
        plataforma baja unos 9 grados por minuto, 2.9 min de 65 a 38.7 (tesis, 4.2)."""
        t = self._estado.get("bed_temper", 26.0)
        self._fundir({"bed_temper": round(max(26.0, t - 3.0), 1)})

    def pedir_estado(self):
        return {"enviado": True}

    def pausar(self):
        if self._estado.get("gcode_state") in EN_CURSO:
            self._pausada_desde = time.monotonic()
            self._fundir({"gcode_state": EN_PAUSA})
        return {"enviado": True, "aceptada": True}

    def reanudar(self):
        if self._estado.get("gcode_state") == EN_PAUSA:
            self._pausa_acumulada += time.monotonic() - self._pausada_desde
            self._pausada_desde = None
            self._fundir({"gcode_state": "RUNNING"})
        return {"enviado": True, "aceptada": True}

    def detener(self):
        self._pausada_desde = None
        self._fin = time.monotonic()
        self._fundir({"gcode_state": "FAILED"})
        return {"enviado": True, "aceptada": True}

    def luz(self, encender: bool):
        self.luz_encendida = encender
        return {"enviado": True, "aceptada": True}
