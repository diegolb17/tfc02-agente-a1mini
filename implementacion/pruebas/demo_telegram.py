"""Conversacion tipo hacia el chat del operador, para las capturas de la tesis.

Telegram real; impresora, camara y modelo simulados; el envio al panel activo.
Recorre dos impresiones: una con falla (supervision, foto, pausa con botones y
remocion de la pieza fallida) y otra normal (fin de impresion con confirmacion,
remocion y verificacion). El operador responde con los botones en su telefono.

  python pruebas/demo_telegram.py
"""
import logging
import sqlite3
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador.config import leer_config     # noqa: E402
from orquestador.principal import construir     # noqa: E402

AVISO = ("Simulación de prueba para la tesis. La impresora, la cámara y el modelo son simulados; "
         "los mensajes y los botones son los reales del sistema. Verás dos impresiones de unos 20 s: "
         "la primera con una falla y la segunda normal. Responde con los botones cuando aparezcan.")


def cerrados(ruta: Path) -> int:
    con = sqlite3.connect(ruta)
    n = con.execute("SELECT COUNT(*) FROM trabajos WHERE resultado IS NOT NULL").fetchone()[0]
    con.close()
    return n


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    config = leer_config()
    if config.operador_id is None:
        sys.exit("El operador aun no esta registrado en .env")
    config.carpeta_datos = RAIZ / "datos" / "demo_telegram"
    config.carpeta_datos.mkdir(parents=True, exist_ok=True)
    config.referencia = config.carpeta_datos / "referencia_plataforma_vacia.jpg"
    config.periodo_supervision = 10.0          # 10 min simulados
    config.recordatorio_pausa = 300.0          # sin insistir durante la demostracion
    base = config.carpeta_datos / "registro.sqlite"
    base.unlink(missing_ok=True)
    s = construir(config, simular=True, base_datos=base, descargar_config=False)
    s.micro.al_evacuar = lambda: setattr(s.camara, "escena", "plataforma_vacia")
    hilo = threading.Thread(target=s.orquestador.ejecutar, args=(2400,), daemon=True)
    hilo.start()
    s.telegram.enviar(AVISO)
    time.sleep(2)
    s.camara.escena = "plataforma_vacia"
    s.orquestador.cola.put(("mensaje", "/referencia", time.time()))
    time.sleep(4)
    s.camara.escena = "espagueti"
    s.impresora.iniciar_impresion("pieza_soporte_camara.3mf")
    while hilo.is_alive() and cerrados(base) < 1:
        time.sleep(1)
    time.sleep(5)
    s.camara.escena = "pieza_presente"
    s.impresora.iniciar_impresion("pieza_bandeja_frontal.3mf")
    while hilo.is_alive() and cerrados(base) < 2:
        time.sleep(1)
    time.sleep(3)
    s.telegram.enviar("Fin de la simulación de prueba. Gracias.")
    s.orquestador.detener()
    return 0


if __name__ == "__main__":
    sys.exit(main())
