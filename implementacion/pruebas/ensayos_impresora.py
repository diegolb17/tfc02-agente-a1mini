"""Ensayos L4, L5 y L6 de la Tabla K2 con la A1 mini real.

No inicia impresiones ni mueve ejes. Solo enciende y apaga la luz; la pausa y la
reanudacion se ensayan unicamente si encuentra una impresion en curso. El codigo
de acceso y el numero de serie se leen de .env y no se escriben en la salida.

  python pruebas/ensayos_impresora.py
"""
import io
import json
import statistics
import sys
import time
from pathlib import Path

from PIL import Image, ImageStat

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador.camara import CamaraA1, SUPERVISION     # noqa: E402
from orquestador.config import leer_config               # noqa: E402
from orquestador.impresora import ImpresoraMQTT          # noqa: E402

SALIDA = RAIZ / "pruebas" / "salida_ensayos_impresora.txt"
CARPETA = RAIZ / "pruebas" / "capturas_reales"
TESIS = RAIZ.parent / "TESIS_LATEX" / "Imagenes" / "capturas"


def esperar(condicion, limite: float) -> float | None:
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        if condicion():
            return time.monotonic() - inicio
        time.sleep(0.02)
    return None


def brillo(jpeg: bytes) -> float:
    return ImageStat.Stat(Image.open(io.BytesIO(jpeg)).convert("L")).mean[0]


# Recorte de la zona de la cama en la imagen de la camara integrada (1 680 x 1 080):
# deja fuera el resto de la habitacion para las figuras de la tesis.
RECORTE_CAMA = (180, 560, 1240, 1080)


def main() -> int:
    c = leer_config()
    out = [f"Ensayos con la Bambu Lab A1 mini real, {time.strftime('%Y-%m-%d %H:%M')}",
           f"Impresora en {c.impresora_ip}; numero de serie y codigo de acceso leidos de .env (no se registran)."]
    imp = ImpresoraMQTT(c.impresora_ip, c.serie, c.codigo_acceso)
    t0 = time.monotonic()
    imp.conectar()
    out.append(f"Conexion MQTT por TLS al puerto 8883: {time.monotonic() - t0:.2f} s.")
    esperar(lambda: "gcode_state" in imp.ultimo_reporte or imp.estado()["fase"] != "DESCONOCIDO", 15)
    version = getattr(imp, "version", {})
    out.append(f"Firmware informado por get_version: {json.dumps(version, ensure_ascii=False)}")

    # L4: cinco lecturas. Se compara el estado que arma el orquestador con el campo
    # crudo del mensaje del equipo; la comparacion con la pantalla la hace Diego.
    out += ["", "L4. Lectura de estado por MQTT"]
    lecturas = []
    for i in range(1, 6):
        if i > 1:
            time.sleep(8)
        e = imp.estado()
        crudo = imp.ultimo_reporte
        lecturas.append(e)
        out.append(f"  lectura {i}: fase {e['fase']} (crudo {imp._estado.get('gcode_state')}); plataforma "
                   f"{e['temp_plataforma']} grados (objetivo {imp._estado.get('bed_target_temper')}); boquilla "
                   f"{e['temp_boquilla']} grados; luz {e['luz']}; avance {e['avance_pct']} %; "
                   f"ultimo mensaje hace {time.time() - imp.instante_reporte:.1f} s con {len(crudo)} campos")
    fases = {e["fase"] for e in lecturas}
    temps = [e["temp_plataforma"] for e in lecturas if e["temp_plataforma"] is not None]
    out.append(f"  Fases leidas: {sorted(fases)}; temperatura de la plataforma de {min(temps)} a {max(temps)} grados "
               f"(dispersion {max(temps) - min(temps):.1f}).")
    en_curso = imp.estado()["fase"] in ("RUNNING", "PREPARE")

    # L5: luz encendida y apagada, con el tiempo hasta que el equipo confirma el cambio.
    out += ["", "L5. Ordenes por MQTT"]
    cam = CamaraA1(c.impresora_ip, c.codigo_acceso)
    luz_inicial = bool(imp.luz_reportada)
    tiempos_luz, capturas_luz = [], {}
    # Cada orden cambia el estado: si la luz ya esta apagada, una orden de apagar no genera reporte.
    secuencia = [not luz_inicial, luz_inicial] * 3
    for encender in secuencia:
        imp.luz_reportada = None
        t0 = time.monotonic()
        r = imp.luz(encender)
        dt = esperar(lambda: imp.luz_reportada is encender, 8)
        tiempos_luz.append(dt)
        out.append(f"  luz {'encendida' if encender else 'apagada'}: respuesta {r.get('respuesta', {}).get('result') if r.get('respuesta') else 'sin eco'}; "
                   f"confirmada por el equipo en {f'{dt:.2f} s' if dt is not None else 'mas de 8 s'}")
        if encender not in capturas_luz:
            time.sleep(1.0)
            capturas_luz[encender] = cam.capturar()
    validos = [t for t in tiempos_luz if t is not None]
    out.append(f"  Brillo medio de la imagen: {brillo(capturas_luz[False].jpeg):.1f} con la luz apagada y "
               f"{brillo(capturas_luz[True].jpeg):.1f} con la luz encendida (escala de 0 a 255).")
    if en_curso:
        for orden in ("pausar", "reanudar"):
            t0 = time.monotonic()
            r = getattr(imp, orden)()
            objetivo = "PAUSE" if orden == "pausar" else "RUNNING"
            dt = esperar(lambda: imp.estado()["fase"] == objetivo, 10)
            out.append(f"  {orden}: aceptada {r.get('aceptada')}; fase {objetivo} en {dt}")
    else:
        out.append(f"  Pausa y reanudacion: no ensayadas, la impresora esta en {imp.estado()['fase']} y no hay impresion en curso.")
    out.append(f"  Criterio, cambio en menos de 5 s: {'cumple para la luz' if validos and max(validos) < 5 and len(validos) == len(tiempos_luz) else 'no cumple'} "
               f"(maximo {max(validos):.2f} s)" if validos else "  Criterio: sin confirmacion de la luz")

    # L6: diez capturas por el puerto 6000.
    out += ["", "L6. Camara integrada por el puerto 6000"]
    CARPETA.mkdir(parents=True, exist_ok=True)
    tiempos, resoluciones, validas = [], set(), 0
    imp.luz(True)
    esperar(lambda: imp.luz_reportada is True, 8)
    time.sleep(1)
    capturas = []
    for i in range(1, 11):
        t0 = time.monotonic()
        try:
            cap = cam.capturar()
            dt = time.monotonic() - t0
            Image.open(io.BytesIO(cap.jpeg)).verify()
            ok = cap.jpeg[:2] == b"\xff\xd8" and cap.jpeg[-2:] == b"\xff\xd9"
            validas += ok
            tiempos.append(dt)
            resoluciones.add(f"{cap.ancho}x{cap.alto}")
            cap.guardar(CARPETA, f"captura_{i:02d}.jpg")
            capturas.append(cap)
            out.append(f"  captura {i:2d}: {dt:.2f} s, {cap.ancho} x {cap.alto} px, {len(cap.jpeg) / 1024:.0f} kB, JPEG {'valido' if ok else 'invalido'}")
        except Exception as error:
            out.append(f"  captura {i:2d}: fallo, {type(error).__name__}: {error}")
    imp.luz(bool(luz_inicial))
    if tiempos:
        out.append(f"  Validas {validas} de 10; tiempo medio {statistics.mean(tiempos):.2f} s, maximo {max(tiempos):.2f} s; "
                   f"resolucion {sorted(resoluciones)}.")
        out.append(f"  Criterio, imagen valida en las diez y cada una en menos de 5 s: "
                   f"{'cumple' if validas == 10 and max(tiempos) < 5 else 'no cumple'}.")
    # Tres capturas representativas para la tesis.
    TESIS.mkdir(parents=True, exist_ok=True)
    guardadas = []
    for nombre, cap in (("camara_real_luz_apagada", capturas_luz[False]), ("camara_real_luz_encendida", capturas_luz[True]),
                        ("camara_real_supervision_800x600", capturas[-1].reducida(SUPERVISION) if capturas else None)):
        if cap is None:
            continue
        ruta = TESIS / f"{nombre}.png"
        imagen = Image.open(io.BytesIO(cap.jpeg)).convert("RGB")
        imagen.save(ruta)
        guardadas.append(ruta.name)
        if imagen.size == (1680, 1080):
            recorte = TESIS / f"{nombre}_cama.png"
            imagen.crop(RECORTE_CAMA).save(recorte)
            guardadas.append(recorte.name)
    out += ["", "Capturas para la tesis: " + ", ".join(guardadas)]
    imp.cerrar()
    SALIDA.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
