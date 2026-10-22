"""Agente de inteligencia artificial (seccion 5.3).

Dos usos:
- inspeccionar: veredicto de formato fijo (descripcion, clase y confianza) sobre
  una o dos imagenes. El orquestador valida el formato y compara la confianza
  con el umbral; el modelo no decide.
- conversar: preguntas abiertas del operador. El modelo puede invocar las
  funciones del servidor de contexto de modelo, que aplican sus restricciones.

AgenteSimulado sustituye al modelo por respuestas fijas para probar el flujo
sin gasto. El agente no guarda memoria entre consultas (seccion 5.3.3).
"""
import base64
import json
import logging
from dataclasses import dataclass

from .camara import Captura, tokens_imagen
from .mensajes import FASES
from .servidor_funciones import herramientas_openai, invocar

log = logging.getLogger("agente")

INSTRUCCION = (
    "Supervisas una impresora Bambu Lab A1 mini y decides solo sobre lo que la secuencia "
    "automatica no contempla. Respondes en espanol, en frases breves, y dices que ves en la "
    "imagen antes de concluir. Si dudas, no actuas y preguntas al operador. Nunca propones "
    "mover ejes ni cambiar temperaturas. Cuando se te pide un veredicto de inspeccion, lo "
    "entregas en el formato fijo, con la descripcion, la clase y la confianza entre 0 y 1."
)

CONSULTAS = {
    "supervision": (
        ["normal", "falla"],
        "Imagen de supervision durante la impresion. Indica si hay una falla visible: pieza "
        "desprendida, espaguetizacion o filamento acumulado en la boquilla. Clase 'falla' o "
        "'normal'."),
    "confirmacion_falla": (
        ["normal", "falla"],
        "Segunda consulta, con la imagen completa, para confirmar una posible falla detectada "
        "en la supervision. Clase 'falla' solo si la falla se ve con claridad; si no, 'normal'."),
    "fin": (
        ["pieza", "libre", "anomala"],
        "La impresion termino. La primera imagen es la referencia de la plataforma vacia y la "
        "segunda la captura actual, en las mismas condiciones. Clase 'pieza' si hay una pieza "
        "y la escena es la esperada; 'libre' si la plataforma esta vacia; 'anomala' si hay "
        "objetos ajenos, una mano u otra cosa inesperada."),
    "verificacion": (
        ["libre", "pieza"],
        "Verificacion tras la maniobra de remocion. La primera imagen es la referencia de la "
        "plataforma vacia y la segunda la captura actual. Clase 'libre' si la plataforma quedo "
        "como la referencia; 'pieza' si queda una pieza o restos."),
}


@dataclass
class Veredicto:
    clase: str
    confianza: float
    descripcion: str
    valido: bool = True
    tokens_entrada: int = 0
    tokens_salida: int = 0
    error: str = ""


def validar(datos, clases) -> Veredicto:
    """El orquestador solo usa veredictos con el formato esperado."""
    try:
        clase, confianza = datos["clase"], float(datos["confianza"])
        descripcion = str(datos["descripcion"])
        if clase not in clases or not 0.0 <= confianza <= 1.0:
            raise ValueError(f"clase o confianza fuera de rango: {datos}")
        return Veredicto(clase, confianza, descripcion)
    except (KeyError, TypeError, ValueError) as error:
        return Veredicto("invalido", 0.0, "", valido=False, error=str(error))


def _imagen(captura) -> dict:
    jpeg = captura.jpeg if isinstance(captura, Captura) else open(captura, "rb").read()
    return {"type": "input_image",
            "image_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}


class Agente:
    def __init__(self, modelo: str, servidor=None):
        from openai import OpenAI
        self.cliente = OpenAI()
        self.modelo = modelo
        self.servidor = servidor

    def inspeccionar(self, tipo: str, imagenes: list, estado: dict) -> Veredicto:
        clases, pregunta = CONSULTAS[tipo]
        esquema = {"type": "object", "additionalProperties": False,
                   "required": ["descripcion", "clase", "confianza"],
                   "properties": {"descripcion": {"type": "string"},
                                  "clase": {"type": "string", "enum": clases},
                                  "confianza": {"type": "number"}}}
        contenido = [{"type": "input_text",
                      "text": f"{pregunta}\nEstado de la impresora: {json.dumps(estado, ensure_ascii=False)}"}]
        contenido += [_imagen(i) for i in imagenes]
        try:
            r = self.cliente.responses.create(
                model=self.modelo, instructions=INSTRUCCION,
                input=[{"role": "user", "content": contenido}],
                text={"format": {"type": "json_schema", "name": "veredicto",
                                 "schema": esquema, "strict": True}})
            v = validar(json.loads(r.output_text), clases)
            v.tokens_entrada, v.tokens_salida = r.usage.input_tokens, r.usage.output_tokens
            return v
        except Exception as error:      # consulta fallida: el orquestador escala
            log.warning("Consulta %s fallida: %s", tipo, error)
            return Veredicto("invalido", 0.0, "", valido=False, error=str(error))

    def conversar(self, texto: str, contexto: str, imagen=None) -> str:
        herramientas = herramientas_openai(self.servidor)
        contenido = [{"type": "input_text", "text": f"{contexto}\n\nMensaje del operador: {texto}"}]
        if imagen is not None:
            contenido.append(_imagen(imagen))
        r = self.cliente.responses.create(model=self.modelo, instructions=INSTRUCCION,
                                          input=[{"role": "user", "content": contenido}],
                                          tools=herramientas)
        for _ in range(6):
            llamadas = [o for o in r.output if o.type == "function_call"]
            if not llamadas:
                return r.output_text.strip()
            salidas, imagenes = [], []
            for llamada in llamadas:
                resultado = invocar(self.servidor, llamada.name, json.loads(llamada.arguments or "{}"))
                imagenes += resultado.pop("_imagenes", [])
                log.info("El agente invoco %s: %s", llamada.name, resultado)
                salidas.append({"type": "function_call_output", "call_id": llamada.call_id,
                                "output": json.dumps(resultado, ensure_ascii=False)})
            if imagenes:
                salidas.append({"role": "user", "content": [
                    {"type": "input_text", "text": "Imagenes devueltas por las funciones."}]
                    + [_imagen(i) for i in imagenes]})
            r = self.cliente.responses.create(model=self.modelo, instructions=INSTRUCCION,
                                              previous_response_id=r.id, input=salidas,
                                              tools=herramientas)
        return "No pude completar la consulta. Revisa el estado con /estado."


# Respuestas fijas del modelo simulado, segun la imagen de prueba.
_SIMULADAS = {
    ("supervision", "espagueti"): ("falla", 0.82, "Se ve filamento enredado sobre la pieza y "
                                   "fuera de su contorno; parece espaguetización."),
    ("confirmacion_falla", "espagueti"): ("falla", 0.91, "Con la imagen completa se confirma "
                                          "filamento suelto y enredado: la pieza se desprendió."),
    ("fin", "pieza_presente"): ("pieza", 0.86, "Hay una pieza gris sobre la plataforma y no se "
                                "ven objetos ajenos."),
    ("fin", "objeto_ajeno"): ("anomala", 0.74, "Además de la pieza hay un objeto ajeno sobre la "
                              "plataforma."),
    ("verificacion", "pieza_presente"): ("pieza", 0.88, "La pieza sigue sobre la plataforma."),
}
_POR_DEFECTO = {"supervision": ("normal", 0.90, "La impresión avanza sin defectos visibles."),
                "confirmacion_falla": ("normal", 0.80, "Con la imagen completa no se ve falla."),
                "fin": ("libre", 0.95, "La plataforma está vacía."),
                "verificacion": ("libre", 0.93, "La plataforma quedó vacía, igual que la referencia.")}


class AgenteSimulado:
    def __init__(self, modelo: str = "simulado", servidor=None):
        self.modelo = modelo
        self.servidor = servidor

    def inspeccionar(self, tipo: str, imagenes: list, estado: dict) -> Veredicto:
        captura = imagenes[-1]
        clase, confianza, descripcion = _SIMULADAS.get((tipo, captura.etiqueta), _POR_DEFECTO[tipo])
        v = validar({"clase": clase, "confianza": confianza, "descripcion": descripcion},
                    CONSULTAS[tipo][0])
        v.tokens_entrada = 350 + sum(tokens_imagen(i.ancho, i.alto) for i in imagenes)
        v.tokens_salida = 60
        return v

    def conversar(self, texto: str, contexto: str, imagen=None) -> str:
        # Recorre el mismo camino que el modelo real: invoca una funcion por el servidor MCP.
        estado = invocar(self.servidor, "consultar_estado", {})
        return (f"(respuesta simulada) La impresora está {FASES.get(estado.get('fase'), estado.get('fase'))}, con "
                f"{estado.get('avance_pct')} % de avance y la plataforma a "
                f"{estado.get('temp_plataforma')} grados.")
