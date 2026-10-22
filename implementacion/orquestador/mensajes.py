"""Textos que el bot envia al operador.

Espanol peruano con tuteo, sin emojis ni guiones largos, porque las capturas de
la conversacion van en la tesis.
"""

AYUDA = (
    "Hola, soy el asistente de la impresora Bambu Lab A1 mini. Te aviso cuando la "
    "supervisión detecta una falla y cuando una pieza está lista para retirarse.\n\n"
    "Órdenes:\n"
    "/estado: fase, avance, tiempo restante y temperaturas\n"
    "/foto: captura de la plataforma\n"
    "/pausa: pausa la impresión\n"
    "/reanudar: reanuda la impresión pausada\n"
    "/luz: enciende o apaga la luz de la cámara\n"
    "/referencia: guarda la foto de la plataforma vacía\n"
    "/ayuda: este mensaje\n\n"
    "También puedes escribir estado, foto, pausa, reanuda, luz o detén todo. "
    "Cualquier otra pregunta la responde el agente."
)

FASES = {"IDLE": "en reposo", "PREPARE": "preparando", "RUNNING": "imprimiendo",
         "PAUSE": "en pausa", "FINISH": "terminada", "FAILED": "detenida",
         "SLICING": "laminando", "DESCONOCIDO": "sin dato"}


def estado(e: dict) -> str:
    lineas = [f"Estado de la impresora: {FASES.get(e['fase'], e['fase'])}"]
    if e.get("archivo"):
        lineas.append(f"Trabajo: {e['archivo']}")
    if e.get("avance_pct") is not None:
        capa = f" (capa {e['capa']} de {e['capas_totales']})" if e.get("capas_totales") else ""
        lineas.append(f"Avance: {e['avance_pct']} %{capa}")
    if e.get("minutos_restantes") is not None and e["fase"] in ("RUNNING", "PREPARE", "PAUSE"):
        lineas.append(f"Tiempo restante: {e['minutos_restantes']} min")
    if e.get("temp_plataforma") is not None:
        lineas.append(f"Plataforma: {e['temp_plataforma']:.1f} °C")
    if e.get("temp_boquilla") is not None:
        lineas.append(f"Boquilla: {e['temp_boquilla']:.1f} °C")
    lineas.append(f"Luz: {e.get('luz', 'sin dato')}")
    lineas.append(f"Ciclo de remoción: {e.get('ciclo', 'sin dato').lower().replace('_', ' ')}")
    return "\n".join(lineas)


def falla_confirmada(archivo, descripcion, pausada: bool) -> str:
    accion = "Pausé la impresión." if pausada else "No pude pausar la impresión: revisa el modo desarrollador."
    return (f"Falla detectada y confirmada en {archivo or 'la impresión'}. {descripcion} "
            f"{accion} ¿Qué hago?")


def recordatorio_pausa() -> str:
    return "Recordatorio: la impresión sigue en pausa por la falla detectada. ¿Reanudo o cancelo el trabajo?"


def fin_confianza_alta(archivo, descripcion, confianza) -> str:
    return (f"Terminó la impresión de {archivo or 'la pieza'}. {descripcion} "
            f"Confianza {confianza:.2f}: inicio el ciclo de remoción.")


def fin_confirmar(archivo, descripcion, confianza, umbral) -> str:
    return (f"Terminó la impresión de {archivo or 'la pieza'}. {descripcion} "
            f"Mi confianza es {confianza:.2f}, menor que el umbral de {umbral:.2f}. "
            f"¿Inicio la remoción?")


def fin_anomalia(archivo, descripcion) -> str:
    return (f"Terminó la impresión de {archivo or 'la pieza'}, pero veo algo inesperado: "
            f"{descripcion} No inicio la remoción sin tu confirmación.")


def fin_sin_veredicto(error) -> str:
    return (f"Terminó la impresión, pero no pude evaluar la imagen ({error}). "
            f"¿Inicio la remoción?")


SIN_REFERENCIA = ("Falta la imagen de referencia de la plataforma vacía, así que no puedo "
                  "comparar. Tómala con /referencia cuando la plataforma esté libre.")
PLATAFORMA_YA_LIBRE = "Terminó la impresión y la plataforma ya está libre. El equipo está disponible."
SIN_RESPUESTA = "Pasaron 30 minutos sin respuesta: no ejecuto la acción. La pieza sigue en la plataforma."
REMOCION_CONFIRMADA = "Confirmado: inicio el ciclo de remoción."
REMOCION_CANCELADA = "Entendido, no inicio la remoción. La pieza queda en la plataforma."
REMOCION_FALLIDA = "Cancelé el trabajo con falla. Inicio el ciclo de remoción de la pieza fallida."


def retirada(intento: int) -> str:
    return f"Pieza retirada en el intento {intento}. El equipo está disponible."


def verificacion_dudosa(descripcion, confianza, umbral) -> str:
    return (f"Verificación tras la remoción: {descripcion} Mi confianza es {confianza:.2f}, "
            f"menor que el umbral de {umbral:.2f}. ¿La plataforma quedó libre?")


RETENIDA = ("La pieza sigue en la plataforma tras 3 intentos. Retírala a mano o pide un "
            "intento más.")


def parada(tipo: str) -> str:
    return (f"Parada del ciclo: {tipo.lower().replace('_', ' ')}. Las salidas quedaron en cero. "
            f"Revisa el equipo y pulsa Reanudar cuando esté listo.")


SIN_RED = ("No hay conexión con el modelo de lenguaje: la impresión sigue sin supervisión. "
           "Te aviso cuando vuelva la red.")
RED_RECUPERADA = "Volvió la conexión con el modelo: la supervisión continúa."
CONFIRMAR_DETENER = "¿Detengo y cancelo la impresión? No se puede deshacer."
REFERENCIA_EN_IMPRESION = "No puedo tomar la referencia mientras hay una impresión en curso."
