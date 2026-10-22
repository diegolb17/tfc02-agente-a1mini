"""Puebla el panel de Cloudflare con ciclos simulados completos.

Recorre tres escenarios de prueba_simulacion.py con el envio al panel activo:
una impresion con confirmacion del operador (umbral 1.0), otra con falla,
pausa y cancelacion, y una tercera con un objeto ajeno sobre la plataforma.
Los datos quedan rotulados como simulados por el nombre de cada archivo.

  python pruebas/poblar_panel.py
"""
import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "pruebas"))

from orquestador.config import leer_config     # noqa: E402
from prueba_simulacion import ESCENARIOS, ESPERADO, escenario     # noqa: E402

NOMBRES = {"A_umbral_maximo": "simulacion_confirmacion", "B_falla_y_reintento": "simulacion_falla_pausa",
           "D_objeto_ajeno": "simulacion_objeto_ajeno"}


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    config = leer_config()
    if not (config.panel_url and config.panel_clave):
        sys.exit("Faltan PANEL_URL y PANEL_CLAVE en .env")
    for nombre, umbral, escena, intentos, decisiones, mensajes, _ in ESCENARIOS:
        if nombre not in NOMBRES:
            continue
        r = escenario(NOMBRES[nombre], umbral, escena, intentos, decisiones, mensajes,
                      sin_ciclo=ESPERADO[nombre][0] is None,
                      panel_url=config.panel_url, panel_clave=config.panel_clave)
        print(nombre, r["trabajos"], f"{len(r['capturas'])} capturas, {len(r['intervenciones'])} intervenciones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
