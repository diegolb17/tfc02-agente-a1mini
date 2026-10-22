"""Capturas de pantalla de cada pagina del panel, con Edge sin interfaz (Playwright).

Ingresa con PANEL_USUARIO y PANEL_CONTRASENA de .env y guarda las imagenes en
TESIS_LATEX/Imagenes/capturas/panel_*.png.

  python pruebas/capturas_panel.py
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from orquestador.config import leer_config     # noqa: E402

DESTINO = RAIZ.parent / "TESIS_LATEX" / "Imagenes" / "capturas"
PAGINAS = [("resumen", "/"), ("historial", "/historial"), ("intervenciones", "/intervenciones"),
           ("metricas", "/metricas"), ("imagenes", "/imagenes"), ("configuracion", "/configuracion")]


def main() -> int:
    config = leer_config()
    DESTINO.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="msedge", headless=True)
        contexto = navegador.new_context(viewport={"width": 1280, "height": 860}, device_scale_factor=1.5,
                                         locale="es-PE", timezone_id="America/Lima")
        pagina = contexto.new_page()
        pagina.goto(config.panel_url + "/login")
        pagina.screenshot(path=str(DESTINO / "panel_ingreso.png"))
        pagina.fill("input[name=usuario]", os.environ["PANEL_USUARIO"])
        pagina.fill("input[name=contrasena]", os.environ["PANEL_CONTRASENA"])
        pagina.click("button[type=submit]")
        pagina.wait_for_url(config.panel_url + "/")
        generadas = ["panel_ingreso.png"]
        for nombre, ruta in PAGINAS:
            pagina.goto(config.panel_url + ruta)
            pagina.wait_for_load_state("networkidle")
            archivo = f"panel_{nombre}.png"
            pagina.screenshot(path=str(DESTINO / archivo), full_page=True)
            generadas.append(archivo)
        # La pagina se adapta al telefono (tesis, 5.5.2).
        movil = navegador.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                      storage_state=contexto.storage_state(), locale="es-PE",
                                      timezone_id="America/Lima")
        pm = movil.new_page()
        pm.goto(config.panel_url + "/")
        pm.wait_for_load_state("networkidle")
        pm.screenshot(path=str(DESTINO / "panel_resumen_movil.png"), full_page=True)
        generadas.append("panel_resumen_movil.png")
        navegador.close()
    for g in generadas:
        print(DESTINO / g)
    return 0


if __name__ == "__main__":
    sys.exit(main())
