# -*- coding: utf-8 -*-
"""Láminas del grupo B: módulo de enfriamiento (soporte del ventilador, ducto, rejilla)."""
import numpy as np
from laminas import (lamina, Pieza, Lamina, Vista, cota, cota_alineada, nota, cota_diametro, cota_radio,
                     cota_angulo, eje_circulo, eje_linea, rugosidad, marca_corte, marca_detalle, traza,
                     titulo_vista, globo, tabla, primer_diedro, iso, NOTAS_FDM, _datos, X, Y, Z)
from piezas_a import _bajo, _derecha, _cx


# -----------------------------------------------------------------------------
@lamina('MEC-2-09', 'Soporte_ventilador', 'SOPORTE DEL VENTILADOR')
def mec_2_09(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 0.5
    lam = Lamina('A3')
    xc = 106.0                                  # eje del ventilador
    plano = ((xc, 0, 0), (1, 0, 0))
    f = Vista(pz, Y, Z, E, ocultas=True, nombre='frente').colocar_centro(95, 212)
    p = Vista(pz, -Z, Y, E, ocultas=True, nombre='planta')
    p.alinear_x(f, (xc, 0, 0)); _bajo(p, f, 40)
    s = Vista(pz, X, Z, E, ocultas=False, corte=plano, nombre='corte A-A')
    s.alinear_y(f, (xc, 0, 0)); _derecha(s, f, 34)
    for v in (f, p, s):
        v.dibujar(lam)
    # --- frente (entrada de aire) ---
    cota(lam, f, (48, 1, 0), (164, 1, 0), f.rect[1] - 7, 'h')                         # 116
    cota(lam, f, (54, 1, 137), (158, 1, 137), f.rect[3] + 12, 'h')                    # 104
    cota(lam, f, (64.75, 1, 126.37), (147.25, 1, 126.37), f.rect[3] + 5, 'h')         # 82.5
    cota(lam, f, (164, 1, 0), (164, 1, 137.12), f.rect[2] + 14, 'v')                  # 137.1
    cota(lam, f, (164, 1, 0), (164, 1, 33.12), f.rect[2] + 6, 'v')                    # 33.1
    cota(lam, f, (164, 1, 43.87), (164, 1, 126.37), f.rect[2] + 6, 'v')               # 82.5
    cota(lam, f, (48, 1, 0), (48, 1, 43.87), f.rect[0] - 6, 'v')                      # 43.9
    cota(lam, f, (48, 1, 0), (48, 1, 85.12), f.rect[0] - 13, 'v')                     # 85.1 eje
    eje_circulo(lam, f, (xc, 1, 85.12), 44)
    for xx in (64.75, 147.25):
        for zz in (43.87, 126.37):
            eje_circulo(lam, f, (xx, 1, zz), 2.25)
    cota_diametro(lam, f, (xc, 1, 85.12), 44, 35, texto='Ø88 ENTRADA', largo=12)
    cota_diametro(lam, f, (64.75, 1, 126.37), 2.25, 135, texto='4x Ø4.5 PASANTE', largo=10)
    traza(lam, f, (xc, 0, 0), (1, 0, 0), X, 'A', margen=(12, 24))
    # --- planta ---
    cota(lam, p, (48, 1, 0), (48, 114, 0), p.rect[0] - 8, 'v')                        # 113
    cota(lam, p, (48, 1, 0), (48, 47, 0), p.rect[0] - 15, 'v')                        # 46 caja
    cota(lam, p, (164, 47, 18), (164, 111, 18), p.rect[2] + 6, 'v')                   # 64 guías
    cota(lam, p, (164, 95, 18), (164, 114, 18), p.rect[2] + 13, 'v')                  # 19
    cota(lam, p, (76, 111, 18), (88, 111, 18), p.rect[3] + 5, 'h', texto_lado=-7)     # 12
    cota(lam, p, (88, 111, 18), (124, 111, 18), p.rect[3] + 5, 'h')                   # 36
    cota(lam, p, (82, 95, 18), (130, 95, 18), p.rect[3] + 12, 'h', texto_lado=16)     # 48
    for xx in (82, 130):
        eje_circulo(lam, p, (xx, 95, 18), 2.25)
    eje_circulo(lam, p, (126, 30, 38), 6)
    cota_diametro(lam, p, (130, 95, 18), 2.25, -30, texto='2x Ø4.5 PASANTE', largo=30)
    cota(lam, p, (48, 30, 38), (126, 30, 38), p.rect[1] - 8, 'h')                     # 78 posición del Ø12
    cota(lam, p, (164, 1, 38), (164, 30, 38), p.rect[2] + 42, 'v')                    # 29 posición del Ø12
    cota_diametro(lam, p, (126, 30, 38), 6, -40, texto='Ø12 PASO DE CABLE', largo=14)
    nota(lam, p, (48, 9, 2), 'R2 EN ARISTAS EXTERIORES', -8, 10)
    # --- corte A-A ---
    titulo_vista(lam, _cx(s), s.rect[3] + 12, 'CORTE A-A', '1:2')
    cota(lam, s, (xc, 47, 137), (xc, 1, 137), s.rect[3] + 5, 'h')                     # 46
    cota(lam, s, (xc, 47, 131.4), (xc, 9, 131.4), s.rect[1] - 7, 'h')                 # 38 cavidad
    cota(lam, s, (xc, 9, 85), (xc, 1, 85), s.rect[1] - 7, 'h', texto_lado=6)          # 8 pared
    cota(lam, s, (xc, 114, 0), (xc, 47, 0), s.rect[1] - 14, 'h')                      # 67
    cota(lam, s, (xc, 1, 38.8), (xc, 1, 131.4), s.rect[2] + 6, 'v')                   # 92.6
    cota(lam, s, (xc, 1, 131.4), (xc, 1, 137.12), s.rect[2] + 6, 'v', texto_lado=6)   # 5.7
    cota(lam, s, (xc, 114, 0), (xc, 114, 4), s.rect[0] - 6, 'v', texto_lado=-5)       # 4 base
    cota(lam, s, (xc, 114, 0), (xc, 114, 18), s.rect[0] - 13, 'v')                    # 18 guía
    cota(lam, s, (xc, 47, 4), (xc, 47, 38), s.rect[0] - 6, 'v')                       # 34 plenum
    nota(lam, s, (xc, 28, 100), ['ALOJAMIENTO DEL VENTILADOR', '92.6 x 92.6 x 38'], 24, 18)
    # --- isométrica ---
    v_iso = iso(lam, pz, 0.5, (330, 205), dir=(-1, -1, -0.7), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 330, 140, 'ISOMÉTRICA', '1:2')
    notas = NOTAS_FDM + [
        'Aloja un ventilador axial de 92 x 92 x 38 mm con el eje según Y; entrada de aire por la cara frontal Ø88.',
        'Los 4 tornillos M4 x 60 con arandela y tuerca M4 aprietan pared (8), ventilador (38) y brida del ducto MEC-2-10 (4).',
        'La base apoya en la bahía lateral de la cuna; las guías de 12 x 18 centran el ducto.',
        'Orientación de impresión: base sobre la cama.',
    ]
    lam.estampar(_datos(codigo, titulo, '1:2', nombre), notas)
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-10', 'Ducto_cuchilla', 'DUCTO DE ENFRIAMIENTO (CUCHILLA DE AIRE)')
def mec_2_10(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 1.0
    lam = Lamina('A3')
    xc, zc = 106.0, 85.12
    plano = ((xc, 0, 0), (1, 0, 0))
    f = Vista(pz, Y, Z, E, ocultas=True, nombre='frente').colocar_centro(112, 200)
    p = Vista(pz, -Z, Y, E, ocultas=True, nombre='planta')
    p.alinear_x(f, (xc, 0, 0)); _bajo(p, f, 26)
    s = Vista(pz, X, Z, E, ocultas=False, corte=plano, nombre='corte A-A')
    s.alinear_y(f, (xc, 0, 0)); _derecha(s, f, 34)
    for v in (f, p, s):
        v.dibujar(lam)
    # --- frente (desde la brida) ---
    cota(lam, f, (29.5, 121, zc), (182.5, 121, zc), f.rect[3] + 14, 'h')              # 153
    cota(lam, f, (56, 47, 135), (156, 47, 135), f.rect[3] + 6, 'h')                   # 100
    cota(lam, f, (64.75, 47, 126.37), (147.25, 47, 126.37), f.rect[1] - 7, 'h')       # 82.5
    cota(lam, f, (156, 47, 35), (156, 47, 135), f.rect[2] + 8, 'v')                   # 100
    cota(lam, f, (156, 47, 43.87), (156, 47, 126.37), f.rect[2] + 15, 'v')            # 82.5
    cota(lam, f, (182.5, 121, 76.7), (182.5, 121, 93.5), f.rect[2] + 8 - 0, 'v', texto_lado=12)   # 16.8
    cota(lam, f, (56, 47, 35), (56, 47, zc), f.rect[0] - 8, 'v')                      # 50.1 eje
    eje_circulo(lam, f, (xc, 47, zc), 44)
    for xx in (64.75, 147.25):
        for zz in (43.87, 126.37):
            eje_circulo(lam, f, (xx, 47, zz), 2.25)
    cota_diametro(lam, f, (xc, 47, zc), 44, 160, texto='Ø88', largo=10)
    # esquinas R3 de la brida (el trazado de aristas las deja abiertas)
    for (cxx, czz, a0) in ((59, 38.12, 180), (153, 38.12, 270), (153, 132.12, 0), (59, 132.12, 90)):
        lam.arco(f.m((cxx, 47, czz)), 3 * E, a0, a0 + 90, 'visible')
        # silueta del canto redondeado R2 en la esquina: R3 + 2 = R5, cierra el contorno de 104 x 104
        lam.arco(f.m((cxx, 47, czz)), 5 * E, a0, a0 + 90, 'visible')
    cota_diametro(lam, f, (64.75, 47, 43.87), 2.25, -135, texto='4x Ø4.5 PASANTE', largo=12)
    cota_radio(lam, f, (59, 47, 38.12), 3, 225, texto='R3 (4x)', largo=8)
    traza(lam, f, (xc, 0, 0), (1, 0, 0), X, 'A', margen=(12, 24))
    # --- planta ---
    cota(lam, p, (183.5, 47, zc), (183.5, 121, zc), p.rect[2] + 8, 'v')               # 74
    cota(lam, p, (183.5, 47, zc), (183.5, 51, zc), p.rect[2] + 15, 'v', texto_lado=-6)  # 4 brida
    cota_angulo(lam, p, (156, 51, zc), (156, 121, zc), (182.5, 121, zc), 40, texto='20.7°')
    nota(lam, p, (170, 119, zc), ['SALIDA 153 x 16.8 (exterior)', 'ranura interior 149 x 12.8'], 34, 10)
    eje_linea(lam, p, (xc, 44, zc), (xc, 124, zc))
    # --- corte A-A ---
    titulo_vista(lam, _cx(s), s.rect[3] + 12, 'CORTE A-A', '1:1')
    cota(lam, s, (xc, 47, 135.12), (xc, 121, 135.12), s.rect[3] + 5, 'h')             # 74
    cota(lam, s, (xc, 121, 76.7), (xc, 121, 93.5), s.rect[0] - 8, 'v')                # 16.8
    cota(lam, s, (xc, 47, 35.12), (xc, 47, 135.12), s.rect[2] + 8, 'v')               # 100
    cota(lam, s, (xc, 51, 41.12), (xc, 51, 129.12), s.rect[2] + 15, 'v', prefijo='Ø')   # Ø88
    nota(lam, s, (xc, 90, 115.5), 'ESPESOR DE PARED 2', -30, 12)
    eje_linea(lam, s, (xc, 44, zc), (xc, 124, zc))
    # --- isométrica ---
    v_iso = iso(lam, pz, 0.5, (340, 205), dir=(-1, 1, -0.6), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 340, 150, 'ISOMÉTRICA', '1:2')
    notas = NOTAS_FDM + [
        'Transición continua de la sección Ø88 de la brida a la ranura de salida de 149 x 12.8; pared de 2 mm.',
        'Brida de 100 x 100 x 4 con canto redondeado R2 en todo el contorno (silueta exterior de 104 x 104).',
        'La brida se atornilla a la cara posterior del soporte MEC-2-09 con los 4 tornillos M4 x 60 del ventilador.',
        'Orientación de impresión: brida sobre la cama, ranura hacia arriba; no requiere soportes interiores.',
    ]
    lam.estampar(_datos(codigo, titulo, '1:1', nombre), notas)
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-11', 'Rejilla_frontal_derecha', 'REJILLAS DE ADMISIÓN (2, SIMÉTRICAS)')
def mec_2_11(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 1.0
    lam = Lamina('A3')
    vs = primer_diedro(lam, pz, dir_frente=-X, up=Z, escala=E, centro=(140, 215), sep=20, lateral='izq')
    f, p, l = vs['frente'], vs['planta'], vs['lateral']
    for v in (f, p, l):
        v.dibujar(lam)
    # --- frente (cara del panel realzado, +X) ---
    cota(lam, f, (4, 2, -2), (4, 170, -2), f.rect[3] + 12, 'h')                         # 168
    cota(lam, f, (4, 14.5, -2), (4, 161.5, -2), f.rect[3] + 5, 'h')                     # 147
    cota(lam, f, (4, 2, -2), (4, 14.5, -2), f.rect[3] + 5, 'h', texto_lado=-7)          # 12.5
    cota(lam, f, (4, 170, -2), (4, 170, -38), f.rect[2] + 8, 'v')                       # 36
    cota(lam, f, (4, 170, -8.5), (4, 170, -35.5), f.rect[2] + 15, 'v')                  # 27
    cota(lam, f, (4, 2, -14), (4, 2, -30), f.rect[0] - 6, 'v')                          # 16
    cota(lam, f, (4, 2, -2), (4, 2, -14), f.rect[0] - 6, 'v', texto_lado=6)             # 12
    cota(lam, f, (4, 2, -32), (4, 29.5, -32), f.rect[1] - 7, 'h')                       # 27.5
    cota(lam, f, (4, 29.5, -32), (4, 35.5, -32), f.rect[1] - 7, 'h', texto_lado=0)      # 6 paso
    cota(lam, f, (4, 29.5, -32), (4, 146.5, -32), f.rect[1] - 14, 'h', texto='117 (20 RANURAS DE 3, PASO 6)')
    for zz in (-30, -14):
        eje_circulo(lam, f, (4, 7, zz), 1.7)
    cota(lam, f, (4, 2, -38), (4, 7, -38), f.rect[1] - 14, 'h')                         # 5, posición de los Ø3.4
    cota_diametro(lam, f, (4, 7, -30), 1.7, -135, texto='2x Ø3.4 PASANTE', largo=12)
    # detalle B de una ranura
    marca_detalle(lam, f, (4, 143.5 + 1.5, -22), 16, 'B', ang=35)
    d = Vista(pz, -X, Z, 3.0, ocultas=False, nombre='detalle').recortar((4, 145, -22), 48)
    d.colocar_centro(330, 215)
    d.dibujar(lam)
    titulo_vista(lam, 330, 150, 'DETALLE B', '3:1')
    cota(lam, d, (4, 143.5, -15), (4, 146.5, -15), d.rect[3] - 6, 'h', texto_lado=8)    # 3 ranura
    cota(lam, d, (4, 140.5, -15), (4, 143.5, -15), d.rect[3] - 6, 'h', texto_lado=-8)   # 3 tabique
    cota(lam, d, (4, 152, -32), (4, 152, -12), d.rect[2] - 10, 'v')                      # 20
    cota_radio(lam, d, (4, 145, -31), 1.0, -60, texto='R1', largo=8)
    # --- planta (canto superior) ---
    cota(lam, p, (-4, 2, -2), (4, 2, -2), p.rect[0] - 6, 'v')                           # 8
    cota(lam, p, (-4, 2, -2), (0, 2, -2), p.rect[0] - 13, 'v', texto_lado=-5)           # 4
    # --- lateral ---
    cota(lam, l, (-4, 170, -38), (4, 170, -38), l.rect[1] - 7, 'h')                     # 8
    notas = NOTAS_FDM + [
        'Lámina válida para las dos rejillas: la izquierda (37.8 g) es simétrica de la derecha respecto al plano YZ.',
        '20 ranuras de 3 x 20 con paso 6 mm y extremos R1; área libre de paso de aire 1 183 mm² por rejilla.',
        'Se atornilla al frente de la bandeja con 2 tornillos M3 sobre insertos (Ø4.2 en MEC-2-05 y 2-06).',
        'Panel realzado hacia el exterior. Impresión plana sobre la cama.',
    ]
    datos = _datos(codigo, titulo, '1:1', nombre)
    lam.estampar(datos, notas)
    return lam
