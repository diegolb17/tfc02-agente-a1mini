# -*- coding: utf-8 -*-
"""Láminas de ensamble (MEC-0-xx) y de subconjuntos (MEC-1-xx): vistas del conjunto en
coordenadas del ensamble, globos de posición y lista de piezas."""
import math
import numpy as np
from laminas import (lamina, Pieza, Lamina, Vista, cota, nota, titulo_vista, globo, tabla, iso,
                     primer_diedro, _datos, X, Y, Z, FECHA, REVISION, revision_de)
from motor.malla import rasgos, transform_ensamble

# posición, componente, denominación, plano
PIEZAS = [
    (1, 'Cuna_frontal_derecha', 'Estructura, cuarto frontal derecho', 'MEC-2-01'),
    (2, 'Cuna_frontal_izquierda', 'Estructura, cuarto frontal izquierdo', 'MEC-2-02'),
    (3, 'Cuna_posterior_derecha', 'Estructura, cuarto posterior derecho', 'MEC-2-03'),
    (4, 'Cuna_posterior_izquierda', 'Estructura, cuarto posterior izquierdo', 'MEC-2-04'),
    (5, 'Bandeja_frontal_derecha', 'Bandeja, cuarto frontal derecho', 'MEC-2-05'),
    (6, 'Bandeja_frontal_izquierda', 'Bandeja, cuarto frontal izquierdo', 'MEC-2-06'),
    (7, 'Bandeja_posterior_derecha', 'Bandeja, cuarto posterior derecho', 'MEC-2-07'),
    (8, 'Bandeja_posterior_izquierda', 'Bandeja, cuarto posterior izquierdo', 'MEC-2-08'),
    (9, 'Soporte_ventilador', 'Soporte del ventilador', 'MEC-2-09'),
    (10, 'Ducto_cuchilla', 'Ducto de enfriamiento', 'MEC-2-10'),
    (11, 'Rejilla_frontal_derecha', 'Rejilla de admisión derecha', 'MEC-2-11'),
    (12, 'Rejilla_frontal_izquierda', 'Rejilla de admisión izquierda (simétrica)', 'MEC-2-11'),
    (13, 'Soporte_actuador', 'Soporte del actuador lineal', 'MEC-2-12'),
    (14, 'Tapa_actuador', 'Tapa del soporte del actuador', 'MEC-2-13'),
    (15, 'Soporte_camara', 'Soporte de la cámara', 'MEC-2-14'),
    (16, 'Horquilla_camara', 'Horquilla de la cámara (rótula)', 'MEC-2-15'),
    (17, 'Carcasa_ESP32CAM', 'Carcasa de la cámara ESP32-CAM', 'MEC-2-16'),
    (18, 'Horquilla_lampara', 'Horquilla de la lámpara (rótula)', 'MEC-2-17'),
    (19, 'Aro_lampara', 'Aro portalámpara MR16 (rótula)', 'MEC-2-18'),
]
COMERCIALES = [(20, 'Equipo_A1mini', 'Impresora Bambu Lab A1 mini (envolvente)', 'comercial')]

_cache = {}


def pieza_ens(nombre):
    if nombre not in _cache:
        _cache[nombre] = Pieza(nombre).en_ensamble(nombre)
    return _cache[nombre]


def conjunto(nombres, desplazar=None):
    """Une las piezas en coordenadas del ensamble. desplazar: dict nombre -> vector (vista explosionada).
    Guarda en el resultado el número de triángulos de cada pieza para ubicar después sus píxeles visibles."""
    piezas = []
    for n in nombres:
        pe = pieza_ens(n)
        if desplazar and n in desplazar:
            pe = pe.transformada(np.eye(3), np.asarray(desplazar[n], float))
        piezas.append(pe)
    pz = Pieza.unir(piezas)
    pz.n_tri = [len(q.malla.F) for q in piezas]
    pz.desplazar = desplazar or {}
    return pz


def centroide(nombre):
    return pieza_ens(nombre).malla.V.mean(axis=0)


def lista_piezas(lam, x, y, filas, alto=5.5):
    """Devuelve la y del borde superior de la tabla."""
    cols = [('POS', 10, 'c'), ('DENOMINACIÓN', 78, 'l'), ('CANT', 11, 'c'), ('MATERIAL', 20, 'c'),
            ('MASA (g)', 18, 'r'), ('PLANO', 23, 'c')]
    return tabla(lam, x, y, cols, filas, alto=alto, tam=2.8)


def filas_bom(items):
    filas = []
    total = 0.0
    for pos, comp, den, plano in items:
        r = rasgos(comp)
        total += r['masa_g']
        filas.append((pos, den, 1, r['material'], '%.1f' % r['masa_g'], plano))
    return filas, total


def anclas_visibles(v, pz):
    """Para cada pieza del conjunto, el punto de hoja de su zona visible más alejado del borde de esa
    zona (así el globo apunta sin duda a la pieza y no a una vecina o al aire). None si no se ve."""
    from scipy.ndimage import distance_transform_edt
    pr = v.pr
    if not hasattr(pr, 'ib') or not hasattr(pz, 'n_tri'):
        return None
    lim = np.cumsum([0] + list(pz.n_tri))
    ib = pr.ib
    dists = []
    for k in range(len(pz.n_tri)):
        mask = (ib >= lim[k]) & (ib < lim[k + 1])
        dists.append(distance_transform_edt(mask) if mask.sum() >= 4 else None)
    # las piezas finas eligen primero; cada ancla se separa al menos 10 mm de hoja de las anteriores
    sep_px = 10.0 / (pr.res * v.escala)
    orden = sorted(range(len(dists)), key=lambda k: -1 if dists[k] is None else float(dists[k].max()))
    out = [None] * len(dists)
    elegidos = []
    jj, ii = np.indices(ib.shape)
    for k in orden:
        d = dists[k]
        if d is None:
            continue
        cand = d.copy()
        for (j0, i0) in elegidos:
            cand[(jj - j0) ** 2 + (ii - i0) ** 2 < sep_px ** 2] = 0
        if cand.max() <= 0:
            cand = d
        j, i = np.unravel_index(int(np.argmax(cand)), cand.shape)
        elegidos.append((j, i))
        q = (pr.x0 + (i + 0.5) * pr.res, pr.y0 + (j + 0.5) * pr.res)
        out[k] = np.array(v.m2(q))
    return out


def globos_auto(lam, v, items, radio_mm=None, margen=14, pz=None):
    """Globos repartidos en el contorno de la vista, enlazados a un punto visible de cada pieza
    (o a su centroide si no se dispone del z-buffer)."""
    x0, y0, x1, y1 = v.rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b = (x1 - x0) / 2 + margen, (y1 - y0) / 2 + margen
    anclas = anclas_visibles(v, pz) if pz is not None else None
    puntos = []
    for k, (pos, comp, _, _) in enumerate(items):
        if anclas is not None and anclas[k] is not None:
            p = anclas[k]
        else:
            c = centroide(comp) + (np.asarray(pz.desplazar.get(comp, (0, 0, 0)), float) if pz is not None else 0)
            p = np.array(v.m(tuple(c)))
        ang = math.atan2((p[1] - cy) / b, (p[0] - cx) / a)
        puntos.append((ang, pos, p))
    puntos.sort()
    n = len(puntos)
    # respeta el ángulo real de cada centroide y separa los que colisionan
    angs = [ang for ang, _, _ in puntos]
    dmin = 2 * math.pi / max(n, 9)
    for i in range(1, n):
        if angs[i] - angs[i - 1] < dmin:
            angs[i] = angs[i - 1] + dmin
    if n > 1 and angs[-1] - angs[0] > 2 * math.pi - dmin:
        angs = [-math.pi + (i + 0.5) * 2 * math.pi / n for i in range(n)]
    for i, (ang, pos, p) in enumerate(puntos):
        t = angs[i]
        q = np.array([cx + a * math.cos(t), cy + b * math.sin(t)])
        globo(lam, v, tuple(p), pos, q[0] - p[0], q[1] - p[1], hoja=True, r=3.6, tam=3.0)


ESCALAS = [(0.5, '1:2'), (0.4, '1:2.5'), (1 / 3, '1:3'), (0.25, '1:4'), (0.2, '1:5')]


def escala_que_cabe(pz, dir_iso, zona, margen):
    """Mayor escala de la escalera estándar cuya isométrica (más el anillo de globos) cabe en zona."""
    from motor.hlr import base_vista
    R = base_vista(dir_iso, Z)
    P = pz.malla.V @ R.T
    ext = P[:, :2].max(0) - P[:, :2].min(0)
    ancho, alto = zona[2] - zona[0] - 2 * margen, zona[3] - zona[1] - 2 * margen
    for e, txt in ESCALAS:
        if ext[0] * e <= ancho and ext[1] * e <= alto:
            return e, txt
    return ESCALAS[-1]


def _ensamble_datos(codigo, titulo, escala):
    rev, fecha, nota_rev = revision_de(codigo)
    return {'titulo': titulo, 'codigo': codigo, 'escala': escala, 'formato': 'A3', 'fecha': fecha,
            'material': 'VARIOS', 'tolerancia': 'ISO 2768-m', 'rugosidad': 'Ra 12.5', 'revision': rev,
            'nota_revision': nota_rev}


# -----------------------------------------------------------------------------
@lamina('MEC-0-01', 'Ensamble', 'ENSAMBLE GENERAL DEL SISTEMA')
def mec_0_01(codigo, nombre, titulo):
    # la impresora no forma parte del sistema y no se dibuja (observación de Diego del 20 oct 2026)
    todos = [p[1] for p in PIEZAS]
    pz = conjunto(todos)
    E = 0.2
    lam = Lamina('A3')
    vs = primer_diedro(lam, pz, dir_frente=X, up=Z, escala=E, centro=(95, 190), sep=18, lateral='izq',
                       ocultas=False, res=0.2)
    f, p, l = vs['frente'], vs['planta'], vs['lateral']
    for v in (f, p, l):
        v.dibujar(lam)
    mn, mx = pz.malla.bbox
    # envolventes del sistema
    cota(lam, f, (mn[0], mx[1], mn[2]), (mn[0], mn[1], mn[2]), f.rect[3] + 8, 'h', texto='%.0f' % (mx[1] - mn[1]))
    cota(lam, f, (mn[0], mn[1], mn[2]), (mn[0], mn[1], mx[2]), f.rect[2] + 8, 'v', texto='%.0f' % (mx[2] - mn[2]))
    cota(lam, p, (mn[0], mx[1], mn[2]), (mx[0], mx[1], mn[2]), p.rect[0] - 8, 'v', texto='%.0f' % (mx[0] - mn[0]))
    # altura de la estructura y su fondo
    cota(lam, f, (0, 340, 0), (324, 340, 158), f.rect[0] - 8, 'v', texto='158 (estructura)')   # borde izquierdo: la referencia no cruza el alzado
    cota(lam, l, (0, 0, 0), (324.2, 0, 0), l.rect[1] - 8, 'h', texto='324.2 (estructura)')
    # 21 oct: la referencia sale de la vista lateral hacia arriba, donde no cruza ninguna cota
    _a = l.m((150, 60, 290))
    nota(lam, l, (150, 60, 290), ['MÓDULO DE VISIÓN E ILUMINACIÓN', 'objetivo a 123 sobre la placa de impresión'], 14, 262 - _a[1],
         flecha=False, punto=True)
    _b = l.m((100, 60, 120))
    nota(lam, l, (100, 60, 120), 'MÓDULO DE ENFRIAMIENTO (bahía lateral)', 26, (l.rect[1] - 30) - _b[1],
         flecha=False, punto=True)
    v_iso = Vista(pz, (1, -1, -0.7), Z, 0.2, ocultas=False, nombre='iso', res=0.25).colocar_centro(330, 190)
    v_iso.dibujar(lam)
    titulo_vista(lam, 330, 115, 'ISOMÉTRICA', '1:5')
    _m = sum(rasgos(c)['masa_g'] for _, c, _, _ in PIEZAS)
    notas = ['Cotas en milímetros.',
             'La impresora Bambu Lab A1 mini no forma parte del sistema y no se representa; se aloja en la cavidad de la estructura.',
             'Masa de las 19 piezas propias: %s g, sin electrónica ni cableado.' % ('{:,.0f}'.format(_m).replace(',', ' ')),
             'Los subconjuntos se detallan en MEC-1-01 a MEC-1-04 y el ensamble explosionado con la lista de piezas en MEC-0-02.']
    lam.estampar(_ensamble_datos(codigo, titulo, '1:5'), notas)
    return lam


N20 = np.array([-0.342, 0.0, 0.940])          # normal de la cara inclinada (eje del tubo de la cámara)
DESPIECE = {
    'Bandeja_frontal_derecha': (0, 0, -75), 'Bandeja_frontal_izquierda': (0, 0, -75),
    'Bandeja_posterior_derecha': (0, 0, -75), 'Bandeja_posterior_izquierda': (0, 0, -75),
    'Rejilla_frontal_derecha': (-40, 0, -75), 'Rejilla_frontal_izquierda': (-40, 0, -75),
    'Soporte_actuador': (-55, 0, 0), 'Tapa_actuador': (-90, 0, 0),
    'Soporte_ventilador': (-60, -110, 40), 'Ducto_cuchilla': (-30, -55, 20),
    'Soporte_camara': tuple(70 * N20), 'Horquilla_camara': tuple(115 * N20), 'Carcasa_ESP32CAM': tuple(160 * N20),
    'Horquilla_lampara': tuple(95 * N20 + np.array([0, -25, 0])), 'Aro_lampara': tuple(130 * N20 + np.array([0, -45, 0])),
}

COMPONENTES_COMERCIALES = [
    (20, 'Impresora Bambu Lab A1 mini (equipo alojado, no se dibuja)', 1, 'no es del sistema'),
    (21, 'Ventilador Delta PFB0924GHEP6, 92 x 92 x 38, 24 V', 1, 'comercial'),
    (22, 'Ventilador de extracción 30 x 30 x 10 mm, 24 V', 1, 'comercial'),
    (23, 'Actuador lineal Actuonix L12-50-210-12-P', 1, 'comercial'),
    (24, 'Módulo ESP32-CAM con sensor OV2640', 1, 'comercial'),
    (25, 'Dicroico LED MR16 GU5.3, 12 V, 6 W', 1, 'comercial'),
    (26, 'Entrada IEC 60320 C14 con interruptor y fusible', 1, 'comercial'),
    (27, 'Botón de emergencia Ø22, contacto NC', 1, 'comercial'),
    # 22 oct 2026 (P12): longitudes calculadas con el espesor apretado de cada unión y el inserto de 10 mm
    # (enganche de 6 a 10 mm, punta dentro del alojamiento); el detalle está en el Anexo G.
    (28, 'Inserto roscado de latón M4 x 10 (agujeros Ø5.6)', 35, 'comercial'),
    (29, 'Inserto de latón M3: 8 de 4 mm y 3 de 3 mm', 11, 'comercial'),
    (30, 'ISO 4762 M4 x 60, tuerca ISO 4032 y arandela ISO 7089 (ventilador)', 4, 'apriete 50'),
    (31, 'ISO 4762 M4 x 25: uniones entre cuartos y soporte del ventilador', 18, 'apriete 15 a 18'),
    (32, 'ISO 4762 M4 x 12: estructura a bandeja y tapa del actuador', 12, 'apriete 4.3 a 5.5'),
    (33, 'ISO 4762 M4 x 30: soporte del actuador al cuarto MEC-2-02', 4, 'apriete 24'),
    (34, 'ISO 4762 M4 x 55: eje del agujero posterior del actuador', 1, 'MEC-1-05'),
    (35, 'ISO 4762 M3 x 16: soporte de la cámara, a insertos M3 x 4', 4, 'apriete 10'),
    (36, 'ISO 7380-1 M3 x 8: rejillas de admisión, a insertos M3 x 4', 4, 'apriete 4'),
    (37, 'ISO 7045 M3 x 20 con tuerca ISO 4032: extractor', 4, 'pared 4 + 10'),
    # prisioneros: 4 en total, uno por horquilla sobre el tubo, uno en la copa de la lámpara y uno en el aro
    (38, 'Prisionero ISO 4029 M3 x 4: horquillas al tubo (uno cada una)', 2, 'pared 3.8'),
    (39, 'Prisionero ISO 4029 M3 x 5: copa de la rótula de la lámpara', 1, 'pared 4.85'),
    (40, 'Prisionero ISO 4029 M3 x 3 autorroscante (aro, piloto Ø2.5)', 1, 'pared 2.7'),
    (41, 'Pasador ISO 2338 Ø5 m6 x 28 (alineación entre cuartos)', 16, 'agujeros 30'),
    (42, 'Almohadilla de neopreno 60 Shore A, Ø25 x 5, adhesiva', 8, 'bajo la bandeja'),
    (43, 'Lámina de neopreno 60 Shore A de 5 mm: tiras 195 x 5 y 315 x 5', 1, 'cavidad'),
]


@lamina('MEC-0-02', 'Despiece', 'ENSAMBLE EXPLOSIONADO Y LISTA DE PIEZAS')
def mec_0_02(codigo, nombre, titulo):
    items = PIEZAS
    pz = conjunto([p[1] for p in items], desplazar=DESPIECE)
    lam = Lamina('A3')
    zona = (18, 52, 236, 284)
    dir_iso = (1, -1, -0.62)
    e, esc = escala_que_cabe(pz, dir_iso, zona, 18)
    v = Vista(pz, dir_iso, Z, e, ocultas=False, nombre='iso', res=0.15)
    v.colocar_centro((zona[0] + zona[2]) / 2, (zona[1] + zona[3]) / 2)
    v.dibujar(lam)
    globos_auto(lam, v, items, margen=16, pz=pz)
    titulo_vista(lam, (zona[0] + zona[2]) / 2, 34, 'ISOMÉTRICA EXPLOSIONADA DEL CONJUNTO (sin el equipo)', esc)
    filas, total = filas_bom(items)
    filas.append(('', 'MASA TOTAL DE FABRICACIÓN PROPIA', '', '', '%.0f' % total, ''))
    y_top = lista_piezas(lam, 248, 78, filas, alto=4.45)   # 24 oct: sobre el recuadro de la revisión E
    # componentes comerciales, sobre la lista de piezas
    col = [('POS', 10, 'c'), ('COMPONENTE COMERCIAL', 108, 'l'), ('CANT', 12, 'c'), ('OBSERVACIÓN', 30, 'c')]
    alto_c = 3.7      # 24 oct: 24 filas y la lista sube sobre el recuadro de revisión; con 3.85 tocaba el marco superior
    base_c = y_top + 9
    lam.texto(248, base_c + alto_c * (len(COMPONENTES_COMERCIALES) + 1) + 2, 'COMPONENTES COMERCIALES (no se fabrican)', 2.6, 0, 'l', negrita=True)
    tabla(lam, 248, base_c, col, COMPONENTES_COMERCIALES, alto=alto_c, tam=2.8)
    lam.estampar(_ensamble_datos(codigo, titulo, esc), None)
    return lam


def _subconjunto(codigo, titulo, posiciones, dir_iso, escala, notas, iso_centro=(125, 175), tabla_pos=(248, 118), notas_pos=None):
    @lamina(codigo, 'Sub', titulo)
    def _fn(codigo, nombre, titulo):
        items = [p for p in PIEZAS if p[0] in posiciones]
        pz = conjunto([p[1] for p in items])
        lam = Lamina('A3')
        zona = (18, 60, 236, 282)
        e, esc = escala_que_cabe(pz, dir_iso, zona, 18)
        v = Vista(pz, dir_iso, Z, e, ocultas=False, nombre='iso', res=0.12)
        v.colocar_centro((zona[0] + zona[2]) / 2, (zona[1] + zona[3]) / 2)
        v.dibujar(lam)
        globos_auto(lam, v, items, margen=16, pz=pz)
        titulo_vista(lam, (zona[0] + zona[2]) / 2, 42, 'ISOMÉTRICA DEL SUBCONJUNTO', esc)
        filas, total = filas_bom(items)
        filas.append(('', 'MASA DEL SUBCONJUNTO', '', '', '%.0f' % total, ''))
        lista_piezas(lam, tabla_pos[0], tabla_pos[1], filas)
        lam.estampar(_ensamble_datos(codigo, titulo, esc), notas, notas_pos=notas_pos)
        return lam
    return _fn


# -----------------------------------------------------------------------------
# 22 oct 2026 (P12): interfaz con la impresora. La cavidad se mide en el marco de la impresora, el del modelo
# Equipo_A1mini: x a lo largo de la pendiente, y transversal, z normal a la cara inclinada.
R20, T20 = transform_ensamble('Equipo_A1mini')


def s20(xl, yl, zl):
    """Punto del marco de la impresora llevado a coordenadas del ensamble (mm)."""
    return tuple(R20 @ np.array([xl, yl, zl], float) + T20)


# caras interiores de la pared de retención (x 12), del nervio posterior (x 333) y de las paredes laterales
# (y 127 y 328); suelo a z -5, borde superior a z 0, suelo de 4 mm (z -9 a -5)
CAV = (12.0, 333.0, 127.0, 328.0)
BASE_A1 = (17.0, 332.0, 128.0, 323.0)              # base de la A1 mini en el modelo, apoyada en z -5
TABIQUES = (0.0, 81.05, 162.1, 243.14, 320.19, 324.19)   # caras de los tabiques verticales que apoyan el suelo (X)


def _fantasma(lam, v, pts):
    for a, b in zip(pts[:-1], pts[1:]):
        lam.linea(v.m(a), v.m(b), 'fantasma')


@lamina('MEC-1-01', 'Sub', 'SUBCONJUNTO DE LA ESTRUCTURA INCLINADA')
def mec_1_01(codigo, nombre, titulo):
    from motor.hoja import cota_alineada, traza, marca_detalle
    items = [p for p in PIEZAS if p[0] in (1, 2, 3, 4)]
    pz = conjunto([p[1] for p in items])
    lam = Lamina('A3')
    # --- isométrica con globos, arriba a la izquierda
    zona = (18, 182, 212, 286)
    e, esc = escala_que_cabe(pz, (1, -1, -0.7), zona, 12)
    v = Vista(pz, (1, -1, -0.7), Z, e, ocultas=False, nombre='iso', res=0.15)
    v.colocar_centro((zona[0] + zona[2]) / 2, (zona[1] + zona[3]) / 2 + 3)
    v.dibujar(lam)
    globos_auto(lam, v, items, margen=9, pz=pz)
    titulo_vista(lam, (zona[0] + zona[2]) / 2, zona[1] - 3, 'ISOMÉTRICA DEL SUBCONJUNTO', esc)

    # --- corte A-A por la cavidad (Y 290), mirando hacia +Y
    yA = 290.0
    va = Vista(pz, Y, Z, 1 / 3.0, ocultas=False, corte=((0, yA, 0), (0, 1, 0)), nombre='corteA', res=0.12)
    va.colocar_punto((0, yA, 0), x=44, y=95)
    va.dibujar(lam)
    xa, xb = BASE_A1[0], BASE_A1[1]
    _fantasma(lam, va, [s20(xa, yA, 40), s20(xa, yA, -5), s20(xb, yA, -5), s20(xb, yA, 40)])
    textos = ('81.05', '81.05', '81.04', '77.05', '4')
    for (a_, b_), t_ in zip(zip(TABIQUES[:-1], TABIQUES[1:]), textos):
        cota(lam, va, (a_, yA, 0), (b_, yA, 0), va.rect[1] - 7, 'h', texto=t_)
    cota(lam, va, (0, yA, 0), (4, yA, 0), va.rect[1] - 14, 'h', texto='4')
    nota(lam, va, s20(170, yA, -5), ['BASE DE LA A1 MINI', '(línea de trazo y dos puntos)'], 22, 30, tam=2.8)
    # sentido de la vista B, normal a la cara inclinada
    p1, p2 = np.array(va.m(s20(255, yA, 34))), np.array(va.m(s20(255, yA, 6)))
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    lam.linea(tuple(p1), tuple(p2 - u * 1.0), 'cota')
    lam.flecha(tuple(p2), tuple(u), largo=3.0, ancho=1.1)
    lam.texto(p1[0] - 2.5, p1[1] + 1.0, 'B', 4.0, 0, 'c', negrita=True)
    marca_detalle(lam, va, s20(10, yA, -3), 5.5, 'C', ang=200)
    marca_detalle(lam, va, s20(334, yA, -3), 5.5, 'D', ang=20)
    titulo_vista(lam, (va.rect[0] + va.rect[2]) / 2, va.rect[1] - 24, 'CORTE A-A', '1:3')

    # --- detalles C y D a 1:1 (pared de retención y nervio posterior)
    def detalle(pieza, c3, letra, cx, cy, r=18):
        d = Vista(Pieza(pieza), Y, Z, 1.0, ocultas=False, corte=((0, yA, 0), (0, 1, 0)), nombre='det', res=0.06)
        d.recortar(c3, r)
        d.colocar_punto(c3, x=cx, y=cy)
        d.dibujar(lam)
        titulo_vista(lam, cx, cy - r - 7, 'DETALLE %s' % letra, '1:1')
        return d
    dc = detalle('Cuna_frontal_izquierda', s20(16, yA, -4), 'C', 205, 147)
    _fantasma(lam, dc, [s20(xa, yA, 9), s20(xa, yA, -5), s20(xa + 14, yA, -5)])
    cota_alineada(lam, dc, s20(14.5, yA, -5), s20(14.5, yA, 0), -9, texto='5')
    cota_alineada(lam, dc, s20(21, yA, -9), s20(21, yA, -5), -4, texto='4')
    cota_alineada(lam, dc, s20(CAV[0], yA, 0), s20(xa, yA, 0), 7, texto='5')
    nota(lam, dc, s20(6, yA, -1), 'PARED DE RETENCIÓN', -10, 15, tam=2.8)
    dd = detalle('Cuna_posterior_izquierda', s20(332, yA, -4), 'D', 205, 98)
    _fantasma(lam, dd, [s20(xb - 14, yA, -5), s20(xb, yA, -5), s20(xb, yA, 9)])
    cota_alineada(lam, dd, s20(330.5, yA, -5), s20(330.5, yA, 0), 9, texto='5')
    cota_alineada(lam, dd, s20(CAV[1], yA, 0), s20(337, yA, 0), 7, texto='4')
    nota(lam, dd, s20(335, yA, -1), 'NERVIO POSTERIOR', 8, 14, tam=2.8)

    # --- vista B, normal a la cara inclinada: la cavidad en verdadera magnitud
    dB = R20 @ np.array([0, 0, -1.0])
    uB = R20 @ np.array([1.0, 0, 0])
    vb = Vista(pz, dB, uB, 0.25, ocultas=False, nombre='vistaB', res=0.2)
    vb.colocar_centro(332, 146)
    vb.dibujar(lam)
    x0c, x1c, y0c, y1c = CAV
    cota(lam, vb, s20(x0c, y1c, 0), s20(x1c, y1c, 0), vb.rect[0] - 8, 'v', texto='321')
    cota(lam, vb, s20(x0c, y0c, 0), s20(x0c, y1c, 0), vb.rect[1] - 15, 'h', texto='201')
    bx0, bx1, by0, by1 = BASE_A1
    _fantasma(lam, vb, [s20(bx0, by0, -5), s20(bx1, by0, -5), s20(bx1, by1, -5), s20(bx0, by1, -5), s20(bx0, by0, -5)])
    cota(lam, vb, s20(bx0, by0, -5), s20(bx1, by0, -5), vb.rect[2] + 8, 'v', texto='315')
    cota(lam, vb, s20(bx1, by0, -5), s20(bx1, by1, -5), vb.rect[3] + 15, 'h', texto='195')
    traza(lam, vb, (150, yA, 100), (0, 1, 0), (0, 1, 0), 'A')
    titulo_vista(lam, 332, vb.rect[1] - 25, 'VISTA B', '1:4')

    filas, total = filas_bom(items)
    filas.append(('', 'MASA DEL SUBCONJUNTO', '', '', '%.0f' % total, ''))
    lista_piezas(lam, 248, 252, filas, alto=5.2)
    notas = ['Cuartos unidos con tornillos ISO 4762 M4 x 25 sobre insertos de latón M4 x 10 y alineados con '
             'pasadores ISO 2338 Ø5 x 28; plano superior inclinado 20°.',
             'Cavidad de la impresora: 321 x 201 entre la pared de retención, el nervio posterior y las paredes '
             'laterales; suelo 5 mm bajo el borde, de 4 mm, sobre cinco tabiques verticales.',
             'La base de la A1 mini (315 x 195) queda a 5 mm de la pared de retención y de la pared izquierda, '
             'huecos que ocupan tiras de neopreno de 5 mm (MEC-0-02), y a 1 mm del nervio y de la pared derecha.',
             'El soporte del actuador se atornilla a la cara frontal del cuarto MEC-2-02 con 4 tornillos ISO 4762 M4 x 30 '
             'sobre insertos M4 x 10 de ese cuarto (MEC-1-05).']
    lam.estampar(_ensamble_datos(codigo, titulo, esc), notas, notas_pos=(228, 244))
    return lam


# 24 oct 2026: el soporte del actuador se atornilla a la cara frontal del cuarto MEC-2-02 (insertos de la cuna), no a la
# bandeja; sale de este subconjunto y se detalla en MEC-1-05
_subconjunto('MEC-1-02', 'SUBCONJUNTO DE LA BANDEJA', (5, 6, 7, 8, 11, 12), (1, -1, -0.7), 0.5, iso_centro=(135, 190), tabla_pos=(248, 128), notas_pos=(228, 215),
             notas=['La bandeja apoya sobre la mesa y recibe la estructura; las rejillas cierran la admisión frontal.',
              'El soporte del actuador no pertenece a la bandeja: se atornilla a la cara frontal del cuarto MEC-2-02 (MEC-1-05).',
              'Extractor de 30 x 30 x 10 en la pared posterior de la bandeja posterior izquierda (MEC-2-08).',
              'La bandeja posterior derecha lleva la ventana del módulo de entrada de red X1 (ELE-0-01).',
              'Ocho almohadillas de neopreno Ø25 x 5 bajo la bandeja (MEC-0-02): cuatro en las esquinas y cuatro en el '
              'centro de los lados, con el centro a 20 mm de los bordes.'])
_subconjunto('MEC-1-03', 'SUBCONJUNTO DE ENFRIAMIENTO', (9, 10), (1, -1, -0.7), 0.5,
             ['Ventilador axial de 92 mm (comercial, MEC-0-02) en el soporte; el ducto forma la cuchilla de aire sobre la cama.',
              'El módulo apoya en la bahía lateral de la estructura y se retira sin desmontar otras piezas.'])
_subconjunto('MEC-1-04', 'SUBCONJUNTO DE VISIÓN E ILUMINACIÓN', (15, 16, 17, 18, 19), (1, -1, -0.6), 0.5,
             ['Soporte perpendicular al plano inclinado de la cuna posterior derecha; cámara ESP32-CAM y dicroico MR16 sobre rótulas de bola.',
              'Objetivo a 123 mm sobre la placa y 214 mm de su centro; el aro de la lámpara queda fuera del encuadre de la cámara.'])


import mecanismo  # noqa: E402,F401  (registra MEC-1-05)
