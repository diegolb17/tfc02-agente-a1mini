"""Captura de imagen.

En la implementacion parcial se usa la camara integrada de la A1 mini en lugar
de la ESP32-CAM del diseno: el equipo entrega tramas JPEG por TLS en el puerto
6000 cuando esta en modo LAN. El orquestador reduce la imagen segun la consulta
(seccion 5.3.1): 800 por 600 para la supervision y hasta 1 600 por 1 200 para la
verificacion y la confirmacion de una falla.
"""
import io
import math
import socket
import ssl
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

SUPERVISION = (800, 600)
VERIFICACION = (1600, 1200)


def tokens_imagen(ancho: int, alto: int) -> int:
    """Tokens de entrada de una imagen: parches de 32 por 32 a 1.2 tokens cada uno."""
    return round(math.ceil(ancho / 32) * math.ceil(alto / 32) * 1.2)


@dataclass
class Captura:
    jpeg: bytes
    ancho: int
    alto: int
    origen: str
    instante: float = field(default_factory=time.time)
    etiqueta: str = ""      # solo en simulacion: que muestra la imagen de prueba
    ruta: Path | None = None

    @property
    def tokens(self) -> int:
        return tokens_imagen(self.ancho, self.alto)

    def reducida(self, limite: tuple[int, int]) -> "Captura":
        """Copia reducida que cabe en el limite, sin deformar la imagen."""
        imagen = Image.open(io.BytesIO(self.jpeg)).convert("RGB")
        imagen.thumbnail(limite, Image.LANCZOS)
        salida = io.BytesIO()
        imagen.save(salida, "JPEG", quality=85)
        return Captura(salida.getvalue(), imagen.width, imagen.height, self.origen,
                       self.instante, self.etiqueta)

    def guardar(self, carpeta: Path, nombre: str) -> Path:
        carpeta.mkdir(parents=True, exist_ok=True)
        self.ruta = carpeta / nombre
        self.ruta.write_bytes(self.jpeg)
        return self.ruta


def _desde_bytes(jpeg: bytes, origen: str, etiqueta: str = "") -> Captura:
    imagen = Image.open(io.BytesIO(jpeg))
    return Captura(jpeg, imagen.width, imagen.height, origen, etiqueta=etiqueta)


class CamaraA1:
    """Camara integrada de la A1 mini por el puerto 6000."""

    def __init__(self, ip: str, codigo_acceso: str, espera: float = 10.0):
        self.ip, self.codigo, self.espera = ip, codigo_acceso, espera

    def _paquete_autenticacion(self) -> bytes:
        # 0x40 y 0x3000 en little endian, dos ceros, usuario y codigo de 32 bytes.
        return (struct.pack("<IIII", 0x40, 0x3000, 0, 0)
                + b"bblp".ljust(32, b"\0")
                + self.codigo.encode("ascii").ljust(32, b"\0"))

    @staticmethod
    def _leer(conexion, n: int) -> bytes:
        datos = bytearray()
        while len(datos) < n:
            trozo = conexion.recv(n - len(datos))
            if not trozo:
                raise ConnectionError("La camara cerro la conexion")
            datos.extend(trozo)
        return bytes(datos)

    def capturar(self) -> Captura:
        contexto = ssl.create_default_context()
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
        with socket.create_connection((self.ip, 6000), timeout=self.espera) as base:
            with contexto.wrap_socket(base, server_hostname=self.ip) as conexion:
                conexion.sendall(self._paquete_autenticacion())
                # Cada trama: cabecera de 16 bytes cuyo primer entero es el tamano.
                for _ in range(5):
                    cabecera = self._leer(conexion, 16)
                    tamano = struct.unpack("<I", cabecera[:4])[0]
                    if not 0 < tamano < 10_000_000:
                        raise ValueError(f"Cabecera de trama invalida: {cabecera.hex()}")
                    jpeg = self._leer(conexion, tamano)
                    if jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9":
                        return _desde_bytes(jpeg, "camara A1 mini")
        raise ValueError("No llego una trama JPEG completa")


class CamaraSimulada:
    """Devuelve imagenes de prueba segun el escenario que fija la simulacion."""

    def __init__(self, carpeta: Path):
        self.carpeta = carpeta
        self.escena = "plataforma_vacia"

    def capturar(self) -> Captura:
        ruta = self.carpeta / f"{self.escena}.jpg"
        return _desde_bytes(ruta.read_bytes(), "imagen de prueba", etiqueta=self.escena)
