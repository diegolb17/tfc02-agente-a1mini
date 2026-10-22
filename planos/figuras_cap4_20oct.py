# -*- coding: utf-8 -*-
"""Figuras del capitulo 4 rehechas con el modelo corregido para la impresion (v98, 19 oct 2026) y las marcas de
Diego del 20 oct 2026:
  fig_cap4_21.png  vista general: la impresora se rellena de gris claro (antes solo sus aristas iban en gris y
                   "en la figura no se ve nada en gris")
  fig_cap4_20.png  soportes del actuador y de la camara, con rotulos del mismo cuerpo que la Figura 8
  fig_cap4_22.png  emplazamiento de la camara y de la lampara, con las cifras medidas sobre el modelo
  fig_cap4_23.png  bandeja de la electronica con las rejillas, desde la geometria vigente
  fig_cap4_despiece.png  vista explosionada (misma funcion de figuras_cap4_despiece.py)
Las posiciones de la camara, la lampara y la placa se leen del modelo (geometria.py), no se escriben a mano."""
import os
import sys

import numpy as np
from PIL import Image

from motor.malla import Pieza
from motor.hoja import Lamina, Vista, nota, MM
from ensambles import PIEZAS, pieza_ens, conjunto, centroide
from figuras_cap4_15oct import volcar, TAM21
from geometria import vision

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.normpath(os.path.join(AQUI, '..', 'TESIS_LATEX', 'Imagenes'))
Z = np.array([0, 0, 1.0])
T = 6.5              # rotulos de las figuras a 0.8 del ancho de pagina: quedan cerca de 9 puntos, como la Figura 8
G = vision()


def guardar(lam, nombre, margen=6):
    im, _ = volcar(lam, nombre + '_20oct', margen=margen)
    im.save(os.path.join(IMG, nombre + '.png'))
    print('figura', nombre, im.size)


def mascara_pieza(v, pz, k, clip, dpi, shape):
    """Pixeles de la imagen recortada en que la pieza k del conjunto es la superficie visible (z-buffer de la vista)."""
    pr = v.pr
    lim = np.cumsum([0] + list(pz.n_tri))
    alto, ancho = shape
    uu, ww = np.meshgrid(np.arange(ancho), np.arange(alto))
    X = clip.x0 + (uu + 0.5) * 72.0 / dpi
    Yp = clip.y0 + (ww + 0.5) * 72.0 / dpi
    xs = X / MM
    ys = Lamina('A3').H - Yp / MM
    q0 = (xs - v.ox) / v.escala
    q1 = (ys - v.oy) / v.escala
    i = np.floor((q0 - pr.x0) / pr.res).astype(int)
    j = np.floor((q1 - pr.y0) / pr.res).astype(int)
    ok = (i >= 0) & (j >= 0) & (i < pr.ib.shape[1]) & (j < pr.ib.shape[0])
    m = np.zeros(shape, bool)
    ib = pr.ib[j[ok], i[ok]]
    m[ok] = (ib >= lim[k]) & (ib < lim[k + 1])
    return m


def notas_21(lam, v):
    nota(lam, v, tuple(centroide('Carcasa_ESP32CAM')), ['Unidad de visión:', 'cámara ESP32-CAM sobre rótula'], 44, 34, tam=TAM21)
    nota(lam, v, tuple(G['aro']), ['Unidad de iluminación:', 'dicroico MR16 sobre rótula'], 46, 4, tam=TAM21)
    p_tubo = tuple(G['soporte_base'] + 95 * G['eje_tubo'])
    nota(lam, v, p_tubo, ['Soporte tubular Ø40,', 'normal al plano inclinado'], 72, -40, tam=TAM21)
    nota(lam, v, tuple(pieza_ens('Soporte_ventilador').malla.V.mean(axis=0)), ['Módulo de enfriamiento', 'en la bahía lateral'], 62, -64, tam=TAM21)
    nota(lam, v, (-12, 294, 22), 'Soporte del actuador lineal', -34, -38, tam=TAM21)


def fig_21():
    propias = [p[1] for p in PIEZAS]
    con = conjunto(propias + ['Equipo_A1mini'])
    d = (1, -1, -0.7)
    lam = Lamina('A3')
    va = Vista(con, d, Z, 0.42, ocultas=False, nombre='iso', res=0.15).colocar_centro(203, 150)
    va.dibujar(lam)
    eq = pieza_ens('Equipo_A1mini').malla.V
    p_eq = tuple(np.array([eq[:, 0].mean(), eq[:, 1].mean(), eq[:, 2].max() - 40]))
    notas_21(lam, va)
    nota(lam, va, p_eq, ['Impresora Bambu Lab A1 mini,', 'en gris: no forma parte del diseño'], -36, 26, tam=TAM21)
    im, clip = volcar(lam, 'fig21_20oct')
    clip = clip & lam.page.rect          # get_pixmap recorta el clip a la hoja: el mapeo debe usar el mismo origen
    a = np.array(im)
    m = mascara_pieza(va, con, len(propias), clip, 300, a.shape[:2])
    gris = np.array(im.convert('L'))
    # caras de la impresora en gris claro; sus aristas en gris medio; piezas propias y rotulos quedan en negro
    cara = m & (gris > 200)
    arista = m & (gris <= 200)
    out = a.copy()
    out[cara] = [222, 222, 222]
    out[arista] = [120, 120, 120]
    Image.fromarray(out).save(os.path.join(IMG, 'fig_cap4_21.png'))
    print('figura fig_cap4_21.png', out.shape, 'pixeles de la impresora: %d' % m.sum())


def fig_20():
    """Soportes del actuador (izquierda) y modulo de vision e iluminacion (derecha)."""
    act = Pieza.unir([pieza_ens('Soporte_actuador'), pieza_ens('Tapa_actuador')])
    vis = conjunto(['Soporte_camara', 'Horquilla_camara', 'Carcasa_ESP32CAM', 'Horquilla_lampara', 'Aro_lampara'])
    lam = Lamina('A3')
    va = Vista(act, (1, -1, -0.7), Z, 1.4, ocultas=False, nombre='iso', res=0.04).colocar_centro(100, 150)
    vv = Vista(vis, (1, -1, -0.6), Z, 0.7, ocultas=False, nombre='iso', res=0.06).colocar_centro(262, 150)
    va.dibujar(lam); vv.dibujar(lam)
    lam.texto(100, 60, 'Soporte y tapa del actuador lineal', T, 0, 'c', negrita=True)
    lam.texto(262, 50, 'Soporte tubular, horquillas, carcasa y aro', T, 0, 'c', negrita=True)
    nota(lam, va, (-24, 294, 30), ['Canal de 15.4 x 17.5 para', 'el cuerpo del actuador'], -20, 44, tam=T)
    nota(lam, va, (-27, 294, 22), ['Tapa atornillada:', 'apriete por rozamiento'], -12, -62, tam=T)
    nota(lam, vv, tuple(centroide('Carcasa_ESP32CAM')), ['Carcasa ESP32-CAM', 'sobre bola SØ16'], -60, 30, tam=T)
    nota(lam, vv, tuple(G['aro']), ['Aro MR16 sobre', 'bola SØ20'], 30, 28, tam=T)
    nota(lam, vv, tuple(G['soporte_base'] + 80 * G['eje_tubo']), ['Tubo Ø40/Ø34 x 165', 'sobre placa de 10'], 50, -36, tam=T)
    guardar(lam, 'fig_cap4_20')


def fig_22():
    """Emplazamiento relativo de la camara y de la unidad de iluminacion respecto de la placa."""
    todos = ['Soporte_camara', 'Horquilla_camara', 'Carcasa_ESP32CAM', 'Horquilla_lampara', 'Aro_lampara',
             'Cuna_posterior_derecha', 'Cuna_posterior_izquierda', 'Cuna_frontal_derecha', 'Cuna_frontal_izquierda', 'Equipo_A1mini']
    pz = conjunto(todos)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.55), Z, 0.42, ocultas=False, nombre='iso', res=0.12).colocar_centro(160, 150)
    v.dibujar(lam)
    cama, lente, aro = tuple(G['centro_placa']), tuple(G['lente']), tuple(G['aro'])
    lam.linea(v.m(lente), v.m(cama), 'eje')
    lam.linea(v.m(aro), v.m(cama), 'eje')
    lam.punto(v.m(cama), 1.0)
    nota(lam, v, lente, ['Objetivo: %.0f mm sobre la placa,' % G['h_lente'],
                         '%.0f mm al centro, oblicuidad de %.0f°' % (G['d_lente'], G['oblicuidad'])], 40, 30, tam=T)
    nota(lam, v, aro, ['Dicroico: %.0f mm sobre la placa,' % G['h_aro'],
                       'haz dirigido al centro, %.0f° fuera' % G['aro_fuera_eje'], 'del eje óptico (fuera del encuadre)'], 56, -26, tam=T)
    nota(lam, v, cama, 'Centro de la placa (180 x 180)', 80, -62, tam=T)
    guardar(lam, 'fig_cap4_22')


def fig_23():
    """Bandeja de la electronica con las rejillas de admision al frente y el soporte del actuador."""
    nombres = ['Bandeja_frontal_derecha', 'Bandeja_frontal_izquierda', 'Bandeja_posterior_derecha',
               'Bandeja_posterior_izquierda', 'Rejilla_frontal_derecha', 'Rejilla_frontal_izquierda',
               'Soporte_actuador', 'Tapa_actuador']
    pz = conjunto(nombres)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.9), Z, 0.52, ocultas=False, nombre='iso', res=0.08).colocar_centro(218, 150)
    v.dibujar(lam)
    nota(lam, v, tuple(centroide('Rejilla_frontal_derecha')), ['Rejillas de admisión', 'al frente'], 24, -40, tam=T)
    nota(lam, v, tuple(centroide('Bandeja_posterior_izquierda')), ['Bandeja en cuatro cuartos,', 'unidos con tornillos M4'], -22, 46, tam=T)
    nota(lam, v, tuple(centroide('Soporte_actuador')), 'Soporte del actuador', -50, -30, tam=T)
    nota(lam, v, tuple(centroide('Bandeja_posterior_derecha') + np.array([60, 0, 0])), ['Ventana del módulo', 'de entrada de red'], 50, 30, tam=T)
    guardar(lam, 'fig_cap4_23')


def fig_24():
    """Centro de masa de las piezas propias y del conjunto con el equipo (calculos_20oct.json)."""
    import json
    J = json.load(open(os.path.join(AQUI, '..', 'TESIS_LATEX', '_conversion', 'calculos_20oct.json'), encoding='utf-8'))['masas']
    zm = J['z_mesa']
    cp, cc = J['cg_propias_mm'], J['cg_conjunto_mm']
    com_p = (cp[0], cp[1], cp[2] + zm)
    com_t = (cc[0], cc[1], cc[2] + zm)
    pz = conjunto([p[1] for p in PIEZAS] + ['Equipo_A1mini'])
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.6), Z, 0.36, ocultas=False, nombre='iso', res=0.15).colocar_centro(195, 140)
    v.dibujar(lam)
    for c, r in ((com_p, 2.4), (com_t, 2.4)):
        q = v.m(c)
        lam.circulo(q, r, 'gruesa')
        lam.linea((q[0] - r, q[1]), (q[0] + r, q[1]), 'gruesa'); lam.linea((q[0], q[1] - r), (q[0], q[1] + r), 'gruesa')
    for c in (com_p, com_t):
        base = (c[0], c[1], zm)
        lam.linea(v.m(c), v.m(base), 'eje')
        lam.punto(v.m(base), 0.8)
    nota(lam, v, com_p, ['Centro de masa de las 19 piezas propias (%.2f kg):' % (J['total_g'] / 1000),
                         'x %.1f, y %.1f, %.1f mm sobre la mesa' % tuple(cp)], -40, -64, tam=T)
    nota(lam, v, com_t, ['Centro de masa del conjunto con el equipo (%.2f kg):' % J['m_conjunto'],
                         'x %.1f, y %.1f, %.1f mm sobre la mesa' % tuple(cc)], 60, 112, tam=T)
    nota(lam, v, (0, 0, zm), ['Origen: esquina frontal derecha', 'de la estructura, plano de la mesa'], 14, -26, tam=T)
    guardar(lam, 'fig_cap4_24')


def fig_despiece():
    import figuras_cap4_despiece
    figuras_cap4_despiece.fig_despiece()


if __name__ == '__main__':
    quien = sys.argv[1:] or ['21', '20', '22', '23', 'despiece']
    for q in quien:
        {'21': fig_21, '20': fig_20, '22': fig_22, '23': fig_23, '24': fig_24, 'despiece': fig_despiece}[q]()
