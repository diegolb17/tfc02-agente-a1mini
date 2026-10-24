"""Arma el repositorio publicable a partir de las carpetas de trabajo de TFC02.

Copia solo codigo y fuentes: la implementacion parcial, los guiones de calculo,
los generadores de planos, el proyecto electronico y las fuentes de los
diagramas. No copia el texto de la tesis, sus PDF, IDEA.md ni archivos con
claves, y termina con un escaneo de secretos que falla si encuentra alguno.

  python armar_repositorio.py          copia y escanea
  python armar_repositorio.py --solo-escanear
"""
import re
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TFC02 = AQUI.parent

IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "datos", "datos_simulacion",
                                 "*.log", "*.sqlite", "logs", "_respaldo*", "node_modules", ".wrangler",
                                 ".dev.vars", "capturas_reales", "camara_real*", "calibracion")

# destino: (origen, patrones de archivos; None copia la carpeta completa)
COPIAS = {
    "implementacion": (TFC02 / "IMPLEMENTACION", None),
    "calculos": (TFC02 / "TESIS_LATEX" / "_conversion", ["calculos_*.py", "calculos_*.json"]),
    "planos": (TFC02 / "PLANOS", ["[!_]*.py"]),
    "planos/motor": (TFC02 / "PLANOS" / "motor", None),
    "planos/fusion": (TFC02 / "FUSION MCP", ["fusion_cli.py", "_exportar_geometria.py"]),
    "electronica": (TFC02 / "ELECTRONICA", ["[!_]*.py", "DECISIONES.md", "cotizacion_*.md"]),
    "electronica/TFC_Remocion": (TFC02 / "ELECTRONICA" / "TFC_Remocion", None),
    "diagramas": (TFC02 / "DIAGRAMAS" / "validacion", ["*_tikz.tex", "estilo_diagramas.tex"]),
}

SECRETOS = [
    (r"ghp_[A-Za-z0-9]{20,}", "token de GitHub"),
    (r"github_pat_[A-Za-z0-9_]{20,}", "token de GitHub de grano fino"),
    (r"\bsk-[A-Za-z0-9_\-]{20,}", "clave de OpenAI"),
    (r"\bfc-[a-f0-9]{24,}", "clave de Firecrawl"),
    (r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,}", "token de bot de Telegram"),
    (r"(?i)api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{12,}", "api_key con valor"),
    (r"\bKIE\b", "referencia a KIE"),
    # Partido en dos literales para que el propio guion no contenga el usuario.
    (r"(?i)diego" r"luba17", "correo o usuario personal de Diego"),
]


def copiar() -> None:
    for destino, (origen, patrones) in COPIAS.items():
        objetivo = AQUI / destino
        if patrones is None:
            if objetivo.exists():
                shutil.rmtree(objetivo)
            shutil.copytree(origen, objetivo, ignore=IGNORAR)
        else:
            objetivo.mkdir(parents=True, exist_ok=True)
            for viejo in objetivo.glob("*"):
                if viejo.is_file():
                    viejo.unlink()
            for patron in patrones:
                for archivo in origen.glob(patron):
                    if archivo.is_file():
                        shutil.copy2(archivo, objetivo / archivo.name)
        print(f"{destino}: {sum(1 for p in objetivo.rglob('*') if p.is_file())} archivos")


def valores_sensibles() -> dict[str, str]:
    """Valores reales de .env que nunca pueden aparecer en el repositorio publico."""
    claves = ("TELEGRAM_TOKEN", "TELEGRAM_OPERADOR_ID", "IMPRESORA_IP", "IMPRESORA_SERIE", "IMPRESORA_CODIGO_ACCESO",
              "OPENAI_API_KEY", "PANEL_CLAVE", "PANEL_CONTRASENA")
    env = TFC02 / "IMPLEMENTACION" / ".env"
    valores = {}
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.startswith("#"):
                k, v = linea.split("=", 1)
                if k.strip() in claves and len(v.strip()) >= 6:
                    valores[k.strip()] = v.strip()
    return valores


def escanear() -> list[str]:
    hallazgos = []
    sensibles = valores_sensibles()
    for archivo in AQUI.rglob("*"):
        if not archivo.is_file() or ".git" in archivo.parts or archivo.name == "armar_repositorio.py":
            continue
        try:
            texto = archivo.read_text(encoding="utf-8", errors="ignore")
            crudo = archivo.read_bytes()
        except OSError:
            continue
        for nombre, valor in sensibles.items():
            if valor.encode() in crudo:
                hallazgos.append(f"{archivo.relative_to(AQUI)}: valor de {nombre} de .env")
        for patron, nombre in SECRETOS:
            for m in re.finditer(patron, texto):
                hallazgos.append(f"{archivo.relative_to(AQUI)}: {nombre} ({m.group(0)[:12]}...)")
    nombres_prohibidos = [p for p in AQUI.rglob("*") if p.name in (".env", "IDEA.md", ".dev.vars") or
                          (p.suffix == ".pdf" and p.stem.lower().startswith("tesis"))]
    hallazgos += [f"{p.relative_to(AQUI)}: archivo prohibido" for p in nombres_prohibidos
                  if ".git" not in p.parts]
    return hallazgos


if __name__ == "__main__":
    if "--solo-escanear" not in sys.argv:
        copiar()
    hallazgos = escanear()
    if hallazgos:
        print("SECRETOS O ARCHIVOS PROHIBIDOS, no subir:")
        print("\n".join(hallazgos))
        sys.exit(1)
    print("Escaneo de secretos limpio.")
