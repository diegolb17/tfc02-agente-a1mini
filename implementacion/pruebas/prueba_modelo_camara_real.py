"""L7 y L8 con imagenes reales de la camara integrada de la A1 mini.

Tres consultas de supervision (800 x 600 como maximo) y una de verificacion
(referencia y captura hasta 1 600 x 1 200), con los tokens medidos, la latencia
y el costo. Tope de gasto: 0.05 USD. La camara integrada entrega 1 680 x 1 080,
de modo que la reduccion conserva la proporcion de 14 a 9.

  python pruebas/prueba_modelo_camara_real.py
"""
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador.agente import Agente, CONSULTAS, INSTRUCCION      # noqa: E402
from orquestador.camara import CamaraA1, SUPERVISION, VERIFICACION, tokens_imagen   # noqa: E402
from orquestador.config import leer_config                          # noqa: E402
from orquestador.impresora import ImpresoraMQTT                     # noqa: E402

PRECIO_ENTRADA, PRECIO_SALIDA, TOPE = 0.75, 4.50, 0.05
SALIDA = RAIZ / "pruebas" / "salida_modelo_camara_real.txt"


def costo(e, s):
    return e * PRECIO_ENTRADA / 1e6 + s * PRECIO_SALIDA / 1e6


def main() -> int:
    c = leer_config()
    imp = ImpresoraMQTT(c.impresora_ip, c.serie, c.codigo_acceso)
    imp.conectar()
    time.sleep(2)
    estado = imp.estado()
    cam = CamaraA1(c.impresora_ip, c.codigo_acceso)
    imp.luz(True)
    time.sleep(3)
    referencia = cam.capturar()
    capturas = [cam.capturar() for _ in range(3)]
    imp.luz(False)
    imp.cerrar()
    agente = Agente(c.modelo, api_key=c.openai_api_key)

    def base(tipo):
        r = agente.cliente.responses.create(
            model=agente.modelo, instructions=INSTRUCCION, reasoning={"effort": agente.esfuerzo}, max_output_tokens=16,
            input=[{"role": "user", "content": [{"type": "input_text",
                    "text": f"{CONSULTAS[tipo][1]}\nEstado de la impresora: {json.dumps(estado, ensure_ascii=False)}"}]}])
        return r.usage.input_tokens, r.usage.output_tokens

    gasto, lineas = 0.0, []
    b_sup, s = base("supervision")
    gasto += costo(b_sup, s)
    b_ver, s = base("verificacion")
    gasto += costo(b_ver, s)
    for i, cap in enumerate(capturas, 1):
        if gasto > TOPE:
            break
        red = cap.reducida(SUPERVISION)
        v = agente.inspeccionar("supervision", [red], estado)
        gasto += costo(v.tokens_entrada, v.tokens_salida)
        lineas.append(f"supervision {i}: {red.ancho} x {red.alto} px; veredicto {v.clase} {v.confianza:.2f}; entrada "
                      f"{v.tokens_entrada} (imagen {v.tokens_entrada - b_sup}, calculado {tokens_imagen(red.ancho, red.alto)}); "
                      f"salida {v.tokens_salida}; {v.latencia_s:.2f} s; {costo(v.tokens_entrada, v.tokens_salida) * 1000:.3f} "
                      f"milesimas de USD; {v.descripcion or v.error}")
    ref, act = referencia.reducida(VERIFICACION), capturas[-1].reducida(VERIFICACION)
    v = agente.inspeccionar("verificacion", [ref, act], estado)
    gasto += costo(v.tokens_entrada, v.tokens_salida)
    lineas.append(f"verificacion: referencia y captura de {act.ancho} x {act.alto} px; veredicto {v.clase} {v.confianza:.2f}; "
                  f"entrada {v.tokens_entrada} (imagen {(v.tokens_entrada - b_ver) / 2:.0f} por imagen, calculado "
                  f"{tokens_imagen(act.ancho, act.alto)}); salida {v.tokens_salida}; {v.latencia_s:.2f} s; "
                  f"{costo(v.tokens_entrada, v.tokens_salida) * 1000:.3f} milesimas de USD; {v.descripcion or v.error}")
    texto = [f"Consultas reales a {c.modelo} con imagenes de la camara integrada de la A1 mini, {time.strftime('%Y-%m-%d %H:%M')}",
             f"Imagen original de la camara: {referencia.ancho} x {referencia.alto} px. Fase de la impresora: {estado['fase']}.",
             f"Base sin imagen: supervision {b_sup} tokens, verificacion {b_ver} tokens.", *lineas,
             f"Gasto total: {gasto:.4f} USD (tope {TOPE})."]
    SALIDA.write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\n".join(texto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
