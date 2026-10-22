"""Microcontrolador simulado.

En el diseno, la secuencia de remocion la ejecuta la ESP32 (Figura 31 de la
tesis) y recibe las ordenes por UART. La implementacion parcial no tiene ese
hardware, de modo que esta clase reproduce el pseudocodigo con los mismos
tiempos maximos para que el orquestador pueda probar su parte del ciclo:
precondiciones, avisos, verificacion con el agente y hasta tres intentos.
"""
import threading
import time

T_SALIDA = 38.7            # grados, fin del enfriamiento (tesis, 4.2)
T_MAX_ENFRIAMIENTO = 360   # 6 min
T_FLEXION = 6.9            # s, carrera de 35 mm del L12-P (maximo 12 s)
T_EVACUACION = 30.0        # s, barrido a tres cotas (maximo 60 s)
INTENTOS = 3


class MicrocontroladorSimulado:
    def __init__(self, impresora, al_evento, escala: float = 60.0, fallas: dict | None = None):
        self.impresora = impresora
        self.al_evento = al_evento          # f(tipo, detalle)
        self.escala = escala
        self.fallas = fallas or {}          # p. ej. {"ventilador": True} para probar fallas
        self.estado = "REPOSO"
        self.boton_emergencia_liberado = True
        self._resultado = threading.Event()
        self._libre = False
        self._hilo = None
        self.al_evacuar = None              # solo en la simulacion en vivo: cambia la escena
        self.espera_verificacion = 120.0   # s reales; si decide el operador, el orquestador la amplia

    def _dormir(self, segundos: float) -> None:
        time.sleep(segundos / self.escala)

    def iniciar(self) -> bool:
        """Orden INICIAR; el microcontrolador comprueba sus propias precondiciones."""
        if self.estado not in ("REPOSO", "PARADA_ATENDIDA"):
            return False
        if not self.boton_emergencia_liberado:
            self.al_evento("falla", "PARADA_DE_EMERGENCIA")
            return False
        self._hilo = threading.Thread(target=self._ciclo, daemon=True)
        self._hilo.start()
        return True

    def resultado_verificacion(self, libre: bool) -> None:
        self._libre = libre
        self._resultado.set()

    def reanudar(self) -> None:
        if self.estado == "PARADA":
            self.estado = "PARADA_ATENDIDA"

    def _falla(self, tipo: str) -> None:
        self.estado = "PARADA"
        self.al_evento("falla", tipo)

    def _ciclo(self) -> None:
        inicio = time.monotonic()
        self.estado = "ENFRIAMIENTO"
        self.al_evento("etapa", "1 enfriamiento: ventilador al 100 %")
        if self.fallas.get("ventilador"):
            self._dormir(5)
            return self._falla("VENTILADOR_DETENIDO")
        t = 0.0
        while (self.impresora.estado().get("temp_plataforma") or 0) > T_SALIDA and t < T_MAX_ENFRIAMIENTO:
            self._dormir(20)
            t += 20
            if hasattr(self.impresora, "enfriar_forzado"):
                self.impresora.enfriar_forzado()
        temperatura = self.impresora.estado().get("temp_plataforma")
        if temperatura is not None and temperatura > T_SALIDA:
            return self._falla("ENFRIAMIENTO_SIN_EFECTO")
        self.al_evento("etapa", f"enfriamiento terminado a {temperatura} grados en {t / 60:.1f} min")
        for intento in range(1, INTENTOS + 1):
            self.estado = "FLEXION"
            self.al_evento("etapa", f"2 flexion, intento {intento}: actuador a 35 mm")
            self._dormir(T_FLEXION)
            self.estado = "EVACUACION"
            self.al_evento("etapa", "3 evacuacion: retraccion y barrido del cabezal a tres cotas")
            if self.al_evacuar:
                self.al_evacuar()
            self._dormir(T_EVACUACION)
            self.estado = "VERIFICACION"
            self._resultado.clear()
            self.al_evento("verificar", intento)
            if not self._resultado.wait(timeout=self.espera_verificacion):
                return self._falla("VERIFICACION_SIN_RESPUESTA")
            if self._libre:
                self.estado = "REPOSO"
                self.al_evento("fin", {"resultado": "retirada", "intentos": intento,
                                       "tiempo_ciclo_s": round((time.monotonic() - inicio) * self.escala)})
                return
        self.estado = "REPOSO"
        self.al_evento("fin", {"resultado": "retenida", "intentos": INTENTOS,
                               "tiempo_ciclo_s": round((time.monotonic() - inicio) * self.escala)})
