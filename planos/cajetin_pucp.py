# -*- coding: utf-8 -*-
"""Cajetín PUCP para láminas de la tesis, sobreimpreso con PyMuPDF.

Reproduce el formato que usan las tesis MTR aprobadas del banco PUCP (bloque en la
esquina inferior derecha): fila superior ACABADO SUPERFICIAL / TOLERANCIA GENERAL /
MATERIAL; cabecera institucional; MÉTODO DE PROYECCIÓN (primer diedro) + título +
ESCALA; ELABORADO POR con código de alumno + FECHA; REVISADO POR + LÁMINA.

    python cajetin_pucp.py --demo        genera una A3 de prueba con el cajetín vacío
Uso desde otro guion:
    from cajetin_pucp import estampar
    estampar(pagina, datos)              # pagina = fitz.Page apaisada
"""
import os
import sys
import math
import datetime

import fitz

AQUI = os.path.dirname(os.path.abspath(__file__))
ESCUDO = os.path.join(AQUI, '..', 'TESIS_LATEX', 'Imagenes', 'marca_pucp_clara.png')

MM = 72.0 / 25.4
UNIVERSIDAD = 'PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ'
FACULTAD = 'FACULTAD DE CIENCIAS E INGENIERÍA - INGENIERÍA MECATRÓNICA'
PROYECTO = 'SISTEMA MECATRÓNICO DE SUPERVISIÓN Y REMOCIÓN AUTOMÁTICA DE PIEZAS, BAMBU LAB A1 MINI'
AUTOR = 'LUNA BALDWIN, DIEGO MANUEL'
CODIGO_ALUMNO = '20211878'
ASESOR = 'LAUREL BRAVO, CHRISTIHAN JOEL'
FUENTE = 'helv'
FUENTE_B = 'hebo'


def _txt(page, rect, texto, tam, negrita=False, alinear=1, color=(0, 0, 0)):
    """Texto centrado vertical y horizontalmente dentro de rect (alinear 0 izq, 1 centro)."""
    fuente = FUENTE_B if negrita else FUENTE
    # reduce el tamaño hasta que quepa en el ancho
    while tam > 4 and fitz.get_text_length(texto, fontname=fuente, fontsize=tam) > rect.width - 2 * MM:
        tam -= 0.25
    alto_linea = tam * 1.15
    y = rect.y0 + (rect.height - alto_linea) / 2 + tam * 0.95
    ancho = fitz.get_text_length(texto, fontname=fuente, fontsize=tam)
    x = rect.x0 + 1 * MM if alinear == 0 else rect.x0 + (rect.width - ancho) / 2
    page.insert_text((x, y), texto, fontsize=tam, fontname=fuente, color=color)


def _caja(page, rect, grosor=0.6):
    page.draw_rect(rect, color=(0, 0, 0), width=grosor)


def _simbolo_primer_diedro(page, rect):
    """Símbolo del método de proyección del primer diedro (ISO 128 / ISO 5456-2): el cono truncado
    se dibuja de lado (trapecio) a la izquierda, con su lado estrecho a la izquierda, y su vista
    desde la izquierda (dos círculos concéntricos) a la derecha. En primer diedro el lado estrecho
    del trapecio queda en el extremo opuesto a los círculos; en tercer diedro miraría hacia ellos."""
    cy = rect.y0 + rect.height * 0.50
    r = min(rect.height, rect.width) * 0.16
    h1 = r * 0.9                  # semialtura del lado estrecho (diámetro menor = círculo interior)
    h2 = r * 2.0                  # semialtura del lado ancho (diámetro mayor = círculo exterior)
    # trapecio a la izquierda: lado estrecho a la izquierda
    tx = rect.x0 + rect.width * 0.12
    w = rect.width * 0.30
    pts = [(tx, cy - h1), (tx + w, cy - h2), (tx + w, cy + h2), (tx, cy + h1)]
    page.draw_polyline(pts + [pts[0]], color=(0, 0, 0), width=0.6)
    page.draw_line((tx - 2, cy), (tx + w + 2, cy), color=(0, 0, 0), width=0.3)
    # círculos a la derecha: el exterior tiene el diámetro del lado ancho y el interior el del estrecho
    cx = rect.x0 + rect.width * 0.72
    page.draw_circle((cx, cy), h2, color=(0, 0, 0), width=0.6)
    page.draw_circle((cx, cy), h1, color=(0, 0, 0), width=0.6)
    page.draw_line((cx - h2 - 2, cy), (cx + h2 + 2, cy), color=(0, 0, 0), width=0.3)
    page.draw_line((cx, cy - h2 - 2), (cx, cy + h2 + 2), color=(0, 0, 0), width=0.3)


def _simbolo_rugosidad(page, rect, texto):
    """Símbolo básico de rugosidad (ISO 1302) con el valor Ra a la derecha."""
    h = rect.height * 0.55
    x = rect.x0 + rect.width * 0.42
    y = rect.y0 + rect.height * 0.80
    page.draw_polyline([(x, y - h * 0.5), (x + h * 0.4, y), (x + h * 1.0, y - h * 1.3)], color=(0, 0, 0), width=0.6)
    page.draw_line((x + h * 0.4, y), (x + h * 1.0, y - h * 1.3), color=(0, 0, 0), width=0.6)
    page.insert_text((x + h * 1.1, y - h * 0.55), texto, fontsize=rect.height * 0.30, fontname=FUENTE)


def estampar(page, datos, marca_de_agua=True, notas=None, notas_pos=None):
    """Dibuja marco, cajetín y notas sobre una página apaisada ya existente.

    datos: dict con titulo, codigo (lámina), escala, material, masa, fecha, formato,
           tolerancia (p. ej. 'ISO 2768-m'), rugosidad (p. ej. 'Ra 12.5'), hoja ('1/1').
    notas: lista de cadenas que van en el bloque de notas sobre el cajetín.
    """
    W, H = page.rect.width, page.rect.height
    m = 10 * MM
    # marco
    _caja(page, fitz.Rect(m, m, W - m, H - m), 1.0)
    # marca de agua
    if marca_de_agua and os.path.exists(ESCUDO):
        lado = min(W, H) * 0.45
        page.insert_image(fitz.Rect(W / 2 - lado / 2, H / 2 - lado / 2, W / 2 + lado / 2, H / 2 + lado / 2),
                          filename=ESCUDO, overlay=False)
    # cajetín: 180 x 56 mm en A3/A2, escalado al ancho de la hoja en A4
    cw = min(180 * MM, (W - 2 * m) * 0.62)
    ch = cw * 56 / 180
    x0, y0 = W - m - cw, H - m - ch
    x1, y1 = W - m, H - m
    f = cw / (180 * MM)             # factor de escala del cajetín
    t = 7.5 * f                     # tamaño base de texto

    # fila 1: acabado superficial / tolerancia general / material  (altura 12 mm)
    h1 = 12 * MM * f
    c1 = fitz.Rect(x0, y0, x0 + cw * 0.34, y0 + h1)
    c2 = fitz.Rect(c1.x1, y0, x0 + cw * 0.70, y0 + h1)
    c3 = fitz.Rect(c2.x1, y0, x1, y0 + h1)
    for c in (c1, c2, c3):
        _caja(page, c)
    if datos.get('fila1'):
        # láminas eléctricas: tres pares (etiqueta, valor) en lugar de rugosidad, tolerancia y material
        for c, (et, val) in zip((c1, c2, c3), datos['fila1']):
            _txt(page, fitz.Rect(c.x0, c.y0, c.x1, c.y0 + h1 * 0.42), et, t * 0.8)
            _txt(page, fitz.Rect(c.x0, c.y0 + h1 * 0.42, c.x1, c.y1), val, t * 1.05, True)
    else:
        for c, et in ((c1, 'ACABADO SUPERFICIAL'), (c2, 'TOLERANCIA GENERAL'), (c3, 'MATERIAL')):
            _txt(page, fitz.Rect(c.x0, c.y0, c.x1, c.y0 + h1 * 0.42), et, t * 0.8)
        _simbolo_rugosidad(page, fitz.Rect(c1.x0, c1.y0 + h1 * 0.35, c1.x1, c1.y1), datos.get('rugosidad', 'Ra 12.5'))
        _txt(page, fitz.Rect(c2.x0, c2.y0 + h1 * 0.42, c2.x1, c2.y1), datos.get('tolerancia', 'ISO 2768-m'), t * 1.05, True)
        _txt(page, fitz.Rect(c3.x0, c3.y0 + h1 * 0.42, c3.x1, c3.y1), datos.get('material', 'PLA'), t * 1.05, True)

    # fila 2: institución (altura 9 mm)
    h2 = 9 * MM * f
    r2 = fitz.Rect(x0, y0 + h1, x1, y0 + h1 + h2)
    _caja(page, r2)
    _txt(page, fitz.Rect(r2.x0, r2.y0, r2.x1, r2.y0 + h2 * 0.55), UNIVERSIDAD, t * 1.1, True)
    _txt(page, fitz.Rect(r2.x0, r2.y0 + h2 * 0.5, r2.x1, r2.y1), FACULTAD, t * 0.8)

    # fila 3: proyección | proyecto + título | escala  (altura 20 mm)
    h3 = 20 * MM * f
    ya = y0 + h1 + h2
    p1 = fitz.Rect(x0, ya, x0 + cw * 0.24, ya + h3)
    p2 = fitz.Rect(p1.x1, ya, x0 + cw * 0.80, ya + h3)
    p3 = fitz.Rect(p2.x1, ya, x1, ya + h3)
    for c in (p1, p2, p3):
        _caja(page, c)
    _txt(page, fitz.Rect(p1.x0, p1.y0, p1.x1, p1.y0 + h3 * 0.25), 'MÉTODO DE PROYECCIÓN', t * 0.7)
    if datos.get('proyeccion', True):
        _simbolo_primer_diedro(page, fitz.Rect(p1.x0, p1.y0 + h3 * 0.25, p1.x1, p1.y1))
    else:
        # esquemas: no son proyecciones de un objeto
        _txt(page, fitz.Rect(p1.x0, p1.y0 + h3 * 0.30, p1.x1, p1.y1), 'NO APLICA', t * 1.0, True)
    _txt(page, fitz.Rect(p2.x0, p2.y0, p2.x1, p2.y0 + h3 * 0.30), PROYECTO, t * 0.7)
    _txt(page, fitz.Rect(p2.x0, p2.y0 + h3 * 0.30, p2.x1, p2.y1), datos['titulo'], t * 1.6, True)
    _txt(page, fitz.Rect(p3.x0, p3.y0, p3.x1, p3.y0 + h3 * 0.30), 'ESCALA', t * 0.8)
    _txt(page, fitz.Rect(p3.x0, p3.y0 + h3 * 0.30, p3.x1, p3.y1), datos.get('escala', '1:1'), t * 1.6, True)

    # fila 4: elaborado por | código | fecha  (altura 7.5 mm)
    h4 = 7.5 * MM * f
    yb = ya + h3
    e1 = fitz.Rect(x0, yb, x0 + cw * 0.24, yb + h4)
    e2 = fitz.Rect(e1.x1, yb, x0 + cw * 0.80, yb + h4)
    e3 = fitz.Rect(e2.x1, yb, x1, yb + h4)
    for c in (e1, e2, e3):
        _caja(page, c)
    _txt(page, e1, CODIGO_ALUMNO, t * 1.1, True)
    _txt(page, e2, 'ELABORADO POR:   ' + AUTOR, t * 0.95, alinear=0)
    _txt(page, fitz.Rect(e3.x0, e3.y0, e3.x1, e3.y0 + h4 * 0.45), 'FECHA:', t * 0.65, alinear=0)
    _txt(page, fitz.Rect(e3.x0, e3.y0 + h4 * 0.35, e3.x1, e3.y1), datos.get('fecha', datetime.date.today().strftime('%d.%m.%Y')), t * 0.95)

    # fila 5: revisado por | lámina  (altura 7.5 mm)
    yc = yb + h4
    r1 = fitz.Rect(x0, yc, x0 + cw * 0.64, y1)
    rv = fitz.Rect(r1.x1, yc, x0 + cw * 0.80, y1)
    r2b = fitz.Rect(rv.x1, yc, x1, y1)
    for c in (r1, rv, r2b):
        _caja(page, c)
    _txt(page, r1, 'REVISADO POR:   ' + ASESOR, t * 0.95, alinear=0)
    _txt(page, fitz.Rect(rv.x0, rv.y0, rv.x1, rv.y0 + h4 * 0.45), 'REVISIÓN:', t * 0.65, alinear=0)
    _txt(page, fitz.Rect(rv.x0, rv.y0 + h4 * 0.35, rv.x1, rv.y1), datos.get('revision', 'A'), t * 1.05, True)
    _txt(page, fitz.Rect(r2b.x0, r2b.y0, r2b.x1, r2b.y0 + h4 * 0.45), 'LÁMINA:', t * 0.65, alinear=0)
    _txt(page, fitz.Rect(r2b.x0, r2b.y0 + h4 * 0.35, r2b.x1, r2b.y1), '%s-%s' % (datos['codigo'], datos.get('formato', 'A3')), t * 1.05, True)

    # bloque de notas sobre el cajetín, alineado a su borde izquierdo
    if notas:
        tn = max(t * 0.9, 8.2)
        lineas = []
        for i, n in enumerate(notas, 1):
            palabras, actual, pref = n.split(), '', '%d. ' % i
            for w in palabras:
                prueba = (actual + ' ' + w).strip()
                if fitz.get_text_length(pref + prueba, fontname=FUENTE, fontsize=tn) > cw - 2 * MM and actual:
                    lineas.append(pref + actual)
                    actual, pref = w, '    '
                else:
                    actual = prueba
            lineas.append(pref + actual)
        # la cabecera NOTAS ocupa una linea mas; sin contarla la ultima nota tocaba el borde superior del cajetin
        alto = (len(lineas) + 1) * tn * 1.45 + 1 * MM
        rn = fitz.Rect(x0, y0 - alto - 1.5 * MM, x1, y0 - 1.5 * MM)
        if notas_pos is not None:      # (x_mm, y_mm) de la esquina superior izquierda, origen abajo-izquierda
            rn = fitz.Rect(notas_pos[0] * MM, H - notas_pos[1] * MM, notas_pos[0] * MM + cw, H - notas_pos[1] * MM + alto)
        y = rn.y0 + 2 * MM + tn
        page.insert_text((rn.x0, y - tn * 0.3), 'NOTAS', fontsize=tn, fontname=FUENTE_B)
        y += tn * 1.45
        for linea in lineas:
            page.insert_text((rn.x0, y), linea, fontsize=tn, fontname=FUENTE)
            y += tn * 1.45
    return fitz.Rect(x0, y0, x1, y1)


def demo(ruta):
    doc = fitz.open()
    page = doc.new_page(width=420 * MM, height=297 * MM)
    estampar(page, {'titulo': 'SOPORTE DEL ACTUADOR LINEAL', 'codigo': 'MEC-2-12', 'escala': '1:1',
                    'material': 'PLA', 'masa': '60.6 g', 'formato': 'A3'},
             notas=['Cotas en milímetros. Tolerancias generales según ISO 2768-m.',
                    'Pieza de fabricación aditiva (FDM, PLA): acabado Ra 12.5 salvo indicación.',
                    'Agujeros Ø3.4 para tornillo M3; verificar con calibre tras la impresión.'])
    doc.save(ruta)
    print('demo:', ruta)


if __name__ == '__main__':
    if '--demo' in sys.argv:
        salida = os.path.join(AQUI, '_auto', 'cajetin_demo.pdf')
        os.makedirs(os.path.dirname(salida), exist_ok=True)
        demo(salida)
        d = fitz.open(salida)
        d[0].get_pixmap(dpi=110).save(salida.replace('.pdf', '.png'))
        print('png:', salida.replace('.pdf', '.png'))
