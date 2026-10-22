# Sistema mecatrónico con agente de IA para la supervisión y remoción de piezas en la Bambu Lab A1 mini

Repositorio de la tesis de Diego Manuel Luna Baldwin (PUCP, Ingeniería Mecatrónica, 1MTR02 Trabajo de Fin de Carrera 2, 2026-2). Asesor: Christihan Laurel Bravo.

Contiene el código de la implementación parcial del dominio de software y los guiones que generan los cálculos, los planos, el proyecto electrónico y los diagramas de la tesis. El texto de la tesis no forma parte del repositorio.

## Estructura

| Carpeta | Contenido |
|---|---|
| `implementacion/` | Orquestador en Python: bot de Telegram, cliente MQTT de la impresora, cámara integrada de la A1 mini, servidor MCP con las nueve funciones del agente, agente con GPT-5.4 mini, registro SQLite y prueba de simulación |
| `calculos/` | Guiones de las memorias de cálculo (enfriamiento, vuelco, costos, potencia) y sus resultados en JSON |
| `planos/` | Generadores de las láminas mecánicas y eléctricas con un motor de dibujo propio (`motor/`) y los guiones de exportación desde Fusion 360 (`fusion/`) |
| `electronica/` | Guiones que generan el esquemático y la placa en KiCad, y el proyecto `TFC_Remocion` con su verificación eléctrica y de reglas de diseño |
| `diagramas/` | Fuentes TikZ de los diagramas de estados, de flujo y de comunicaciones del capítulo 5 |
| `armar_repositorio.py` | Vuelve a armar este repositorio desde las carpetas de trabajo y escanea secretos antes de cada subida |

## Implementación parcial

Requisitos: Python 3.11 o posterior.

```
cd implementacion
python -m pip install -r requisitos.txt
copy .env.ejemplo .env      (y completa los valores)
```

Modos de ejecución:

| Orden | Qué hace |
|---|---|
| `python -m orquestador --simular --consola` | Todo simulado y en consola; no usa red ni claves |
| `python -m orquestador --simular --registrar-operador` | Bot real de Telegram con impresora, cámara y modelo simulados; el primer `/start` privado queda como operador autorizado. En este modo `/simular_impresion` y `/simular_falla` recorren el ciclo completo |
| `python -m orquestador --simular-modelo` | Impresora y cámara reales; el modelo responde con veredictos fijos, sin costo |
| `python -m orquestador` | Sistema real: requiere la impresora en modo LAN y modo desarrollador y la variable `OPENAI_API_KEY` |
| `python -m orquestador.servidor_funciones` | Lanza solo el servidor MCP por stdio, con impresora simulada, para inspeccionar sus funciones |
| `python pruebas/prueba_simulacion.py` | Prueba de punta a punta en cuatro escenarios; deja la salida en `pruebas/salida_simulacion.txt` |

Criterios que el código aplica, tomados del capítulo 5 de la tesis:

- El agente solo actúa a través de las nueve funciones del servidor MCP. Ninguna mueve ejes ni cambia temperaturas, y las que tienen efecto físico comprueban su restricción antes de ejecutarse.
- La decisión sobre la confianza la toma el orquestador, no el modelo. Con el umbral al máximo (1.0), que es el valor inicial mientras no se calibre con un conjunto de prueba, el sistema pide siempre la confirmación del operador.
- La supervisión captura cada 10 minutos a 800 por 600 píxeles. Una posible falla se confirma con una segunda consulta a resolución completa antes de pausar la impresora.
- El bot atiende solo al identificador del operador autorizado. Las órdenes de rutina se reconocen por palabras clave sin llamar al modelo.
- En esta implementación, la imagen sale de la cámara integrada de la A1 mini (puerto 6000) en lugar de la ESP32-CAM del diseño. El microcontrolador de la secuencia de remoción está simulado con los mismos tiempos máximos.

## Guiones de cálculo, planos y electrónica

- Los guiones de `calculos/` reproducen las cifras de los Anexos E y F; cada uno escribe su JSON de resultados.
- Los generadores de `planos/` leen la geometría que exporta `fusion/_exportar_geometria.py` desde el modelo de Fusion 360. Esa geometría (unos 70 MB) no se incluye.
- En `electronica/`, la cadena es `generar_esquematico.py`, `exportar.py`, `clases_de_red.py`, `generar_placa.py`, `rutear.py` y `vias_costura.py`. Las tres últimas se ejecutan con el Python de KiCad.

## Lo que no está

El texto y los PDF de la tesis, la geometría exportada de Fusion 360 y cualquier clave o token. Los secretos van en `implementacion/.env`, que está excluido del control de versiones.
