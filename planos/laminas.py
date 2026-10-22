# -*- coding: utf-8 -*-
"""Generador de las láminas del Anexo G (planos mecánicos).

    python laminas.py MEC-2-12            una lámina
    python laminas.py --todas             todas
Salida: laminas/<codigo>_<nombre>.pdf y _rev/<codigo>_<nombre>.png para revisión."""
import os
import sys
import time
import numpy as np

from motor.malla import Pieza, rasgos
from motor.hoja import (Lamina, Vista, cota, cota_alineada, nota, cota_diametro, cota_radio, cota_angulo, traza,
                        eje_circulo, eje_linea, rugosidad, marca_corte, marca_detalle, titulo_vista, globo, tabla,
                        primer_diedro, iso)

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, 'laminas')
FECHA = '21.10.2026'
REVISION = 'C'          # C: alojamientos del actuador, extractor de 30 mm y cuello del aro (21 oct 2026)
X, Y, Z = np.eye(3)

NOTAS_FDM = [
    'Cotas en milímetros. Tolerancias generales según ISO 2768-m salvo indicación.',
    'Fabricación aditiva FDM en PLA, boquilla 0.4 mm, capa 0.2 mm, 4 perímetros, relleno 40 %.',
    'Acabado de impresión Ra 12.5 en toda la pieza; cantos vivos rotos, rebabas eliminadas.',
]


def _nombre_salida(codigo, pieza):
    return os.path.join(SALIDA, '%s_%s.pdf' % (codigo, pieza))


def _datos(codigo, titulo, escala, pieza, material=None):
    r = rasgos(pieza)
    return {'titulo': titulo, 'codigo': codigo, 'escala': escala, 'formato': 'A3', 'fecha': FECHA,
            'material': material or r['material'], 'masa': '%.1f g' % r['masa_g'],
            'tolerancia': 'ISO 2768-m', 'rugosidad': 'Ra 12.5', 'revision': REVISION}


REGISTRO = {}


def lamina(codigo, pieza, titulo):
    def deco(fn):
        REGISTRO[codigo] = (pieza, titulo, fn)
        return fn
    return deco


# =============================================================================
@lamina('MEC-2-12', 'Soporte_actuador', 'SOPORTE DEL ACTUADOR LINEAL')
def mec_2_12(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 2.0
    lam = Lamina('A3')
    # alzado: cara X=-24 (canal y agujeros) mirando hacia +X
    vs = primer_diedro(lam, pz, dir_frente=X, up=Z, escala=E, centro=(118, 185), sep=22, lateral='izq')
    f, p, l = vs['frente'], vs['planta'], vs['lateral']
    # la planta se sustituye por el corte A-A a Z = 28 (por los insertos y el canal)
    zc = 28.0
    s = Vista(pz, -Z, X, E, ocultas=False, corte=((0, 0, zc), (0, 0, -1)), nombre='corte')
    s.alinear_x(f, pz.malla.V.mean(axis=0))
    s.oy += (f.rect[1] - 22) - s.rect[3]
    for v in (f, s, l):
        v.dibujar(lam)
    # ---- alzado ----
    y0, y1 = 0.0, 44.0
    ya, yb = 264.0, 324.0            # Y extremos (en la hoja: +Y a la izquierda)
    cota(lam, f, (-24, yb, y0), (-24, 301.7, y0), f.rect[3] + 4, 'h')                    # 22.3
    cota(lam, f, (-24, 301.7, y0), (-24, 286.3, y0), f.rect[3] + 4, 'h', tol=('+0.2', '0'))   # 15.4
    cota(lam, f, (-24, yb, y0), (-24, ya, y0), f.rect[3] + 11, 'h')                      # 60
    cota(lam, f, (-24, ya, y0), (-24, ya, y1), f.rect[2] + 11, 'v')                      # 44
    # 21 oct 2026: los pasantes inferiores suben de Z 8 a Z 18 (alojamientos de la cuna con 11 mm de fondo)
    cota(lam, f, (-24, 268, 18), (-24, 268, 34), f.rect[2] + 4, 'v')                     # 16
    cota(lam, f, (-24, 268, 0), (-24, 268, 18), f.rect[2] + 4, 'v')                      # 18
    cota(lam, f, (-24, 280, 16), (-24, 280, 28), f.rect[0] - 4, 'v')                     # 12
    cota(lam, f, (-24, 280, 0), (-24, 280, 16), f.rect[0] - 11, 'v')                     # 16
    cota(lam, f, (-24, 320, 0), (-24, 268, 0), f.rect[1] - 7, 'h')                       # 52
    cota(lam, f, (-24, 308, 0), (-24, 280, 0), f.rect[1] - 14, 'h')                      # 28
    cota(lam, f, (-24, yb, 0), (-24, 320, 0), f.rect[1] - 7, 'h', texto_lado=-6)        # 4
    for (yy, zz) in ((268, 18), (268, 34), (320, 18), (320, 34)):
        eje_circulo(lam, f, (-24, yy, zz), 2.25)
    for (yy, zz) in ((280, 16), (280, 28), (308, 16), (308, 28)):
        eje_circulo(lam, f, (-24, yy, zz), 2.8)
    cota_diametro(lam, f, (-24, 320, 34), 2.25, 135, texto='4x Ø4.5 PASANTE', largo=7)
    cota_diametro(lam, f, (-24, 280, 16), 2.8, -45, texto='4x Ø5.6 prof. 11', largo=6)
    # traza del corte A-A (plano Z=28, se mira desde arriba)
    yc = f.m((-24, 294, zc))[1]
    marca_corte(lam, f, (f.rect[0] - 16, yc), (f.rect[2] + 16, yc), 'A', lado=1, hoja=True)
    # ---- corte A-A ----
    titulo_vista(lam, (s.rect[0] + s.rect[2]) / 2, s.rect[1] - 10, 'CORTE A-A', '2:1')
    cota(lam, s, (-24, ya, zc), (0, ya, zc), s.rect[2] + 6, 'v')                          # 24
    cota(lam, s, (-24, 294, zc), (-6.5, 294, zc), s.rect[0] - 6, 'v')                     # 17.5 canal
    cota(lam, s, (-24, 308, zc), (-13, 308, zc), s.rect[0] - 13, 'v')                     # 11 inserto
    # ---- lateral (desde la izquierda) ----
    cota(lam, l, (-24, yb, 0), (0, yb, 0), l.rect[3] + 6, 'h')                           # 24
    # ---- isométrica ----
    v_iso = iso(lam, pz, 1.0, (335, 215), dir=(1, -1, -0.7), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 335, 160, 'ISOMÉTRICA', '1:1')
    notas = NOTAS_FDM + [
        'Insertos roscados de latón M4 x 10 colocados en caliente en los cuatro agujeros Ø5.6.',
        'Orientación de impresión: cara de 60 x 44 (fondo del canal hacia arriba) sobre la cama, sin soportes.',
        'El actuador queda apretado entre el fondo del canal y la tapa MEC-2-13; no se atornilla.',
    ]
    lam.estampar(_datos(codigo, titulo, '2:1', nombre), notas)
    return lam


# =============================================================================
def generar(codigo):
    pieza, titulo, fn = REGISTRO[codigo]
    t = time.time()
    lam = fn(codigo, pieza, titulo)
    ruta = _nombre_salida(codigo, pieza)
    png = lam.guardar(ruta)
    print('%s -> %s  (%.0f s)  png: %s' % (codigo, os.path.basename(ruta), time.time() - t, os.path.basename(png)))
    return ruta


if __name__ == '__main__':
    import piezas_a  # noqa: F401  (registra sus láminas)
    args = sys.argv[1:]
    if not args or args[0] == '--todas':
        for c in sorted(REGISTRO):
            generar(c)
    else:
        for c in args:
            generar(c)
