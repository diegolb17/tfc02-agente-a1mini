# -*- coding: utf-8 -*-
"""Genera el esquematico de la unidad de control y potencia.

TODO SALE DE LA TESIS. Los componentes son los de la Tabla 31 del capitulo 4,
las corrientes las del inventario del Anexo E.6, los anchos de pista y los
valores de las resistencias criticas los que calcula calculo_pistas.py, y las
decisiones de seguridad las de la seccion 4.7.4 con la norma ISO 13850.

LAS DECISIONES QUE EL DOCUMENTO NO FIJABA, y que aqui hay que tomar para poder
dibujar, van marcadas con la palabra ELECCION en su comentario, para poder
llevarlas despues al texto.

La conexion entre bloques se hace con etiquetas globales y no con cables largos:
un esquematico de potencia cableado extremo a extremo se vuelve ilegible, y la
lista de redes es la misma.
"""
import os
import sys

import esquema
from esquema import g

BASE = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.join(BASE, 'TFC_Remocion')

# ---------------------------------------------------------------------------
# Constantes del diseño, todas con su procedencia
# ---------------------------------------------------------------------------
R_LIM_ACTUADOR = '56k'    # ITRIP = 64/56 = 1.14 A (hoja de datos del DRV8871). NO garantiza el
                          # tope de 40 N: el bloqueo del actuador es de 0.246 A. Pendiente (tesis 4.7.2)
R_DIVISOR_NTC = '33k'     # Tabla 31: óptimo entre 40 y 60 grados
# 45.08 W de escenario simultaneo sobre 24 V = 1.88 A. Se usa un rearmable de
# polimero y no un cartucho: es de agujero pasante como todo lo demas, ocupa
# 5.1 mm entre islas frente a los 20 de un portafusibles de 5x20, y no exige
# reponer nada tras un disparo. Retiene 3.0 A y dispara a 5.1 A.
# REVISION B (20 oct 2026): el de 3.0 A nunca actuaba antes que la proteccion de la fuente, que limita entre 2.4 y
# 3.3 A; se adopta uno de 1.6 A de retencion y 3.2 de disparo (Littelfuse RXEF160 o equivalente radial de 5.1 mm).
# KiCad no trae su huella: se usa la radial de 5.1 mm de la serie MF-RG, con el mismo paso.
FUSIBLE_PLACA = 'RXEF160  1.6A'
FP_FUSIBLE = 'Fuse:Fuse_Bourns_MF-RG300'
R_PUERTA = '10R'          # ELECCION: limita el pico del excitador a 1.2 A
R_BAJADA = '100k'         # ELECCION: mantiene la puerta a masa mientras el
                          # microcontrolador arranca y sus salidas están en alta
                          # impedancia, para que el ventilador no arranque solo

# TODO EN AGUJERO PASANTE, por disponibilidad y por soldadura.
#
# El montaje superficial obliga a comprar fuera y a soldar con aire caliente. En
# las tiendas de electronica de Lima lo que hay en mostrador es pasante: la
# resistencia axial de un cuarto de vatio, el condensador de disco, el
# electrolitico radial y el diodo DO-201. Un prototipo de tesis se suelda a mano
# y se repara a mano, de modo que la eleccion no es de gusto sino de que el
# trabajo se pueda terminar en Lima sin esperar una importacion.
FP_R = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
FP_C = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
FP_CE = 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm'
FP_D = 'Diode_THT:D_DO-201AD_P15.24mm_Horizontal'
FP_DIP8 = 'Package_DIP:DIP-8_W7.62mm'
FP_CONN6 = 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical'
# El DRV8871 va en tira de 8: con 6 contactos el pin 8 del simbolo (OUT2) quedaba sin isla y el
# actuador sin su segundo borne; la red tenia una sola isla y ni ERC ni DRC lo detectaban (12 oct 2026).
FP_CONN8 = 'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical'
FP_CONN2 = 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
FP_CONN3 = 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'
FP_CONN4 = 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'
FP_CONN5 = 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical'
FP_CE5 = 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm'
FP_D35 = 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal'


def pin(h, lib, ref_xy, rot, num):
    return h.pin_xy(lib, ref_xy[0], ref_xy[1], rot, num)


# Separacion minima entre el pin y su etiqueta, en unidades de rejilla.
#
# Se suma a la que pida cada llamada, de modo que el escalonado que evita que
# dos etiquetas de un mismo conector se toquen sigue siendo el mismo. Sin ella
# la etiqueta quedaba pegada al simbolo y su recuadro caia sobre el NUMERO del
# pin, que es texto de 1.27 mm: no se ve al mirar la hoja entera y se lee mal
# al ampliar, que es justo lo que hace quien revisa un plano.
SEPARACION_ETIQUETA = 4


def conectar(h, lib, xy, rot, num, etiqueta, largo=5, sentido='der'):
    """Saca un cable corto del pin y le pone una etiqueta global."""
    px, py = pin(h, lib, xy, rot, num)
    largo = largo + SEPARACION_ETIQUETA
    dx = {'der': g(largo), 'izq': -g(largo)}.get(sentido, 0)
    dy = {'arr': -g(largo), 'aba': g(largo)}.get(sentido, 0)
    qx, qy = px + dx, py + dy
    h.cable(px, py, qx, qy)
    h.etiqueta(etiqueta, qx, qy, 0 if sentido == 'der' else 180)
    return qx, qy


def bloque_entrada(h, x0, y0):
    """Entrada de 24 V, proteccion y parada de emergencia."""
    h.texto('ENTRADA 24 V, PROTECCION Y PARADA DE EMERGENCIA', x0, y0 - g(12), 2.2)

    # conector desde la fuente Mean Well LRS-50-24
    LC = 'Connector_Generic:Conn_01x02'
    j1 = (x0, y0)
    h.componente(LC, 'J1', '24V DC in', j1[0], j1[1], 0, FP_CONN2,
                 {'Nota': 'desde LRS-50-24'})
    conectar(h, LC, j1, 0, 1, 'V24_BRUTO', largo=5)
    conectar(h, LC, j1, 0, 2, 'GND', largo=11)

    # fusible del lado de continua. El de 1 A de la Tabla 31 es el de RED y va
    # en la entrada de la fuente, no aqui: a la placa llegan ya los 24 V.
    LF = 'Device:Fuse'
    f1 = (x0 + g(34), y0)
    h.componente(LF, 'F1', FUSIBLE_PLACA, f1[0], f1[1], 90, FP_FUSIBLE,
                 {'Nota': 'rearmable, 1.6 A de retención y 3.2 de disparo'})
    conectar(h, LF, f1, 90, 1, 'V24_BRUTO', sentido='izq', largo=8)
    conectar(h, LF, f1, 90, 2, 'V24_FUS', largo=8)

    # proteccion contra inversion de polaridad, en serie
    LD = 'Diode:1N5822'
    d1 = (x0 + g(66), y0)
    h.componente(LD, 'D1', '1N5822  40V 3A', d1[0], d1[1], 90, FP_D)
    conectar(h, LD, d1, 90, 2, 'V24_FUS', sentido='izq', largo=8)
    conectar(h, LD, d1, 90, 1, '+24V', largo=8)

    # REVISION B: reserva de la entrada de 24 V, donde conmuta el actuador
    LCE = 'Device:C_Polarized'
    c8 = (x0 + g(84), y0 + g(16))
    h.componente(LCE, 'C8', '100uF 35V', c8[0], c8[1], 0, FP_CE)
    conectar(h, LCE, c8, 0, 1, '+24V', sentido='arr', largo=3)
    conectar(h, LCE, c8, 0, 2, 'GND', sentido='aba', largo=1)

    # parada de emergencia: contacto normalmente cerrado de apertura positiva,
    # ISO 13850. Corta el riel de los ACTUADORES y no el de control, conforme a
    # la clausula 5.3.5 de la IEC 60204-1 que la seccion 4.7.4 invoca.
    j2 = (x0 + g(98), y0)
    h.componente(LC, 'J2', 'Botón emergencia NC', j2[0], j2[1], 0, FP_CONN2,
                 {'Nota': 'ISO 13850, apertura positiva'})
    conectar(h, LC, j2, 0, 1, '+24V', sentido='izq', largo=5)
    conectar(h, LC, j2, 0, 2, '+24V_ACT', largo=5)

    # el microcontrolador debe SABER si la seta esta pulsada, para informarlo.
    # ELECCION: divisor de 100k/15k desde +24V_ACT, que da 3.13 V con la seta
    # liberada y 0 con ella pulsada.
    LR = 'Device:R'
    r7 = (x0 + g(126), y0 + g(4))
    r8 = (x0 + g(126), y0 + g(16))
    h.componente(LR, 'R7', '100k', r7[0], r7[1], 0, FP_R)
    h.componente(LR, 'R8', '15k', r8[0], r8[1], 0, FP_R)
    conectar(h, LR, r7, 0, 1, '+24V_ACT', sentido='arr')
    p1 = pin(h, LR, r7, 0, 2)
    p2 = pin(h, LR, r8, 0, 1)
    h.cable(p1[0], p1[1], p2[0], p2[1])
    h.etiqueta('ESTOP_SENSE', p1[0], p1[1])
    conectar(h, LR, r8, 0, 2, 'GND', sentido='aba')


def bloque_convertidores(h, x0, y0):
    """Los tres convertidores reductores, como modulos de cuatro terminales."""
    h.texto('CONVERTIDORES REDUCTORES', x0, y0 - g(12), 2.2)
    LC = 'Connector_Generic:Conn_01x04'
    # (referencia, valor, salida, riel de ENTRADA, desplazamiento)
    mods = [
        ('U1', 'LM2596 ajustable', '+12V', '+24V_ACT', 0),
        ('U2', 'MP1584 ajustable', '+5V1', '+24V', 34),
    ]
    for ref, valor, salida, entrada, dx in mods:
        m = (x0 + g(dx), y0)
        h.componente(LC, ref, valor, m[0], m[1], 0, FP_CONN4,
                     {'Nota': 'módulo, no componente discreto',
                      'Corte': 'tras el botón de emergencia' if entrada == '+24V_ACT'
                               else 'permanente'})
        # las etiquetas salen escalonadas: a la misma distancia se tocan, porque
        # los contactos distan 2.54 mm y el rotulo mide casi eso de alto
        conectar(h, LC, m, 0, 1, entrada, sentido='izq', largo=9)
        conectar(h, LC, m, 0, 2, 'GND', sentido='izq', largo=5)
        conectar(h, LC, m, 0, 3, salida, largo=5)
        conectar(h, LC, m, 0, 4, 'GND', largo=9)


def bloque_ventilador(h, x0, y0):
    """Etapa del ventilador principal, REVISION B: alimentado siempre y gobernado por su entrada de modulacion.

    En la revision A el ventilador se conmutaba con Q1 en el lado bajo: su negativo quedaba flotando y el tacometro,
    de colector abierto referido a ese negativo, podia llevar hasta 24 V a una entrada de 3.6 V como maximo. La ficha
    del Delta PFB0924GHEP6 admite 2.8 V de nivel alto en la entrada de modulacion y detiene el rotor con ciclo nulo,
    de modo que basta gobernarlo por ella y se retiran Q1, R2 y D2."""
    h.texto('ETAPA DEL VENTILADOR PRINCIPAL', x0, y0 - g(12), 2.2)
    LR = 'Device:R'
    # serie de la linea de modulacion: limita la corriente si el cable se cortocircuita
    r12 = (x0 + g(12), y0 + g(4))
    h.componente(LR, 'R12', '100R', r12[0], r12[1], 90, FP_R)
    conectar(h, LR, r12, 90, 1, 'FAN_PWM', sentido='izq')
    conectar(h, LR, r12, 90, 2, 'FAN_PWM_V', sentido='der')
    # tacometro: colector abierto, polarizado a 3.3 V, con serie y diodo de fijacion al riel de 3.3 V
    r11 = (x0 + g(12), y0 + g(16))
    h.componente(LR, 'R11', '1k', r11[0], r11[1], 90, FP_R)
    conectar(h, LR, r11, 90, 1, 'FAN_TACH', sentido='izq')
    conectar(h, LR, r11, 90, 2, 'FAN_TACH_V', sentido='der')
    r10 = (x0 + g(44), y0 + g(16))
    h.componente(LR, 'R10', '10k', r10[0], r10[1], 0, FP_R)
    conectar(h, LR, r10, 0, 1, '+3V3', sentido='arr', largo=2)
    conectar(h, LR, r10, 0, 2, 'FAN_TACH', sentido='aba', largo=2)
    LD = 'Diode:1N4148'
    # catodo arriba, al riel de 3.3 V; anodo abajo, a la entrada del microcontrolador
    d3 = (x0 + g(58), y0 + g(16))
    h.componente(LD, 'D3', '1N4148', d3[0], d3[1], 270, FP_D35)
    conectar(h, LD, d3, 270, 1, '+3V3', sentido='arr', largo=2)
    conectar(h, LD, d3, 270, 2, 'FAN_TACH', sentido='aba', largo=2)
    # conector del ventilador de cuatro conductores, los cuatro conectados
    LC4 = 'Connector_Generic:Conn_01x04'
    j3 = (x0 + g(92), y0 + g(8))
    h.componente(LC4, 'J3', 'Vent. principal', j3[0], j3[1], 0, FP_CONN4)
    conectar(h, LC4, j3, 0, 1, 'GND', sentido='izq', largo=5)
    conectar(h, LC4, j3, 0, 2, '+24V_ACT', sentido='izq', largo=13)
    conectar(h, LC4, j3, 0, 3, 'FAN_TACH_V', sentido='izq', largo=5)
    conectar(h, LC4, j3, 0, 4, 'FAN_PWM_V', sentido='izq', largo=13)


def bloque_actuador(h, x0, y0):
    """Etapa del actuador lineal, con el limite de corriente por resistencia."""
    h.texto('ETAPA DEL ACTUADOR LINEAL', x0, y0 - g(12), 2.2)

    LU = 'Driver_Motor:DRV8871DDA'
    u6 = (x0 + g(12), y0 + g(10))
    h.componente(LU, 'U6', 'DRV8871', u6[0], u6[1], 0,
                 FP_CONN8,
                 {'Nota': 'módulo de ruptura sobre tira de contactos'})
    # numeracion real de la biblioteca: IN1=3, IN2=2, ILIM=4, VM=5, OUT1=6,
    # OUT2=8, y la masa en 1, 7 y 9
    conectar(h, LU, u6, 0, 3, 'ACT_IN1', sentido='izq', largo=9)
    conectar(h, LU, u6, 0, 2, 'ACT_IN2', sentido='izq', largo=9)
    conectar(h, LU, u6, 0, 5, '+12V', sentido='arr')
    conectar(h, LU, u6, 0, 6, 'ACT_OUT1', largo=5)
    conectar(h, LU, u6, 0, 8, 'ACT_OUT2', largo=11)
    conectar(h, LU, u6, 0, 1, 'GND', sentido='aba')

    # la resistencia que fija el tope de empuje en 38.3 N, por debajo de los 40
    # que admite la seccion 4.4. Va por circuito y no por programa, de modo que
    # el limite no dependa del estado del dominio logico.
    LR = 'Device:R'
    r3 = (x0 + g(30), y0 + g(26))
    h.componente(LR, 'R3', R_LIM_ACTUADOR, r3[0], r3[1], 0, FP_R,
                 {'Nota': 'fija 1.14 A, no garantiza tope de fuerza'})
    conectar(h, LR, r3, 0, 1, 'ACT_ILIM', sentido='arr')
    conectar(h, LR, r3, 0, 2, 'GND', sentido='aba')
    conectar(h, LU, u6, 0, 4, 'ACT_ILIM', largo=6, sentido='aba')

    # condensador de reserva junto a la etapa, que el arranque del motor exige
    LCE = 'Device:C_Polarized'
    # abajo y a la derecha: en su sitio anterior su etiqueta de +12 V caia
    # sobre la de ACT_OUT2 del conector del actuador
    c3 = (x0 + g(54), y0 + g(32))
    h.componente(LCE, 'C3', '100uF 25V', c3[0], c3[1], 0, FP_CE)
    conectar(h, LCE, c3, 0, 1, '+12V', sentido='arr')
    conectar(h, LCE, c3, 0, 2, 'GND', sentido='aba')

    LC5 = 'Connector_Generic:Conn_01x05'
    j4 = (x0 + g(76), y0 + g(10))
    # REVISION B: variante L12-P, motor y potenciometro de posicion
    h.componente(LC5, 'J4', 'Actuador L12-P', j4[0], j4[1], 0, FP_CONN5)
    conectar(h, LC5, j4, 0, 1, 'ACT_OUT1', sentido='izq', largo=5)
    conectar(h, LC5, j4, 0, 2, 'ACT_OUT2', sentido='izq', largo=15)
    conectar(h, LC5, j4, 0, 3, '+3V3', sentido='izq', largo=5)
    conectar(h, LC5, j4, 0, 4, 'ACT_POS', sentido='izq', largo=15)
    conectar(h, LC5, j4, 0, 5, 'GND', sentido='izq', largo=5)
    # filtro del cursor del potenciometro, junto a la entrada analogica
    LCC = 'Device:C'
    c5 = (x0 + g(42), y0 + g(32))
    h.componente(LCC, 'C5', '100nF', c5[0], c5[1], 0, FP_C)
    conectar(h, LCC, c5, 0, 1, 'ACT_POS', sentido='arr', largo=2)
    conectar(h, LCC, c5, 0, 2, 'GND', sentido='aba', largo=1)


def bloque_iluminacion(h, x0, y0):
    """Conmutacion del dicroico MR16 de 12 V y 6 W (0.5 A) en lado bajo, REVISION B.

    El IRLZ44N esta caracterizado desde 4 V de puerta y no a 3.3, de modo que lo acciona el TC4427 alimentado a 12 V,
    con R1 de 10 ohm en la puerta y R9 de 100 k de bajada, que la sujeta mientras el excitador no esta alimentado.
    El segundo canal del excitador queda libre, con su entrada a masa."""
    h.texto('UNIDAD DE ILUMINACION', x0, y0 - g(12), 2.2)
    LU = 'Driver_FET:TC4427xOA'
    u5 = (x0 + g(10), y0 + g(10))
    h.componente(LU, 'U5', 'TC4427', u5[0], u5[1], 0, FP_DIP8)
    conectar(h, LU, u5, 0, 6, '+12V', sentido='arr')
    conectar(h, LU, u5, 0, 3, 'GND', sentido='aba')
    conectar(h, LU, u5, 0, 2, 'LED_PWM', sentido='izq', largo=9)
    conectar(h, LU, u5, 0, 4, 'GND', sentido='izq', largo=3)
    h.no_conectado(LU, u5, 0, 1)
    h.no_conectado(LU, u5, 0, 8)
    h.no_conectado(LU, u5, 0, 5)
    LR = 'Device:R'
    LQ = 'Transistor_FET:IRLZ44N'
    r1 = (x0 + g(26), y0 + g(10))
    h.componente(LR, 'R1', '10R', r1[0], r1[1], 270, FP_R)
    ps = pin(h, LU, u5, 0, 7)
    pr = pin(h, LR, r1, 270, 1)
    h.cable(ps[0], ps[1], pr[0], pr[1])
    q2 = (x0 + g(38), y0 + g(10))
    h.componente(LQ, 'Q2', 'IRLZ44N', q2[0], q2[1], 0, 'Package_TO_SOT_THT:TO-220-3_Vertical')
    pg = pin(h, LQ, q2, 0, 1)
    pr2 = pin(h, LR, r1, 270, 2)
    h.cable(pr2[0], pr2[1], pg[0], pg[1])
    conectar(h, LQ, q2, 0, 2, 'LED_RET')
    conectar(h, LQ, q2, 0, 3, 'GND', sentido='aba')
    r9 = (x0 + g(32), y0 + g(22))
    h.componente(LR, 'R9', '100k', r9[0], r9[1], 0, FP_R)
    pb = pin(h, LR, r9, 0, 1)
    h.cable(pg[0], pg[1], pg[0], pb[1])
    h.cable(pg[0], pb[1], pb[0], pb[1])
    conectar(h, LR, r9, 0, 2, 'GND', sentido='aba', largo=1)
    # desacoplo del excitador, junto a su alimentacion
    LCC = 'Device:C'
    LCE = 'Device:C_Polarized'
    c6 = (x0 - g(10), y0 + g(32))
    c7 = (x0 - g(2), y0 + g(32))
    h.componente(LCC, 'C6', '100nF', c6[0], c6[1], 0, FP_C)
    h.componente(LCE, 'C7', '4.7uF 25V', c7[0], c7[1], 0, FP_CE5)
    for lib, c in ((LCC, c6), (LCE, c7)):
        conectar(h, lib, c, 0, 1, '+12V', sentido='arr', largo=2)
        conectar(h, lib, c, 0, 2, 'GND', sentido='aba', largo=1)
    LC2 = 'Connector_Generic:Conn_01x02'
    j6 = (x0 + g(68), y0 + g(10))
    h.componente(LC2, 'J6', 'Dicroico 12V 6W', j6[0], j6[1], 0, FP_CONN2)
    conectar(h, LC2, j6, 0, 1, '+12V', sentido='izq')
    conectar(h, LC2, j6, 0, 2, 'LED_RET', sentido='izq', largo=11)


def bloque_microcontrolador(h, x0, y0):
    """La placa de desarrollo ESP32 DevKit V1 y sus conexiones.

    Se monta la PLACA y no el modulo desnudo. Es lo que se vende en Lima, y trae
    resueltos a bordo el regulador de 3.3 V, el puente de USB a serie y los
    pulsadores de arranque y descarga, de modo que desaparecen de esta placa el
    AMS1117, su condensadores, la subida de EN y la cabecera de programacion.

    Su simbolo y su huella no existen en las bibliotecas de KiCad y se generan
    con generar_devkit.py, los dos desde la misma tabla de contactos.
    """
    h.texto('MICROCONTROLADOR', x0, y0 - g(12), 2.2)
    LU = 'TFC:ESP32-DevKitV1-30'
    u4 = (x0 + g(24), y0 + g(26))
    h.componente(LU, 'U4', 'ESP32 DevKit V1', u4[0], u4[1], 0,
                 'TFC:ESP32_DevKitV1_30pin',
                 {'Nota': 'placa de 30 contactos, no el módulo suelto'})

    # alimentacion: entra por VIN desde el riel de 5.1 V y la placa produce sus
    # propios 3.3 V, que alimentan el potenciometro del actuador y la polarizacion del tacometro
    # Del 1 al 15 la columna es la izquierda y del 16 al 30 la derecha, de modo
    # que el cable ha de salir hacia fuera en cada caso. Las longitudes van
    # escalonadas porque los cuatro contactos son consecutivos y sus rotulos, a
    # la misma distancia, se montan unos sobre otros.
    conectar(h, LU, u4, 0, 16, '+5V1', largo=10)
    conectar(h, LU, u4, 0, 17, 'GND', largo=4)
    conectar(h, LU, u4, 0, 14, 'GND', sentido='izq', largo=4)
    conectar(h, LU, u4, 0, 15, '+3V3', sentido='izq', largo=10)

    # ELECCION de patillas, con el criterio entre parentesis:
    #   D25 y D26 al puente del actuador   (salidas sin restriccion de arranque)
    #   D27 a la modulacion del ventilador
    #   D14 a la iluminacion
    #   D32 a la habilitacion de la celda
    #   D34 y D35 a las entradas analogicas (solo entrada, del convertidor 1)
    #   D4  a la realimentacion de velocidad del ventilador
    #   TX2 y RX2 al enlace serie con el computador, dejando TX0 y RX0 libres
    #   para la consola de USB de la propia placa
    asign = [(23, 'ACT_IN1'), (22, 'ACT_IN2'), (21, 'FAN_PWM'),
             (20, 'LED_PWM'), (27, 'ACT_POS'),
             (26, 'ESTOP_SENSE'), (11, 'FAN_TACH'),
             (9, 'UART_TX'), (10, 'UART_RX')]
    for k, (num, red) in enumerate(asign):
        sentido = 'izq' if num <= 15 else 'der'
        conectar(h, LU, u4, 0, num, red, sentido=sentido,
                 largo=4 if k % 2 == 0 else 9)

    # las patillas que el diseno deja libres, declaradas como tales
    for num in (1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 18, 19, 24, 25, 28, 29, 30):
        h.no_conectado(LU, u4, 0, num)



def bloque_salidas(h, x0, y0):
    """Conectores de los elementos que no llevan etapa propia en la placa."""
    h.texto('CONECTORES DE SALIDA Y ENLACE', x0, y0 - g(12), 2.2)
    LC2 = 'Connector_Generic:Conn_01x02'
    LC4 = 'Connector_Generic:Conn_01x04'

    salidas = [
        ('J8', 'Vent. extracción', '+24V', 'GND', 0),
        # El modulo de camara se enlaza SOLO por alimentacion: entrega la
        # imagen por red inalambrica, conforme a la seccion 4.5.1, de modo que
        # no hay senal que traer a la placa.
        ('J12', 'Módulo de cámara', '+5V1', 'GND', 14),
    ]
    for ref, valor, a, b, dy in salidas:
        j = (x0, y0 + g(dy))
        h.componente(LC2, ref, valor, j[0], j[1], 0, FP_CONN2)
        conectar(h, LC2, j, 0, 1, a, sentido='izq', largo=5)
        conectar(h, LC2, j, 0, 2, b, sentido='izq', largo=11)

    # enlace con el computador de placa unica: alimentacion y puerto serie.
    # La seccion 5.1 establece que este enlace es CABLEADO y no inalambrico.
    j11 = (x0 + g(24), y0 + g(8))
    h.componente(LC4, 'J11', 'Enlace Raspberry Pi', j11[0], j11[1], 0, FP_CONN4)
    conectar(h, LC4, j11, 0, 1, '+5V1', sentido='izq', largo=5)
    conectar(h, LC4, j11, 0, 2, 'GND', sentido='izq', largo=11)
    conectar(h, LC4, j11, 0, 3, 'UART_TX', sentido='izq', largo=5)
    conectar(h, LC4, j11, 0, 4, 'UART_RX', sentido='izq', largo=11)

    # REVISION B: los picos de transmision del modulo de camara reinician el modulo; reserva junto a J11 y J12
    LCE = 'Device:C_Polarized'
    LCC = 'Device:C'
    c9 = (x0 + g(40), y0 + g(12))
    c10 = (x0 + g(50), y0 + g(12))
    h.componente(LCE, 'C9', '470uF 16V', c9[0], c9[1], 0, FP_CE)
    h.componente(LCC, 'C10', '100nF', c10[0], c10[1], 0, FP_C)
    for lib, c in ((LCE, c9), (LCC, c10)):
        conectar(h, lib, c, 0, 1, '+5V1', sentido='arr', largo=2)
        conectar(h, lib, c, 0, 2, 'GND', sentido='aba', largo=1)


def bloque_banderas(h, x0, y0):
    """Banderas de alimentacion sobre cada riel.

    La comprobacion de reglas exige saber quien ALIMENTA cada red de potencia.
    En esta placa nadie la alimenta desde dentro: los cinco rieles entran por
    conector, desde la fuente y desde los modulos convertidores. La bandera es
    la forma normalizada de declararselo."""
    h.texto('DECLARACION DE ALIMENTACION', x0, y0 - g(12), 2.2)
    # El riel de 3.3 V NO lleva bandera: lo alimenta el regulador U7, que ya es
    # una salida de potencia, y poner las dos hace que la comprobacion vea dos
    # fuentes sobre la misma red.
    for k, red in enumerate(['+24V', '+24V_ACT', '+12V', '+5V1',
                             'GND', 'V24_BRUTO']):
        x = x0 + g(16 * (k % 4))
        y = y0 + g(26 * (k // 4))
        h.bandera(red, x, y)


def main():
    if not os.path.isdir(PROY):
        os.makedirs(PROY)
    # REVISION B (20 oct 2026): cambios de la Tabla H1 del Anexo H
    h = esquema.Hoja('Unidad de control y potencia  TFC02  rev. B', 'A2')

    # Reparto sobre la hoja A2, de 594 por 420 mm. La columna izquierda lleva
    # la cadena de potencia de arriba abajo, en el orden en que circula la
    # energia, y la derecha el gobierno y las salidas.
    # LA COLUMNA IZQUIERDA NO ARRANCA EN EL MARGEN. Las etiquetas de entrada
    # de los convertidores salen HACIA LA IZQUIERDA del simbolo, de modo que
    # con el bloque pegado al margen su rotulo caia fuera del marco de la hoja.
    IZQ = g(44)
    bloque_entrada(h, IZQ, g(26))
    bloque_convertidores(h, IZQ, g(72))
    bloque_ventilador(h, IZQ, g(112))
    bloque_actuador(h, IZQ, g(186))
    bloque_iluminacion(h, g(170), g(186))
    bloque_microcontrolador(h, g(250), g(26))
    bloque_salidas(h, g(185), g(112))
    bloque_banderas(h, g(270), g(196))

    ruta = os.path.join(PROY, 'TFC_Remocion.kicad_sch')
    h.guardar(ruta)
    sys.stdout.write('esquemático generado con %d componentes\n'
                     % len(h.instancias))
    sys.stdout.write('  %s\n' % ruta)
    for ref, lib, val, fp in sorted(h.instancias):
        if not ref.startswith('#'):
            sys.stdout.write('    %-5s %-22s %s\n' % (ref, val, lib))


if __name__ == '__main__':
    main()
