"""Interfaz del operador por Telegram (secciones 5.5.1 y 5.5.4).

La unidad de procesamiento consulta los mensajes por consulta de larga espera
(getUpdates con plazo), de modo que no hace falta direccion publica ni abrir
puertos. El bot atiende solo al identificador del operador autorizado; los
mensajes de cualquier otro identificador se descartan sin respuesta.
"""
import json
import logging
import queue
import threading
import time

import requests

log = logging.getLogger("telegram")


def _teclado(botones):
    """botones: lista de filas, cada fila una lista de (texto, dato)."""
    if not botones:
        return None
    return json.dumps({"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in fila]
                                           for fila in botones]})


class Telegram:
    def __init__(self, token: str, operador_id: int | None, al_registrar=None):
        self.url = f"https://api.telegram.org/bot{token}/"
        self.operador_id = operador_id
        self.al_registrar = al_registrar     # solo en el modo de registro del operador
        self._parar = threading.Event()
        self._hilo = None

    def _llamar(self, metodo: str, archivos=None, espera: float = 30, **datos) -> dict:
        datos = {k: v for k, v in datos.items() if v is not None}
        r = requests.post(self.url + metodo, data=datos, files=archivos, timeout=espera)
        respuesta = r.json()
        if not respuesta.get("ok"):
            raise RuntimeError(f"Telegram {metodo}: {respuesta.get('description')}")
        return respuesta["result"]

    def identidad(self) -> dict:
        return self._llamar("getMe")

    def enviar(self, texto: str, botones=None) -> int | None:
        if self.operador_id is None:
            log.warning("Sin operador autorizado: no se envia '%s'", texto[:60])
            return None
        r = self._llamar("sendMessage", chat_id=self.operador_id, text=texto,
                         reply_markup=_teclado(botones))
        return r["message_id"]

    def enviar_foto(self, jpeg: bytes, texto: str, botones=None) -> int | None:
        if self.operador_id is None:
            return None
        r = self._llamar("sendPhoto", archivos={"photo": ("captura.jpg", jpeg, "image/jpeg")},
                         chat_id=self.operador_id, caption=texto[:1024],
                         reply_markup=_teclado(botones), espera=60)
        return r["message_id"]

    def quitar_botones(self, mensaje_id: int) -> None:
        try:
            self._llamar("editMessageReplyMarkup", chat_id=self.operador_id,
                         message_id=mensaje_id, reply_markup=json.dumps({"inline_keyboard": []}))
        except RuntimeError:
            pass

    def responder_boton(self, consulta_id: str, texto: str | None = None) -> None:
        try:
            self._llamar("answerCallbackQuery", callback_query_id=consulta_id, text=texto)
        except RuntimeError:
            pass

    def escuchar(self, cola: queue.Queue) -> None:
        self._hilo = threading.Thread(target=self._bucle, args=(cola,), daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        self._parar.set()

    def _autorizado(self, usuario_id: int, texto: str, tipo_chat: str) -> bool:
        if self.operador_id is None and self.al_registrar and tipo_chat == "private" \
                and texto.strip().startswith("/start"):
            self.operador_id = usuario_id
            self.al_registrar(usuario_id)
            log.info("Operador registrado: %s", usuario_id)
            return True
        if usuario_id != self.operador_id:
            log.info("Mensaje de %s descartado (no es el operador autorizado)", usuario_id)
            return False
        return True

    def _bucle(self, cola: queue.Queue) -> None:
        desplazamiento = None
        while not self._parar.is_set():
            try:
                novedades = self._llamar("getUpdates", espera=60, timeout=50,
                                         offset=desplazamiento,
                                         allowed_updates=json.dumps(["message", "callback_query"]))
            except Exception as error:      # red caida: se reintenta sin detener el sistema
                log.warning("getUpdates fallo: %s", error)
                time.sleep(5)
                continue
            for novedad in novedades:
                desplazamiento = novedad["update_id"] + 1
                if "message" in novedad:
                    m = novedad["message"]
                    texto = m.get("text", "")
                    if self._autorizado(m["from"]["id"], texto, m["chat"]["type"]):
                        cola.put(("mensaje", texto, time.time()))
                elif "callback_query" in novedad:
                    c = novedad["callback_query"]
                    if self._autorizado(c["from"]["id"], "", "callback"):
                        cola.put(("boton", c.get("data", ""), c["id"], c["message"]["message_id"]))


class TelegramConsola:
    """Sustituto para la simulacion: imprime los mensajes y responde con un guion.

    El guion es una funcion f(texto, botones) que devuelve None o una tupla
    (retraso_s, evento) con el evento que el operador simulado pone en la cola.
    """

    def __init__(self, guion=None, operador_id: int = 1):
        self.guion = guion
        self.operador_id = operador_id
        self.transcripcion: list[str] = []
        self._cola = None
        self._contador = 0

    def identidad(self) -> dict:
        return {"username": "consola"}

    def _registrar(self, prefijo: str, texto: str, botones) -> int:
        self._contador += 1
        linea = f"[BOT] {prefijo}{texto}"
        if botones:
            linea += "  " + " ".join(f"[{t}]" for fila in botones for t, _ in fila)
        self.transcripcion.append(linea)
        log.info(linea)
        if self.guion and self._cola is not None:
            respuesta = self.guion(texto, botones)
            if respuesta:
                retraso, evento = respuesta
                if evento[0] == "boton":
                    etiquetas = {d: t for fila in (botones or []) for t, d in fila}
                    etiqueta = f"pulsa [{etiquetas.get(evento[1], evento[1])}]"
                    evento = (evento[0], evento[1], f"c{self._contador}", self._contador)
                else:
                    etiqueta = f"escribe: {evento[1]}"
                threading.Timer(retraso, self._entregar, args=(evento, etiqueta)).start()
        return self._contador

    def _entregar(self, evento, etiqueta: str) -> None:
        self.transcripcion.append(f"[OPERADOR] {etiqueta}")
        self._cola.put(evento)

    def enviar(self, texto, botones=None):
        return self._registrar("", texto, botones)

    def enviar_foto(self, jpeg, texto, botones=None):
        return self._registrar("(foto) ", texto, botones)

    def quitar_botones(self, mensaje_id):
        pass

    def responder_boton(self, consulta_id, texto=None):
        pass

    def escuchar(self, cola):
        self._cola = cola

    def detener(self):
        pass

    def operador_escribe(self, texto: str) -> None:
        self.transcripcion.append(f"[OPERADOR] {texto}")
        self._cola.put(("mensaje", texto, time.time()))
