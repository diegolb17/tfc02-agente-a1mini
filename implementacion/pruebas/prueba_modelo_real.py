"""Consultas reales a gpt-5.4-mini con las imagenes de prueba, sin impresora.

Mide los tokens de entrada y salida, la latencia y el veredicto de las tres
consultas del orquestador: supervision (800 x 600), fin de impresion y
verificacion (referencia mas captura de 1 600 x 1 200). Para aislar los tokens
de imagen repite cada consulta una vez sin imagen y resta. Se detiene antes de
pasar el tope de gasto.

  python pruebas/prueba_modelo_real.py
"""
import base64
import json
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador.agente import Agente, CONSULTAS, INSTRUCCION   # noqa: E402
from orquestador.camara import SUPERVISION, _desde_bytes, tokens_imagen   # noqa: E402
from orquestador.config import leer_config   # noqa: E402

PRECIO_ENTRADA, PRECIO_SALIDA = 0.75, 4.50     # USD por millon de tokens (Tabla 19)
TOPE_USD = 0.28
IMAGENES = RAIZ / "pruebas" / "imagenes_cenital"   # las del ensayo del 22 oct
SALIDA = RAIZ / "pruebas" / "salida_modelo_real.txt"

ESPERADO = {
    "supervision": {"espagueti": "falla", "pieza_presente": "normal", "plataforma_vacia": "normal",
                    "objeto_ajeno": "normal"},
    "fin": {"pieza_presente": "pieza", "objeto_ajeno": "anomala", "plataforma_vacia": "libre"},
    "verificacion": {"plataforma_vacia": "libre", "pieza_presente": "pieza"},
}
PLAN = (
    [("supervision", e) for e in ["espagueti"] * 3 + ["pieza_presente"] * 3 + ["plataforma_vacia", "objeto_ajeno"]]
    + [("fin", e) for e in ["pieza_presente"] * 3 + ["objeto_ajeno"] * 2 + ["plataforma_vacia"]]
    + [("verificacion", e) for e in ["plataforma_vacia"] * 3 + ["pieza_presente"] * 3]
)
ESTADO = {"fase": "RUNNING", "avance_pct": 48, "temp_plataforma": 65.0, "temp_boquilla": 220.0}


def costo(entrada: int, salida: int) -> float:
    return entrada * PRECIO_ENTRADA / 1e6 + salida * PRECIO_SALIDA / 1e6


def captura(escena: str, tipo: str):
    c = _desde_bytes((IMAGENES / f"{escena}.jpg").read_bytes(), "prueba", escena)
    return c.reducida(SUPERVISION) if tipo == "supervision" else c


def base_sin_imagen(agente: Agente, tipo: str) -> tuple[int, int]:
    """Misma consulta sin imagen: tokens de texto e instruccion."""
    clases, pregunta = CONSULTAS[tipo]
    r = agente.cliente.responses.create(
        model=agente.modelo, instructions=INSTRUCCION, reasoning={"effort": agente.esfuerzo},
        input=[{"role": "user", "content": [{"type": "input_text",
                "text": f"{pregunta}\nEstado de la impresora: {json.dumps(ESTADO, ensure_ascii=False)}"}]}],
        max_output_tokens=16)
    return r.usage.input_tokens, r.usage.output_tokens


def prueba_detalle_bajo(agente: Agente, c) -> int:
    """Comprueba si detail=low reduce el conteo en esta familia (tesis, 5.3.1)."""
    imagen = {"type": "input_image", "detail": "low",
              "image_url": "data:image/jpeg;base64," + base64.b64encode(c.jpeg).decode()}
    r = agente.cliente.responses.create(
        model=agente.modelo, instructions=INSTRUCCION, reasoning={"effort": agente.esfuerzo},
        input=[{"role": "user", "content": [{"type": "input_text", "text": CONSULTAS["supervision"][1]}, imagen]}],
        max_output_tokens=16)
    return r.usage.input_tokens


def main() -> int:
    config = leer_config()
    agente = Agente(config.modelo, api_key=config.openai_api_key)
    print(f"Modelo {config.modelo}; clave terminada en ...{config.openai_api_key[-4:]}")
    gasto, filas, lineas = 0.0, [], []

    bases = {}
    for tipo in ("supervision", "fin", "verificacion"):
        e, s = base_sin_imagen(agente, tipo)
        bases[tipo] = e
        gasto += costo(e, s)

    for i, (tipo, escena) in enumerate(PLAN, 1):
        if gasto > TOPE_USD:
            lineas.append(f"Detenido antes de la consulta {i}: gasto acumulado {gasto:.4f} USD.")
            break
        actual = captura(escena, tipo)
        imagenes = [actual] if tipo == "supervision" else [captura("plataforma_vacia", tipo), actual]
        v = agente.inspeccionar(tipo, imagenes, ESTADO)
        c = costo(v.tokens_entrada, v.tokens_salida)
        gasto += c
        n_img = len(imagenes)
        tokens_img = (v.tokens_entrada - bases[tipo]) / n_img if v.valido else None
        filas.append({"n": i, "tipo": tipo, "escena": escena, "res": f"{actual.ancho}x{actual.alto}",
                      "esperado": ESPERADO[tipo][escena], "clase": v.clase, "conf": v.confianza,
                      "entrada": v.tokens_entrada, "salida": v.tokens_salida,
                      "razonamiento": v.tokens_razonamiento, "latencia": v.latencia_s,
                      "tokens_imagen": tokens_img, "calculado": tokens_imagen(actual.ancho, actual.alto),
                      "costo": c, "descripcion": v.descripcion or v.error})
        print(f"{i:2d} {tipo:12s} {escena:16s} {v.clase:8s} {v.confianza:.2f} "
              f"entrada {v.tokens_entrada} salida {v.tokens_salida} {v.latencia_s} s")

    bajo = prueba_detalle_bajo(agente, captura("pieza_presente", "supervision"))
    gasto += costo(bajo, 16)

    lineas_tabla = []
    for f in filas:
        acierto = "si" if f["clase"] == f["esperado"] else "no"
        lineas_tabla.append(
            f"{f['n']:2d} | {f['tipo']:12s} | {f['escena']:16s} | {f['res']:9s} | esperado {f['esperado']:7s} | "
            f"{f['clase']:8s} {f['conf']:.2f} | acierto {acierto} | entrada {f['entrada']:5d} | "
            f"salida {f['salida']:4d} (razonamiento {f['razonamiento']}) | {f['latencia']:.2f} s | "
            f"{f['costo'] * 1000:.3f} milesimas de USD")
    resumen = []
    for tipo in ("supervision", "fin", "verificacion"):
        g = [f for f in filas if f["tipo"] == tipo and f["tokens_imagen"] is not None]
        if not g:
            continue
        resumen.append(
            f"{tipo}: {len(g)} consultas; base sin imagen {bases[tipo]} tokens; tokens por imagen medidos "
            f"{statistics.mean(f['tokens_imagen'] for f in g):.0f} frente a {g[0]['calculado']} calculados; "
            f"entrada media {statistics.mean(f['entrada'] for f in g):.0f}; salida media "
            f"{statistics.mean(f['salida'] for f in g):.0f}; latencia media "
            f"{statistics.mean(f['latencia'] for f in g):.2f} s (maxima {max(f['latencia'] for f in g):.2f}); "
            f"costo medio {statistics.mean(f['costo'] for f in g) * 1000:.3f} milesimas de USD; aciertos "
            f"{sum(f['clase'] == f['esperado'] for f in g)} de {len(g)}")
    latencias = [f["latencia"] for f in filas]
    sup = [f for f in filas if f["tipo"] == "supervision"]
    tokens_detalle_alto = statistics.mean(f["entrada"] for f in sup) if sup else 0
    texto = [
        "Consultas reales a gpt-5.4-mini con las imagenes de prueba, " + time.strftime("%Y-%m-%d %H:%M"),
        f"Modelo: {config.modelo}; esfuerzo de razonamiento: {agente.esfuerzo}; precios: {PRECIO_ENTRADA} y "
        f"{PRECIO_SALIDA} USD por millon de tokens de entrada y salida.",
        "Las imagenes son dibujos esquematicos generados por pruebas/generar_imagenes_prueba.py, no capturas de la "
        "camara: los aciertos no miden el desempeno de la vision; los tokens, la latencia y el costo si son reales.",
        "",
        "Detalle por consulta:",
        *lineas_tabla,
        "",
        "Resumen por tipo de consulta:",
        *resumen,
        "",
        f"Latencia de las {len(latencias)} consultas: media {statistics.mean(latencias):.2f} s, mediana "
        f"{statistics.median(latencias):.2f} s, maxima {max(latencias):.2f} s.",
        f"Detalle bajo (detail=low) en supervision: {bajo} tokens de entrada frente a {tokens_detalle_alto:.0f} con "
        f"el detalle por defecto.",
        f"Gasto total de la prueba, incluidas las consultas sin imagen: {gasto:.4f} USD (tope {TOPE_USD}).",
    ]
    SALIDA.write_text("\n".join(texto + lineas) + "\n", encoding="utf-8")
    print("\n".join(texto[-8:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
