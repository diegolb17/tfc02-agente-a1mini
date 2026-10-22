# -*- coding: utf-8 -*-
"""Láminas eléctricas y electrónicas del Anexo H, con el mismo cajetín PUCP que las mecánicas.

    python electricos.py              todas
    python electricos.py ELE-0-01     una

ELE-0-01  Esquema eléctrico general (red, protecciones, fuente, placa y cargas)    A3  S/E
ELE-0-02  Lista de elementos y de cableado                                          A3  S/E
ELE-1-01  Esquemático de la unidad de control y potencia (desde KiCad)              A2  S/E
ELE-1-02  Emplazamiento de componentes del circuito impreso (desde KiCad)           A3  2:1
ELE-2-01  Cara superior de cobre (desde KiCad)                                      A3  2:1
ELE-2-02  Cara inferior de cobre (desde KiCad)                                      A3  2:1

Los esquemas usan símbolos IEC 60617 y designación de referencia IEC 81346. Las láminas de KiCad
se insertan como vectores (show_pdf_page), sin rasterizar. Salida: laminas_ele/ y _rev/."""
import os
import sys
import math
import subprocess
import tempfile

import fitz

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from motor.hoja import Lamina, tabla, MM          # noqa: E402

SALIDA = os.path.join(AQUI, 'laminas_ele')
FECHA = '21.10.2026'
REVISION_ELE = 'B'      # revision B de la placa (Tabla H1 del Anexo H)
ELEC = os.path.normpath(os.path.join(AQUI, '..', 'ELECTRONICA', 'TFC_Remocion'))
SCH = os.path.join(ELEC, 'TFC_Remocion.kicad_sch')
PCB = os.path.join(ELEC, 'TFC_Remocion.kicad_pcb')
CLI = r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'

FILA_ESQ = [('NORMA DE SÍMBOLOS', 'IEC 60617'), ('TENSIONES', '220 V CA / 24 V CC'), ('DESIGNACIÓN', 'IEC 81346')]
FILA_PCB = [('ACABADO', 'HASL, MÁSCARA VERDE'), ('NORMA DE DISEÑO', 'IPC-2221, CLASE 2'),
            ('MATERIAL', 'FR-4, 1.6 mm, Cu 35 µm')]


def datos(codigo, titulo, escala, formato='A3', pcb=False):
    return {'titulo': titulo, 'codigo': codigo, 'escala': escala, 'formato': formato, 'fecha': FECHA,
            'fila1': FILA_PCB if pcb else FILA_ESQ, 'proyeccion': pcb, 'revision': REVISION_ELE}


# =============================================================================
# Símbolos IEC 60617 (coordenadas de hoja en mm, origen abajo a la izquierda)
# =============================================================================
T_REF = 2.6     # designación de referencia
T_DES = 2.1     # descripción
T_PIN = 1.9     # número de borne


def borne(lam, x, y, r=0.75):
    lam.circulo((x, y), r, 'fina')


def nodo(lam, x, y):
    lam.punto((x, y), 0.6)


def cable(lam, pts, estilo='visible'):
    lam.polilinea(pts, estilo)


def fusible_h(lam, xc, y, w=8.0, h=2.8):
    lam.polilinea([(xc - w / 2, y - h / 2), (xc + w / 2, y - h / 2), (xc + w / 2, y + h / 2), (xc - w / 2, y + h / 2)],
                  'visible', cerrar=True)
    lam.linea((xc - w / 2, y), (xc + w / 2, y), 'fina')


def diodo_h(lam, xc, y, s=3.2):
    """Diodo con el ánodo a la izquierda y el cátodo a la derecha."""
    lam.polilinea([(xc - s / 2, y - s / 2), (xc + s / 2, y), (xc - s / 2, y + s / 2)], 'visible', cerrar=True)
    lam.linea((xc + s / 2, y - s / 2), (xc + s / 2, y + s / 2), 'visible')


def contacto_na(lam, x0, x1, y):
    """Contacto normalmente abierto horizontal entre x0 y x1; devuelve el punto medio de la cuchilla."""
    xa = x0 + (x1 - x0) * 0.32
    xb = x1 - (x1 - x0) * 0.32
    lam.linea((x0, y), (xa, y), 'visible')
    lam.linea((xb, y), (x1, y), 'visible')
    lam.linea((xa, y), (xb + 0.6, y + 2.6), 'visible')
    return ((xa + xb) / 2, y + 1.3)


def contacto_nc(lam, x0, x1, y):
    """Contacto normalmente cerrado horizontal: la cuchilla apoya bajo el tope del lado derecho."""
    xa = x0 + (x1 - x0) * 0.32
    xb = x1 - (x1 - x0) * 0.32
    lam.linea((x0, y), (xa, y), 'visible')
    lam.linea((xb, y), (x1, y), 'visible')
    lam.linea((xb, y), (xb, y - 2.4), 'visible')
    lam.linea((xa, y), (xb + 0.8, y - 2.4), 'visible')
    return ((xa + xb) / 2, y - 1.2)


def circulo_carga(lam, xc, yc, r, ys, x_borne, texto='M', sub='='):
    """Máquina o lámpara con conductores horizontales que llegan desde x_borne a las alturas ys."""
    lam.circulo((xc, yc), r, 'visible')
    for y in ys:
        dy = y - yc
        dx = math.sqrt(max(r * r - dy * dy, 0.0))
        lam.linea((x_borne, y), (xc - dx, y), 'visible')
    if texto == 'X':
        k = r / math.sqrt(2)
        lam.linea((xc - k, yc - k), (xc + k, yc + k), 'visible')
        lam.linea((xc - k, yc + k), (xc + k, yc - k), 'visible')
    elif texto:
        lam.texto(xc, yc - (0.2 if sub else 1.0), texto, 3.2, 0, 'c', negrita=True)
        if sub:
            lam.texto(xc, yc - r * 0.62, sub, 2.4, 0, 'c')


def ntc(lam, xc, y1, y2, x_borne):
    """Termistor NTC vertical entre las alturas y1 > y2 (símbolo de resistencia con la diagonal de -t)."""
    w, h = 2.6, (y1 - y2) * 0.55
    ym = (y1 + y2) / 2
    lam.linea((x_borne, y1), (xc, y1), 'visible')
    lam.linea((x_borne, y2), (xc, y2), 'visible')
    lam.linea((xc, y1), (xc, ym + h / 2), 'visible')
    lam.linea((xc, y2), (xc, ym - h / 2), 'visible')
    lam.polilinea([(xc - w / 2, ym - h / 2), (xc + w / 2, ym - h / 2), (xc + w / 2, ym + h / 2), (xc - w / 2, ym + h / 2)],
                  'visible', cerrar=True)
    lam.linea((xc - 2.6, ym - h / 2 - 0.8), (xc + 2.6, ym + h / 2 + 0.8), 'fina')
    lam.linea((xc - 2.6, ym - h / 2 - 0.8), (xc - 3.8, ym - h / 2 - 0.8), 'fina')
    lam.texto(xc + 3.2, ym - 0.7, '-t°', 2.0, 0, 'l')


def tierra_proteccion(lam, x, y):
    """Símbolo de tierra de protección (IEC 60417-5019) colgando del punto (x, y)."""
    lam.linea((x, y), (x, y - 2.2), 'visible')
    for k, w in enumerate((3.6, 2.4, 1.2)):
        yy = y - 2.2 - k * 0.8
        lam.linea((x - w / 2, yy), (x + w / 2, yy), 'visible')
    lam.circulo((x, y - 3.0), 2.9, 'fina')


def convertidor(lam, x0, y0, w, h, ent='~', sal='='):
    lam.polilinea([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)], 'visible', cerrar=True)
    lam.linea((x0, y0), (x0 + w, y0 + h), 'fina')
    lam.texto(x0 + w * 0.27, y0 + h * 0.62, ent, 4.2, 0, 'c', negrita=True)
    lam.texto(x0 + w * 0.73, y0 + h * 0.16, sal, 4.2, 0, 'c', negrita=True)


def rect(lam, x0, y0, x1, y1, estilo='visible'):
    lam.polilinea([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], estilo, cerrar=True)


def limite(lam, x0, y0, x1, y1):
    """Límite de conjunto (línea de trazo y doble punto)."""
    rect(lam, x0, y0, x1, y1, 'fantasma')


def etiqueta_cable(lam, x, y, w):
    lam.texto(x, y + 0.9, w, 1.8, 0, 'c')


# =============================================================================
# ELE-0-01  Esquema eléctrico general
# =============================================================================
def ele_0_01():
    lam = Lamina('A3')
    lam.texto(20, 278, 'ESQUEMA ELÉCTRICO GENERAL DEL SISTEMA', 4.0, 0, 'l', negrita=True)
    lam.texto(20, 272.5, 'Cadena de alimentación, protecciones, parada de emergencia y conexión de las cargas a la placa A1.'
              ' El detalle de A1 está en ELE-1-01; secciones y colores en ELE-0-02.', 2.2, 0, 'l')

    yL, yN, yPE = 232.0, 220.0, 198.0
    # ---------------- red y módulo de entrada X1 -----------------------------------------------
    lam.texto(14, 266, 'RED 220 V CA, 60 Hz', 2.4, 0, 'l', negrita=True)
    lam.texto(14, 262, 'cable con conector C13', 2.0, 0, 'l')
    for y, t in ((yL, 'L'), (yN, 'N'), (yPE, 'PE')):
        lam.texto(16, y - 0.7, t, 2.2, 0, 'c', negrita=True)
        cable(lam, [(19, y), (34, y)])
    limite(lam, 30, 181, 94, 254)
    lam.texto(31, 257, 'X1', T_REF, 0, 'l', negrita=True)
    lam.texto(38, 257, 'Módulo de entrada IEC 60320 C14', T_DES, 0, 'l')
    for y in (yL, yN, yPE):
        borne(lam, 34, y)
    # fusible de red en la fase
    cable(lam, [(34.75, yL), (44, yL)])
    fusible_h(lam, 48, yL)
    lam.texto(48, yL + 2.6, 'F2', T_REF, 0, 'c', negrita=True)
    lam.texto(48, yL - 5.2, 'T1A 250 V', 1.9, 0, 'c')
    cable(lam, [(52, yL), (60, yL)])
    cable(lam, [(34.75, yN), (60, yN)])
    # interruptor general bipolar
    m1 = contacto_na(lam, 60, 74, yL)
    m2 = contacto_na(lam, 60, 74, yN)
    lam.linea((m2[0], m2[1]), (m1[0], m1[1] + 4.5), 'oculta')
    lam.linea((m1[0] - 1.6, m1[1] + 4.5), (m1[0] + 1.6, m1[1] + 4.5), 'visible')
    lam.texto(67, yL + 8.5, 'S1', T_REF, 0, 'c', negrita=True)
    lam.texto(67, yN - 5.0, 'bipolar', 1.9, 0, 'c')
    # piloto del interruptor
    cable(lam, [(74, yL), (94, yL)])
    cable(lam, [(74, yN), (94, yN)])
    nodo(lam, 82, yL)
    nodo(lam, 82, yN)
    cable(lam, [(82, yL), (82, (yL + yN) / 2 + 2.2)])
    cable(lam, [(82, yN), (82, (yL + yN) / 2 - 2.2)])
    circulo_carga(lam, 82, (yL + yN) / 2, 2.2, [], 82, texto='X')
    lam.texto(85, (yL + yN) / 2 - 0.7, 'H1', 2.0, 0, 'l', negrita=True)
    # tierra de protección
    cable(lam, [(34.75, yPE), (94, yPE)])
    nodo(lam, 44, yPE)
    tierra_proteccion(lam, 44, yPE)
    lam.texto(33, 187.5, 'Interruptor bipolar iluminado y', 1.75, 0, 'l')
    lam.texto(33, 184.2, 'portafusible 5 x 20 mm integrados', 1.75, 0, 'l')

    # ---------------- fuente T1 ----------------------------------------------------------------
    x0, x1 = 112.0, 150.0
    for y, w in ((yL, 'W1'), (yN, 'W2'), (yPE, 'W3')):
        cable(lam, [(94, y), (x0, y)])
        etiqueta_cable(lam, 103, y, w)
    convertidor(lam, x0, 190, x1 - x0, 50)
    lam.texto(x0, 244, 'T1', T_REF, 0, 'l', negrita=True)
    lam.texto(x0 + 6, 244, 'Fuente conmutada', T_DES, 0, 'l')
    lam.texto((x0 + x1) / 2, 185, 'Mean Well LRS-50-24', T_DES, 0, 'c')
    lam.texto((x0 + x1) / 2, 181, '24 V CC, 2.2 A, 52.8 W', T_DES, 0, 'c')
    for y, n, t in ((yL, '1', 'L'), (yN, '2', 'N'), (yPE, '3', 'FG')):
        lam.texto(x0 + 1.2, y + 0.9, n, T_PIN, 0, 'l')
        lam.texto(x0 + 1.2, y - 2.6, t, T_PIN, 0, 'l')
    for y, n, t in ((yL, '5', '+V'), (yN, '4', '-V')):
        lam.texto(x1 - 1.2, y + 0.9, n, T_PIN, 0, 'r')
        lam.texto(x1 - 1.2, y - 2.6, t, T_PIN, 0, 'r')

    # ---------------- placa A1 ----------------------------------------------------------------
    XA0, XA1 = 176.0, 302.0
    YA0, YA1 = 80.0, 262.0
    limite(lam, XA0, YA0, XA1, YA1)
    lam.texto(XA0 + 1, YA1 + 3, 'A1', T_REF, 0, 'l', negrita=True)
    lam.texto(XA0 + 9, YA1 + 3, 'Unidad de control y potencia, circuito impreso (detalle en ELE-1-01)', T_DES, 0, 'l')
    for y, w in ((yL, 'W4'), (yN, 'W5')):
        cable(lam, [(x1, y), (XA0, y)])
        etiqueta_cable(lam, 163, y, w)
        borne(lam, XA0, y)
    lam.texto(XA0 + 1.3, yL + 0.9, 'J1:1', T_PIN, 0, 'l')
    lam.texto(XA0 + 1.3, yN + 0.9, 'J1:2', T_PIN, 0, 'l')
    # cadena de protección dentro de la placa
    cable(lam, [(XA0 + 0.75, yL), (186, yL)])
    fusible_h(lam, 190, yL)
    lam.texto(190, yL + 2.6, 'F1', T_REF, 0, 'c', negrita=True)
    lam.texto(190, yL - 5.2, '1.6 A rearm.', 1.8, 0, 'c')
    cable(lam, [(194, yL), (199, yL)])
    diodo_h(lam, 201, yL)
    lam.texto(201, yL + 3.0, 'D1', T_REF, 0, 'c', negrita=True)
    cable(lam, [(202.6, yL), (212, yL)])
    nodo(lam, 212, yL)
    lam.texto(213, yL + 1.0, '+24V', 2.0, 0, 'l', negrita=True)
    # conectores del lado derecho: (ref, [(borne, red interna, cable, etiqueta del extremo)])
    pasos = []
    y = 255.0
    grupos = [
        ('J2', [('1', '+24V', 'W6'), ('2', '+24V_ACT', 'W7')]),
        ('J8', [('1', '+24V', 'W8'), ('2', 'GND', 'W9')]),
        ('J3', [('1', 'GND', 'W10'), ('2', '+24V_ACT', 'W11'), ('3', 'FAN_TACH_V', 'W12'), ('4', 'FAN_PWM_V', 'W13')]),
        ('J4', [('1', 'ACT_OUT1', 'W14'), ('2', 'ACT_OUT2', 'W15'), ('3', '+3V3', 'W16'), ('4', 'ACT_POS', 'W17'),
                ('5', 'GND', 'W18')]),
        ('J6', [('1', '+12V', 'W19'), ('2', 'LED_RET', 'W20')]),
        ('J11', [('1', '+5V1', 'W21'), ('2', 'GND', 'W22'), ('3', 'UART_TX', 'W23'), ('4', 'UART_RX', 'W24')]),
        ('J12', [('1', '+5V1', 'W25'), ('2', 'GND', 'W26')]),
    ]
    pos = {}
    for ref, pins in grupos:
        for k, (n, red, w) in enumerate(pins):
            pos[(ref, n)] = y
            borne(lam, XA1, y)
            lam.texto(XA1 - 1.3, y + 0.9, '%s:%s' % (ref, n), T_PIN, 0, 'r')
            if red not in ('+24V', '+24V_ACT') or ref != 'J2':
                lam.linea((XA1 - 12, y), (XA1 - 0.75, y), 'visible')
                lam.texto(XA1 - 13, y - 0.7, red, 1.75, 0, 'r')
            y -= 6.0
        y -= 6.0
    # J2: lazo del boton de emergencia, con conductores reales
    yj21, yj22 = pos[('J2', '1')], pos[('J2', '2')]
    cable(lam, [(212, yL), (212, yj21), (XA1 - 0.75, yj21)])
    cable(lam, [(XA1 - 0.75, yj22), (262, yj22), (262, 200)])
    nodo(lam, 262, yj22)
    lam.texto(263.5, yj22 - 3.4, '+24V_ACT', 2.0, 0, 'l', negrita=True)
    lam.texto(263.5, yj22 - 6.6, '(tras S2)', 1.8, 0, 'l')
    # derivaciones de potencia dentro de la placa (resumen; detalle en ELE-1-01)
    # U2: 5.1 V desde +24V, antes del boton de emergencia
    cable(lam, [(212, yL), (212, 196)])
    convertidor(lam, 204, 178, 16, 18, ent='=', sal='=')
    lam.texto(222, 190, 'U2', T_REF, 0, 'l', negrita=True)
    lam.texto(222, 186.2, 'MP1584', 1.8, 0, 'l')
    lam.texto(222, 183, '+5V1 permanente', 1.8, 0, 'l')
    cable(lam, [(212, 178), (212, 170)])
    lam.texto(212, 166.5, '+5V1', 2.0, 0, 'c', negrita=True)
    # U1: 12 V desde +24V_ACT, tras el boton de emergencia
    convertidor(lam, 254, 182, 16, 18, ent='=', sal='=')
    lam.texto(244, 194, 'U1', T_REF, 0, 'r', negrita=True)
    lam.texto(252, 190.2, 'LM2596', 1.8, 0, 'r')
    lam.texto(252, 187, '+12V tras', 1.8, 0, 'r')
    lam.texto(252, 183.8, 'S2', 1.8, 0, 'r')
    cable(lam, [(262, 182), (262, 174)])
    lam.texto(262, 170.5, '+12V', 2.0, 0, 'c', negrita=True)
    # bloques de gobierno
    rect(lam, 182, 96, 228, 152)
    lam.texto(184, 148, 'U4', T_REF, 0, 'l', negrita=True)
    lam.texto(192, 148, 'ESP32 DevKit V1', T_DES, 0, 'l')
    for k, s in enumerate(['VIN: +5V1   3V3: pot. y tacómetro', 'D25, D26: actuador (U6)', 'D27: ventilador (R12)',
                           'D14: dicroico (U5, Q2)', 'D34: posición   D35: S2', 'D4: tacómetro (R10, R11, D3)',
                           'TX2, RX2: enlace con A2']):
        lam.texto(184, 142 - k * 6.2, s, 1.8, 0, 'l')
    rect(lam, 233, 126, 271, 152)
    lam.texto(235, 148, 'Etapas de potencia', T_DES, 0, 'l', negrita=True)
    for k, s in enumerate(['U6 DRV8871: actuador', 'U5 + Q2: dicroico', 'Ventilador: PWM directo', 'por R12, sin transistor']):
        lam.texto(235, 143 - k * 4.4, s, 1.75, 0, 'l')
    rect(lam, 233, 96, 271, 121)
    lam.texto(235, 117, 'Sensado', T_DES, 0, 'l', negrita=True)
    for k, s in enumerate(['R7 100 k, R8 15 k:', 'lectura de S2', 'C5: filtro de posición', 'R10, R11, D3: tacómetro']):
        lam.texto(235, 112.5 - k * 4.0, s, 1.75, 0, 'l')
    lam.texto(XA0 + 2, YA0 + 3, 'Masa común GND en todos los retornos; F1 rearmable, retiene 1.6 A y dispara a 3.2 A.', 1.75, 0, 'l')

    # ---------------- cargas exteriores --------------------------------------------------------
    XC = 312.0      # inicio de las etiquetas de cable
    def eti(ref, n):
        return pos[(ref, n)]
    for (ref, pins) in grupos:
        for n, red, w in pins:
            if w:
                etiqueta_cable(lam, XC + 3, eti(ref, n), w)
    # S2 boton de emergencia, lazo J2
    y1, y2 = eti('J2', '1'), eti('J2', '2')
    cable(lam, [(XA1 + 0.75, y1), (330, y1)])
    mid = contacto_nc(lam, 330, 346, y1)
    cable(lam, [(346, y1), (350, y1), (350, y2), (XA1 + 0.75, y2)])
    lam.linea(mid, (mid[0], y1 + 5.0), 'oculta')
    lam.arco((mid[0], y1 + 5.0), 2.4, 0, 180, 'visible')
    lam.linea((mid[0] - 2.4, y1 + 5.0), (mid[0] + 2.4, y1 + 5.0), 'visible')
    lam.texto(331, y1 + 1.0, '11', T_PIN, 0, 'l')
    lam.texto(345, y1 + 1.0, '12', T_PIN, 0, 'r')
    lam.texto(353, y1 + 0.5, 'S2', T_REF, 0, 'l', negrita=True)
    lam.texto(353, y1 - 3.2, 'Botón de emergencia, NC', T_DES, 0, 'l')
    lam.texto(353, y1 - 6.4, 'apertura positiva, ISO 13850', 1.8, 0, 'l')
    # M3 extractor
    y1, y2 = eti('J8', '1'), eti('J8', '2')
    circulo_carga(lam, 350, (y1 + y2) / 2, 4.6, [y1, y2], XA1 + 0.75)
    lam.texto(357, y1 - 0.5, 'M3', T_REF, 0, 'l', negrita=True)
    lam.texto(357, y2 - 1.5, 'Extractor 30 mm, 24 V, permanente', 1.8, 0, 'l')
    # M1 ventilador principal: los cuatro hilos conectados; la modulacion entra por R12 (revision B)
    ys = [eti('J3', n) for n in '1234']
    circulo_carga(lam, 352, (ys[0] + ys[3]) / 2, 10.5, ys, XA1 + 0.75)
    lam.texto(364, ys[0] - 1.0, 'M1', T_REF, 0, 'l', negrita=True)
    lam.texto(364, ys[1] - 1.5, 'Ventilador principal', T_DES, 0, 'l')
    lam.texto(364, ys[2] - 1.8, 'Delta PFB0924GHEP6', 1.8, 0, 'l')
    lam.texto(364, ys[3] - 1.8, '24 V, 4 hilos, PWM y tacómetro', 1.8, 0, 'l')
    # M2 actuador L12-P: motor y potenciometro de posicion, cinco hilos (revision B)
    yy = [eti('J4', n) for n in '12345']
    rect(lam, 334, yy[4] - 3.4, 352, yy[0] + 3.4)
    for y, t in zip(yy, ['motor +', 'motor -', 'pot. +', 'cursor', 'pot. -']):
        lam.linea((XA1 + 0.75, y), (334, y), 'visible')
        lam.texto(335.2, y - 0.7, t, 1.7, 0, 'l')
    lam.texto(355, yy[0] - 1.0, 'M2', T_REF, 0, 'l', negrita=True)
    lam.texto(355, yy[1] - 1.5, 'Actuador lineal L12-P', T_DES, 0, 'l')
    lam.texto(355, yy[2] - 1.8, '12 V, 80 N, carrera 50 mm,', 1.8, 0, 'l')
    lam.texto(355, yy[3] - 1.8, 'potenciómetro de posición', 1.8, 0, 'l')
    # E1 dicroico
    y1, y2 = eti('J6', '1'), eti('J6', '2')
    circulo_carga(lam, 350, (y1 + y2) / 2, 3.8, [y1, y2], XA1 + 0.75, texto='X')
    lam.texto(357, y1 - 0.5, 'E1', T_REF, 0, 'l', negrita=True)
    lam.texto(357, y2 - 1.5, 'Dicroico LED MR16, 12 V, 6 W', 1.8, 0, 'l')
    # A2 Raspberry Pi Zero 2 W
    yy = [eti('J11', n) for n in '1234']
    rect(lam, 334, yy[3] - 4, 372, yy[0] + 4)
    for y, t in zip(yy, ['2  5 V', '6  GND', '10  RXD (GPIO15)', '8  TXD (GPIO14)']):
        lam.linea((XA1 + 0.75, y), (334, y), 'visible')
        lam.texto(335.2, y - 0.7, t, 1.75, 0, 'l')
    lam.texto(374, yy[0] - 1.0, 'A2', T_REF, 0, 'l', negrita=True)
    lam.texto(374, yy[1] - 1.5, 'Raspberry Pi', T_DES, 0, 'l')
    lam.texto(374, yy[2] - 1.5, 'Zero 2 W', T_DES, 0, 'l')
    lam.texto(374, yy[3] - 1.5, '(cabecera GPIO)', 1.8, 0, 'l')
    # A3 ESP32-CAM
    y1, y2 = eti('J12', '1'), eti('J12', '2')
    rect(lam, 334, y2 - 4, 360, y1 + 4)
    for y, t in ((y1, '5V'), (y2, 'GND')):
        lam.linea((XA1 + 0.75, y), (334, y), 'visible')
        lam.texto(335.2, y - 0.7, t, 1.75, 0, 'l')
    lam.texto(362, y1 - 1.0, 'A3', T_REF, 0, 'l', negrita=True)
    lam.texto(362, y2 - 1.8, 'ESP32-CAM, imagen por Wi-Fi', 1.8, 0, 'l')

    notas = [
        'Símbolos según IEC 60617; designación de referencia según IEC 81346. Esquema sin escala.',
        'S1 corta fase y neutro antes de T1. El borne FG de T1 se une a la tierra de protección de X1 (W3).',
        'S2 corta +24V_ACT: ventilador principal, U1 (12 V), actuador y dicroico. Quedan vivos U2, A1:U4, A2, A3 y M3.',
        'Liberar S2 no rearranca el ciclo: el reinicio exige una orden deliberada (ISO 13850).',
        'F2 es provisional hasta contrastar su curva con la irrupción de T1. Toda la placa trabaja a 24 V o menos.',
        'Hilos W1 a W26: sección, color y terminación en ELE-0-02.',
    ]
    lam.estampar(datos('ELE-0-01', 'ESQUEMA ELÉCTRICO GENERAL', 'S/E'), notas=notas, notas_pos=(14, 64))
    return lam.guardar(os.path.join(SALIDA, 'ELE-0-01_Esquema_general.pdf'))


# =============================================================================
# ELE-0-02  Lista de elementos y de cableado
# =============================================================================
ELEMENTOS = [
    ('X1', 'Módulo de entrada de red', 'IEC 60320 C14, interruptor bipolar iluminado, portafusible 5 x 20', 'Pared posterior de la bandeja (MEC-2-07)'),
    ('F2', 'Fusible de red', '5 x 20 mm, T1A 250 V (provisional)', 'En X1'),
    ('S1', 'Interruptor general', 'Bipolar, iluminado, 10 A 250 V CA', 'En X1'),
    ('T1', 'Fuente conmutada', 'Mean Well LRS-50-24, 24 V, 2.2 A', 'Bandeja, junto a X1'),
    ('A1', 'Unidad de control y potencia', 'Circuito impreso 100 x 80 mm (ELE-1-01)', 'Bandeja'),
    ('S2', 'Parada de emergencia', 'Botón rojo enclavable, NC, Ø22 mm', 'Cara lateral de la estructura (MEC-2-02)'),
    ('M1', 'Ventilador principal', 'Delta PFB0924GHEP6, 24 V, 0.65 A, PWM y tacómetro', 'Bahía lateral (MEC-2-09)'),
    ('M2', 'Actuador lineal', 'Actuonix L12-50-210-12-P, 12 V, 80 N, potenciómetro', 'Soporte del actuador (MEC-2-12)'),
    ('M3', 'Ventilador de extracción', '30 x 30 x 10 mm, 24 V, 0.05 A', 'Pared posterior de la bandeja (MEC-2-08)'),
    ('E1', 'Iluminación', 'Dicroico LED MR16 GU5.3, 12 V, 6 W', 'Aro portalámpara (MEC-2-18)'),
    ('A2', 'Computador de placa única', 'Raspberry Pi Zero 2 W', 'Bandeja'),
    ('A3', 'Módulo de cámara', 'ESP32-CAM con OV2640', 'Carcasa del soporte tubular (MEC-2-16)'),
]

CABLES = [
    # (hilo, señal, desde, hasta, sección, color, terminación)
    ('W1', 'L', 'X1: fase tras S1', 'T1: 1 (L)', '0.75 mm² (18 AWG)', 'Marrón', 'Faston aislado 4.8 / puntera'),
    ('W2', 'N', 'X1: neutro tras S1', 'T1: 2 (N)', '0.75 mm² (18 AWG)', 'Azul', 'Faston aislado 4.8 / puntera'),
    ('W3', 'PE', 'X1: tierra', 'T1: 3 (FG)', '0.75 mm² (18 AWG)', 'Verde y amarillo', 'Faston aislado 4.8 / puntera'),
    ('W4', '+24 V', 'T1: 5 (+V)', 'A1-J1: 1', '0.50 mm² (20 AWG)', 'Rojo', 'Puntera / hembra 2.54 mm'),
    ('W5', '0 V', 'T1: 4 (-V)', 'A1-J1: 2', '0.50 mm² (20 AWG)', 'Negro', 'Puntera / hembra 2.54 mm'),
    ('W6', '+24V', 'A1-J2: 1', 'S2: 11', '0.50 mm² (20 AWG)', 'Rojo', 'Hembra 2.54 mm / terminal de horquilla'),
    ('W7', '+24V_ACT', 'S2: 12', 'A1-J2: 2', '0.50 mm² (20 AWG)', 'Naranja', 'Terminal de horquilla / hembra 2.54 mm'),
    ('W8', '+24V', 'A1-J8: 1', 'M3: rojo', '0.14 mm² (26 AWG)', 'Rojo', 'Hembra 2.54 mm, conductor propio'),
    ('W9', 'GND', 'A1-J8: 2', 'M3: negro', '0.14 mm² (26 AWG)', 'Negro', 'Hembra 2.54 mm, conductor propio'),
    ('W10', 'GND', 'A1-J3: 1', 'M1: negro', '0.35 mm² (22 AWG)', 'Negro', 'Hembra 2.54 mm / empalme termocontraíble'),
    ('W11', '+24V_ACT', 'A1-J3: 2', 'M1: amarillo', '0.35 mm² (22 AWG)', 'Amarillo', 'Hembra 2.54 mm / empalme termocontraíble'),
    ('W12', 'FAN_TACH', 'A1-J3: 3', 'M1: verde', '0.14 mm² (26 AWG)', 'Verde', 'Hembra 2.54 mm / empalme termocontraíble'),
    ('W13', 'FAN_PWM', 'A1-J3: 4', 'M1: azul', '0.14 mm² (26 AWG)', 'Azul', 'Hembra 2.54 mm / empalme termocontraíble'),
    ('W14', 'ACT_OUT1', 'A1-J4: 1', 'M2: rojo', '0.25 mm² (24 AWG)', 'Rojo', 'Hembra 2.54 mm, conductor propio'),
    ('W15', 'ACT_OUT2', 'A1-J4: 2', 'M2: negro', '0.25 mm² (24 AWG)', 'Negro', 'Hembra 2.54 mm, conductor propio'),
    ('W16', '+3V3', 'A1-J4: 3', 'M2: amarillo', '0.14 mm² (26 AWG)', 'Amarillo', 'Hembra 2.54 mm, conductor propio'),
    ('W17', 'ACT_POS', 'A1-J4: 4', 'M2: morado', '0.14 mm² (26 AWG)', 'Morado', 'Hembra 2.54 mm, conductor propio'),
    ('W18', 'GND', 'A1-J4: 5', 'M2: naranja', '0.14 mm² (26 AWG)', 'Naranja', 'Hembra 2.54 mm, conductor propio'),
    ('W19', '+12V', 'A1-J6: 1', 'E1: casquillo GU5.3', '0.35 mm² (22 AWG)', 'Rojo', 'Hembra 2.54 mm / casquillo'),
    ('W20', 'LED_RET', 'A1-J6: 2', 'E1: casquillo GU5.3', '0.35 mm² (22 AWG)', 'Negro', 'Hembra 2.54 mm / casquillo'),
    ('W21', '+5V1', 'A1-J11: 1', 'A2: pin 2 (5 V)', '0.35 mm² (22 AWG)', 'Rojo', 'Hembra 2.54 mm en ambos extremos'),
    ('W22', 'GND', 'A1-J11: 2', 'A2: pin 6 (GND)', '0.35 mm² (22 AWG)', 'Negro', 'Hembra 2.54 mm en ambos extremos'),
    ('W23', 'UART_TX', 'A1-J11: 3', 'A2: pin 10 (RXD)', '0.14 mm² (26 AWG)', 'Amarillo', 'Hembra 2.54 mm en ambos extremos'),
    ('W24', 'UART_RX', 'A1-J11: 4', 'A2: pin 8 (TXD)', '0.14 mm² (26 AWG)', 'Verde', 'Hembra 2.54 mm en ambos extremos'),
    ('W25', '+5V1', 'A1-J12: 1', 'A3: 5V', '0.35 mm² (22 AWG)', 'Rojo', 'Hembra 2.54 mm en ambos extremos'),
    ('W26', 'GND', 'A1-J12: 2', 'A3: GND', '0.35 mm² (22 AWG)', 'Negro', 'Hembra 2.54 mm en ambos extremos'),
]


def ele_0_02():
    lam = Lamina('A3')
    lam.texto(20, 278, 'LISTA DE ELEMENTOS', 3.6, 0, 'l', negrita=True)
    col_e = [('Ref.', 12, 'c'), ('Elemento', 50, 'l'), ('Modelo o valor', 92, 'l'), ('Ubicación', 78, 'l')]
    alto = 5.2
    y_top = 274.0
    y_base = y_top - alto * (len(ELEMENTOS) + 1)
    tabla(lam, 20, y_base, col_e, ELEMENTOS, alto=alto, tam=2.2)
    y2 = y_base - 9.0
    lam.texto(20, y2, 'LISTA DE CABLEADO', 3.6, 0, 'l', negrita=True)
    col_c = [('Hilo', 12, 'c'), ('Señal', 22, 'c'), ('Desde', 44, 'l'), ('Hasta', 44, 'l'), ('Sección', 40, 'l'),
             ('Color', 28, 'l'), ('Terminación', 72, 'l')]
    alto_c = 4.6
    base_c = y2 - 4.0 - alto_c * (len(CABLES) + 1)
    tabla(lam, 20, base_c, col_c, CABLES, alto=alto_c, tam=2.0)
    notas = [
        'Colores de red según IEC 60445: fase marrón, neutro azul, tierra de protección verde y amarillo.',
        'Conductores de red H05V-K; terminales faston con funda aislante completa y punteras en los bornes de tornillo de T1.',
        'Secciones de continua por corriente y caída: W4 a W7 llevan hasta 1.4 A; W10, W11 y W19, W20 hasta 0.65 A.',
        'Los hilos de cada carga van agrupados y sujetos con bridas; el mazo cruza entre pisos por el paso de cable.',
        'Los cuatro conductores de M1 se conectan: el PWM (azul) llega por R12 y el tacómetro (verde) por R11.',
        'Longitudes a fijar en el montaje, con 20 % de holgura sobre el recorrido medido en el modelo.',
    ]
    lam.estampar(datos('ELE-0-02', 'LISTA DE ELEMENTOS Y DE CABLEADO', 'S/E'), notas=notas, notas_pos=(20, 64))
    return lam.guardar(os.path.join(SALIDA, 'ELE-0-02_Lista_elementos_cableado.pdf'))


# =============================================================================
# Láminas desde KiCad
# =============================================================================
def _kicad(args):
    p = subprocess.run([CLI] + args, capture_output=True, text=True, errors='replace')
    if p.returncode != 0:
        raise RuntimeError('kicad-cli: ' + (p.stderr or p.stdout)[-400:])


def _bbox_contenido(page, excluir_texto=False):
    r = fitz.Rect()
    for d in page.get_drawings():
        rr = d['rect']
        if rr.width < page.rect.width * 0.98 or rr.height < page.rect.height * 0.98:
            r |= rr
    if not excluir_texto:
        for b in page.get_text('blocks'):
            r |= fitz.Rect(b[:4])
    return r


def _insertar(lam, pdf, x_mm, y_mm, escala, clip):
    """Inserta clip (en puntos del PDF de origen) con su esquina inferior izquierda en (x_mm, y_mm)
    y la escala dada respecto del tamaño real del origen."""
    src = fitz.open(pdf)
    w = clip.width * escala
    h = clip.height * escala
    dest = fitz.Rect(x_mm * MM, (lam.H - y_mm) * MM - h, x_mm * MM + w, (lam.H - y_mm) * MM)
    lam.page.show_pdf_page(dest, src, 0, clip=clip, keep_proportion=True)
    return w / MM, h / MM


HOJAS_ESQ = [
    ('ENERGÍA, VENTILADOR Y CONECTORES', ['ENTRADA 24 V, PROTECCION Y PARADA DE EMERGENCIA', 'CONVERTIDORES REDUCTORES',
                                         'ETAPA DEL VENTILADOR PRINCIPAL', 'CONECTORES DE SALIDA Y ENLACE',
                                         'DECLARACION DE ALIMENTACION']),
    ('MICROCONTROLADOR, ACTUADOR E ILUMINACIÓN', ['MICROCONTROLADOR', 'ETAPA DEL ACTUADOR LINEAL', 'UNIDAD DE ILUMINACION']),
]


def _bloques_esquematico(pg):
    """Bloques del esquematico de KiCad: grupos de dibujos y textos separados por huecos de mas de 7 mm, asignados
    al titulo de bloque que queda arriba y a la izquierda (los bloques se enlazan por etiquetas globales)."""
    tit = []
    for b in pg.get_text('blocks'):
        t = ' '.join(b[4].split())
        r = fitz.Rect(b[:4])
        letras = sum(ch.isalpha() for ch in t) / max(1, len(t.replace(' ', '')))
        if t.isupper() and len(t) >= 12 and r.height >= 8 and letras > 0.85:
            tit.append((t, r))
    items = [fitz.Rect(w[:4]) for w in pg.get_text('words')] + [fitz.Rect(d['rect']) for d in pg.get_drawings()]
    items = [r for r in items if r.width < pg.rect.width * 0.5 and r.height < pg.rect.height * 0.5]
    G = 7 * MM
    ex = [fitz.Rect(r.x0 - G / 2, r.y0 - G / 2, r.x1 + G / 2, r.y1 + G / 2) for r in items]
    par = list(range(len(items)))

    def raiz(k):
        while par[k] != k:
            par[k] = par[par[k]]
            k = par[k]
        return k
    celda = 40.0
    grilla = {}
    for k, r in enumerate(ex):
        for gx in range(int(r.x0 // celda), int(r.x1 // celda) + 1):
            for gy in range(int(r.y0 // celda), int(r.y1 // celda) + 1):
                grilla.setdefault((gx, gy), []).append(k)
    for lst in grilla.values():
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                if ex[lst[a]].intersects(ex[lst[b]]):
                    ra, rb = raiz(lst[a]), raiz(lst[b])
                    if ra != rb:
                        par[ra] = rb
    grupos = {}
    for k, r in enumerate(items):
        c = raiz(k)
        grupos[c] = r if c not in grupos else grupos[c] | r
    bloques = {t: fitz.Rect(r) for t, r in tit}
    for r in grupos.values():
        dentro = [t for t, tr in tit if r.contains(tr)]
        if dentro:
            bloques[dentro[0]] |= r
            continue
        cx = (r.x0 + r.x1) / 2
        cand = [(tr.y0, tr.x0, t) for t, tr in tit if tr.x0 <= cx and tr.y0 <= r.y0 + 2]
        if cand:
            bloques[max(cand)[2]] |= r
    return bloques


def _empaquetar(tam, regiones):
    """Coloca rectangulos (ancho, alto) por estantes en las regiones (x0, y0, x1, y1), de arriba abajo.
    Devuelve las esquinas superiores izquierdas o None si no caben."""
    pos = {}
    pend = sorted(tam, key=lambda k: -tam[k][1])
    for (x0, y0, x1, y1) in regiones:
        y = y1
        while pend:
            fila_alto = tam[pend[0]][1]
            if y - fila_alto < y0:
                break
            x = x0
            puestos = []
            for k in list(pend):
                w, h = tam[k]
                if x + w <= x1 and h <= fila_alto + 1e-6:
                    pos[k] = (x, y)
                    x += w + 8
                    puestos.append(k)
            if not puestos:
                break
            for k in puestos:
                pend.remove(k)
            y -= fila_alto + 8
    return pos if not pend else None


def ele_1_01():
    tmp = os.path.join(tempfile.gettempdir(), 'tfc_sch.pdf')
    _kicad(['sch', 'export', 'pdf', '--output', tmp, '--black-and-white', '--exclude-drawing-sheet',
            '--no-background-color', '--exclude-pdf-property-popups', SCH])
    pg = fitz.open(tmp)[0]
    bloques = _bloques_esquematico(pg)
    # dos maneras de repartir la hoja libre alrededor del cajetin: franja superior completa mas la esquina inferior
    # izquierda, o columna izquierda completa mas el cuadro superior derecho; se queda la que admite mayor escala
    repartos = [[(16, 108, 404, 281), (16, 16, 220, 100)],
                [(16, 16, 222, 281), (230, 108, 404, 281)]]
    salidas = []
    for n, (nombre, titulos) in enumerate(HOJAS_ESQ, 1):
        clips = {t: fitz.Rect(bloques[t].x0 - 3 * MM, bloques[t].y0 - 3 * MM, bloques[t].x1 + 3 * MM, bloques[t].y1 + 3 * MM)
                 for t in titulos if t in bloques}
        mejor = None
        for regiones in repartos:
            esc = 2.0
            while esc > 0.5:
                tam = {t: (c.width / MM * esc, c.height / MM * esc) for t, c in clips.items()}
                pos = _empaquetar(tam, regiones)
                if pos:
                    break
                esc -= 0.05
            if pos and (mejor is None or esc > mejor[0] + 1e-9):
                mejor = (esc, tam, pos)
        esc, tam, pos = mejor
        lam = Lamina('A3')
        for t, (x, ytop) in pos.items():
            _insertar(lam, tmp, x, ytop - tam[t][1], esc, clips[t])
        notas = [
            'Esquemático de KiCad 10 del proyecto TFC_Remocion, revisión B; comprobación eléctrica (ERC) sin errores.',
            'Los bloques se enlazan por etiquetas globales del mismo nombre: su posición en la hoja no cambia ninguna conexión.',
            'Hoja %d de 2: %s. Escala de impresión %.2f respecto del original.' % (n, nombre.lower(), esc),
        ]
        if n == 1:
            notas.insert(2, 'Ventilador alimentado siempre a 24 V y gobernado por su entrada de modulación (R12); tacómetro por R10, R11 y D3.')
        else:
            notas.insert(2, 'D34 lee la posición del actuador L12-P (C5 de filtro); Q2 lo acciona el TC4427 (U5) con R1 de 10 ohm.')
        lam.estampar(datos('ELE-1-01', 'ESQUEMÁTICO DE LA UNIDAD DE CONTROL Y POTENCIA, HOJA %d DE 2' % n, 'S/E'), notas=notas)
        ruta_h = os.path.join(SALIDA, '_ELE-1-01_hoja%d.pdf' % n)
        lam.guardar(ruta_h, dpi=80)
        salidas.append(ruta_h)
    destino = os.path.join(SALIDA, 'ELE-1-01_Esquematico_placa.pdf')
    doc = fitz.open()
    for f in salidas:
        doc.insert_pdf(fitz.open(f))
    doc.save(destino, garbage=3, deflate=True)
    doc.close()
    for f in salidas:
        os.remove(f)
    return destino


def _placa_pdf(capas, nombre, espejo=False, sin_valores=False):
    tmp = os.path.join(tempfile.gettempdir(), 'tfc_%s.pdf' % nombre)
    args = ['pcb', 'export', 'pdf', '--output', tmp, '--mode-single', '--layers', capas, '--black-and-white',
            '--drill-shape-opt', '2']
    if espejo:
        args.append('--mirror')
    if sin_valores:
        args.append('--exclude-value')
    _kicad(args + [PCB])
    return tmp


def _cota2d(lam, p1, p2, desp, texto, eje='h', tam=2.8):
    """Cota con líneas de referencia; p1, p2 en mm de hoja; desp: separación de la línea de cota."""
    (x1, y1), (x2, y2) = p1, p2
    if eje == 'h':
        yc = y1 + desp
        lam.linea((x1, y1 + math.copysign(1, desp)), (x1, yc + math.copysign(1.5, desp)), 'cota')
        lam.linea((x2, y2 + math.copysign(1, desp)), (x2, yc + math.copysign(1.5, desp)), 'cota')
        lam.linea((x1, yc), (x2, yc), 'cota')
        lam.flecha((x1, yc), (-1, 0))
        lam.flecha((x2, yc), (1, 0))
        lam.texto((x1 + x2) / 2, yc + 0.9, texto, tam, 0, 'c')
    else:
        xc = x1 + desp
        lam.linea((x1 + math.copysign(1, desp), y1), (xc + math.copysign(1.5, desp), y1), 'cota')
        lam.linea((x2 + math.copysign(1, desp), y2), (xc + math.copysign(1.5, desp), y2), 'cota')
        lam.linea((xc, y1), (xc, y2), 'cota')
        lam.flecha((xc, y1), (0, -1))
        lam.flecha((xc, y2), (0, 1))
        lam.texto(xc - 0.9, (y1 + y2) / 2, texto, tam, 90, 'c')


def _lamina_placa(codigo, titulo, capas, nombre_pdf, notas, espejo=False, cotas=True, sin_valores=False):
    tmp = _placa_pdf(capas, codigo, espejo, sin_valores)
    src = fitz.open(tmp)
    pg = src[0]
    # contorno de la placa: el rectángulo de 100 x 80 mm del Edge.Cuts
    clip = _bbox_contenido(pg, excluir_texto=True)
    E = 2.0
    lam = Lamina('A3')
    x0, y0 = 34.0, 106.0                     # esquina inferior izquierda de la placa en la hoja
    w, h = _insertar(lam, tmp, x0, y0, E, clip)
    # cotas del contorno y de los agujeros de fijación (dimensiones reales del archivo de la placa)
    W, H = 100.0, 80.0
    sx = w / (clip.width / MM)               # = E
    bx0, by0 = x0, y0
    if cotas:
        _cota2d(lam, (bx0, by0 + H * E), (bx0 + W * E, by0 + H * E), 12, '100')
        _cota2d(lam, (bx0 + W * E, by0), (bx0 + W * E, by0 + H * E), 12, '80', eje='v')
        # agujeros: centros a 3.5 mm de los bordes, Ø3.2
        hx = [3.5, 96.5]
        hy = [3.5, 76.5]
        _cota2d(lam, (bx0 + hx[0] * E, by0), (bx0 + hx[1] * E, by0), -10, '93')
        _cota2d(lam, (bx0, by0 + hy[0] * E), (bx0, by0 + hy[1] * E), -10, '73', eje='v')
        _cota2d(lam, (bx0, by0), (bx0 + hx[0] * E, by0), -18, '3.5')
        # llamada del agujero entre el borde superior de la placa y la cota de 100, sin cruzar cotas
        ya = by0 + H * E + 5.5
        lam.linea((bx0 + 3.5 * E + 1.6 * E * 0.7, by0 + 76.5 * E + 1.6 * E * 0.7), (bx0 + 3.5 * E + 10, ya), 'cota')
        lam.linea((bx0 + 3.5 * E + 10, ya), (bx0 + 3.5 * E + 62, ya), 'cota')
        lam.texto(bx0 + 3.5 * E + 11, ya + 0.8, '4x Ø3.2 PASANTE, SIN METALIZAR', 2.6, 0, 'l')
    lam.texto(bx0 + W * E / 2, by0 - 30, titulo.split(',')[0] + '  (2:1)', 3.4, 0, 'c', negrita=True)
    lam.estampar(datos(codigo, titulo, '2:1', pcb=True), notas=notas)
    return lam.guardar(os.path.join(SALIDA, nombre_pdf))


NOTAS_PCB = [
    'Placa de dos caras, FR-4 de 1.6 mm, cobre de 35 µm, acabado HASL sin plomo y máscara verde en ambas caras.',
    'Cotas en milímetros; contorno con tolerancia de ±0.2 mm. Taladros según el archivo Excellon del proyecto.',
    'Anchos y separaciones según las clases de red del Anexo H (IPC-2221); bus de 24 V en 1.6 mm.',
    'Revisión B: 149 pistas, 4 vías de señal y 10 vías de costura del plano de masa junto a U6 y a D34 y D35.',
]


def ele_1_02():
    notas = NOTAS_PCB + ['Componentes de agujero pasante, soldadura manual; valores según la lista de componentes del Anexo H.',
                         'Fijación con cuatro tornillos M3 sobre separadores de 6 mm en el piso de la bandeja.']
    return _lamina_placa('ELE-1-02', 'EMPLAZAMIENTO DE COMPONENTES, VISTA SUPERIOR',
                         'F.Silkscreen,Edge.Cuts', 'ELE-1-02_Emplazamiento.pdf', notas, sin_valores=True)


def ele_2_01():
    return _lamina_placa('ELE-2-01', 'CARA SUPERIOR DE COBRE, VISTA SUPERIOR', 'F.Cu,Edge.Cuts',
                         'ELE-2-01_Cobre_superior.pdf', NOTAS_PCB + ['Plano de masa en la región de cobre que rodea a las pistas.'])


def ele_2_02():
    return _lamina_placa('ELE-2-02', 'CARA INFERIOR DE COBRE, VISTA DESDE EL LADO DE COMPONENTES', 'B.Cu,Edge.Cuts',
                         'ELE-2-02_Cobre_inferior.pdf',
                         NOTAS_PCB + ['Vista desde la cara superior, sin espejar: coincide con la orientación de ELE-2-01.'])


LAMINAS = {'ELE-0-01': ele_0_01, 'ELE-0-02': ele_0_02, 'ELE-1-01': ele_1_01, 'ELE-1-02': ele_1_02,
           'ELE-2-01': ele_2_01, 'ELE-2-02': ele_2_02}


def fusionar():
    salida = os.path.join(AQUI, 'Planos_ELE_Anexo_H_completo.pdf')
    doc = fitz.open()
    for c in sorted(LAMINAS):
        f = [x for x in os.listdir(SALIDA) if x.startswith(c)][0]
        doc.insert_pdf(fitz.open(os.path.join(SALIDA, f)))
    doc.save(salida, garbage=3, deflate=True)
    return salida


if __name__ == '__main__':
    os.makedirs(SALIDA, exist_ok=True)
    pedidas = [a for a in sys.argv[1:] if not a.startswith('--')] or sorted(LAMINAS)
    for c in pedidas:
        print(c, '->', LAMINAS[c]())
    if len(pedidas) == len(LAMINAS):
        print('fusionado:', fusionar())
