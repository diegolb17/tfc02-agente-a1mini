# -*- coding: utf-8 -*-
"""Figuras del capítulo 4 regeneradas con la geometría vigente (motor de planos):
  fig_cap4_16.png  recorrido del aire por el módulo de enfriamiento (corte por el eje del ventilador)
  fig_cap4_17.png  despiece del módulo de enfriamiento (soporte + ducto separados)
  fig_cap4_21.png  ensamble general con los soportes montados (isométrica)
Salida: TESIS_LATEX/Imagenes/ (PNG 300 dpi, fondo blanco, sin cajetín)."""
import os
import math
import numpy as np
import fitz
from motor.malla import Pieza, transform_ensamble
from motor.hoja import Lamina, Vista, nota, titulo_vista, MM
from ensambles import PIEZAS, pieza_ens, conjunto

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.normpath(os.path.join(AQUI, '..', 'TESIS_LATEX', 'Imagenes'))
Z = np.array([0, 0, 1.0])


def recortar_y_guardar(lam, nombre, margen=6, dpi=300):
    """Guarda la página recortada al contenido dibujado (sin marco ni cajetín)."""
    lam._volcar()
    pdf = os.path.join(AQUI, '_rev', nombre + '.pdf')
    lam.doc.save(pdf)
    d = fitz.open(pdf)
    pg = d[0]
    r = None
    for b in pg.get_drawings():
        r = b['rect'] if r is None else r | b['rect']
    for t in pg.get_text('blocks'):
        rb = fitz.Rect(t[:4])
        r = rb if r is None else r | rb
    r = fitz.Rect(r.x0 - margen * MM, r.y0 - margen * MM, r.x1 + margen * MM, r.y1 + margen * MM)
    salida = os.path.join(IMG, nombre + '.png')
    pg.get_pixmap(dpi=dpi, clip=r).save(salida)
    print('figura', salida, 'recorte %.0f x %.0f mm' % (r.width / MM, r.height / MM))


def fig_21():
    todos = [p[1] for p in PIEZAS] + ['Equipo_A1mini']
    pz = conjunto(todos)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.7), Z, 0.45, ocultas=False, nombre='iso', res=0.15).colocar_centro(210, 150)
    v.dibujar(lam)
    # llamadas
    nota(lam, v, (139, 60, 327), 'Unidad de visión (cámara ESP32-CAM sobre rótula)', 40, 20)
    nota(lam, v, (87, 43, 271), 'Unidad de iluminación (dicroico MR16 sobre rótula)', -60, 24)
    nota(lam, v, (193, 60, 145), 'Soporte tubular Ø40, perpendicular al plano inclinado', 120, -34)
    nota(lam, v, (100, 60, 120), 'Módulo de enfriamiento en la bahía lateral', 40, -30)
    nota(lam, v, (-12, 294, 22), 'Soporte del actuador lineal', -40, -20)
    recortar_y_guardar(lam, 'fig_cap4_21')


def fig_17():
    sop = pieza_ens('Soporte_ventilador')
    duc = pieza_ens('Ducto_cuchilla').transformada(np.eye(3), (0, 90, 0))      # separado 90 mm según +Y
    pz = Pieza.unir([sop, duc])
    lam = Lamina('A3')
    v = Vista(pz, (-1, 1, -0.6), Z, 0.8, ocultas=False, nombre='iso', res=0.08).colocar_centro(210, 150)
    v.dibujar(lam)
    # eje de montaje (línea de trazos entre las dos piezas)
    R, t = transform_ensamble('Ducto_cuchilla')
    eje_loc_a = np.array([106, 47, 85.12]); eje_loc_b = np.array([106, 47 + 90, 85.12])
    a = R @ eje_loc_a + t; b = R @ eje_loc_b + t
    lam.linea(v.m(tuple(a)), v.m(tuple(b)), 'eje')
    nota(lam, v, tuple(R @ np.array([106, 1, 85]) + t), 'Soporte del ventilador (entrada Ø88)', -50, 30)
    nota(lam, v, tuple(R @ np.array([106, 121 + 90, 85]) + t), 'Ducto: de Ø88 a ranura de 149 x 12.8', 30, 30)
    nota(lam, v, tuple(R @ np.array([106, 47 + 45, 85]) + t), 'Ventilador axial 92 x 92 x 38 (comercial) entre ambas piezas', 40, -40)
    recortar_y_guardar(lam, 'fig_cap4_17')


def fig_16():
    sop = pieza_ens('Soporte_ventilador')
    duc = pieza_ens('Ducto_cuchilla')
    pz = Pieza.unir([sop, duc])
    R, t = transform_ensamble('Ducto_cuchilla')
    # plano por el eje del ventilador: local X = 106, normal local +X
    p0 = R @ np.array([106, 60, 85]) + t
    n = R @ np.array([1.0, 0, 0])
    lam = Lamina('A3')
    v = Vista(pz, tuple(n), Z, 1.0, ocultas=False, corte=(tuple(p0), tuple(n)), nombre='corte', res=0.06).colocar_centro(210, 150)
    v.dibujar(lam)
    # flechas del recorrido del aire (en coordenadas locales del módulo -> ensamble)
    def P(x, y, z):
        return tuple(R @ np.array([x, y, z], float) + t)
    tramos = [((106, -30, 85), (106, 5, 85)), ((106, 12, 85), (106, 44, 85)), ((106, 55, 85), (106, 100, 85)),
              ((106, 104, 85), (106, 135, 85))]
    for a, b in tramos:
        pa, pb = np.array(v.m(P(*a))), np.array(v.m(P(*b)))
        lam.linea(tuple(pa), tuple(pb), 'gruesa')
        lam.flecha(tuple(pb), tuple(pb - pa), largo=6, ancho=2.6)
    nota(lam, v, P(106, -20, 85), 'Aire ambiente por la entrada Ø88', 10, 40)
    nota(lam, v, P(106, 28, 120), 'Ventilador axial 92 mm (eje según el flujo)', 60, 40)
    nota(lam, v, P(106, 100, 124), 'Ducto convergente (pared 2 mm)', -10, 24)
    nota(lam, v, P(106, 121, 80), 'Cuchilla de aire 149 x 12.8 sobre la cama', 14, -42)
    recortar_y_guardar(lam, 'fig_cap4_16')


if __name__ == '__main__':
    fig_21()
    fig_17()
    fig_16()


def fig_20():
    """Soportes del actuador (izquierda) y módulo de visión e iluminación (derecha)."""
    act = Pieza.unir([pieza_ens('Soporte_actuador'), pieza_ens('Tapa_actuador')])
    vis = conjunto(['Soporte_camara', 'Horquilla_camara', 'Carcasa_ESP32CAM', 'Horquilla_lampara', 'Aro_lampara'])
    lam = Lamina('A3')
    va = Vista(act, (1, -1, -0.7), Z, 1.2, ocultas=False, nombre='iso', res=0.05).colocar_centro(90, 150)
    vv = Vista(vis, (1, -1, -0.6), Z, 0.6, ocultas=False, nombre='iso', res=0.08).colocar_centro(270, 150)
    va.dibujar(lam); vv.dibujar(lam)
    titulo_vista(lam, 90, 60, 'Soporte y tapa del actuador lineal', '1.2:1', tam=3.5)
    titulo_vista(lam, 270, 60, 'Soporte tubular, horquillas, carcasa y aro', '1:1.7', tam=3.5)
    nota(lam, va, (-24, 294, 30), 'Canal 15.4 x 17.5 para el cuerpo del actuador', -30, 30)
    nota(lam, va, (-27, 294, 22), 'Tapa atornillada: apriete por rozamiento', -30, -30)
    nota(lam, vv, (139, 60, 327), 'Carcasa ESP32-CAM sobre bola SØ16', 30, 20)
    nota(lam, vv, (87, 43, 271), 'Aro MR16 sobre bola SØ20', 50, -30)
    nota(lam, vv, (193, 60, 145), 'Tubo Ø40/Ø34 x 200', 40, -10)
    recortar_y_guardar(lam, 'fig_cap4_20')


def fig_22():
    """Emplazamiento relativo de la cámara y de la unidad de iluminación respecto de la cama."""
    todos = ['Soporte_camara', 'Horquilla_camara', 'Carcasa_ESP32CAM', 'Horquilla_lampara', 'Aro_lampara',
             'Cuna_posterior_derecha', 'Cuna_posterior_izquierda', 'Cuna_frontal_derecha', 'Cuna_frontal_izquierda', 'Equipo_A1mini']
    pz = conjunto(todos)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.55), Z, 0.4, ocultas=False, nombre='iso', res=0.15).colocar_centro(200, 150)
    v.dibujar(lam)
    cama = (64.4, 225.5, 187.3)
    lente = (139.0, 60.0, 327.0)
    aro = (86.6, 43.0, 271.0)
    lam.linea(v.m(lente), v.m(cama), 'eje')
    lam.linea(v.m(aro), v.m(cama), 'eje')
    lam.punto(v.m(cama), 0.9)
    nota(lam, v, lente, ['Objetivo: 157 mm sobre la cama, 210 mm al centro', 'oblicuidad 41.6°, encuadre fijo'], 40, 30)
    nota(lam, v, aro, ['Dicroico: 116 mm sobre la cama, 36° bajo la horizontal', '69° fuera del eje óptico (fuera del encuadre)'], 70, -20)
    nota(lam, v, cama, 'Centro de la cama (180 x 180)', -40, -40)
    recortar_y_guardar(lam, 'fig_cap4_22')


if __name__ == '__main__':
    fig_20()
    fig_22()


def fig_24():
    """Posición del centro de masa: piezas propias y conjunto con el equipo (datos de Fusion, 12 oct 2026)."""
    todos = [p[1] for p in PIEZAS] + ['Equipo_A1mini']
    pz = conjunto(todos)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.6), Z, 0.4, ocultas=False, nombre='iso', res=0.15).colocar_centro(200, 150)
    v.dibujar(lam)
    com_p = (162.4, 154.0, 57.1)        # piezas propias, coordenadas del modelo (mesa en Z = -40)
    com_t = (165.3, 198.2, 137.8)       # conjunto con el equipo de 5.50 kg en el centroide de su envolvente
    for c, r in ((com_p, 2.2), (com_t, 2.2)):
        q = v.m(c)
        lam.circulo(q, r, 'gruesa')
        lam.linea((q[0] - r, q[1]), (q[0] + r, q[1]), 'gruesa'); lam.linea((q[0], q[1] - r), (q[0], q[1] + r), 'gruesa')
    # proyección sobre la mesa (Z = -40) de ambos centros
    for c in (com_p, com_t):
        base = (c[0], c[1], -40.0)
        lam.linea(v.m(c), v.m(base), 'eje')
        lam.punto(v.m(base), 0.8)
    nota(lam, v, com_p, ['Centro de masa de las 19 piezas propias (3.39 kg)', 'x 162.4, y 154.0, 97.1 mm sobre la mesa'], -70, -40)
    nota(lam, v, com_t, ['Centro de masa del conjunto con el equipo (8.89 kg)', 'x 165.3, y 198.2, 177.8 mm sobre la mesa'], 100, 70)
    nota(lam, v, (0, 0, -40), 'Origen: esquina frontal derecha de la estructura, plano de la mesa', 30, -34)
    recortar_y_guardar(lam, 'fig_cap4_24')


if __name__ == '__main__':
    fig_24()
