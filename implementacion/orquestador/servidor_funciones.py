"""Servidor de contexto de modelo con las nueve funciones de la Tabla 20.

Ninguna funcion mueve un eje ni acciona directamente un elemento. Las que
tienen efecto fisico comprueban aqui su restriccion antes de ejecutarse, de modo
que una solicitud indebida del modelo se rechaza con un motivo y nunca llega al
equipo. El orquestador usa las mismas funciones, por lo que la restriccion vale
para todos los caminos.

El servidor es un servidor MCP real (SDK oficial de Python): el orquestador lo
aloja en su propio proceso, lista sus herramientas para declararlas al modelo y
las invoca con call_tool. Tambien puede lanzarse solo por stdio para
inspeccionarlo: python -m orquestador.servidor_funciones
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Literal

from mcp.server.mcpserver import MCPServer

from .camara import SUPERVISION, VERIFICACION


@dataclass
class EstadoCiclo:
    """Autorizaciones que fija el orquestador y que las funciones consultan."""
    falla_confirmada: bool = False       # segunda consulta en alta resolucion
    remocion_autorizada: bool = False    # confianza >= umbral o confirmacion del operador
    reanudar_autorizado: bool = False    # el operador pulso Reanudar
    ultima_captura: object = None
    capturas: dict = field(default_factory=dict)


class Funciones:
    def __init__(self, config, impresora, camara, telegram, registro, micro, solicitar):
        self.config = config
        self.impresora = impresora
        self.camara = camara
        self.telegram = telegram
        self.registro = registro
        self.micro = micro
        self._solicitar = solicitar          # f(accion, motivo) del orquestador
        self.ciclo = EstadoCiclo()
        self.carpeta_capturas = config.carpeta_datos / "capturas"

    # 1
    def consultar_estado(self) -> dict:
        e = self.impresora.estado()
        e["ciclo"] = getattr(self.micro, "estado", "sin microcontrolador")
        return e

    # 2
    def capturar_imagen(self, resolucion: str = "supervision") -> dict:
        luz_previa = self.impresora.luz_encendida
        if not luz_previa:
            self.impresora.luz(True)
            time.sleep(0.5)
        try:
            original = self.camara.capturar()
        finally:
            if not luz_previa:
                self.impresora.luz(False)
        limite = SUPERVISION if resolucion == "supervision" else VERIFICACION
        captura = original.reducida(limite)
        nombre = time.strftime("%Y%m%d_%H%M%S") + f"_{resolucion}.jpg"
        captura.guardar(self.carpeta_capturas, nombre)
        self.ciclo.ultima_captura = captura
        self.ciclo.capturas[resolucion] = captura
        return {"imagen": str(captura.ruta), "ancho": captura.ancho, "alto": captura.alto,
                "tokens": captura.tokens, "origen": captura.origen, "_imagenes": [str(captura.ruta)]}

    # 3
    def comparar_con_referencia(self) -> dict:
        referencia = self.config.referencia
        if not referencia.exists():
            return {"error": "No hay imagen de referencia de la plataforma vacia. "
                             "El operador la toma con /referencia."}
        if self.ciclo.ultima_captura is None:
            self.capturar_imagen("verificacion")
        actual = self.ciclo.ultima_captura
        return {"captura": str(actual.ruta), "referencia": str(referencia),
                "_imagenes": [str(referencia), str(actual.ruta)]}

    # 4
    def notificar_operador(self, texto: str, con_imagen: bool = False) -> dict:
        if con_imagen and self.ciclo.ultima_captura is not None:
            self.telegram.enviar_foto(self.ciclo.ultima_captura.jpeg, texto)
        else:
            self.telegram.enviar(texto)
        return {"enviado": True}

    # 5
    def solicitar_confirmacion(self, accion: str, motivo: str) -> dict:
        self._solicitar(accion, motivo)
        return {"estado": "pregunta enviada", "plazo_min": self.config.plazo_confirmacion / 60,
                "nota": "Sin respuesta en el plazo, la accion no se ejecuta."}

    # 6
    def pausar_impresion(self, motivo: str) -> dict:
        if not self.ciclo.falla_confirmada:
            return {"rechazada": "Solo se pausa tras una falla confirmada por una segunda "
                                 "consulta con la imagen completa."}
        r = self.impresora.pausar()
        self.registro.evento("pausa", motivo)
        return {"pausada": r.get("aceptada", True), "detalle": r.get("respuesta")}

    # 7
    def reanudar_impresion(self) -> dict:
        if not self.ciclo.reanudar_autorizado:
            return {"rechazada": "Reanudar exige la confirmacion explicita del operador."}
        self.ciclo.reanudar_autorizado = False
        self.ciclo.falla_confirmada = False
        r = self.impresora.reanudar()
        self.registro.evento("reanudacion", "orden del operador")
        return {"reanudada": r.get("aceptada", True), "detalle": r.get("respuesta")}

    # 8
    def iniciar_remocion(self) -> dict:
        fase = self.impresora.estado()["fase"]
        if fase not in ("FINISH", "FAILED"):
            return {"rechazada": f"La impresion no ha terminado (fase {fase})."}
        if not self.ciclo.remocion_autorizada:
            return {"rechazada": "Falta pieza presente con confianza suficiente o la "
                                 "confirmacion del operador."}
        self.ciclo.remocion_autorizada = False
        iniciada = self.micro.iniciar()
        self.registro.evento("remocion", "orden INICIAR al microcontrolador" if iniciada
                             else "el microcontrolador rechazo INICIAR")
        return {"iniciada": iniciada}

    # 9
    def registrar_evento(self, tipo: str, detalle: str) -> dict:
        return {"id": self.registro.evento(tipo, detalle)}


def crear_servidor(f: Funciones) -> MCPServer:
    """Declara las nueve funciones como herramientas MCP."""
    s = MCPServer("a1mini-orquestador", instructions="Funciones de supervision y remocion "
                  "de la Bambu Lab A1 mini. Ninguna mueve ejes ni cambia temperaturas.")

    @s.tool(description="Fase de la impresion, avance, tiempo restante, temperaturas de "
                        "plataforma y boquilla, y estado del ciclo. Solo lectura.")
    def consultar_estado() -> dict:
        return f.consultar_estado()

    @s.tool(description="Enciende la luz, toma una captura y la devuelve. 'supervision' "
                        "la reduce a 800 x 600; 'verificacion' la deja hasta 1 600 x 1 200.")
    def capturar_imagen(resolucion: Literal["supervision", "verificacion"] = "supervision") -> dict:
        return f.capturar_imagen(resolucion)

    @s.tool(description="Devuelve la captura actual junto con la imagen de referencia de la "
                        "plataforma vacia. Solo lectura.")
    def comparar_con_referencia() -> dict:
        return f.comparar_con_referencia()

    @s.tool(description="Envia un aviso al operador por Telegram, con la ultima captura si "
                        "con_imagen es verdadero. No espera respuesta.")
    def notificar_operador(texto: str, con_imagen: bool = False) -> dict:
        return f.notificar_operador(texto, con_imagen)

    @s.tool(description="Envia al operador una pregunta con botones y espera su respuesta "
                        "hasta 30 minutos. Se usa cuando la confianza es baja; sin respuesta, "
                        "la accion no se ejecuta.")
    def solicitar_confirmacion(accion: str, motivo: str) -> dict:
        return f.solicitar_confirmacion(accion, motivo)

    @s.tool(description="Pide a la impresora pausar el trabajo. Solo tras una falla "
                        "confirmada por una segunda consulta en alta resolucion.")
    def pausar_impresion(motivo: str) -> dict:
        return f.pausar_impresion(motivo)

    @s.tool(description="Pide a la impresora reanudar el trabajo. Exige la confirmacion "
                        "del operador.")
    def reanudar_impresion() -> dict:
        return f.reanudar_impresion()

    @s.tool(description="Pide al microcontrolador iniciar el ciclo de remocion. Exige "
                        "impresion terminada y pieza presente con confianza suficiente o "
                        "la confirmacion del operador.")
    def iniciar_remocion() -> dict:
        return f.iniciar_remocion()

    @s.tool(description="Envia un evento al registro del panel.")
    def registrar_evento(tipo: str, detalle: str) -> dict:
        return f.registrar_evento(tipo, detalle)

    return s


def herramientas_openai(servidor: MCPServer) -> list[dict]:
    """Convierte las herramientas MCP al formato de funciones de la interfaz de OpenAI."""
    herramientas = asyncio.run(servidor.list_tools())
    return [{"type": "function", "name": h.name, "description": h.description,
             "parameters": h.input_schema} for h in herramientas]


def invocar(servidor: MCPServer, nombre: str, argumentos: dict) -> dict:
    """Invoca una herramienta por el servidor MCP y devuelve su resultado como dict."""
    resultado = asyncio.run(servidor.call_tool(nombre, argumentos))
    if resultado.structured_content:
        datos = resultado.structured_content
        return datos.get("result", datos) if isinstance(datos, dict) else {"resultado": datos}
    texto = "".join(getattr(c, "text", "") for c in resultado.content)
    try:
        return json.loads(texto)
    except ValueError:
        return {"error" if resultado.is_error else "resultado": texto}


if __name__ == "__main__":
    # Servidor solo, por stdio, con impresora y camara simuladas, para inspeccion.
    from .config import leer_config
    from .principal import construir
    sistema = construir(leer_config(), simular=True, consola=True)
    crear_servidor(sistema.funciones).run("stdio")
