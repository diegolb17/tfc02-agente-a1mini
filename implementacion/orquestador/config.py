"""Configuracion del orquestador.

Se lee de IMPLEMENTACION/.env (que nunca se sube al repositorio) y de las
variables de entorno. Los valores por defecto siguen el capitulo 5 de la tesis.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ENV = RAIZ / ".env"


def cargar_env(ruta: Path = RUTA_ENV) -> None:
    """Carga pares CLAVE=valor sin pisar variables ya definidas en el entorno."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def guardar_en_env(clave: str, valor: str, ruta: Path = RUTA_ENV) -> None:
    """Escribe o reemplaza una clave en .env (se usa al registrar al operador)."""
    lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    nuevas, hallada = [], False
    for linea in lineas:
        if linea.split("=", 1)[0].strip() == clave:
            nuevas.append(f"{clave}={valor}")
            hallada = True
        else:
            nuevas.append(linea)
    if not hallada:
        nuevas.append(f"{clave}={valor}")
    ruta.write_text("\n".join(nuevas) + "\n", encoding="utf-8")
    os.environ[clave] = valor


def _entero(nombre: str):
    valor = os.environ.get(nombre, "").strip()
    return int(valor) if valor else None


def _real(nombre: str, defecto: float) -> float:
    valor = os.environ.get(nombre, "").strip()
    return float(valor) if valor else defecto


@dataclass
class Config:
    # Telegram (seccion 5.5.1): el bot atiende solo al operador autorizado.
    telegram_token: str = ""
    operador_id: int | None = None
    # Impresora en modo LAN y modo desarrollador (seccion 5.1.5).
    impresora_ip: str = ""
    serie: str = ""
    codigo_acceso: str = ""
    # Modelo adoptado en la seccion 5.3.1.
    modelo: str = "gpt-5.4-mini"
    # El umbral arranca al maximo hasta fijarlo con el conjunto de prueba:
    # con 1.0 el sistema pide siempre la confirmacion del operador (R-SEG-01).
    umbral_confianza: float = 1.0
    # Confianza minima para tomar en serio una falla y pedir la segunda consulta.
    umbral_falla: float = 0.5
    # Tiempos de la tesis, en segundos.
    periodo_supervision: float = 600.0     # captura cada 10 min
    plazo_confirmacion: float = 1800.0     # espera del operador, 30 min
    recordatorio_pausa: float = 900.0      # recordatorio cada 15 min
    # Panel de Cloudflare (seccion 5.5.2); vacio hasta autorizarlo.
    panel_url: str = ""
    panel_clave: str = ""
    carpeta_datos: Path = field(default_factory=lambda: RAIZ / "datos")
    referencia: Path = field(default_factory=lambda: RAIZ / "datos" / "referencia_plataforma_vacia.jpg")

    @property
    def impresora_configurada(self) -> bool:
        return bool(self.impresora_ip and self.serie and self.codigo_acceso)


def leer_config() -> Config:
    cargar_env()
    return Config(
        telegram_token=os.environ.get("TELEGRAM_TOKEN", ""),
        operador_id=_entero("TELEGRAM_OPERADOR_ID"),
        impresora_ip=os.environ.get("IMPRESORA_IP", ""),
        serie=os.environ.get("IMPRESORA_SERIE", ""),
        codigo_acceso=os.environ.get("IMPRESORA_CODIGO_ACCESO", ""),
        modelo=os.environ.get("MODELO", "gpt-5.4-mini"),
        umbral_confianza=_real("UMBRAL_CONFIANZA", 1.0),
        umbral_falla=_real("UMBRAL_FALLA", 0.5),
        periodo_supervision=_real("PERIODO_SUPERVISION_S", 600.0),
        plazo_confirmacion=_real("PLAZO_CONFIRMACION_S", 1800.0),
        recordatorio_pausa=_real("RECORDATORIO_PAUSA_S", 900.0),
        panel_url=os.environ.get("PANEL_URL", ""),
        panel_clave=os.environ.get("PANEL_CLAVE", ""),
    )
