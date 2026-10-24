"""Calibracion de los umbrales con el conjunto etiquetado (ensayo L11, R-PERF-01).

Lee las imagenes que el bot guardo con /etiqueta en datos/calibracion/<clase>/,
con las clases libre, pieza, falla y ajeno, y corre el modelo sobre ellas:

- Supervision (800 x 600) en todas: la probabilidad de falla es la confianza si el
  modelo dice falla y su complemento si dice normal. Para cada umbral calcula la
  sensibilidad a las fallas, la tasa de falsos negativos y la de falsas alarmas, y
  propone el MAYOR umbral que mantiene la sensibilidad en 95 % o mas (el menor
  seria 0, que la cumple siempre pero pausa ante cualquier duda).
- Fin de impresion (referencia y captura) en libre, pieza y ajeno: para el umbral
  de confianza de R-SEG-01 propone el menor valor con el que ninguna escena libre
  o con objeto ajeno habria iniciado la remocion sin preguntar.

Sin --ejecutar solo cuenta las imagenes y estima el costo. --simulado recorre el
calculo con el modelo de respuestas fijas, sin gasto.

  python pruebas/calibrar_umbral.py                 estimacion
  python pruebas/calibrar_umbral.py --ejecutar      consulta el modelo real (tope 0.80 USD)

Con 200 imagenes de la camara integrada (50 por clase) cuesta unos 0.21 USD solo la
supervision y unos 0.75 USD con la consulta de fin de impresion.
"""
import argparse
import csv
import io
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from orquestador.agente import Agente, AgenteSimulado     # noqa: E402
from orquestador.camara import SUPERVISION, VERIFICACION, _desde_bytes, tokens_imagen   # noqa: E402
from orquestador.config import leer_config                # noqa: E402

PRECIO_ENTRADA, PRECIO_SALIDA = 0.75, 4.50
BASE_TEXTO, SALIDA_MEDIA = 240, 100            # tokens medidos el 22 y el 24 de octubre
CLASES = ("libre", "pieza", "falla", "ajeno")
UMBRALES = [round(0.05 * k, 2) for k in range(21)]
ESTADO = {"fase": "RUNNING", "avance_pct": 50}


def cargar(carpeta: Path) -> dict[str, list[Path]]:
    return {c: sorted((carpeta / c).glob("*.jpg")) for c in CLASES}


def costo_tokens(entrada: int, salida: int) -> float:
    return entrada * PRECIO_ENTRADA / 1e6 + salida * PRECIO_SALIDA / 1e6


def leer(ruta: Path, clase: str):
    captura = _desde_bytes(ruta.read_bytes(), "calibracion", clase)
    captura.ruta = ruta
    return captura


def estimar(imagenes: dict, referencia) -> tuple[float, float, int, int]:
    """Costo por consulta de supervision y de fin, y cuantas de cada una."""
    todas = [r for c in CLASES for r in imagenes[c]]
    if not todas:
        return 0.0, 0.0, 0, 0
    muestra = leer(todas[0], "")
    sup = muestra.reducida(SUPERVISION)
    ver = muestra.reducida(VERIFICACION)
    c_sup = costo_tokens(BASE_TEXTO + tokens_imagen(sup.ancho, sup.alto) + 50, SALIDA_MEDIA)
    c_fin = costo_tokens(BASE_TEXTO + 2 * (tokens_imagen(ver.ancho, ver.alto) + 25), SALIDA_MEDIA)
    n_fin = sum(len(imagenes[c]) for c in ("libre", "pieza", "ajeno")) - (1 if referencia else 0)
    return c_sup, c_fin, len(todas), max(n_fin, 0)


def main() -> int:
    a = argparse.ArgumentParser(description="Calibracion de umbrales con el conjunto etiquetado")
    a.add_argument("--carpeta", type=Path, default=RAIZ / "datos" / "calibracion")
    a.add_argument("--ejecutar", action="store_true", help="consulta el modelo real")
    a.add_argument("--simulado", action="store_true", help="modelo de respuestas fijas, sin gasto")
    a.add_argument("--tope", type=float, default=0.80, help="gasto maximo en USD")
    a.add_argument("--solo-supervision", action="store_true", help="omite la consulta de fin de impresion")
    args = a.parse_args()

    imagenes = cargar(args.carpeta)
    conteo = {c: len(v) for c, v in imagenes.items()}
    referencia = imagenes["libre"][0] if imagenes["libre"] else None
    c_sup, c_fin, n_sup, n_fin = estimar(imagenes, referencia)
    if args.solo_supervision:
        n_fin = 0
    costo = n_sup * c_sup + n_fin * c_fin
    print(f"Imagenes por clase: {conteo} (total {sum(conteo.values())}).")
    print(f"Consultas previstas: {n_sup} de supervision y {n_fin} de fin de impresion; costo estimado {costo:.2f} USD.")
    if not args.ejecutar and not args.simulado:
        print("Solo estimacion. Agrega --ejecutar para consultar el modelo.")
        return 0
    if conteo["falla"] == 0:
        print("Faltan imagenes de falla: la sensibilidad no se puede calcular.")
        return 1
    if args.ejecutar and costo > args.tope:
        print(f"El costo estimado supera el tope de {args.tope} USD; sube --tope o usa --solo-supervision.")
        return 1

    c = leer_config()
    agente = AgenteSimulado() if args.simulado else Agente(c.modelo, api_key=c.openai_api_key)
    filas, gasto = [], 0.0
    for clase in CLASES:
        for ruta in imagenes[clase]:
            if gasto > args.tope:
                break
            captura = leer(ruta, {"libre": "plataforma_vacia", "pieza": "pieza_presente",
                                  "falla": "espagueti", "ajeno": "objeto_ajeno"}[clase] if args.simulado else "")
            v = agente.inspeccionar("supervision", [captura.reducida(SUPERVISION)], ESTADO)
            gasto += costo_tokens(v.tokens_entrada, v.tokens_salida)
            p_falla = v.confianza if v.clase == "falla" else (1 - v.confianza if v.valido else 0.5)
            fila = {"archivo": ruta.name, "clase": clase, "sup_veredicto": v.clase, "sup_confianza": v.confianza,
                    "p_falla": round(p_falla, 3), "fin_veredicto": "", "fin_confianza": "", "latencia_s": v.latencia_s}
            if clase != "falla" and not args.solo_supervision and referencia and ruta != referencia:
                ref = leer(referencia, "plataforma_vacia")
                vf = agente.inspeccionar("fin", [ref.reducida(VERIFICACION), captura.reducida(VERIFICACION)], ESTADO)
                gasto += costo_tokens(vf.tokens_entrada, vf.tokens_salida)
                fila["fin_veredicto"], fila["fin_confianza"] = vf.clase, vf.confianza
            filas.append(fila)

    with open(args.carpeta / "resultados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    lineas = [f"Calibracion de umbrales, {time.strftime('%Y-%m-%d %H:%M')}, modelo "
              f"{'simulado' if args.simulado else c.modelo}; imagenes {conteo}; gasto {gasto:.4f} USD.", "",
              "Supervision: umbral | sensibilidad a fallas | falsos negativos | falsas alarmas"]
    fallas = [f for f in filas if f["clase"] == "falla"]
    resto = [f for f in filas if f["clase"] != "falla"]
    propuesto = None
    for u in UMBRALES:
        tp = sum(f["p_falla"] >= u for f in fallas)
        fp = sum(f["p_falla"] >= u for f in resto)
        sens = tp / len(fallas)
        fpr = fp / len(resto) if resto else 0.0
        lineas.append(f"  {u:.2f} | {100 * sens:5.1f} % | {100 * (1 - sens):5.1f} % | {100 * fpr:5.1f} %")
        if sens >= 0.95:
            propuesto = (u, sens, fpr)
    if propuesto:
        lineas.append(f"Umbral de falla propuesto (mayor con sensibilidad de 95 % o mas): {propuesto[0]:.2f}; "
                      f"sensibilidad {100 * propuesto[1]:.1f} %, falsas alarmas {100 * propuesto[2]:.1f} %.")
    con_fin = [f for f in filas if f["fin_veredicto"]]
    if con_fin:
        lineas += ["", "Fin de impresion: umbral | escenas libres o ajenas que iniciarian solas | piezas que iniciarian solas"]
        seguro = None
        for u in UMBRALES:
            inseguras = sum(f["clase"] in ("libre", "ajeno") and f["fin_veredicto"] == "pieza" and f["fin_confianza"] >= u
                            for f in con_fin)
            piezas = [f for f in con_fin if f["clase"] == "pieza"]
            automaticas = sum(f["fin_veredicto"] == "pieza" and f["fin_confianza"] >= u for f in piezas)
            lineas.append(f"  {u:.2f} | {inseguras} | {automaticas} de {len(piezas)}")
            if inseguras == 0 and seguro is None:
                seguro = (u, automaticas, len(piezas))
        if seguro and seguro[0] < 1.0:
            lineas.append(f"Umbral de confianza propuesto (menor sin inicios indebidos): {seguro[0]:.2f}; con el, "
                          f"{seguro[1]} de {seguro[2]} piezas iniciarian la remocion sin preguntar.")
        else:
            lineas.append("Ningun umbral menor que 1.0 evita todos los inicios indebidos: se mantiene en 1.0.")
    salida = RAIZ / "pruebas" / ("salida_calibracion_simulada.txt" if args.simulado else "salida_calibracion.txt")
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
