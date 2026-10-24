# -*- coding: utf-8 -*-
"""Láminas del grupo A: tapa del actuador y módulo de visión e iluminación."""
import numpy as np
from laminas import (lamina, Pieza, Lamina, Vista, cota, cota_alineada, nota, cota_diametro, cota_radio,
                     cota_angulo, eje_circulo, eje_linea, rugosidad, marca_corte, traza, titulo_vista, globo,
                     tabla, primer_diedro, iso, NOTAS_FDM, _datos, X, Y, Z)


def _bajo(v, ref, sep):
    """Coloca la vista v debajo de ref (misma x, separación sep)."""
    v.oy += (ref.rect[1] - sep) - v.rect[3]


def _derecha(v, ref, sep):
    v.ox += (ref.rect[2] + sep) - v.rect[0]


def _cx(v):
    return (v.rect[0] + v.rect[2]) / 2


# -----------------------------------------------------------------------------
@lamina('MEC-2-13', 'Tapa_actuador', 'TAPA DEL SOPORTE DEL ACTUADOR')
def mec_2_13(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 2.0
    lam = Lamina('A3')
    vs = primer_diedro(lam, pz, dir_frente=X, up=Z, escala=E, centro=(120, 200), sep=22, lateral='izq', planta=False)
    f, l = vs['frente'], vs['lateral']
    f.dibujar(lam); l.dibujar(lam)
    x0 = -29.5
    cota(lam, f, (x0, 314, 10), (x0, 274, 10), f.rect[3] + 11, 'h')                 # 40
    cota(lam, f, (x0, 314, 10), (x0, 308, 10), f.rect[3] + 4, 'h', texto_lado=-7)   # 6
    cota(lam, f, (x0, 308, 10), (x0, 280, 10), f.rect[3] + 4, 'h')                  # 28
    cota(lam, f, (x0, 274, 10), (x0, 274, 34), f.rect[2] + 11, 'v')                 # 24
    cota(lam, f, (x0, 274, 10), (x0, 274, 16), f.rect[2] + 4, 'v', texto_lado=-7)   # 6
    cota(lam, f, (x0, 274, 16), (x0, 274, 28), f.rect[2] + 4, 'v')                  # 12
    for yy in (280, 308):
        for zz in (16, 28):
            eje_circulo(lam, f, (x0, yy, zz), 2.25)
    cota_diametro(lam, f, (x0, 308, 16), 2.25, 225, texto='4x Ø4.5 PASANTE', largo=18)
    cota(lam, l, (-29.5, 314, 34), (-24.5, 314, 34), l.rect[3] + 6, 'h')             # 5
    v_iso = iso(lam, pz, 2.0, (320, 205), dir=(1, -1, -0.7), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 320, 145, 'ISOMÉTRICA', '2:1')
    notas = NOTAS_FDM + [
        'Cierra el canal del soporte MEC-2-12 y aprieta el cuerpo del actuador contra el fondo del canal.',
        'Fijación con 4 tornillos ISO 4762 M4 x 12 sobre los insertos roscados del soporte (tapa 5, holgura 0.5 y rosca útil 6.5 en el inserto de 10); par 0.5 N·m.',
        'Bajo la tapa, el tornillo M4 x 55 del soporte MEC-2-12 retiene el actuador por su agujero posterior (MEC-1-05).',
        'Orientación de impresión: cara de 40 x 24 sobre la cama.',
    ]
    lam.estampar(_datos(codigo, titulo, '2:1', nombre), notas)
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-14', 'Soporte_camara', 'SOPORTE DE LA CÁMARA')
def mec_2_14(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 1.0
    lam = Lamina('A3')
    plano = ((0, 0, 0), (0, -1, 0))
    # corte A-A por el plano Y=0 (eje del tubo), tubo horizontal hacia la derecha, placa a la izquierda
    s = Vista(pz, -Y, X, E, ocultas=False, corte=plano, nombre='corte A-A')
    s.colocar_centro(22 + 100, 215)
    # vista desde la izquierda (cara inferior de la placa), a la derecha del corte
    l = Vista(pz, Z, X, E, ocultas=True, nombre='placa')
    l.alinear_y(s, (0, 0, 0)); _derecha(l, s, 44)
    s.dibujar(lam); l.dibujar(lam)
    # --- corte A-A ---
    titulo_vista(lam, _cx(s), s.rect[3] + 22, 'CORTE A-A', '1:1')
    cota(lam, s, (30, 0, 0), (30, 0, 175), s.rect[3] + 12, 'h')                  # 175
    cota(lam, s, (30, 0, 0), (30, 0, 10), s.rect[3] + 5, 'h', texto_lado=-7)     # 10
    cota(lam, s, (-20, 0, 140), (20, 0, 140), s.rect[2] + 8, 'v', prefijo='Ø')   # Ø40
    cota(lam, s, (-17, 0, 140), (17, 0, 140), s.rect[2] + 16, 'v', prefijo='Ø')  # Ø34
    cota(lam, s, (-30, 0, 0), (30, 0, 0), s.rect[0] - 8, 'v')                    # 60
    eje_linea(lam, s, (0, 0, -3), (0, 0, 179))
    nota(lam, s, (21.46, 0, 11.46), 'R5 EN LA RAÍZ DEL TUBO', 30, -14)
    nota(lam, s, (0, 0, 3), ['PASO DE CABLE Ø8', 'comunica el tubo con el interior de la cuna'], 40, -36)
    # --- cara inferior de la placa ---
    titulo_vista(lam, _cx(l), l.rect[1] - 34, 'VISTA INFERIOR DE LA PLACA', '1:1')
    cota(lam, l, (-30, -50, 0), (-30, 50, 0), l.rect[3] + 14, 'h', texto_lado=14)   # 100
    cota(lam, l, (-30, -35, 0), (-30, 35, 0), l.rect[3] + 7, 'h', texto_lado=14)    # 70
    cota(lam, l, (-30, -50, 0), (-30, -35, 0), l.rect[3] + 7, 'h', texto_lado=-7)   # 15
    cota(lam, l, (-30, 50, 0), (30, 50, 0), l.rect[2] + 14, 'v')                 # 60
    cota(lam, l, (-17, 50, 0), (17, 50, 0), l.rect[2] + 7, 'v')                  # 34
    cota(lam, l, (-30, 50, 0), (-17, 50, 0), l.rect[2] + 7, 'v', texto_lado=-7)  # 13
    for xx in (-17, 17):
        for yy in (-35, 35):
            eje_circulo(lam, l, (xx, yy, 0), 1.7)
    eje_circulo(lam, l, (0, 0, 0), 20)
    cota_diametro(lam, l, (-17, -35, 0), 1.7, -140, texto='4x Ø3.4 PASANTE', largo=22)
    traza(lam, l, (0, 0, 0), (0, 1, 0), -Y, 'A', margen=22)
    # --- isométrica ---
    v_iso = iso(lam, pz, 0.5, (100, 108), dir=(-1, 1, -0.6), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 100, 50, 'ISOMÉTRICA', '1:2')
    notas = NOTAS_FDM + [
        'Fijación al techo de la cuna MEC-2-03 con 4 tornillos M3 x 16 sobre insertos roscados de latón M3 x 4.',
        'Los insertos van en pilares de la cuna, bajo los agujeros Ø3.4; la placa apoya sobre el plano de 20°.',
        'El tubo queda perpendicular a la cara inclinada; la horquilla MEC-2-15 se cala en su extremo libre.',
        'Orientación de impresión: placa sobre la cama, tubo vertical (175 mm), sin soportes.',
    ]
    lam.estampar(_datos(codigo, titulo, '1:1', nombre), notas)
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-15', 'Horquilla_camara', 'HORQUILLA DE LA CÁMARA (RÓTULA)')
def mec_2_15(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 2.0
    lam = Lamina('A3')
    plano = ((0, 0, 0), (1, 0, 0))
    # corte A-A por el plano X=0, mirando hacia +X (el prisionero, en -Y, queda a la derecha)
    s = Vista(pz, X, Z, E, ocultas=False, corte=plano, nombre='corte A-A')
    s.colocar_centro(120, 200)
    p = Vista(pz, -Z, X, E, ocultas=False, nombre='planta')
    p.alinear_x(s, (0, 0, 0)); _bajo(p, s, 30)
    s.dibujar(lam); p.dibujar(lam)
    # --- corte ---
    titulo_vista(lam, _cx(s), s.rect[3] + 21, 'CORTE A-A', '2:1')
    cota(lam, s, (0, -24, 0), (0, -24, 44), s.rect[2] + 20, 'v')                       # 44
    cota(lam, s, (0, -24, 0), (0, -24, 25), s.rect[2] + 8, 'v')                        # 25
    cota(lam, s, (0, -24, 25), (0, -24, 28), s.rect[2] + 8, 'v', texto_lado=5)         # 3
    cota(lam, s, (0, -24, 28), (0, -24, 44), s.rect[2] + 8, 'v')                       # 16
    cota(lam, s, (0, 24, 0), (0, 24, 40.6), s.rect[0] - 8, 'v')                        # 40.6
    cota(lam, s, (0, 12, 34), (0, 12, 44), s.rect[0] - 16, 'v')                        # 10 ranura
    cota(lam, s, (0, 24, 0), (0, -24, 0), s.rect[1] - 8, 'h', prefijo='Ø')             # Ø48
    cota(lam, s, (0, 20.2, 0), (0, -20.2, 0), s.rect[1] - 15, 'h', prefijo='Ø', tol=('+0.2', '0'))   # Ø40.4
    cota(lam, s, (0, 7.41, 44), (0, -7.41, 44), s.rect[3] + 4, 'h', texto='Ø14.8 ±0.1')
    cota(lam, s, (0, 12, 44), (0, -12, 44), s.rect[3] + 11, 'h', prefijo='Ø')          # Ø24
    cota_diametro(lam, s, (0, 0, 40.6), 8.15, 160, texto='SØ16.3', tol=('+0.2', '0'), largo=12)
    nota(lam, s, (0, 22.1, 12), ['Ø4.0 x 3.8 PARA INSERTO M3', 'prisionero M3 radial'], -14, -34)
    cota(lam, s, (0, 24, 0), (0, 24, 12), s.rect[0] - 24, 'v')                         # 12 altura del agujero
    eje_linea(lam, s, (0, 0, -3), (0, 0, 47))
    # --- planta ---
    cota_diametro(lam, p, (0, 0, 44), 12, 45, texto='Ø24', largo=28)
    cota_diametro(lam, p, (0, 0, 44), 2.5, -45, texto='Ø5 PASO DE CABLE', largo=36)
    nota(lam, p, (0, 8.4, 44), ['4 RANURAS 1 x 10', 'a 90°'], 52, 22)
    eje_circulo(lam, p, (0, 0, 44), 24)
    traza(lam, p, (0, 0, 0), (1, 0, 0), X, 'A')
    # --- isométrica ---
    v_iso = iso(lam, pz, 1.5, (320, 215), dir=(1, -1, -0.8), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 320, 150, 'ISOMÉTRICA', '1.5:1')
    notas = NOTAS_FDM + [
        'Se cala sobre el tubo Ø40 del soporte MEC-2-14; un prisionero ISO 4029 M3 x 4 sobre inserto M3 x 3 (agujero Ø4.0; la pared mide 3.8) la inmoviliza.',
        'La bola Ø16 de la carcasa MEC-2-16 entra a presión por la boca Ø14.8; las 4 ranuras dan la elasticidad.',
        'Orientación de impresión: base del collarín sobre la cama, copa hacia arriba, sin soportes.',
    ]
    lam.estampar(_datos(codigo, titulo, '2:1', nombre), notas)
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-16', 'Carcasa_ESP32CAM', 'CARCASA DE LA CÁMARA ESP32-CAM')
def mec_2_16(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 2.0
    lam = Lamina('A3')
    plano = ((0, 0, 0), (0, 1, 0))
    f = Vista(pz, -X, Z, E, ocultas=True, nombre='frente').colocar_centro(75, 175)
    s = Vista(pz, Y, Z, E, ocultas=False, corte=plano, nombre='corte B-B')
    s.alinear_y(f, (0, 0, 0)); _derecha(s, f, 34)
    r = Vista(pz, X, Z, E, ocultas=False, nombre='posterior')
    r.alinear_y(f, (0, 0, 0)); _derecha(r, s, 30)
    for v in (f, s, r):
        v.dibujar(lam)
    # --- frente (ventana del objetivo) ---
    cota(lam, f, (14, -16.5, 60.5), (14, 16.5, 60.5), f.rect[3] + 6, 'h', texto_lado=14)   # 33
    cota(lam, f, (14, -16.5, 14), (14, -16.5, 60.5), f.rect[0] - 8, 'v')              # 46.5
    cota(lam, f, (14, -16.5, 0), (14, -16.5, 60.5), f.rect[0] - 16, 'v')              # 60.5
    cota(lam, f, (14, 16.5, 37.25), (14, 16.5, 60.5), f.rect[2] + 34, 'v')            # 23.3
    eje_circulo(lam, f, (14, 0, 37.25), 6)
    cota_diametro(lam, f, (14, 0, 37.25), 6, 25, texto='Ø12 VENTANA', largo=26)
    eje_circulo(lam, f, (14, 0, 0), 8)
    cota_diametro(lam, f, (14, 0, 0), 8, -45, texto='SØ16 ±0.1', largo=8)
    nota(lam, f, (14, -3, 11), 'CUELLO Ø6', -10, -8)
    eje_linea(lam, f, (14, 0, -10), (14, 0, 63))
    traza(lam, f, (0, 0, 0), (0, 1, 0), Y, 'B', margen=14)
    # --- corte B-B ---
    titulo_vista(lam, _cx(s), s.rect[3] + 12, 'CORTE B-B', '2:1')
    cota(lam, s, (0, 0, 60.5), (14, 0, 60.5), s.rect[3] + 4, 'h')                    # 14
    cota(lam, s, (0, 0, 58), (11.5, 0, 58), s.rect[1] - 6, 'h')                      # 11.5
    cota(lam, s, (11.5, 0, 58), (14, 0, 58), s.rect[1] - 6, 'h', texto_lado=6)       # 2.5
    cota(lam, s, (14, 0, 16.5), (14, 0, 58), s.rect[2] + 8, 'v')                     # 41.5
    cota(lam, s, (14, 0, 7.4), (14, 0, 14), s.rect[2] + 8, 'v', texto_lado=6)        # 6.6 cuello
    nota(lam, s, (-2, 0, -3), 'PASO DE CABLE Ø4', -8, -12)
    eje_linea(lam, s, (0, 0, -10), (0, 0, 63))
    # --- vista posterior (alojamiento abierto) ---
    titulo_vista(lam, _cx(r), r.rect[3] + 12, 'VISTA POSTERIOR', '2:1')
    cota(lam, r, (0, -14, 16.5), (0, 14, 16.5), r.rect[1] - 6, 'h')                  # 28
    cota(lam, r, (0, 14, 16.5), (0, 16.5, 16.5), r.rect[1] - 6, 'h', texto_lado=7)   # 2.5
    cota(lam, r, (0, 16.5, 58), (0, 16.5, 60.5), r.rect[2] + 6, 'v', texto_lado=7)   # 2.5
    nota(lam, r, (0, 0, 16.5), ['ALOJAMIENTO 28 x 41.5 x 11.5', 'módulo ESP32-CAM 27 x 40.5'], 26, -24)
    # --- isométrica ---
    v_iso = iso(lam, pz, 1.5, (345, 200), dir=(-1, -1, -0.7), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 345, 128, 'ISOMÉTRICA', '1.5:1')
    notas = NOTAS_FDM + [
        'La bola SØ16 entra a presión en la copa de la horquilla MEC-2-15; el cable de la cámara pasa por el taladro Ø4.',
        'Módulo ESP32-CAM de 27 x 40.5 x 4.5 (hoja de datos) por la cara posterior, sin tiras de pines; cinta de doble cara.',
        'Ventana Ø12 centrada en el alojamiento según la hoja de datos (objetivo a 20 mm del borde); admite ±1 mm de plegado del flex.',
        'Orientación de impresión: cara superior de la caja (opuesta al cuello) sobre la cama, cuello y bola hacia arriba;',
        'soporte en árbol solo bajo la mitad inferior de la bola. La bola sobresale 8 mm tras la cara posterior.',
    ]
    lam.estampar(_datos(codigo, titulo, '2:1', nombre), notas)
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-17', 'Horquilla_lampara', 'HORQUILLA DE LA LÁMPARA (RÓTULA)')
def mec_2_17(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 2.0
    lam = Lamina('A3')
    yc = 70.8                       # el plano pasa junto a las ranuras (ancho 1) para cortar pared
    plano = ((0, yc, 0), (0, 1, 0))
    f = Vista(pz, -X, Z, E, ocultas=True, nombre='frente').colocar_centro(136, 222)
    p = Vista(pz, -Z, -X, E, ocultas=False, nombre='planta')
    p.alinear_x(f, (0, 0, 0)); _bajo(p, f, 26)
    s = Vista(pz, Y, Z, E, ocultas=False, corte=plano, nombre='corte B-B')
    s.alinear_y(f, (0, 0, 0)); _derecha(s, f, 40)
    for v in (f, p, s):
        v.dibujar(lam)
    # --- frente ---
    cota(lam, f, (0, -24, 0), (0, 85, 0), f.rect[3] + 12, 'h')                         # 109
    cota(lam, f, (0, 0, 0), (0, 70, 0), f.rect[3] + 5, 'h')                            # 70
    cota(lam, f, (0, -24, 0), (0, 24, 0), f.rect[1] - 6, 'h', prefijo='Ø')             # Ø48
    cota(lam, f, (0, -20.2, 0), (0, 20.2, 0), f.rect[1] - 13, 'h', prefijo='Ø', tol=('+0.2', '0'))   # Ø40.4
    cota(lam, f, (0, -24, 0), (0, -24, 20), f.rect[0] - 8, 'v')                        # 20
    cota(lam, f, (0, 85, 0), (0, 85, 2), f.rect[2] + 8, 'v', texto_lado=-5)            # 2
    cota(lam, f, (0, 85, 2), (0, 85, 19), f.rect[2] + 8, 'v')                          # 17
    cota(lam, f, (0, 85, 0), (0, 85, 35), f.rect[2] + 16, 'v')                         # 35
    nota(lam, f, (0, -22, 10), ['Ø4.0 PARA INSERTO M3', 'prisionero de la abrazadera'], 10, 24)
    eje_linea(lam, f, (0, 0, -3), (0, 0, 23))
    eje_linea(lam, f, (0, 70, 16), (0, 70, 38))
    traza(lam, f, (0, 70, 0), (0, 1, 0), Y, 'B', margen=(16, 10))
    # --- planta ---
    cota(lam, p, (-12, 85, 19), (12, 85, 19), p.rect[2] + 8, 'v')                      # 24
    cota_diametro(lam, p, (0, 70, 35), 15, -35, texto='Ø30', largo=14)
    cota_diametro(lam, p, (0, 70, 35), 9.33, -65, texto='Ø18.7 ±0.1', largo=24)
    nota(lam, p, (0, 70 + 10.5, 35), ['4 RANURAS 1 x 10', 'a 90°'], 16, 12)
    eje_circulo(lam, p, (0, 0, 20), 24)
    eje_circulo(lam, p, (0, 70, 35), 15)
    eje_linea(lam, p, (0, -27, 20), (0, 88, 20))
    # --- corte B-B ---
    titulo_vista(lam, _cx(s), s.rect[1] - 18, 'CORTE B-B', '2:1')
    cota(lam, s, (-12, yc, 0), (-15, yc, 31), s.rect[0] - 8, 'v')                      # 31 (base del brazo)
    cota(lam, s, (-15, yc, 35), (15, yc, 35), s.rect[3] + 4, 'h', prefijo='Ø')         # Ø30
    cota(lam, s, (-12, yc, 2), (12, yc, 2), s.rect[1] - 6, 'h')                        # 24
    cota_diametro(lam, s, (0, yc, 31), 10.15, -40, texto='SØ20.3', tol=('+0.2', '0'), largo=14)
    # agujero del prisionero de la copa: radial a 135° (entre dos ranuras); en el corte se ve su boca
    # sobre la esfera, detrás del plano B-B
    _hy = s.m((-7.18, 77.18, 31))[1]
    nota(lam, s, (-7.18, 77.18, 31), ['Ø4.0 PARA INSERTO M3', 'radial a 45° de las ranuras (planta)'], -8, s.rect[3] + 13 - _hy)
    # planta: eje del agujero, contorno oculto y ángulo respecto de la ranura de +Y
    import math as _m
    u = np.array([_m.cos(_m.radians(135)), _m.sin(_m.radians(135)), 0.0])
    n_ = np.array([-u[1], u[0], 0.0])
    c0 = np.array([0.0, 70.0, 31.0])
    eje_linea(lam, p, tuple(c0), tuple(c0 + u * 17.0), ext=2)
    for sgn in (-1, 1):
        a3 = c0 + u * 10.15 + n_ * 2.0 * sgn
        b3 = c0 + u * 15.0 + n_ * 2.0 * sgn
        lam.linea(p.m(tuple(a3)), p.m(tuple(b3)), 'oculta')
    cota_angulo(lam, p, (0, 70, 35), (0, 86, 35), tuple(c0 + u * 16.0), 26, texto='45°')
    # --- isométrica ---
    v_iso = iso(lam, pz, 1.0, (335, 120), dir=(-1, -1, -0.8), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 335, 72, 'ISOMÉTRICA', '1:1')
    notas = NOTAS_FDM + [
        'Abrazadera sobre el tubo Ø40 de MEC-2-14, bajo la horquilla de la cámara; la inmoviliza un prisionero ISO 4029 M3 x 4 en inserto M3 x 3 (Ø4.0; pared de 3.8).',
        'El agujero de la copa va a 45° de las ranuras (no sobre una ranura), a la altura del centro de la esfera (z 31).',
        'La bola SØ20 del aro MEC-2-18 entra a presión por la boca Ø18.7; la inmoviliza un segundo prisionero, ISO 4029 M3 x 5 en inserto M3 x 3 (Ø4.0; pared de 4.85).',
        'Orientación de impresión: base de la abrazadera sobre la cama, copa hacia arriba; el brazo queda 2 mm sobre la cama y lleva soporte debajo.',
    ]
    lam.estampar(_datos(codigo, titulo, '2:1', nombre), notas, notas_pos=(14, 60))
    return lam


# -----------------------------------------------------------------------------
@lamina('MEC-2-18', 'Aro_lampara', 'ARO PORTALÁMPARA MR16 (RÓTULA)')
def mec_2_18(codigo, nombre, titulo):
    pz = Pieza(nombre)
    E = 2.0
    lam = Lamina('A3')
    plano = ((0, 0, 0), (0, 1, 0))
    f = Vista(pz, -X, Z, E, ocultas=True, nombre='frente').colocar_centro(95, 172)
    s = Vista(pz, Y, Z, E, ocultas=False, corte=plano, nombre='corte A-A')
    s.alinear_y(f, (0, 0, 0)); _derecha(s, f, 36)
    f.dibujar(lam); s.dibujar(lam)
    # --- frente ---
    cota(lam, f, (0, -28, 44), (0, 28, 44), f.rect[3] + 6, 'h', prefijo='Ø', texto_lado=16)                  # Ø56
    cota(lam, f, (0, -25.3, 44), (0, 25.3, 44), f.rect[3] + 13, 'h', prefijo='Ø', tol=('+0.3', '0'), texto_lado=16)   # Ø50.6
    cota(lam, f, (0, 28, 0), (0, 28, 44), f.rect[2] + 8, 'v')                                 # 44
    cota(lam, f, (0, 28, 0), (0, 28, 72), f.rect[2] + 16, 'v')                                # 72
    cota(lam, f, (0, -28, -10), (0, -28, 0), f.rect[0] - 8, 'v', texto_lado=-7)              # 10
    eje_circulo(lam, f, (0, 0, 44), 28)
    eje_circulo(lam, f, (0, 0, 0), 10)
    cota_diametro(lam, f, (0, 0, 0), 10, -135, texto='SØ20 ±0.1', largo=9)
    eje_linea(lam, f, (0, 0, -13), (0, 0, 75))
    traza(lam, f, (0, 0, 0), (0, 1, 0), Y, 'A', margen=(16, 8))
    lam.circulo(f.m((0, 0, 0)), 10 * E, 'visible')                                      # contorno de la bola
    # --- corte A-A ---
    titulo_vista(lam, _cx(s), s.rect[3] + 12, 'CORTE A-A', '2:1')
    cota(lam, s, (-3.75, 0, 72), (3.75, 0, 72), s.rect[3] + 4, 'h')                          # 7.5
    cota(lam, s, (-3.8, 0, 16), (-3.8, 0, 18.7), s.rect[0] - 6, 'v', texto_lado=-6)          # 2.7
    cota(lam, s, (-3.8, 0, 9.2), (-3.8, 0, 17.5), s.rect[0] - 13, 'v')                       # 8.3 cuello
    nota(lam, s, (3.6, 0, 13), 'CUELLO Ø7.2', 10, -10)
    nota(lam, s, (0, 26.6, 44), ['Ø2.5 PILOTO', 'prisionero M3'], 22, 18)
    eje_linea(lam, s, (0, 0, -13), (0, 0, 75))
    # --- isométrica ---
    v_iso = iso(lam, pz, 1.5, (330, 205), dir=(-1, -1, -0.7), up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, 330, 125, 'ISOMÉTRICA', '1.5:1')
    notas = NOTAS_FDM + [
        'Aloja un dicroico LED MR16 (Ø50, GU5.3, 12 V, 6 W); un prisionero ISO 4029 M3 x 3 autorroscante en el piloto Ø2.5 lo retiene.',
        'La bola SØ20 entra a presión en la copa de la horquilla MEC-2-17 y permite orientar el haz.',
        'Orientación de impresión: aro apoyado de canto con la bola hacia abajo, con soportes bajo la bola.',
    ]
    lam.estampar(_datos(codigo, titulo, '2:1', nombre), notas)
    return lam
