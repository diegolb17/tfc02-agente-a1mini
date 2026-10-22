"""Envio del registro al panel de Cloudflare (secciones 5.5.2 y 5.5.3).

El flujo es siempre saliente. Cada cierto tiempo el orquestador envia las filas
que el panel aun no acepto y sube las capturas a R2; lo que no se pudo enviar
queda marcado como pendiente en el SQLite local y se reintenta en la vuelta
siguiente, de modo que una caida de la red no deja huecos en el historial.
Ademas descarga la configuracion al arrancar y cada 5 minutos.
"""
import logging
import threading
import time
from pathlib import Path

import requests

log = logging.getLogger("panel")
TABLAS = ("trabajos", "eventos", "capturas", "intervenciones")


class Panel:
    def __init__(self, url: str, clave: str, registro, referencia: Path, config=None,
                 periodo: float = 30.0, descargar_config: bool = True):
        self.url = url.rstrip("/")
        self.cabecera = {"Authorization": f"Bearer {clave}"}
        self.registro = registro
        self.referencia = referencia
        self.config = config
        self.periodo = periodo
        self.descargar_config = descargar_config
        self._referencia_enviada = None
        self._ultima_config = 0.0
        self._parar = threading.Event()

    def _subir_imagen(self, clave: str, ruta: Path) -> bool:
        try:
            r = requests.put(f"{self.url}/api/imagen/{clave}", data=ruta.read_bytes(),
                             headers={**self.cabecera, "Content-Type": "image/jpeg"}, timeout=30)
            return r.status_code == 200
        except (OSError, requests.RequestException) as error:
            log.warning("No se subio la imagen %s: %s", clave, error)
            return False

    def sincronizar(self) -> dict:
        """Una vuelta de envio; devuelve cuantas filas acepto el panel por tabla."""
        if self.referencia.exists() and self.referencia.stat().st_mtime != self._referencia_enviada:
            if self._subir_imagen("referencia.jpg", self.referencia):
                self._referencia_enviada = self.referencia.stat().st_mtime
        cuerpo = {}
        for tabla in TABLAS:
            filas = self.registro.pendientes(tabla)
            if tabla == "capturas":
                listas = []
                for fila in filas:
                    clave = f"{fila['id']}.jpg"
                    ruta = Path(fila.get("archivo") or "")
                    # Sin imagen subida, la fila espera a la vuelta siguiente.
                    if ruta.is_file() and not self._subir_imagen(clave, ruta):
                        continue
                    fila["clave_imagen"] = clave if ruta.is_file() else None
                    listas.append(fila)
                filas = listas
            if tabla == "intervenciones":
                for fila in filas:
                    fila["usuario"] = "operador"
            omitir = ("enviado", "archivo") if tabla == "capturas" else ("enviado",)
            cuerpo[tabla] = [{k: v for k, v in f.items() if k not in omitir} for f in filas]
        if not any(cuerpo.values()):
            return {}
        try:
            r = requests.post(f"{self.url}/api/sincronizar", json=cuerpo, headers=self.cabecera, timeout=30)
            r.raise_for_status()
            aceptadas = r.json().get("aceptadas", {})
        except (requests.RequestException, ValueError) as error:
            log.warning("Sincronizacion fallida, las filas quedan pendientes de envio: %s", error)
            return {}
        for tabla, ids in aceptadas.items():
            self.registro.marcar_enviadas(tabla, ids)
        return {t: len(i) for t, i in aceptadas.items()}

    def configuracion(self) -> dict:
        r = requests.get(f"{self.url}/api/configuracion", headers=self.cabecera, timeout=15)
        r.raise_for_status()
        return r.json()

    def aplicar_configuracion(self, telegram=None) -> None:
        """Toma del panel el umbral y el operador autorizado, si son validos."""
        try:
            datos = self.configuracion()
        except (requests.RequestException, ValueError) as error:
            log.warning("No se descargo la configuracion: %s", error)
            return
        try:
            umbral = float(datos.get("umbral_confianza", ""))
            if 0.0 <= umbral <= 1.0 and self.config is not None:
                self.config.umbral_confianza = umbral
        except ValueError:
            pass
        operador = str(datos.get("operador_autorizado", "")).strip()
        if operador.isdigit() and telegram is not None:
            telegram.operador_id = int(operador)

    def escuchar(self, telegram=None) -> None:
        threading.Thread(target=self._bucle, args=(telegram,), daemon=True).start()

    def detener(self) -> None:
        self._parar.set()

    def _bucle(self, telegram) -> None:
        while not self._parar.is_set():
            if self.descargar_config and time.monotonic() - self._ultima_config > 300:
                self._ultima_config = time.monotonic()
                self.aplicar_configuracion(telegram)
            try:
                enviadas = self.sincronizar()
                if enviadas:
                    log.info("Panel: %s", enviadas)
            except Exception:
                log.exception("Error al sincronizar con el panel")
            self._parar.wait(self.periodo)
