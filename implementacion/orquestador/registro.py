"""Registro local en SQLite (seccion 5.5.3).

Cada evento se escribe aqui antes de hacer nada mas con el. Las tablas siguen
la Tabla 22 de la tesis; cada fila lleva un identificador unico creado en la
unidad de procesamiento y la marca de envio al panel, para que un reenvio no
duplique filas cuando el panel de Cloudflare este en marcha.
"""
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS trabajos (
  id TEXT PRIMARY KEY, archivo TEXT, inicio REAL, fin REAL, resultado TEXT,
  intentos INTEGER DEFAULT 0, tiempo_ciclo_s REAL, enviado INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS eventos (
  id TEXT PRIMARY KEY, instante REAL, trabajo TEXT, tipo TEXT, detalle TEXT,
  enviado INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS capturas (
  id TEXT PRIMARY KEY, instante REAL, trabajo TEXT, tipo TEXT, resolucion TEXT,
  veredicto TEXT, confianza REAL, descripcion TEXT, tokens INTEGER, archivo TEXT,
  enviado INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS intervenciones (
  id TEXT PRIMARY KEY, instante REAL, trabajo TEXT, accion TEXT,
  tiempo_respuesta_s REAL, enviado INTEGER DEFAULT 0);
"""


class Registro:
    def __init__(self, ruta: Path):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(ruta, check_same_thread=False)
        self.con.executescript(ESQUEMA)
        self._cerrojo = threading.Lock()
        self.trabajo_actual: str | None = None

    def _insertar(self, tabla: str, **campos) -> str:
        campos.setdefault("id", uuid.uuid4().hex)
        columnas = ", ".join(campos)
        marcas = ", ".join("?" for _ in campos)
        with self._cerrojo:
            self.con.execute(f"INSERT INTO {tabla} ({columnas}) VALUES ({marcas})",
                             list(campos.values()))
            self.con.commit()
        return campos["id"]

    def nuevo_trabajo(self, archivo: str | None) -> str:
        self.trabajo_actual = self._insertar("trabajos", archivo=archivo, inicio=time.time())
        return self.trabajo_actual

    def cerrar_trabajo(self, resultado: str, intentos: int = 0, tiempo_ciclo_s: float | None = None):
        if not self.trabajo_actual:
            return
        with self._cerrojo:
            self.con.execute(
                "UPDATE trabajos SET fin=?, resultado=?, intentos=?, tiempo_ciclo_s=?, enviado=0 WHERE id=?",
                (time.time(), resultado, intentos, tiempo_ciclo_s, self.trabajo_actual))
            self.con.commit()

    def evento(self, tipo: str, detalle) -> str:
        if not isinstance(detalle, str):
            detalle = json.dumps(detalle, ensure_ascii=False)
        return self._insertar("eventos", instante=time.time(), trabajo=self.trabajo_actual,
                              tipo=tipo, detalle=detalle)

    def captura(self, tipo: str, resolucion: str, veredicto: str, confianza: float,
                descripcion: str, tokens: int, archivo: str) -> str:
        return self._insertar("capturas", instante=time.time(), trabajo=self.trabajo_actual,
                              tipo=tipo, resolucion=resolucion, veredicto=veredicto,
                              confianza=confianza, descripcion=descripcion, tokens=tokens,
                              archivo=archivo)

    def intervencion(self, accion: str, tiempo_respuesta_s: float | None) -> str:
        return self._insertar("intervenciones", instante=time.time(), trabajo=self.trabajo_actual,
                              accion=accion, tiempo_respuesta_s=tiempo_respuesta_s)

    def ultimos_eventos(self, n: int = 8) -> list[tuple]:
        with self._cerrojo:
            return self.con.execute(
                "SELECT tipo, detalle FROM eventos WHERE trabajo IS ? ORDER BY instante DESC LIMIT ?",
                (self.trabajo_actual, n)).fetchall()[::-1]

    def pendientes_de_envio(self) -> dict[str, int]:
        with self._cerrojo:
            return {t: self.con.execute(f"SELECT COUNT(*) FROM {t} WHERE enviado=0").fetchone()[0]
                    for t in ("trabajos", "eventos", "capturas", "intervenciones")}
