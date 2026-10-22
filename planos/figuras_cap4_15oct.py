# -*- coding: utf-8 -*-
"""Figuras del capitulo 4 rehechas tras la revision de Denis Pena (15 oct 2026):
  fig_cap4_21.png  vista general con la impresora en gris, porque no forma parte del diseno, y rotulos legibles
  fig_cap4_16.png  corte del modulo de enfriamiento con sus cotas principales y vista frontal de la ranura
  fig_cap4_17.png  vista explosionada del modulo de enfriamiento con rotulos legibles
La impresora se distingue rasterizando dos veces la misma vista, con y sin ella: lo que solo aparece con la impresora
son sus aristas visibles, que se repintan en gris; las piezas propias que ella oculta no aparecen en ninguna."""
import os

import fitz
import numpy as np
from PIL import Image, ImageFilter

from motor.malla import Pieza, transform_ensamble
from motor.hoja import Lamina, Vista, nota, cota, MM
from ensambles import PIEZAS, pieza_ens, conjunto

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.normpath(os.path.join(AQUI, '..', 'TESIS_LATEX', 'Imagenes'))
Z = np.array([0, 0, 1.0])
TAM = 6.5            # altura de texto en la hoja A3; con la reduccion de la figura queda cerca de 9 puntos
TAM21 = 8.0          # la vista general se recorta mas ancha (389 mm): con 8 mm el rotulo queda cerca de 9 puntos a ancho de pagina


def volcar(lam, nombre, clip=None, margen=6, dpi=300):
    lam._volcar()
    pdf = os.path.join(AQUI, '_rev', nombre + '.pdf')
    lam.doc.save(pdf)
    pg = fitz.open(pdf)[0]
    if clip is None:
        r = None
        for b in pg.get_drawings():
            r = b['rect'] if r is None else r | b['rect']
        for t in pg.get_text('blocks'):
            rb = fitz.Rect(t[:4])
            r = rb if r is None else r | rb
        clip = fitz.Rect(r.x0 - margen * MM, r.y0 - margen * MM, r.x1 + margen * MM, r.y1 + margen * MM)
    pix = pg.get_pixmap(dpi=dpi, clip=clip)
    return Image.frombytes('RGB', (pix.width, pix.height), pix.samples), clip


def notas_21(lam, v):
    nota(lam, v, (139, 60, 327), ['Unidad de visión:', 'cámara ESP32-CAM sobre rótula'], 44, 30, tam=TAM21)
    nota(lam, v, (87, 43, 271), ['Unidad de iluminación:', 'dicroico MR16 sobre rótula'], 56, -2, tam=TAM21)
    nota(lam, v, tuple(0.55 * pieza_ens('Carcasa_ESP32CAM').malla.V.mean(axis=0) + 0.45 * pieza_ens('Soporte_camara').malla.V.mean(axis=0)), ['Soporte tubular Ø40,', 'normal al plano inclinado'], 95, -52, tam=TAM21)
    nota(lam, v, tuple(pieza_ens('Soporte_ventilador').malla.V.mean(axis=0)), ['Módulo de enfriamiento', 'en la bahía lateral'], 62, -64, tam=TAM21)
    nota(lam, v, (-12, 294, 22), 'Soporte del actuador lineal', -34, -38, tam=TAM21)


def fig_21():
    propias = [p[1] for p in PIEZAS]
    con = conjunto(propias + ['Equipo_A1mini'])
    sin = conjunto(propias)
    d = (1, -1, -0.7)
    lam_a = Lamina('A3')
    va = Vista(con, d, Z, 0.45, ocultas=False, nombre='iso', res=0.15).colocar_centro(193, 150)   # con TAM21 el rotulo de la impresora no cabia a la izquierda
    va.dibujar(lam_a)
    ref = tuple(pieza_ens('Cuna_frontal_derecha').malla.V.mean(axis=0))
    lam_b = Lamina('A3')
    vb = Vista(sin, d, Z, 0.45, ocultas=False, nombre='iso', res=0.15)
    x, y = va.m(ref)
    vb.colocar_punto(ref, x=x, y=y)
    vb.dibujar(lam_b)
    eq = pieza_ens('Equipo_A1mini').malla.V
    p_eq = tuple(np.array([eq[:, 0].mean(), eq[:, 1].mean(), eq[:, 2].max() - 40]))
    for lam in (lam_a, lam_b):
        notas_21(lam, va)
        nota(lam, va, p_eq, ['Impresora Bambu Lab A1 mini,', 'en gris: no forma parte del diseño'], -40, 26, tam=TAM21)
    im_a, clip = volcar(lam_a, 'fig21_con')
    im_b, _ = volcar(lam_b, 'fig21_sin', clip)
    a = np.array(im_a.convert('L'))
    b_dil = np.array(im_b.convert('L').filter(ImageFilter.MinFilter(7)))
    solo_impresora = (a < 200) & (b_dil > 200)
    out = np.array(im_a)
    out[solo_impresora] = [150, 150, 150]
    Image.fromarray(out).save(os.path.join(IMG, 'fig_cap4_21.png'))
    print('figura fig_cap4_21.png')


def fig_17():
    sop = pieza_ens('Soporte_ventilador')
    duc = pieza_ens('Ducto_cuchilla').transformada(np.eye(3), (0, 90, 0))
    pz = Pieza.unir([sop, duc])
    lam = Lamina('A3')
    v = Vista(pz, (-1, 1, -0.6), Z, 0.8, ocultas=False, nombre='iso', res=0.08).colocar_centro(210, 150)
    v.dibujar(lam)
    R, t = transform_ensamble('Ducto_cuchilla')
    a = R @ np.array([106, 47, 85.12]) + t
    b = R @ np.array([106, 47 + 90, 85.12]) + t
    lam.linea(v.m(tuple(a)), v.m(tuple(b)), 'eje')
    nota(lam, v, tuple(R @ np.array([106, 1, 85]) + t), ['Soporte del ventilador', '(entrada Ø88)'], -46, 34, tam=TAM)
    nota(lam, v, tuple(R @ np.array([106, 121 + 90, 85]) + t), ['Ducto: de Ø88 a la', 'ranura de 149 x 12.8'], 30, 34, tam=TAM)
    nota(lam, v, tuple(R @ np.array([106, 47 + 45, 85]) + t), ['Ventilador axial 92 x 92 x 38,', 'comercial, entre ambas piezas'], 36, -46, tam=TAM)
    im, _ = volcar(lam, 'fig17_15oct')
    im.save(os.path.join(IMG, 'fig_cap4_17.png'))
    print('figura fig_cap4_17.png')


def fig_16():
    sop = pieza_ens('Soporte_ventilador')
    duc = pieza_ens('Ducto_cuchilla')
    pz = Pieza.unir([sop, duc])
    R, t = transform_ensamble('Ducto_cuchilla')
    E = 0.85

    def P(x, y, z):
        return tuple(R @ np.array([x, y, z], float) + t)

    p0 = R @ np.array([106, 60, 85]) + t
    n = R @ np.array([1.0, 0, 0])
    lam = Lamina('A3')
    v = Vista(pz, tuple(n), Z, E, ocultas=False, corte=(tuple(p0), tuple(n)), nombre='corte', res=0.06).colocar_centro(150, 150)
    v.dibujar(lam)
    tramos = [((106, -30, 85), (106, 5, 85)), ((106, 12, 85), (106, 44, 85)), ((106, 55, 85), (106, 100, 85)),
              ((106, 104, 85), (106, 135, 85))]
    for a, b in tramos:
        pa, pb = np.array(v.m(P(*a))), np.array(v.m(P(*b)))
        lam.linea(tuple(pa), tuple(pb), 'gruesa')
        lam.flecha(tuple(pb), tuple(pb - pa), largo=6, ancho=2.6)
    cota(lam, v, P(106, 47, 135.12), P(106, 121, 135.12), v.rect[3] + 10, 'h', tam=TAM)
    lado_brida = v.m(P(106, 51, 85))[0]
    cota(lam, v, P(106, 51, 41.12), P(106, 51, 129.12), v.rect[2] + 12, 'v', prefijo='Ø', tam=TAM)
    lado_sal = v.m(P(106, 121, 85))[0]
    cota(lam, v, P(106, 121, 78.72), P(106, 121, 91.52), lado_sal - 12, 'v', tam=TAM)
    nota(lam, v, P(106, 85, 108), 'Ducto convergente, pared de 2', 4, 62, tam=TAM)
    nota(lam, v, P(106, 28, 120), ['Ventilador axial', '92 x 92 x 38'], 30, 14, tam=TAM)
    lam.texto((v.rect[0] + v.rect[2]) / 2, v.rect[1] - 12, 'CORTE POR EL EJE DEL VENTILADOR', TAM, 0, 'c', negrita=True)
    loc = Pieza('Ducto_cuchilla')
    f = Vista(loc, (0, -1.0, 0), Z, E, ocultas=True, nombre='frente', res=0.06).colocar_centro(325, 150)
    f.dibujar(lam)
    cota(lam, f, (31.5, 121, 85.12), (180.5, 121, 85.12), f.rect[1] - 10, 'h', texto='149 (ranura interior)', tam=TAM)
    cota(lam, f, (29.5, 121, 85.12), (182.5, 121, 85.12), f.rect[3] + 10, 'h', texto='153', tam=TAM)
    xd = max(f.m((180.5, 121, 85.12))[0], f.m((31.5, 121, 85.12))[0])
    cota(lam, f, (106, 121, 78.72), (106, 121, 91.52), f.rect[2] + 12, 'v', texto='12.8', tam=TAM)
    lam.texto((f.rect[0] + f.rect[2]) / 2, f.rect[1] - 26, 'VISTA FRONTAL DESDE LA SALIDA: CUCHILLA DE AIRE', TAM, 0, 'c', negrita=True)
    im, _ = volcar(lam, 'fig16_15oct')
    im.save(os.path.join(IMG, 'fig_cap4_16.png'))
    print('figura fig_cap4_16.png')


if __name__ == '__main__':
    import sys
    quien = sys.argv[1:] or ['21', '17', '16']
    for q in quien:
        {'21': fig_21, '17': fig_17, '16': fig_16}[q]()
