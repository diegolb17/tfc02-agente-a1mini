# Electrónica: lo hecho y dónde está en el documento

29 de setiembre de 2026. Proyecto en `TFC_Remocion/`, generado con los guiones de
esta carpeta.

Estado: **34 componentes, 30 redes, ERC con cero errores, placa ruteada por
completo con 173 pistas y 4 vías, DRC sin violaciones y cero superposiciones de
texto en el plano.**

**YA ESTÁ EN LA TESIS.** Secciones 4.7.5 y 4.7.6 del cuerpo, Anexo H completo.
Las figuras las copia `exportar.py` a `TESIS_LATEX/Imagenes/`, de modo que si el
circuito cambia basta con volver a correrlo y recompilar.

## Cómo se rehace todo, en orden

El orden importa: `generar_placa.py` lee `net.xml`, así que si se regenera el
esquemático y no se vuelve a exportar la lista de redes, la placa sale con la
anterior y NO avisa de nada.

```
PY="C:/Program Files/KiCad/10.0/bin/python.exe"
CLI="C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
"$PY" generar_esquematico.py
"$CLI" sch erc  --output TFC_Remocion/erc.rpt --severity-error --severity-warning TFC_Remocion/TFC_Remocion.kicad_sch
"$CLI" sch export netlist --format kicadxml --output TFC_Remocion/net.xml TFC_Remocion/TFC_Remocion.kicad_sch
"$PY" generar_placa.py
"$PY" clases_de_red.py
"$PY" rutear.py 30
"$CLI" pcb drc --output TFC_Remocion/drc.rpt --severity-error --severity-warning TFC_Remocion/TFC_Remocion.kicad_pcb
python exportar.py
python comprobar_superposicion.py
```

Las dos comprobaciones no son opcionales. El ERC es lo que destapó que alargar
una etiqueta hasta rozar otro cable cortocircuitaba ACT\_OUT2 con +12 V, y
`comprobar_superposicion.py` es lo que permite afirmar que en el plano no hay
un solo texto encima de otro: mirarlo a ojo en una hoja A2 con 435 rótulos no
sirve, los choques son de milímetros.

## Dos defectos de seguridad que el esquemático destapó

**La parada de emergencia no cortaba el actuador.** Al dibujar la cadena quedó a
la vista que el convertidor de 12 V, que es el que alimenta al actuador lineal,
colgaba del bus de 24 V *antes* de la seta. Pulsarla habría detenido los
ventiladores y dejado vivo el único elemento que de verdad constituye un peligro.
Corregido: los convertidores de 12 V y de la celda cuelgan de `+24V_ACT`, esto es
después de la seta, y el de 5.1 V sigue en `+24V` para que el computador conserve
la capacidad de informar tras la parada, conforme a la cláusula 5.3.5 de la
IEC 60204-1 que la sección 4.7.4 ya invoca. El ventilador de extracción también
queda permanente, para que el calor se siga evacuando tras una parada.

**La celda no tenía con qué apagarse.** El convertidor XL4015 no dispone de
entrada de habilitación, de modo que la celda quedaba permanentemente
alimentada. Corregido con un transistor en lado bajo gobernado por el segundo
canal del excitador TC4427, que ya estaba en la placa y cuyo segundo canal
quedaba sin uso: no añade ningún componente.

## Lo que se cambió en el texto de la tesis, ya hecho

**Tabla 31, microcontrolador.** Dice ya «ESP32 DevKit V1, 30 contactos», que es
la placa concreta. Se alimenta por su entrada VIN desde el riel de 5.1 V y
produce a bordo sus propios 3.3 V.

**Tabla 31, fusible.** El de 1 A de acción retardada es el de la entrada de RED y
va antes de la fuente. Se separó en dos filas y se añadió la protección propia de
la placa, de **3 A**, porque el escenario de todas las cargas simultáneas son
45.08 W sobre 24 V, esto es 1.88 A. Es un rearmable de polímero y no un cartucho:
mantiene el criterio de agujero pasante, ocupa 5.1 mm entre islas frente a los 20
de un portafusibles de 5x20, y no hay que reponerlo tras un disparo.

**Tabla 31**, dos filas nuevas: el 2N7000 de la iluminación y el 1N5822 con su
referencia concreta en lugar de «Schottky de 3 A y 40 V».

**Sección 4.7.4.** Se declara qué convertidor cuelga de cada lado de la seta, que
es donde estaba el defecto.

**Sección 4.7.2, cuarto conductor del ventilador.** Queda sin conectar a
propósito. La sección 4.3 establece que su señal de modulación no garantiza la
detención, que es la razón de existir del transistor de lado bajo, y la secuencia
solo usa el ventilador al cien por cien. El conductor de realimentación de
velocidad sí se lleva al microcontrolador. Consta en la lista de componentes del
Anexo H.

## Valores calculados, con su procedencia

Todo sale de `calculo_pistas.py`, que se ejecuta con el Python del sistema.

| Magnitud | Valor | Criterio |
|---|---|---|
| Ancho, bus de 24 V | 0.75 mm | térmico, IPC-2221 |
| Ancho, riel de 12 V | 0.25 mm | térmico |
| Ancho, riel de la celda | 2.00 mm | caída de tensión |
| Ancho, riel de 5.1 V | 1.75 mm | caída de tensión |
| Ancho, riel de 3.3 V | 0.75 mm | caída de tensión |
| Separación entre conductores | 0.25 mm | mínimo de fabricación |
| Resistencia del límite de empuje | 56 kΩ | tope de 38.3 N sobre los 40 admitidos |
| Resistencia de puerta | 10 Ω | limita el pico del excitador a 1.2 A |
| Divisor del termistor | 33 kΩ | sensibilidad máxima entre 40 y 60 grados |

**Se dimensiona con IPC-2221 y no con IPC-2152 a propósito.** La vigente es la
2152, que al tener en cuenta la conductividad térmica del laminado admite anchos
menores. Usar la 2221 da anchos mayores, de modo que es una cota conservadora, y
no exige declarar la conductividad del laminado concreto, dato que no se tiene.

**En tres de los cinco rieles manda la caída de tensión y no el calentamiento.**
Una pista de 0.5 mm aguanta sobradamente 1.18 A sin calentarse, pero sobre los
80 mm de diagonal de la placa deja 102 mV, que en un riel de 5.1 V es el 2 por
ciento y la unidad de procesamiento no lo admite. El ancho se toma del más
exigente de los dos criterios.

## Una salvedad que hay que cerrar con medición

La resistencia de 56 kΩ traduce el tope de 40 N en un tope de corriente
suponiendo **proporcionalidad directa entre fuerza y corriente**, y el actuador
consume corriente incluso en vacío. El valor debe confirmarse con la medición de
fuerza contra corriente que el Anexo K tiene pendiente, antes de soldar la
resistencia definitiva. Si la proporcionalidad no se cumple, el tope real quedará
por debajo de los 40 N, que es el lado seguro pero puede impedir alcanzar la
fuerza necesaria.

## Disponibilidad en Perú

Todo el pasivo pasó a **agujero pasante**: resistencia axial de un cuarto de
vatio, condensador de disco, electrolítico radial y diodo DO-201. El montaje
superficial obliga a importar y a soldar con aire caliente, y un prototipo de
tesis se suelda y se repara a mano.

| Antes | Ahora | Por qué |
|---|---|---|
| Schottky SS54 y SS34, SMC | **1N5822**, DO-201AD | el 1N5822 está en cualquier tienda de Lima |
| BSS138, SOT-23 | **2N7000**, TO-92 | pasante, y sobra para los 0.2 A de la tira |
| TC4427 en SOIC-8 | **TC4427 en DIP-8** | zócalo, soldadura a mano |
| DRV8871 en HSOP-8 | **módulo de ruptura** sobre tira de contactos | el integrado suelto no se consigue |
| Resistencias y condensadores 0805 | axiales y de disco | mostrador |

Ojo con el 2N7000: numera S=1, G=2, D=3, distinto del BSS138. Mantener la
numeración anterior habría dejado la puerta a masa y el surtidor al mando.

**El TC4427 en DIP-8 es el único que puede exigir importación.** No es común en
tienda peruana. Si no aparece, la alternativa es un desplazador de nivel con dos
transistores pequeños y resistencias, todo de mostrador, a costa de contradecir
la Tabla 31.

## El microcontrolador: placa ESP32 DevKit V1 de 30 contactos

Resuelto. Se monta la placa de 35 soles, no el módulo suelto. Con eso
desaparecen del circuito el regulador AMS1117 con sus dos condensadores, la
subida de la patilla de habilitación y la cabecera de programación: la placa lo
trae todo a bordo, incluido el puente de USB a serie.

**Su símbolo y su huella no existen en KiCad y se generan con
`generar_devkit.py`.** El riesgo de dibujar una placa a mano es numerar mal su
tira de contactos, porque un número equivocado no lo detecta ninguna
comprobación. Aquí ese riesgo no existe: la numeración no se adivina sino que se
define en una sola tabla, y de esa misma tabla salen el símbolo y la huella, de
modo que el contacto N de uno y la isla N de la otra son el mismo punto físico
por construcción. Los nombres se leyeron de la serigrafía de la placa.

El orden es el de circuito integrado: del 1 al 15 bajando por la columna
izquierda y del 16 al 30 subiendo por la derecha, con la toma de USB abajo.

### Asignación de patillas

| Contacto | Serigrafía | Red | Criterio |
|---|---|---|---|
| 16 | VIN | +5V1 | entrada de alimentación de la placa |
| 14, 17 | GND | GND | |
| 15 | 3V3 | +3V3 | salida del regulador de la placa, alimenta el divisor del termistor |
| 23 | D25 | ACT_IN1 | salida sin restricción de arranque |
| 22 | D26 | ACT_IN2 | ídem |
| 21 | D27 | FAN_PWM | |
| 20 | D14 | LED_PWM | |
| 25 | D32 | PELT_EN | |
| 27 | D34 | NTC_SENSE | solo entrada, convertidor 1 |
| 26 | D35 | ESTOP_SENSE | solo entrada, convertidor 1 |
| 11 | D4 | FAN_TACH | |
| 9, 10 | TX2, RX2 | UART_TX, UART_RX | TX0 y RX0 quedan libres para la consola de USB |

**Verifica la separación entre tiras antes de fabricar.** La huella asume
25.4 mm entre las dos filas de contactos, que es lo habitual en esta placa, pero
conviene medirlo con calibre sobre la tuya.

## El circuito impreso

**100 por 80 mm, dos caras, 34 componentes colocados, cero violaciones de
colocación.** Se genera con `generar_placa.py`.

El tamaño responde a tres cosas: cabe holgado en el vano interior de la bandeja,
de 337 por 332 mm con 40 de altura libre; queda por debajo de los 100 por 100 que
casi todo fabricante cobra como tamaño base; y es la longitud con que se
dimensionaron los anchos de pista. La ocupación es del 36 por ciento, de modo que
sobra sitio para el ruteo.

**Los tres convertidores NO van sobre la placa.** Se montan en el piso de la
bandeja y llegan por cable a una tira de cuatro contactos. Así el diseño no
depende de unas medidas que varían entre fabricantes: las fichas publican 43 por
21 mm para el módulo del LM2596, pero la separación de sus agujeros no está
documentada y hay quien mide 52 por 20. Con la tira de contactos eso deja de
importar, y además el módulo se puede cambiar sin tocar la placa.

Lleva **plano de masa en la cara inferior**, que resuelve de una vez las
veintisiete conexiones de masa y da camino de retorno corto a las corrientes de
conmutación del ventilador y de la celda, que es donde nace el ruido que
molestaría a la entrada analógica del termistor. Queda definido pero sin
rellenar: el relleno se rehace después de rutear.

### Tres errores de colocación que hubo que corregir

**El contorno de la huella no está centrado en su ancla.** `SetPosition` coloca
por el punto de origen, que en un conector es la isla 1 y no el centro del
cuerpo. Suponer que estaba centrado dejó siete contornos superpuestos y cuatro
islas en cortocircuito.

**El giro intercambia los lados del contorno.** El DevKit mide 28 por 51 mm, pero
girado 90 grados ocupa 51 de ancho. No tenerlo en cuenta hizo que la región de
los conectores cayera encima de él.

**El 2N7000 en TO-92 sin abrir patillas** deja sus islas a 1.27 mm, que con
islas de 1.05 da 0.22 de separación, por debajo del mínimo de fabricación. Se
cambió a la variante con las patillas abiertas a 2.54, que además se suelda
mejor a mano.

## Modelos tridimensionales

KiCad trae los de todo lo normalizado: son 1 182 modelos entre las siete
bibliotecas que usa este diseño. El único que faltaba era el de la placa ESP32,
que no está en ningún catálogo por ser genérica. Se generó uno propio en
`generar_devkit.py`, de tres cajas: la placa, el módulo metálico y el conector de
USB. Para lo que sirve aquí, que es comprobar que el conjunto cabe en la bandeja
y no choca con nada, el volumen basta.

No hizo falta recurrir a GrabCAD ni a los catálogos de distribuidor.

## El ruteo

**Ruteada por completo: 162 pistas, 1 vía, 0 de 70 conexiones sin cerrar y un
solo aviso, cosmético, de serigrafía superpuesta.** Se hace con `rutear.py`.

El camino no es evidente y conviene dejarlo escrito:

1. `pcbnew` exporta al formato Specctra. **`kicad-cli` no sabe hacerlo**, solo la
   interfaz de Python.
2. `freerouting`, en Java, rutea y devuelve una sesión.
3. `pcbnew` importa la sesión y vuelca las pistas.
4. Se rellena el plano de masa y se comprueban las reglas.

### Tres cosas que costaron

**freerouting 2.4.1 guarda mal.** Rutea bien, deja la placa completa sin
violaciones, pero al guardar sin interfaz escribe un archivo de CERO BYTES y sale
con código 0: el fallo es silencioso. Una vez guardó bien y dos no, de modo que
es una carrera y no algo que se arregle con opciones. Se usa la **1.9.0**, que
hace el mismo trabajo y guarda siempre. Corre con Java 21; la 2.4.1 exige Java
25, y están instaladas las dos.

**Sin clases de red el ruteo sale inservible.** El primer intento dejó la placa
entera trazada y con 180 avisos de ancho de pista y 56 de separación, porque el
ruteador no adivina los anchos: los lee de las clases de red del proyecto, y no
había ninguna. Se escriben con `clases_de_red.py`, con los anchos que calcula
`calculo_pistas.py`. Con ellas los 236 avisos desaparecieron.

**El plano de masa va en las dos caras.** Con plano solo abajo, la franja bajo la
fila de convertidores se separaba del resto al pasar las pistas y dejaba islas
de masa sin conectar. Con plano arriba también, los componentes, que son todos
pasantes, unen las dos caras por sus propias islas, sin necesidad de vías de
cosido. Las masas que devuelven corriente de potencia, las de Q1, Q3 y el módulo
del actuador, van unidas de forma sólida y no por radios: un radio de 0.75 mm
admite 1.9 A según IPC-2221 y por el surtidor de Q3 vuelven los 2.58 A de la
celda.

### Clases de red

| Clase | Pista | Separación | Vía | Redes |
|---|---|---|---|---|
| Bus24 | 0.75 mm | 0.50 mm | 1.35 mm | entrada, bus, retorno del ventilador |
| Celda | 2.00 mm | 0.30 mm | 2.60 mm | riel de la celda y su retorno |
| R5V1 | 1.75 mm | 0.30 mm | 2.35 mm | unidad de procesamiento |
| R3V3 | 0.75 mm | 0.25 mm | 1.35 mm | microcontrolador |
| R12V | 0.50 mm | 0.30 mm | 1.10 mm | actuador e iluminación |
| Masa | 0.75 mm | 0.25 mm | 1.35 mm | GND |
| Default | 0.25 mm | 0.25 mm | 0.60 mm | señal |

## El plano: cómo se quitaron las superposiciones

Las corregiste dos veces a ojo y volvían. El problema era que KiCad coloca la
referencia y el valor a una distancia fija del símbolo sin mirar qué hay al
lado. Se resolvió con `comprobar_superposicion.py`, que lee las cajas de los 435
textos del PDF y las cruza todas contra todas. De 30 choques reales se pasó a
cero, arreglando cuatro causas distintas:

1. **El texto giraba con el símbolo.** KiCad suma el giro del símbolo al de su
   campo, de modo que el valor de una resistencia tumbada salía en vertical. Se
   resta.
2. **El alcance del símbolo se medía sin girar.** Un diodo de pie mide 7.62 mm
   de alto y el cálculo lo tomaba por 2, con lo que su valor caía sobre sus
   propios pines.
3. **La etiqueta quedaba pegada al pin** y tapaba su número. Se separan cuatro
   unidades de rejilla más, sumadas a la distancia que pida cada llamada para
   no perder el escalonado.
4. **El nombre de pin del diodo.** La biblioteca escribe A y K pegados al
   cuerpo y en un símbolo de 7.62 mm se pisan. Se ocultan: la banda del cátodo
   ya declara la polaridad.

El trabajo no está guardado en el PDF sino en el guion, de modo que si el
circuito cambia el plano vuelve a salir limpio.

## Un defecto que apareció al revisar: el fusible era de montaje superficial

La placa declaraba «todo en agujero pasante» y F1 llevaba huella 1206, que es
superficial. Contradicción real y en la lista de componentes de la tesis se
habría visto. Corregido con el rearmable de polímero.

## Lo que queda por hacer

1. **Medir la separación entre tiras del DevKit** con calibre cuando lo compres.
   La huella asume 25.4 mm, que es lo habitual en esta placa.
2. **Revisar el ruteo a ojo** antes de fabricar, en
   `TFC_Remocion/revision/placa_capas.pdf`. El ruteo automático cierra todas las
   conexiones pero no entiende de circuitos: conviene comprobar que el retorno
   de la celda y el del ventilador no dan un rodeo largo por el plano.
3. **El aviso sobre símbolos heredados** en el esquemático y el de serigrafía
   superpuesta en la placa son cosméticos.
4. **La resistencia de 56 kΩ** sigue dependiendo de la medición de fuerza contra
   corriente del Anexo K.
