# -*- coding: utf-8 -*-
"""Láminas del grupo C: los cuatro cuartos de la estructura (cuna) y los cuatro de la
bandeja. Generador estándar: tres vistas en primer diedro, isométrica, cotas de
envolvente, ángulo de la cara inclinada en las cunas y TABLA DE AGUJEROS.

Revisión del 12.10.2026: las llamadas por familia con una sola cota de posición no
bastaban para fabricar. Ahora cada agujero, arco y resalte lleva una marca (A1, B2...)
en la vista donde se ve de frente, y la tabla da su diámetro, eje, coordenadas del
centro de la boca respecto del vértice de referencia (mín X, mín Y, mín Z, marcado con
el símbolo de origen en las vistas) y su longitud. Los cilindros parciales de radio
pequeño son redondeos y pasan a una nota general."""
import math
import numpy as np
from laminas import (lamina, Pieza, Lamina, Vista, cota, nota, cota_angulo, eje_circulo, tabla,
                     titulo_vista, primer_diedro, iso, NOTAS_FDM, _datos, X, Y, Z)
from motor.malla import rasgos

COS20, SEN20 = math.cos(math.radians(20)), math.sin(math.radians(20))


def _grupos_cilindros(r):
    """Agrupa las caras cilíndricas por radio y línea de eje; devuelve una lista de dict con
    radio, eje unitario, punto del eje, caja, longitud y fracción angular (1 = agujero completo)."""
    grupos = []
    for c in r['cilindros']:
        e = np.asarray(c['eje'], float)
        e = e / np.linalg.norm(e)
        o = np.asarray(c['origen'], float)
        b = np.asarray(c['bbox'], float)
        cen = (b[0] + b[1]) / 2
        q = o + np.dot(cen - o, e) * e
        for g in grupos:
            if abs(g['r'] - c['radio']) < 1e-3 and abs(abs(np.dot(g['e'], e)) - 1) < 1e-3:
                d0 = g['q'] - q
                d0 = d0 - np.dot(d0, g['e']) * g['e']
                if np.linalg.norm(d0) < 0.05:
                    g['A'] += c['area_mm2']
                    g['b'] = np.array([np.minimum(g['b'][0], b[0]), np.maximum(g['b'][1], b[1])])
                    break
        else:
            grupos.append({'r': float(c['radio']), 'e': e, 'q': q, 'A': float(c['area_mm2']), 'b': b})
    for g in grupos:
        L = float(np.dot(g['b'][1] - g['b'][0], np.abs(g['e'])))
        g['L'] = L
        g['frac'] = g['A'] / (2 * math.pi * g['r'] * L) if L > 1e-6 else 0.0
        # centro del rasgo: punto del eje a media longitud
        cen = (g['b'][0] + g['b'][1]) / 2
        g['c'] = g['q'] + np.dot(cen - g['q'], g['e']) * g['e']
    # fragmentos de cara de menos de 0.5 mm de largo (astillas del cosido de caras): no son rasgos
    return [g for g in grupos if g['L'] >= 0.5]


def _concavo(g, malla):
    """True si la superficie mira hacia su eje (agujero o abertura), False si mira hacia fuera
    (resalte). Se decide con las normales de los triángulos de la malla que yacen sobre el cilindro."""
    V, F = malla.V, malla.F
    T = V[F]
    cen = T.mean(axis=1)
    lo, hi = g['b'][0] - 0.3, g['b'][1] + 0.3
    sel = np.all((cen >= lo) & (cen <= hi), axis=1)
    if not sel.any():
        return True
    c = cen[sel]
    rel = c - g['q']
    rad = rel - np.outer(rel @ g['e'], g['e'])
    dist = np.linalg.norm(rad, axis=1)
    en = np.abs(dist - g['r']) < max(0.25, 0.04 * g['r'])
    if not en.any():
        return True
    n = np.cross(T[sel][en, 1] - T[sel][en, 0], T[sel][en, 2] - T[sel][en, 0])
    radial = rad[en] / (dist[en][:, None] + 1e-12)
    return float(np.sum(np.einsum('ij,ij->i', n, radial))) < 0


def _clasificar(grupos, malla=None):
    agujeros, arcos, resaltes, redondeos = [], [], [], set()
    for g in grupos:
        conc = True if malla is None else _concavo(g, malla)
        g['concavo'] = conc
        if g['r'] < 5 and g['frac'] < 0.42:
            redondeos.add(round(g['r'], 1))
        elif not conc:
            resaltes.append(g)
        elif g['frac'] >= 0.42:
            agujeros.append(g)
        else:
            arcos.append(g)
    return agujeros, arcos, resaltes, sorted(redondeos)


def _nombre_eje(e):
    a = np.abs(e)
    i = int(np.argmax(a))
    if a[i] > 0.999:
        return 'XYZ'[i]
    if abs(a[2] - COS20) < 0.02 and abs(a[0] - SEN20) < 0.02:
        return 'Norm. 20°'
    return '%.2f,%.2f,%.2f' % tuple(e)


def _esc_txt(e):
    return '1:%g' % round(1 / e, 1) if e < 1 else '%g:1' % e


def _origen(lam, p):
    """Símbolo de origen de coordenadas (círculo con cruz y punto) en el punto de hoja p."""
    lam.circulo(p, 1.4, 'fina')
    lam.linea((p[0] - 2.4, p[1]), (p[0] + 2.4, p[1]), 'fina')
    lam.linea((p[0], p[1] - 2.4), (p[0], p[1] + 2.4), 'fina')
    lam.punto(p, 0.45)
    lam.texto(p[0] - 2.0, p[1] - 4.4, 'O', 2.4, 0, 'c', negrita=True)


def _lineas_notas(notas):
    """Líneas que ocupan las notas en el bloque del cajetín (mismo corte de palabras que cajetin_pucp)."""
    import fitz
    tn, ancho = 8.2, (180 - 2) * 72 / 25.4
    n = 0
    for i, s in enumerate(notas, 1):
        actual, pref = '', '%d. ' % i
        n += 1
        for w in s.split():
            prueba = (actual + ' ' + w).strip()
            if fitz.get_text_length(pref + prueba, fontname='helv', fontsize=tn) > ancho and actual:
                n += 1
                actual, pref = w, '    '
            else:
                actual = prueba
    return n


def lamina_estandar(codigo, nombre, titulo, escala, dir_frente, up, lateral='izq', iso_dir=(-1, -1, -0.8),
                    notas_extra=(), centro=(105, 200), sep=24, iso_pos=(335, 210), iso_escala=None,
                    ocultas=True, angulo_cuna=False, extra=None):
    pz = Pieza(nombre)
    r = rasgos(nombre)['rasgos']
    lam = Lamina('A3')
    vs = primer_diedro(lam, pz, dir_frente=dir_frente, up=up, escala=escala, centro=centro, sep=sep,
                       lateral=lateral, ocultas=ocultas)
    f, p, l = vs['frente'], vs['planta'], vs['lateral']
    # --- encaja el bloque de vistas dentro de la zona útil ---
    xmin = min(v.rect[0] for v in (f, p, l)); xmax = max(v.rect[2] for v in (f, p, l))
    ymin = min(v.rect[1] for v in (f, p, l)); ymax = max(v.rect[3] for v in (f, p, l))
    dx = max(0, 30 - xmin) if xmin < 30 else min(0, 222 - xmax)
    dy = max(0, 30 - ymin) if ymin < 30 else min(0, 262 - ymax)
    for v in (f, p, l):
        v.ox += dx; v.oy += dy
    for v in (f, p, l):
        v.dibujar(lam)
    mn, mx = pz.malla.bbox

    # --- cotas de envolvente ---
    def envolvente(v, lado_h, lado_v):
        R = v.pr.R
        ih = int(np.argmax(np.abs(R[0]))); iv = int(np.argmax(np.abs(R[1])))
        a = mn.copy(); b = mn.copy(); b[ih] = mx[ih]
        cota(lam, v, tuple(a), tuple(b), (v.rect[3] + 7) if lado_h > 0 else (v.rect[1] - 7), 'h')
        a = mn.copy(); b = mn.copy(); b[iv] = mx[iv]
        cota(lam, v, tuple(a), tuple(b), (v.rect[2] + 7) if lado_v > 0 else (v.rect[0] - 7), 'v')
    envolvente(f, +1, +1)
    envolvente(p, -1, -1)
    envolvente(l, +1, +1)

    # --- vértice de referencia en las tres vistas ---
    for v in (f, p, l):
        _origen(lam, v.m(tuple(mn)))

    # --- rasgos cilíndricos: marcas y tabla ---
    agujeros, arcos, resaltes, redondeos = _clasificar(_grupos_cilindros(r), pz.malla)
    filas = []
    ocupados = []                       # cajas de texto ya colocadas (hoja)
    contador = [0]

    def vista_de(e):
        for v in (f, p, l):
            if abs(abs(np.dot(e, v.dir)) - 1) < 1e-3:
                return v
        return f

    circulos = []                       # (vista, centro en hoja, radio en hoja) de los agujeros vistos de frente

    def libre(caja, propio):
        if not all(caja[2] < o[0] or caja[0] > o[2] or caja[3] < o[1] or caja[1] > o[3] for o in ocupados):
            return False
        for (cv_, cc_, rr_) in circulos:
            if cv_ is propio[0] and np.allclose(cc_, propio[1]):
                continue
            if cv_ is not propio[0]:
                continue
            # distancia del centro del círculo a la caja
            dx = max(caja[0] - cc_[0], 0, cc_[0] - caja[2])
            dy = max(caja[1] - cc_[1], 0, cc_[1] - caja[3])
            if dx * dx + dy * dy < (rr_ + 0.3) ** 2:
                return False
        return True

    def colocar_marca(v, c3, rad, texto):
        cc = np.array(v.m(tuple(c3)))
        R = rad * v.escala
        w = lam.ancho_texto(texto, 2.2)
        for extra_d in (2.2, 4.0, 6.0):
            for ang in (45, 135, -45, -135, 90, -90, 0, 180):
                u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
                q = cc + u * (R + extra_d)
                x0 = q[0] if u[0] >= -0.01 else q[0] - w
                y0 = q[1] if u[1] >= -0.01 else q[1] - 2.4
                caja = (x0 - 0.3, y0 - 0.3, x0 + w + 0.3, y0 + 2.6)
                if libre(caja, (v, cc)):
                    ocupados.append(caja)
                    # fondo blanco: ninguna arista atraviesa el número (en MEC-2-02 el 10 se leía 0)
                    lam.relleno([(x0 - 0.25, y0 - 0.1), (x0 + w + 0.25, y0 - 0.1), (x0 + w + 0.25, y0 + 2.5), (x0 - 0.25, y0 + 2.5)], gris=1.0)
                    lam.texto(x0, y0 + 0.2, texto, 2.2, 0, 'l', negrita=True)
                    return
        lam.texto(cc[0] + R + 1.5, cc[1] + R + 1.5, texto, 2.2, 0, 'l', negrita=True)

    def boca(g):
        """Centro de la boca del rasgo: el extremo del eje más alejado del centro de la pieza."""
        e, c, L = g['e'], g['c'], g['L']
        m3 = (mn + mx) / 2
        p1, p2 = c + e * L / 2, c - e * L / 2
        return p1 if np.linalg.norm(p1 - m3) > np.linalg.norm(p2 - m3) else p2

    rasgos_tab = ([('agujero', g) for g in agujeros] + [('arco', g) for g in arcos] +
                  [('resalte', g) for g in resaltes])
    # orden: por tipo, diámetro y eje, para que las familias salgan contiguas
    rasgos_tab.sort(key=lambda t: ({'agujero': 0, 'arco': 1, 'resalte': 2}[t[0]], round(t[1]['r'], 2), _nombre_eje(t[1]['e']),
                                   tuple(np.round(t[1]['c'], 1))))
    for tipo, g in rasgos_tab:
        v_ = vista_de(g['e'])
        if tipo == 'agujero' and abs(abs(np.dot(g['e'], v_.dir)) - 1) < 1e-3:
            circulos.append((v_, np.array(v_.m(tuple(boca(g)))), g['r'] * v_.escala))
    for tipo, g in rasgos_tab:
        contador[0] += 1
        marca = '%d' % contador[0]
        v = vista_de(g['e'])
        c3 = boca(g) if tipo == 'agujero' else g['c']
        if abs(abs(np.dot(g['e'], v.dir)) - 1) < 1e-3 and tipo == 'agujero':
            eje_circulo(lam, v, tuple(c3), g['r'])
        colocar_marca(v, c3, g['r'] if tipo != 'resalte' else 0.5, marca)
        rel = c3 - mn
        if tipo == 'agujero':
            elem = 'Ø%g' % round(2 * g['r'], 1)
            if g['r'] >= 10:
                elem += ' abertura'
            elif g['frac'] < 0.75:
                elem += ' parcial'
        elif tipo == 'arco':
            elem = 'R%g arco' % round(g['r'], 1)
        else:
            elem = 'Ø%g resalte' % round(2 * g['r'], 1)
        filas.append((marca, elem, _nombre_eje(g['e']), '%.1f' % rel[0], '%.1f' % rel[1], '%.1f' % rel[2],
                      '%.1f' % g['L']))

    # --- ángulo de la cara inclinada (cunas): plano con normal (±sen20, 0, cos20) ---
    if angulo_cuna:
        candidatos = [pl for pl in r['planos'] if abs(abs(np.asarray(pl['normal'])[2]) - COS20) < 0.02
                      and abs(abs(np.asarray(pl['normal'])[0]) - SEN20) < 0.02]
        candidatos.sort(key=lambda pl: -pl['area_mm2'])
        for pl in candidatos[:1]:
            nrm = np.asarray(pl['normal'], float)
            if nrm[2] < 0:
                nrm = -nrm
            b = np.array(pl['bbox'])
            xlo, xhi = b[0][0], b[1][0]
            zlo = b[0][2]
            y0 = (b[0][1] + b[1][1]) / 2
            x_v = xlo if nrm[0] < 0 else xhi          # extremo bajo de la pendiente
            s = 1 if nrm[0] < 0 else -1
            V = (x_v, y0, zlo); P1 = (x_v + s * 60, y0, zlo); P2 = (x_v + s * 60, y0, zlo + 60 * math.tan(math.radians(20)))
            cota_angulo(lam, f, V, P1, P2, 46, texto='20°')   # 21 oct: con 32 una linea oculta lo hacia leer 120°
            break

    if extra is not None:
        cv = extra(lam, f, p, l, mn, mx)
        if cv is not None:
            _detalle_ventana(lam, pz, l if abs(abs(l.dir[0]) - 1) < 1e-3 else f, cv)

    # --- isométrica, reducida para dejar sitio a la tabla ---
    ie = iso_escala or (1 / 3.0 if escala >= 0.5 else escala * 0.66)
    v_iso = iso(lam, pz, ie, iso_pos, dir=iso_dir, up=Z)
    v_iso.dibujar(lam)
    titulo_vista(lam, iso_pos[0], v_iso.rect[1] - 6, 'ISOMÉTRICA', _esc_txt(ie))

    # --- tabla de agujeros, a la derecha, bajo la isométrica ---
    notas = NOTAS_FDM + list(notas_extra)
    if redondeos:
        notas.append('Redondeos no acotados: %s.' % ' y '.join('R%g' % x for x in redondeos))
    notas.append('Origen O: vértice de mín X, mín Y, mín Z de la pieza. Long.: longitud del agujero según su eje.')
    notas.append('Geometría completa según el modelo 3D nativo TFC_Sistema_A1mini_v3; aquí se acotan interfaces y funciones.')
    # medido: cabecera NOTAS a 71.7 + 4.2 n mm del borde inferior, mas 1.5 de holgura; n cuenta las líneas partidas
    tope_notas = 73.2 + 4.2 * _lineas_notas(notas)

    # 15 oct (N-09): texto de 2.8 mm, el de las listas de piezas, para que la altura de mayúscula supere 2 mm en A3
    col = [('Marca', 13, 'c'), ('Rasgo', 27, 'c'), ('Eje', 19, 'c'), ('X', 15, 'c'), ('Y', 15, 'c'),
           ('Z', 15, 'c'), ('Long.', 14, 'c')]
    W = sum(c[1] for c in col)
    alto = 5.6
    x_t = 404 - W
    y_top = v_iso.rect[1] - 13      # 15 oct: con el titulo de 3 mm pegado a la tabla no toca el de la isometrica
    base = y_top - alto * (len(filas) + 1)
    if base < tope_notas:
        # no cabe a la derecha: va a la zona libre bajo la vista lateral, al lado de la planta que
        # tenga más espacio (a la derecha si la lateral está a la derecha, a la izquierda si no)
        cand = []
        der = (p.rect[2] + 13, 227.0)     # 21 oct: con 10 mm el texto de la cota de 170 de la planta caia sobre la tabla
        izq = (22.0, p.rect[0] - 10)
        for (xa, xb) in (der, izq):
            vistas_encima = [v for v in (f, l) if v.rect[2] > xa and v.rect[0] < xb]
            top = (min(v.rect[1] for v in vistas_encima) - 18) if vistas_encima else 262.0
            cand.append((xb - xa, xa, xb, top))
        cand.sort(reverse=True)
        _, xa, xb, y_top = cand[0]
        x_t = xa
        if x_t + W > xb:
            esc = (xb - x_t) / W
            col = [(t, w * esc, al) for t, w, al in col]
            W = xb - x_t
        base = y_top - alto * (len(filas) + 1)
        if base < 14:
            alto = (y_top - 14) / (len(filas) + 1)
            base = 14
    lam.texto(x_t, y_top + 1.2, 'TABLA DE AGUJEROS (coordenadas en mm desde el origen O)', 3.0, 0, 'l', negrita=True)
    tabla(lam, x_t, base, col, filas, alto=alto, tam=min(2.8, alto * 0.5))
    lam.estampar(_datos(codigo, titulo, _esc_txt(escala), nombre), notas)
    return lam


NOTAS_CUNA = (
    'Cuarto de la estructura inclinada 20°; se une a los vecinos con tornillos M4 sobre insertos M4 x 10 (Ø5.6).',
    'Pared general de 4 mm; resaltes interiores de 13 mm que llevan el espesor local a 17 mm en los anclajes.',
    'Orientación de impresión: cara de apoyo sobre la bandeja hacia abajo; solo la cara inclinada lleva soportes.',
    'Los bloques de unión arrancan de la base. Ø5: alojamientos de los pasadores de alineación con el cuarto vecino.',
)
NOTAS_BANDEJA = (
    'Cuarto de la bandeja portante; recibe la estructura con tornillos M4 sobre insertos M4 x 10 (Ø5.6, Long. en la tabla).',
    'La cavidad interior aloja la electrónica; los pasos de cable comunican los cuartos.',
    'Orientación de impresión: cara inferior sobre la cama; solo los puentes de las ventanas llevan soporte.',
    'Cuñas de 45° bajo la ceja del muro y las pestañas. Ø5: alojamientos de los pasadores de alineación.',
)


def _ventana_entrada_red(lam, f, p, l, mn, mx):
    """MEC-2-07: ventana del módulo de entrada de red en la pared posterior (x 320.2 a 324.2).
    En la vista lateral se acota su posición y se marca el detalle V, donde se acotan la ventana
    y el rebaje a escala 1:1."""
    from laminas import Vista, marca_detalle, cota as _cota
    v = l if abs(abs(l.dir[0]) - 1) < 1e-3 else f
    xw = 324.194
    cv = (xw, 60.0, -20.0)
    # posición del centro respecto del borde Y = 0 y de la base, fuera de la vista
    _cota(lam, v, (xw, 0, -40), (xw, 60, -40), v.rect[1] - 14, 'h')
    _cota(lam, v, (xw, 0, -40), (xw, 0, -20), v.rect[2] + 15, 'v')
    marca_detalle(lam, v, cv, 15.0, 'V', ang=-125)
    # detalle V a escala 1:1
    d = Vista(v.pr.pieza if hasattr(v.pr, 'pieza') else None, v.dir, Z, 1.0, ocultas=True, nombre='detalle') if False else None
    return cv


def _ventana_rejilla(y0, y1):
    """MEC-2-05 y MEC-2-06: ventana de la rejilla de admisión en la pared frontal (X 0 a 4), de Z -36 (suelo) a -8."""
    def _fn(lam, f, p, l, mn, mx):
        from laminas import cota as _cota
        v = l if abs(abs(l.dir[0]) - 1) < 1e-3 else f
        # canto de la ventana más cercano a un borde de la vista; las cotas van por ese lado, con referencias cortas
        xa, xb = v.m((0, y0, -36))[0], v.m((0, y1, -36))[0]
        cands = [(xa - v.rect[0], y0, -1), (v.rect[2] - xa, y0, 1), (xb - v.rect[0], y1, -1), (v.rect[2] - xb, y1, 1)]
        _, ye, lado = min(cands)
        yb = mn[1] if abs(ye - y0) < 1e-6 else mx[1]
        xv = v.rect[2] + 14 if lado > 0 else v.rect[0] - 14
        _cota(lam, v, (0, yb, -36), (0, ye, -36), v.rect[1] - 7, 'h')
        _cota(lam, v, (0, y0, -36), (0, y1, -36), v.rect[1] - 7, 'h')
        _cota(lam, v, (0, ye, -40), (0, ye, -36), xv, 'v', texto_lado=-6)
        _cota(lam, v, (0, ye, -36), (0, ye, -8), xv, 'v')
        return None
    return _fn


def _ventana_inclinada(lam, f, p, l, mn, mx):
    """MEC-2-01: ventana de la cara inclinada, de Y 8 a 44 y de X 74.2 a 125.0 en planta (54.1 en la pendiente)."""
    from laminas import cota as _cota
    from motor.hoja import cota_alineada
    _cota(lam, p, (0, 8, 0), (74.2, 8, 0), p.rect[1] - 14, 'h')
    _cota(lam, p, (74.2, 8, 0), (125.0, 8, 0), p.rect[1] - 14, 'h')
    xv = p.m((74.2, 8, 0))[0] - 7          # dentro de la vista, junto a la ventana: referencias cortas
    _cota(lam, p, (74.2, 0, 0), (74.2, 8, 0), xv, 'v', texto_lado=-6)
    _cota(lam, p, (74.2, 8, 0), (74.2, 44, 0), xv, 'v')
    return None


def _detalle_ventana(lam, pz, l, cv):
    from laminas import Vista
    R_DET = 33.0
    d = Vista(pz, l.dir, Z, 1.0, ocultas=True, nombre='detalle').recortar(cv, R_DET)
    cx, cy = 182.0, 126.0
    d.colocar_punto(cv, x=cx, y=cy)
    d.dibujar(lam)
    titulo_vista(lam, cx, cy - R_DET - 9, 'DETALLE V', '1:1')
    xw = 324.194
    y0, y1, z0, z1 = 36.25, 83.75, -33.75, -6.25          # ventana
    py0, py1, pz0, pz1 = 33.0, 87.0, -35.5, -4.5          # rebaje interior
    # lado derecho de la hoja: el extremo de la ventana que cae a la derecha
    yder = y1 if d.m((xw, y1, z0))[0] > d.m((xw, y0, z0))[0] else y0
    pyder = py1 if yder == y1 else py0
    pyizq = py0 if yder == y1 else py1
    top_p = d.m((xw, 60, pz1))[1]
    bot_p = d.m((xw, 60, pz0))[1]
    der_p = d.m((xw, pyder, -20))[0]
    # anchos: ventana arriba, rebaje abajo
    cota(lam, d, (xw, y0, z1), (xw, y1, z1), top_p + 6, 'h', tol=('+0.3', '0'))
    cota(lam, d, (xw, py0, pz0), (xw, py1, pz0), bot_p - 6, 'h')
    # altos: los dos a la derecha
    cota(lam, d, (xw, yder, z0), (xw, yder, z1), der_p + 6, 'v', tol=('+0.3', '0'))
    cota(lam, d, (xw, pyder, pz0), (xw, pyder, pz1), der_p + 14, 'v')
    # nota del rebaje, fuera del círculo, desde la esquina inferior izquierda del rebaje
    q = d.m((xw, pyder, pz1))
    nota(lam, d, q, ['REBAJE INTERIOR 54 x 31', 'PROF. 2 (PARED 2)'], 22, 24, tam=3.0, hoja=True)


def _cavidad(y_borde, x_cota):
    """22 oct 2026 (P12): interfaz con la impresora, acotada en MEC-1-01. En la planta se acota el borde lateral de
    la cavidad desde el origen O; el resto de la cavidad va en la nota de la lámina."""
    def _fn(lam, f, p, l, mn, mx):
        from laminas import cota as _cota
        _cota(lam, p, (x_cota, mn[1], mx[2]), (x_cota, y_borde, mx[2]), p.rect[2] + 6, 'v')
        return None
    return _fn


def _y(*fns):
    """Encadena varias funciones extra; devuelve el centro de detalle que alguna pida."""
    def _fn(lam, f, p, l, mn, mx):
        cv = None
        for g in fns:
            r = g(lam, f, p, l, mn, mx)
            cv = r if r is not None else cv
        return cv
    return _fn


def _registrar(codigo, nombre, titulo, notas, iso_dir, lateral, cuna, extra=None, iso_escala=None):
    @lamina(codigo, nombre, titulo)
    def _fn(codigo, nombre, titulo):
        return lamina_estandar(codigo, nombre, titulo, 0.5, Y, Z, lateral=lateral, iso_dir=iso_dir,
                               notas_extra=notas, centro=(110, 200), sep=16, iso_pos=(330, 232),
                               angulo_cuna=cuna, extra=extra, iso_escala=iso_escala)
    return _fn


_registrar('MEC-2-01', 'Cuna_frontal_derecha', 'ESTRUCTURA, CUARTO FRONTAL DERECHO', NOTAS_CUNA + (
    'Ventana de 36 x 54.1 en la cara inclinada; en planta mide 36 x 50.8.',
    'Cavidad de la impresora (MEC-1-01): borde de la pared de retención a X 11.3 y de la pared lateral a Y 127 desde O; suelo 5 mm bajo el borde, de 4 mm.',), (-1, -1, -0.8), 'izq', True,
    extra=_y(_ventana_inclinada, _cavidad(127.0, 120.0)))
_registrar('MEC-2-02', 'Cuna_frontal_izquierda', 'ESTRUCTURA, CUARTO FRONTAL IZQUIERDO', NOTAS_CUNA + (
    'Agujero Ø22.5 de la cara lateral: botón de emergencia S2 (ver ELE-0-01).',
    'Cavidad de la impresora (MEC-1-01): borde de la pared de retención a X 11.3 y de la pared lateral a Y 158 desde O; suelo 5 mm bajo el borde, de 4 mm.',), (-1, 1, -0.8), 'der', True,
    extra=_cavidad(328.0, 120.0))
_registrar('MEC-2-03', 'Cuna_posterior_derecha', 'ESTRUCTURA, CUARTO POSTERIOR DERECHO', NOTAS_CUNA + (
    'Agujeros 1 a 4 (Ø4): insertos M3 x 4 en los pilares de los dos tabiques bajo el techo, para el soporte de la cámara MEC-2-14.',
    'Agujero 17: paso del cable de la cámara (Ø8), en el eje del tubo del soporte.',
    'Cavidad de la impresora (MEC-1-01): borde del nervio posterior a X 146.9 y de la pared lateral a Y 127 desde O; suelo 5 mm bajo el borde, de 4 mm.',),
    (1, -1, -0.8), 'izq', True, extra=_cavidad(127.0, 250.0))
_registrar('MEC-2-04', 'Cuna_posterior_izquierda', 'ESTRUCTURA, CUARTO POSTERIOR IZQUIERDO', NOTAS_CUNA + (
    'Cavidad de la impresora (MEC-1-01): borde del nervio posterior a X 146.9 y de la pared lateral a Y 158 desde O; suelo 5 mm bajo el borde, de 4 mm.',), (1, 1, -0.8), 'der', True,
    extra=_cavidad(328.0, 250.0))
_registrar('MEC-2-05', 'Bandeja_frontal_derecha', 'BANDEJA, CUARTO FRONTAL DERECHO', NOTAS_BANDEJA + (
    'Ø4.2: insertos roscados M3 para los 2 tornillos M3 de la rejilla de admisión MEC-2-11.',
    'Ventana de 148 x 28 de la pared frontal, sobre el suelo: paso del aire de la rejilla MEC-2-11.',), (-1, -1, -0.8), 'izq', False,
    extra=_ventana_rejilla(14.0, 162.0))
_registrar('MEC-2-06', 'Bandeja_frontal_izquierda', 'BANDEJA, CUARTO FRONTAL IZQUIERDO', NOTAS_BANDEJA + (
    'Ø4.2: insertos roscados M3 para los 2 tornillos M3 de la rejilla de admisión MEC-2-11.',
    'Ventana de 148 x 28 de la pared frontal, sobre el suelo: paso del aire de la rejilla MEC-2-11.',), (-1, 1, -0.8), 'der', False,
    extra=_ventana_rejilla(178.0, 326.0))
_registrar('MEC-2-07', 'Bandeja_posterior_derecha', 'BANDEJA, CUARTO POSTERIOR DERECHO', NOTAS_BANDEJA + (
    'Ventana del módulo de entrada IEC 60320 C14 con interruptor y portafusible (X1, ELE-0-01): detalle V.',
    'Pared rebajada a 2 mm (rebaje interior de 54 x 31 x 2) para el encaje de los clips del módulo.',), (1, -1, -0.8), 'izq', False,
    extra=_ventana_entrada_red, iso_escala=0.25)   # 22 oct: con la isométrica a 1:3 la tabla bajaba sobre el detalle V
_registrar('MEC-2-08', 'Bandeja_posterior_izquierda', 'BANDEJA, CUARTO POSTERIOR IZQUIERDO', NOTAS_BANDEJA + (
    'Ø28 y 4 x Ø3.2 a 24 mm de la pared posterior: ventilador de extracción de 30 x 30 x 10 mm, fijado con 4 tornillos M3.',),
    (1, 1, -0.8), 'der', False)
