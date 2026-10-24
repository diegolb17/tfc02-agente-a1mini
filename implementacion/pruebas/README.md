# Pruebas de la implementación parcial

Todas se ejecutan desde la carpeta `IMPLEMENTACION`. Las claves se leen de `.env`; ninguna salida las escribe.

| Guion | Qué hace | Salida |
|---|---|---|
| `prueba_simulacion.py` | Flujo completo simulado en cuatro escenarios (L1) | `salida_simulacion.txt` |
| `prueba_modelo_real.py` | 20 consultas a GPT-5.4 mini con las imágenes cenitales del 22 oct (L7 y L8) | `salida_modelo_real.txt` |
| `ensayos_impresora.py` | A1 mini real: estado por MQTT, luz y diez capturas de la cámara integrada (L4 a L6). No imprime ni mueve ejes | `salida_ensayos_impresora.txt` |
| `prueba_modelo_camara_real.py` | Consultas de supervisión y verificación con imágenes reales de la cámara (L7 y L8) | `salida_modelo_camara_real.txt` |
| `ensayo_perdida_red.py` | Pérdida y recuperación del enlace con OpenAI y con el panel, solo dentro del proceso (L12) | `salida_perdida_red.txt` |
| `poblar_panel.py`, `capturas_panel.py` | Ciclos simulados hacia el panel y capturas de sus páginas (L13) | capturas en `TESIS_LATEX/Imagenes/capturas` |
| `generar_imagenes_prueba.py` | Imágenes sintéticas vistas desde la cámara del diseño: 123 mm sobre la plataforma, 214 mm de su centro, 55° de oblicuidad, objetivo de 120° | `imagenes/` |
| `demo_telegram.py` | Conversación tipo hacia el chat del operador | Telegram |
| `calibrar_umbral.py` | Umbrales a partir del conjunto etiquetado (L11) | `salida_calibracion.txt` |

## Demostración de Telegram (conversación tipo para la tesis)

1. Ten el teléfono a mano con el chat del bot abierto. La demostración dura unos 5 minutos si respondes al momento.
2. En la carpeta `IMPLEMENTACION`, ejecuta `python pruebas/demo_telegram.py`.
3. El bot avisa que es una simulación y recorre dos impresiones. En la primera hay una falla: llega la foto con los botones Reanudar y Cancelar trabajo. Si eliges Cancelar, sigue la remoción de la pieza fallida y la pregunta de si la plataforma quedó libre. En la segunda, al terminar, pregunta si inicia la remoción y luego verifica la plataforma.
4. Responde cada pregunta con los botones y captura la pantalla en cada paso. La prueba se cierra sola a los 40 minutos, o antes si terminan los dos ciclos.

## Calibración del umbral (ensayo L11)

1. Inicia el bot con la impresora real y el modelo de respuestas fijas, que no consume la clave de OpenAI: `iniciar_sin_modelo.bat` o `python -m orquestador --simular-modelo`.
2. Coloca a mano sobre la cama lo que corresponda y envía la orden al bot. Cada orden toma una captura real con la luz encendida, la guarda en `datos/calibracion/<clase>/` y responde cuántas llevas:
   - `/etiqueta libre`: la cama vacía.
   - `/etiqueta pieza`: una o varias piezas impresas que ya tengas.
   - `/etiqueta falla`: filamento enredado o una pieza volcada o desprendida.
   - `/etiqueta ajeno`: un objeto que no es pieza (herramienta, espátula) o una mano.
   - `/etiqueta deshacer`: borra la última si te equivocaste.
3. Junta unas 50 por clase, 200 en total. Cambia la posición, el color de las piezas y la luz del ambiente entre capturas.
4. Estima el costo con `python pruebas/calibrar_umbral.py`: unos 0.21 USD solo la supervisión y unos 0.75 USD con la consulta de fin de impresión.
5. Ejecuta `python pruebas/calibrar_umbral.py --ejecutar`, o `--ejecutar --solo-supervision` para gastar menos. El guion propone dos valores:
   - **Umbral de falla:** el mayor que mantiene la sensibilidad a fallas en 95 % o más (R-PERF-01).
   - **Umbral de confianza:** el menor con el que ninguna escena libre o con objeto ajeno habría iniciado la remoción sin preguntar (R-SEG-01).
6. Copia los valores en `.env` (`UMBRAL_FALLA`, `UMBRAL_CONFIANZA`) o en la página Configuración del panel.

Las imágenes salen de la cámara integrada de la A1 mini, no de la ESP32-CAM del diseño. Los umbrales valen para esta cámara y se vuelven a calibrar con la cámara definitiva en su soporte.
