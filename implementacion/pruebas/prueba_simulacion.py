"""Prueba de punta a punta en simulacion: impresora, camara, modelo y operador simulados.

Recorre cuatro escenarios con el tiempo acelerado 60 veces y guarda la
conversacion y los eventos en pruebas/salida_simulacion.txt. No toca la
impresora real ni llama a ninguna interfaz de pago.

  python pruebas/prueba_simulacion.py
"""
import logging
import sqlite3
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador.config import Config          # noqa: E402
from orquestador.principal import construir     # noqa: E402

SALIDA = RAIZ / "pruebas" / "salida_simulacion.txt"
DATOS = RAIZ / "pruebas" / "datos_simulacion"


def operador(decisiones: dict):
    """Guion del operador: responde a cada pregunta con botones tras 1 s."""
    def guion(texto, botones):
        if not botones:
            return None
        datos = [d for fila in botones for _, d in fila]
        for prefijo, eleccion in decisiones.items():
            elegido = next((d for d in datos if d.startswith(prefijo) and d.endswith(eleccion)), None)
            if elegido:
                return 1.0, ("boton", elegido)
        return None
    return guion


def escenario(nombre, umbral, escenas_impresion, escenas_intento, decisiones, mensajes=(), referencia=True,
              sin_ciclo=False):
    config = Config(umbral_confianza=umbral, periodo_supervision=10.0, plazo_confirmacion=30.0,
                    recordatorio_pausa=15.0, carpeta_datos=DATOS / nombre,
                    referencia=DATOS / nombre / "referencia_plataforma_vacia.jpg")
    config.carpeta_datos.mkdir(parents=True, exist_ok=True)
    config.referencia.unlink(missing_ok=True)
    s = construir(config, simular=True, consola=True, guion=operador(decisiones),
                  base_datos=config.carpeta_datos / "registro.sqlite")
    s.impresora.duracion_min = 12.0
    o, cam = s.orquestador, s.camara
    hilo = threading.Thread(target=o.ejecutar, daemon=True)
    hilo.start()
    time.sleep(0.5)
    if referencia:
        cam.escena = "plataforma_vacia"
        s.telegram.operador_escribe("/referencia")
        time.sleep(1.0)
    cam.escena = escenas_impresion
    s.impresora.iniciar_impresion(f"{nombre}.3mf")
    for momento, texto in mensajes:
        threading.Timer(momento, s.telegram.operador_escribe, args=(texto,)).start()
    # La escena cambia cuando el microcontrolador evacua la pieza en cada intento.
    intento, limite = 0, time.monotonic() + 90
    while time.monotonic() < limite:
        if s.micro.estado == "EVACUACION":
            cam.escena = escenas_intento[min(intento, len(escenas_intento) - 1)]
            intento += 1
            while s.micro.estado == "EVACUACION":
                time.sleep(0.05)
        con = sqlite3.connect(config.carpeta_datos / "registro.sqlite")
        cerrados = con.execute("SELECT COUNT(*) FROM trabajos WHERE resultado IS NOT NULL").fetchone()[0]
        intervenciones = con.execute("SELECT COUNT(*) FROM intervenciones").fetchone()[0]
        con.close()
        terminado = cerrados or (sin_ciclo and intervenciones > 0)
        if terminado and not o.pendientes and s.micro.estado in ("REPOSO", "PARADA"):
            time.sleep(1.5)
            break
        time.sleep(0.1)
    o.detener()
    con = sqlite3.connect(config.carpeta_datos / "registro.sqlite")
    trabajos = con.execute("SELECT archivo, resultado, intentos, tiempo_ciclo_s FROM trabajos").fetchall()
    capturas = con.execute("SELECT tipo, resolucion, veredicto, confianza, tokens FROM capturas ORDER BY instante").fetchall()
    intervenciones = con.execute("SELECT accion, tiempo_respuesta_s FROM intervenciones ORDER BY instante").fetchall()
    eventos = con.execute("SELECT tipo, detalle FROM eventos ORDER BY instante").fetchall()
    con.close()
    return {"transcripcion": s.telegram.transcripcion, "trabajos": trabajos, "capturas": capturas,
            "intervenciones": intervenciones, "eventos": eventos}


ESCENARIOS = [
    ("A_umbral_maximo", 1.0, "pieza_presente", ["plataforma_vacia"],
     {"conf:": "si", "verif:": "libre"},
     [(4.0, "estado"), (6.0, "¿la pieza se ve bien?")],
     "Umbral al maximo (valor de la tesis mientras no se calibre): todo pasa por el operador."),
    ("B_falla_y_reintento", 0.85, "espagueti", ["pieza_presente", "plataforma_vacia"],
     {"falla:": "cancelar", "conf:": "si", "verif:": "libre"}, [],
     "Falla en la supervision: segunda consulta, pausa, aviso, el operador cancela y la "
     "remocion de la pieza fallida necesita dos intentos."),
    ("C_confianza_alta", 0.85, "pieza_presente", ["plataforma_vacia"],
     {"conf:": "si", "verif:": "libre"}, [],
     "Umbral ya calibrado en 0.85: con confianza 0.86 el ciclo empieza sin preguntar."),
    ("D_objeto_ajeno", 0.85, "objeto_ajeno", ["plataforma_vacia"],
     {"conf:": "no"}, [],
     "Escena anomala al terminar: el orquestador pide confirmacion y el operador cancela."),
]

ESPERADO = {
    "A_umbral_maximo": ("retirada", 1),
    "B_falla_y_reintento": ("retirada", 2),
    "C_confianza_alta": ("retirada", 1),
    "D_objeto_ajeno": (None, 0),
}


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    lineas, errores = [], []
    lineas.append("Prueba de simulacion del orquestador, " + time.strftime("%Y-%m-%d %H:%M"))
    lineas.append("Impresora, camara, modelo y operador simulados; tiempo acelerado 60 veces.\n")
    for nombre, umbral, escena, intentos, decisiones, mensajes, descripcion in ESCENARIOS:
        r = escenario(nombre, umbral, escena, intentos, decisiones, mensajes,
                      sin_ciclo=ESPERADO[nombre][0] is None)
        lineas.append("=" * 78)
        lineas.append(f"Escenario {nombre} (umbral {umbral}): {descripcion}")
        lineas.append("Conversacion:")
        lineas += ["  " + t for t in r["transcripcion"]]
        lineas.append("Consultas al modelo (tipo, resolucion, veredicto, confianza, tokens de entrada):")
        lineas += [f"  {c}" for c in r["capturas"]]
        lineas.append(f"Intervenciones del operador: {r['intervenciones']}")
        lineas.append(f"Trabajo registrado: {r['trabajos']}")
        resultado = r["trabajos"][0][1] if r["trabajos"] else None
        intentos_reg = r["trabajos"][0][2] if r["trabajos"] else 0
        esperado = ESPERADO[nombre]
        ok = (resultado, intentos_reg or 0) == esperado
        lineas.append(f"Resultado: {resultado}, intentos {intentos_reg}; esperado {esperado}: "
                      f"{'CORRECTO' if ok else 'DISTINTO'}")
        if not ok:
            errores.append(nombre)
    lineas.append("=" * 78)
    lineas.append("Todos los escenarios correctos." if not errores else f"Escenarios distintos: {errores}")
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
