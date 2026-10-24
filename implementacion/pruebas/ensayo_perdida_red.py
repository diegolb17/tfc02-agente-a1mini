"""L12: perdida y recuperacion del enlace con los servicios externos, sin cortar la red.

Solo dentro de este proceso, el cliente de OpenAI apunta a un host que no
resuelve y el panel a un dominio invalido. Se comprueba que el orquestador avisa
la perdida una sola vez, que las filas quedan pendientes de envio, que no ejecuta
ninguna accion fisica y que, al restituir los dos enlaces, avisa la recuperacion
y vacia la cola. Impresora simulada en impresion; modelo real al recuperarse.

  python pruebas/ensayo_perdida_red.py
"""
import logging
import sys
import threading
import time
from pathlib import Path

from openai import OpenAI

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador import mensajes as M          # noqa: E402
from orquestador.agente import Agente           # noqa: E402
from orquestador.config import leer_config      # noqa: E402
from orquestador.principal import construir     # noqa: E402

SALIDA = RAIZ / "pruebas" / "salida_perdida_red.txt"


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    c = leer_config()
    url_panel = c.panel_url
    c.carpeta_datos = RAIZ / "datos" / "ensayo_red"
    c.carpeta_datos.mkdir(parents=True, exist_ok=True)
    c.referencia = c.carpeta_datos / "referencia_plataforma_vacia.jpg"
    c.periodo_supervision = 8.0
    base = c.carpeta_datos / "registro.sqlite"
    base.unlink(missing_ok=True)
    s = construir(c, simular=True, consola=True, base_datos=base, descargar_config=False)
    agente = Agente(c.modelo, s.servidor, c.openai_api_key)
    agente.cliente = OpenAI(api_key=c.openai_api_key, base_url="https://api.openai.invalid/v1",
                            max_retries=0, timeout=10)
    s.agente = s.orquestador.agente = agente
    panel = s.orquestador.panel
    panel.url, panel.periodo = "https://tfc02-panel.invalid", 5.0

    acciones = []
    for nombre in ("pausar", "reanudar", "detener"):
        original = getattr(s.impresora, nombre)
        setattr(s.impresora, nombre, lambda n=nombre, f=original: (acciones.append(n), f())[1])
    iniciar = s.micro.iniciar
    s.micro.iniciar = lambda: (acciones.append("iniciar_remocion"), iniciar())[1]

    s.impresora.duracion_min = 120
    s.camara.escena = "pieza_presente"
    hilo = threading.Thread(target=s.orquestador.ejecutar, daemon=True)
    hilo.start()
    s.impresora.iniciar_impresion("simulacion_perdida_red.3mf")
    linea = [f"Ensayo L12, {time.strftime('%Y-%m-%d %H:%M')}: enlace de OpenAI y del panel invalidos solo en este proceso."]
    t0 = time.monotonic()
    time.sleep(22)
    pendientes_corte = s.registro.pendientes_de_envio()
    avisos_corte = [t for t in s.telegram.transcripcion if M.SIN_RED in t]
    linea.append(f"Fase de corte, {time.monotonic() - t0:.0f} s: avisos de perdida {len(avisos_corte)}; "
                 f"filas pendientes de envio {pendientes_corte}; acciones fisicas {acciones or 'ninguna'}.")

    agente.cliente = OpenAI(api_key=c.openai_api_key)
    panel.url = url_panel.rstrip("/")
    t1 = time.monotonic()
    recuperada = None
    while time.monotonic() - t1 < 40:
        if any(M.RED_RECUPERADA in t for t in s.telegram.transcripcion) and not any(s.registro.pendientes_de_envio().values()):
            recuperada = time.monotonic() - t1
            break
        time.sleep(0.5)
    linea.append(f"Fase de recuperacion: aviso de recuperacion y cola vacia en "
                 f"{f'{recuperada:.1f} s' if recuperada is not None else 'mas de 40 s'}; filas pendientes "
                 f"{s.registro.pendientes_de_envio()}; acciones fisicas {acciones or 'ninguna'}.")
    s.orquestador.detener()
    linea.append("Conversacion en consola:")
    linea += ["  " + t for t in s.telegram.transcripcion]
    eventos = s.registro.con.execute("SELECT tipo, detalle FROM eventos WHERE tipo='sin red'").fetchall()
    linea.append(f"Eventos 'sin red' registrados: {len(eventos)}; detalle: {eventos[0][1][:120] if eventos else ''}")
    cumple = len(avisos_corte) == 1 and any(pendientes_corte.values()) and recuperada is not None and not acciones
    linea.append(f"Criterio (aviso de perdida y de recuperacion, sin accion fisica): {'cumple' if cumple else 'no cumple'}.")
    SALIDA.write_text("\n".join(linea) + "\n", encoding="utf-8")
    print("\n".join(linea))
    return 0 if cumple else 1


if __name__ == "__main__":
    sys.exit(main())
