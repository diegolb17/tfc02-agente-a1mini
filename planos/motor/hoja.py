# -*- coding: utf-8 -*-
"""Composición de láminas en PDF (PyMuPDF): vistas, cotas, símbolos y cajetín PUCP.

Coordenadas de hoja en mm con origen en la esquina inferior izquierda. Las vistas
se colocan en primer diedro (ISO 128): planta debajo del alzado, vista desde la
izquierda a la derecha del alzado."""
import os
import sys
import math
import numpy as np
import fitz

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(AQUI, '..')))
import cajetin_pucp                      # noqa: E402
from . import hlr                        # noqa: E402

MM = 72.0 / 25.4
FUENTE = 'helv'
FUENTE_B = 'hebo'
FORMATOS = {'A3': (420, 297), 'A4': (297, 210), 'A2': (594, 420)}
NEGRO = (0, 0, 0)

ESTILOS = {
    'visible': dict(width=0.5, dashes=None),
    'oculta': dict(width=0.25, dashes='[5.5 2.3] 0'),
    'eje': dict(width=0.18, dashes='[14 2.3 2 2.3] 0'),
    'fina': dict(width=0.25, dashes=None),
    'cota': dict(width=0.25, dashes=None),
    'rayado': dict(width=0.18, dashes=None),
    'gruesa': dict(width=0.7, dashes=None),
    'fantasma': dict(width=0.18, dashes='[10 1.5 2 1.5 2 1.5] 0'),
}


def _fmt(v, dec=None):
    if dec is None:
        if abs(v - round(v)) < 0.05:
            return '%d' % round(v)
        return '%.1f' % v
    return ('%.' + str(dec) + 'f') % v


class Lamina:
    def __init__(self, formato='A3'):
        self.formato = formato
        self.W, self.H = FORMATOS[formato]
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=self.W * MM, height=self.H * MM)
        self._shapes = {}
        self._textos = []
        self._rellenos = []
        self.vistas = []

    # ---- primitivas ---------------------------------------------------------
    def pt(self, x, y):
        return fitz.Point(x * MM, (self.H - y) * MM)

    def _sh(self, estilo):
        if estilo not in self._shapes:
            self._shapes[estilo] = self.page.new_shape()
        return self._shapes[estilo]

    def linea(self, a, b, estilo='fina'):
        self._sh(estilo).draw_line(self.pt(*a), self.pt(*b))

    def polilinea(self, pts, estilo='visible', cerrar=False):
        if len(pts) < 2:
            return
        P = [self.pt(x, y) for x, y in pts]
        if cerrar:
            P.append(P[0])
        self._sh(estilo).draw_polyline(P)

    def circulo(self, c, r, estilo='fina'):
        self._sh(estilo).draw_circle(self.pt(*c), r * MM)

    def arco(self, c, r, a0, a1, estilo='fina', n=None):
        """Arco de a0 a a1 (grados, antihorario) como polilínea."""
        if a1 < a0:
            a1 += 360
        if n is None:
            n = max(8, int((a1 - a0) / 4))
        ang = np.radians(np.linspace(a0, a1, n + 1))
        self.polilinea([(c[0] + r * math.cos(t), c[1] + r * math.sin(t)) for t in ang], estilo)

    def relleno(self, pts, gris=0.0):
        self._rellenos.append(([self.pt(x, y) for x, y in pts], gris))

    def texto(self, x, y, s, tam=3.0, ang=0, anclar='c', negrita=False, gris=0.0):
        """Texto con altura nominal tam (mm); anclar: c centro, l izquierda, r derecha
        (referido a la línea base). ang: 0 o 90 (lectura de abajo hacia arriba)."""
        self._textos.append((x, y, s, tam, ang, anclar, negrita, gris))

    def ancho_texto(self, s, tam=3.0, negrita=False):
        return fitz.get_text_length(s, fontname=FUENTE_B if negrita else FUENTE, fontsize=tam * MM * 1.05) / MM

    def flecha(self, punta, direccion, largo=2.5, ancho=0.8):
        """Punta de flecha rellena en `punta`, apuntando en `direccion` (hacia la punta)."""
        d = np.asarray(direccion, float)
        d = d / (np.linalg.norm(d) + 1e-12)
        n = np.array([-d[1], d[0]])
        p = np.asarray(punta, float)
        base = p - d * largo
        self.relleno([tuple(p), tuple(base + n * ancho / 2), tuple(base - n * ancho / 2)])

    def punto(self, c, r=0.5):
        n = 12
        self.relleno([(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)])

    # ---- salida -------------------------------------------------------------
    def _volcar(self):
        for nombre, sh in self._shapes.items():
            e = ESTILOS[nombre]
            sh.finish(color=NEGRO, width=e['width'] * MM, dashes=e['dashes'], closePath=False,
                      lineCap=1 if nombre in ('oculta', 'eje') else 0, lineJoin=1)
            sh.commit()
        self._shapes = {}
        if self._rellenos:
            sh = self.page.new_shape()
            for pts, gris in self._rellenos:
                sh.draw_polyline(pts + [pts[0]])
                sh.finish(color=(gris,) * 3, fill=(gris,) * 3, width=0.1, closePath=True)
            sh.commit()
            self._rellenos = []
        for x, y, s, tam, ang, anclar, negrita, gris in self._textos:
            f = FUENTE_B if negrita else FUENTE
            fs = tam * MM * 1.05
            w = fitz.get_text_length(s, fontname=f, fontsize=fs) / MM
            if ang == 0:
                x0 = x - w / 2 if anclar == 'c' else (x - w if anclar == 'r' else x)
                self.page.insert_text(self.pt(x0, y), s, fontsize=fs, fontname=f, color=(gris,) * 3)
            else:
                y0 = y - w / 2 if anclar == 'c' else (y - w if anclar == 'r' else y)
                self.page.insert_text(self.pt(x, y0), s, fontsize=fs, fontname=f, rotate=90, color=(gris,) * 3)
        self._textos = []

    def estampar(self, datos, notas=None, marca_de_agua=True, notas_pos=None):
        self._volcar()
        cajetin_pucp.estampar(self.page, datos, marca_de_agua=marca_de_agua, notas=notas, notas_pos=notas_pos)

    def guardar(self, ruta, png=True, dpi=110):
        self._volcar()
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        self.doc.save(ruta, garbage=3, deflate=True)
        if png:
            carpeta = os.path.join(os.path.dirname(ruta), '..', '_rev')
            os.makedirs(carpeta, exist_ok=True)
            salida = os.path.join(carpeta, os.path.splitext(os.path.basename(ruta))[0] + '.png')
            fitz.open(ruta)[0].get_pixmap(dpi=dpi).save(salida)
            return salida
        return ruta


def _unir_polilineas(polis, tol=0.02):
    """Une polilíneas cuyos extremos coinciden (distancia < tol), de punta a cola, para que el
    patrón de trazos de las líneas discontinuas recorra la línea completa."""
    restantes = [np.asarray(p, float) for p in polis if len(p) >= 2]
    if len(restantes) < 2:
        return restantes
    q = max(tol, 1e-9)
    usados = [False] * len(restantes)
    indice = {}
    for i, p in enumerate(restantes):
        for extremo in (0, -1):
            k = (int(round(p[extremo][0] / q)), int(round(p[extremo][1] / q)))
            indice.setdefault(k, []).append(i)

    def vecino(pt, excluir):
        kx, ky = int(round(pt[0] / q)), int(round(pt[1] / q))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in indice.get((kx + dx, ky + dy), ()):
                    if j != excluir and not usados[j]:
                        pj = restantes[j]
                        if np.hypot(*(pj[0] - pt)) < tol:
                            return j, False
                        if np.hypot(*(pj[-1] - pt)) < tol:
                            return j, True
        return None, None

    salida = []
    for i in range(len(restantes)):
        if usados[i]:
            continue
        usados[i] = True
        cad = restantes[i]
        for _ in range(2):                      # crece por la cola y luego por la cabeza
            while True:
                j, invertir = vecino(cad[-1], i)
                if j is None:
                    break
                usados[j] = True
                pj = restantes[j][::-1] if invertir else restantes[j]
                cad = np.vstack([cad, pj[1:]])
            cad = cad[::-1]
        salida.append(cad)
    return salida


class Vista:
    """Una proyección colocada en la hoja a cierta escala."""

    def __init__(self, pieza, dir, up, escala=1.0, ocultas=True, corte=None, nombre='', res=None, tangentes=False):
        self.pr = hlr.Proyeccion(pieza, dir, up, ocultas=ocultas, res=res, corte=corte, tangentes=tangentes)
        self.escala = float(escala)
        self.ox = self.oy = 0.0
        self.nombre = nombre
        self.corte = corte
        self.dir = np.asarray(dir, float) / np.linalg.norm(dir)

    # --- colocación ---
    @property
    def centro2d(self):
        mn, mx = self.pr.bbox
        return (mn + mx) / 2

    @property
    def tam(self):
        """(ancho, alto) en mm de hoja."""
        mn, mx = self.pr.bbox
        return tuple((mx - mn) * self.escala)

    def colocar_centro(self, x, y):
        c = self.centro2d
        self.ox = x - c[0] * self.escala
        self.oy = y - c[1] * self.escala
        return self

    def colocar_punto(self, p3d, x=None, y=None):
        q = self.pr.proyectar(p3d)
        if x is not None:
            self.ox = x - q[0] * self.escala
        if y is not None:
            self.oy = y - q[1] * self.escala
        return self

    def alinear_x(self, otra, p3d):
        """Misma x de hoja que `otra` para el punto p3d (vistas en la misma columna)."""
        self.colocar_punto(p3d, x=otra.m(p3d)[0])
        return self

    def alinear_y(self, otra, p3d):
        self.colocar_punto(p3d, y=otra.m(p3d)[1])
        return self

    @property
    def rect(self):
        mn, mx = self.pr.bbox
        return (self.ox + mn[0] * self.escala, self.oy + mn[1] * self.escala,
                self.ox + mx[0] * self.escala, self.oy + mx[1] * self.escala)

    # --- mapeo ---
    def m(self, p3d):
        q = self.pr.proyectar(p3d)
        return (self.ox + q[0] * self.escala, self.oy + q[1] * self.escala)

    def m2(self, q):
        return (self.ox + q[0] * self.escala, self.oy + q[1] * self.escala)

    def dir2d(self, v3d):
        """Dirección 3D del modelo -> dirección 2D en la hoja (normalizada)."""
        d = (self.pr.R @ np.asarray(v3d, float))[:2]
        return d / (np.linalg.norm(d) + 1e-12)

    # --- detalle: recorta la proyección a un círculo (centro 3D, radio en mm de hoja) ---
    def recortar(self, centro3d, radio_hoja):
        from shapely.geometry import LineString, Point
        c = self.pr.proyectar(centro3d)
        circ = Point(c[0], c[1]).buffer(radio_hoja / self.escala, 64)

        def clip(polis):
            out = []
            for pl in polis:
                if len(pl) < 2:
                    continue
                g = LineString(pl).intersection(circ)
                for gg in getattr(g, 'geoms', [g]):
                    if gg.geom_type == 'LineString' and len(gg.coords) >= 2:
                        out.append(np.array(gg.coords))
            return out
        self.pr.visibles = clip(self.pr.visibles)
        self.pr.ocultas = clip(self.pr.ocultas)
        self.pr.lazos = clip(self.pr.lazos)
        self.pr.bbox = (np.array(c) - radio_hoja / self.escala, np.array(c) + radio_hoja / self.escala)
        self.detalle = (np.array(c), radio_hoja)
        return self

    # --- dibujo ---
    def dibujar(self, lam, rayado=True, paso_rayado=2.5, ang_rayado=45):
        lam.vistas.append(self)
        if getattr(self, 'detalle', None) is not None:
            c, r = self.detalle
            lam.circulo(self.m2(c), r, 'fina')
        # las ocultas llegan partidas en tramos cortos (la visibilidad se decide por tramo); si se
        # dibujan sueltas el patrón de trazos se reinicia en cada tramo y la línea parece continua.
        # además se descartan las ocultas que en la hoja repiten otra ya dibujada (por ejemplo, los
        # dos extremos de un tubo visto según su eje caen sobre la misma circunferencia): dos trazos
        # superpuestos con distinta fase se ven como una línea continua.
        ocupado = set()
        paso = 0.25                                  # mm de hoja

        def muestras(pts):
            pts = np.asarray(pts, float)
            out = [pts[0]]
            for a, b in zip(pts[:-1], pts[1:]):
                n = int(np.hypot(*(b - a)) / paso)
                for k in range(1, n + 1):
                    out.append(a + (b - a) * k / (n + 1))
                out.append(b)
            return np.asarray(out)

        def celdas(m):
            return {(int(round(x / paso)), int(round(y / paso))) for x, y in m}

        for pl in self.pr.visibles:
            ocupado |= celdas(muestras([self.m2(q) for q in pl]))
        for pl in _unir_polilineas(self.pr.ocultas, tol=0.02 / max(self.escala, 1e-6)):
            pts = [self.m2(q) for q in pl]
            m = muestras(pts)
            cs = [(int(round(x / paso)), int(round(y / paso))) for x, y in m]
            repetidas = sum(1 for (cx, cy) in cs if any((cx + dx, cy + dy) in ocupado
                                                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
            if len(cs) and repetidas / len(cs) > 0.9:
                continue
            ocupado |= set(cs)
            lam.polilinea(pts, 'oculta')
        for pl in self.pr.visibles:
            lam.polilinea([self.m2(q) for q in pl], 'visible')
        for lz in self.pr.lazos:
            lam.polilinea([self.m2(q) for q in lz], 'visible')
        if self.corte is not None and rayado and self.pr.lazos:
            self._rayar(lam, paso_rayado, ang_rayado)

    def _rayar(self, lam, paso, ang):
        from shapely.geometry import Polygon, LineString, MultiLineString
        from shapely.ops import unary_union
        polis = []
        for lz in self.pr.lazos:
            if len(lz) < 3:
                continue
            p = Polygon([tuple(self.m2(q)) for q in lz])
            if not p.is_valid:
                p = p.buffer(0)
            if p.area > 0.01:
                polis.append(p)
        if not polis:
            return
        # anidamiento par-impar
        polis.sort(key=lambda p: -p.area)
        region = None
        for p in polis:
            region = p if region is None else region.symmetric_difference(p)
        if region is None or region.is_empty:
            return
        x0, y0, x1, y1 = region.bounds
        d = math.hypot(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        a = math.radians(ang)
        u = (math.cos(a), math.sin(a))
        n = (-math.sin(a), math.cos(a))
        lineas = []
        k = -int(d / paso) - 1
        while k * paso < d:
            px, py = cx + n[0] * k * paso, cy + n[1] * k * paso
            lineas.append(LineString([(px - u[0] * d, py - u[1] * d), (px + u[0] * d, py + u[1] * d)]))
            k += 1
        inter = region.intersection(MultiLineString(lineas))
        geoms = getattr(inter, 'geoms', [inter])
        for g in geoms:
            if g.geom_type == 'LineString':
                lam.polilinea(list(g.coords), 'rayado')
            elif g.geom_type == 'MultiLineString':
                for gg in g.geoms:
                    lam.polilinea(list(gg.coords), 'rayado')


# ---- acotado ------------------------------------------------------------------
TAM_COTA = 3.0
FLECHA = 2.5


def _texto_tol(lam, x, y, texto, tol, tam, ang=0, anclar='c'):
    """Texto de cota con tolerancia: tol None | '±0.1' (str) | ('+0.2', '0') apilada."""
    if tol is None:
        lam.texto(x, y, texto, tam, ang, anclar)
        return lam.ancho_texto(texto, tam)
    if isinstance(tol, str):
        s = texto + ' ' + tol
        lam.texto(x, y, s, tam, ang, anclar)
        return lam.ancho_texto(s, tam)
    sup, inf = tol
    w0 = lam.ancho_texto(texto, tam)
    ts = tam * 0.7
    w1 = max(lam.ancho_texto(sup, ts), lam.ancho_texto(inf, ts))
    sep = 1.4                         # separación entre la cifra y las desviaciones (mm)
    total = w0 + sep + w1
    # desviaciones alineadas a la derecha: el 0 inferior queda bajo la última cifra de la superior
    if ang == 0:
        x0 = x - total / 2 if anclar == 'c' else (x - total if anclar == 'r' else x)
        lam.texto(x0, y, texto, tam, 0, 'l')
        lam.texto(x0 + total, y + tam * 0.55, sup, ts, 0, 'r')
        lam.texto(x0 + total, y - tam * 0.20, inf, ts, 0, 'r')
    else:
        y0 = y - total / 2 if anclar == 'c' else (y - total if anclar == 'r' else y)
        lam.texto(x, y0, texto, tam, 90, 'l')
        lam.texto(x - tam * 0.55, y0 + total, sup, ts, 90, 'r')
        lam.texto(x + tam * 0.20, y0 + total, inf, ts, 90, 'r')
    return total


def cota(lam, v, P1, P2, pos, eje='h', texto=None, prefijo='', sufijo='', tol=None, tam=TAM_COTA,
         texto_lado=None, fuera=None, gap=0.8, exceso=1.5, hoja=False):
    """Cota lineal entre los puntos 3D P1 y P2 (o 2D de hoja si hoja=True).
    eje 'h': mide horizontal, línea de cota en y=pos; 'v': mide vertical, línea en x=pos.
    texto: sobreescribe el valor; texto_lado: desplaza el texto a lo largo de la cota (mm)."""
    a = np.array(P1 if hoja else v.m(P1), float)
    b = np.array(P2 if hoja else v.m(P2), float)
    medida = abs(b[0] - a[0]) if eje == 'h' else abs(b[1] - a[1])
    if medida < 1e-6 and texto is None:
        raise ValueError('cota nula (%s): eje equivocado para %s-%s' % (eje, P1, P2))
    if eje == 'h':
        if a[0] > b[0]:
            a, b = b, a
        valor = abs(b[0] - a[0]) / (1.0 if hoja else v.escala)
        y = pos
        # líneas de referencia
        for p in (a, b):
            s = 1 if y > p[1] else -1
            lam.linea((p[0], p[1] + s * gap), (p[0], y + s * exceso), 'cota')
        L = b[0] - a[0]
        if fuera is None:
            fuera = L < 3.2 * FLECHA
        if fuera:
            lam.linea((a[0] - 3 * FLECHA, y), (b[0] + 3 * FLECHA, y), 'cota')
            lam.flecha((a[0], y), (1, 0))
            lam.flecha((b[0], y), (-1, 0))
        else:
            lam.linea((a[0], y), (b[0], y), 'cota')
            lam.flecha((a[0], y), (-1, 0))
            lam.flecha((b[0], y), (1, 0))
        t = texto if texto is not None else prefijo + _fmt(valor) + sufijo
        tx = (a[0] + b[0]) / 2 + (texto_lado or 0)
        if fuera and texto_lado is None:
            tx = b[0] + 3 * FLECHA + 1
            _texto_tol(lam, tx, y - tam * 0.35, t, tol, tam, 0, 'l')
        else:
            _texto_tol(lam, tx, y + 0.8, t, tol, tam, 0, 'c')
    else:
        if a[1] > b[1]:
            a, b = b, a
        valor = abs(b[1] - a[1]) / (1.0 if hoja else v.escala)
        x = pos
        for p in (a, b):
            s = 1 if x > p[0] else -1
            lam.linea((p[0] + s * gap, p[1]), (x + s * exceso, p[1]), 'cota')
        L = b[1] - a[1]
        if fuera is None:
            fuera = L < 3.2 * FLECHA
        if fuera:
            lam.linea((x, a[1] - 3 * FLECHA), (x, b[1] + 3 * FLECHA), 'cota')
            lam.flecha((x, a[1]), (0, 1))
            lam.flecha((x, b[1]), (0, -1))
        else:
            lam.linea((x, a[1]), (x, b[1]), 'cota')
            lam.flecha((x, a[1]), (0, -1))
            lam.flecha((x, b[1]), (0, 1))
        t = texto if texto is not None else prefijo + _fmt(valor) + sufijo
        ty = (a[1] + b[1]) / 2 + (texto_lado or 0)
        if fuera and texto_lado is None:
            _texto_tol(lam, x - 0.8, b[1] + 3 * FLECHA + 1, t, tol, tam, 90, 'l')
        else:
            _texto_tol(lam, x - 0.8, ty, t, tol, tam, 90, 'c')
    return valor


def cota_alineada(lam, v, P1, P2, desplazamiento, texto=None, prefijo='', sufijo='', tol=None, tam=TAM_COTA, hoja=False):
    """Cota paralela al segmento P1-P2, desplazada perpendicularmente (mm de hoja, signo = lado)."""
    a = np.array(P1 if hoja else v.m(P1), float)
    b = np.array(P2 if hoja else v.m(P2), float)
    d = b - a
    L = np.linalg.norm(d)
    u = d / L
    n = np.array([-u[1], u[0]])
    valor = L / (1.0 if hoja else v.escala)
    a2, b2 = a + n * desplazamiento, b + n * desplazamiento
    s = np.sign(desplazamiento)
    for p, p2 in ((a, a2), (b, b2)):
        lam.linea(tuple(p + n * s * 0.8), tuple(p2 + n * s * 1.5), 'cota')
    lam.linea(tuple(a2), tuple(b2), 'cota')
    lam.flecha(tuple(a2), tuple(-u))
    lam.flecha(tuple(b2), tuple(u))
    t = texto if texto is not None else prefijo + _fmt(valor) + sufijo
    c = (a2 + b2) / 2 + n * 0.8 * (1 if n[1] >= 0 else -1)
    # texto girado sólo si la cota es casi vertical
    if abs(u[0]) < 0.3:
        lam.texto(c[0], c[1], t, tam, 90, 'c')
    else:
        lam.texto(c[0], c[1] + (0 if n[1] >= 0 else -tam * 1.0), t, tam, 0, 'c')
    return valor


def nota(lam, v, P, texto, dx, dy, tam=TAM_COTA, hoja=False, punto=False, tol=None, flecha=True):
    """Línea de referencia desde el punto P (3D o de hoja) con codo horizontal y texto."""
    p = np.array(P if hoja else v.m(P), float)
    q = p + np.array([dx, dy])
    lam.linea(tuple(p), tuple(q), 'cota')
    if flecha:
        lam.flecha(tuple(p), tuple(p - q))
    elif punto:
        lam.punto(tuple(p))
    lado = 1 if dx >= 0 else -1
    lineas = texto if isinstance(texto, (list, tuple)) else [texto]
    w = max(lam.ancho_texto(s, tam) for s in lineas) + 1.5
    lam.linea(tuple(q), (q[0] + lado * w, q[1]), 'cota')
    y = q[1] + 0.8
    for i, s in enumerate(lineas):
        if i == 0:
            _texto_tol(lam, q[0] + lado * 0.8, y, s, tol, tam, 0, 'l' if lado > 0 else 'r')
        else:
            lam.texto(q[0] + lado * 0.8, y - i * tam * 1.5, s, tam, 0, 'l' if lado > 0 else 'r')
    return q


def cota_diametro(lam, v, C, r, ang, texto=None, tol=None, largo=6, tam=TAM_COTA, dentro=False, n_veces=None):
    """Diámetro de un círculo visto de frente: flecha sobre la circunferencia a `ang` grados
    y línea de referencia hacia fuera. C centro 3D, r radio del modelo."""
    c = np.array(v.m(C), float)
    R = r * v.escala
    u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    p = c + u * R
    q = p + u * largo
    t = texto if texto is not None else 'Ø' + _fmt(2 * r)
    if n_veces:
        t = '%dx %s' % (n_veces, t)
    lam.linea(tuple(p), tuple(q), 'cota')
    lam.flecha(tuple(p), tuple(u) if not dentro else tuple(-u))
    lado = 1 if u[0] >= 0 else -1
    w = lam.ancho_texto(t, tam) + (0 if tol is None else 6) + 1.5
    lam.linea(tuple(q), (q[0] + lado * w, q[1]), 'cota')
    _texto_tol(lam, q[0] + lado * 0.8, q[1] + 0.8, t, tol, tam, 0, 'l' if lado > 0 else 'r')
    return q


def cota_radio(lam, v, C, r, ang, texto=None, largo=6, tam=TAM_COTA, desde_centro=False):
    c = np.array(v.m(C), float)
    R = r * v.escala
    u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    p = c + u * R
    q = p + u * largo
    t = texto if texto is not None else 'R' + _fmt(r)
    if desde_centro:
        lam.linea(tuple(c), tuple(q), 'cota')
    else:
        lam.linea(tuple(p), tuple(q), 'cota')
    lam.flecha(tuple(p), tuple(-u))
    lado = 1 if u[0] >= 0 else -1
    w = lam.ancho_texto(t, tam) + 1.5
    lam.linea(tuple(q), (q[0] + lado * w, q[1]), 'cota')
    lam.texto(q[0] + lado * 0.8, q[1] + 0.8, t, tam, 0, 'l' if lado > 0 else 'r')


def cota_angulo(lam, v, V, P1, P2, radio, texto=None, tam=TAM_COTA, hoja=False):
    """Ángulo en el vértice V entre las direcciones a P1 y P2; arco de radio `radio` (mm hoja)."""
    c = np.array(V if hoja else v.m(V), float)
    a = np.array(P1 if hoja else v.m(P1), float) - c
    b = np.array(P2 if hoja else v.m(P2), float) - c
    a0 = math.degrees(math.atan2(a[1], a[0]))
    a1 = math.degrees(math.atan2(b[1], b[0]))
    if (a1 - a0) % 360 > 180:
        a0, a1 = a1, a0
    sweep = (a1 - a0) % 360
    lam.arco(tuple(c), radio, a0, a0 + sweep, 'cota')
    for ang, s in ((a0, 1), (a0 + sweep, -1)):
        p = c + radio * np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        tg = s * np.array([-math.sin(math.radians(ang)), math.cos(math.radians(ang))])
        lam.flecha(tuple(p), tuple(-tg))
        # líneas de referencia hasta el arco
        u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        lam.linea(tuple(c + u * (radio - 4)), tuple(c + u * (radio + 1.5)), 'cota')
    am = math.radians(a0 + sweep / 2)
    t = texto if texto is not None else _fmt(sweep) + '°'
    p = c + (radio + 2.5) * np.array([math.cos(am), math.sin(am)])
    lam.texto(p[0], p[1] - tam * 0.35, t, tam, 0, 'c')


def eje_circulo(lam, v, C, r, ext=2.0, hoja=False):
    """Cruz de centro para un círculo visto de frente."""
    c = v.m(C) if not hoja else C
    R = r * v.escala + ext
    if R < 3.0:
        lam.linea((c[0] - R, c[1]), (c[0] + R, c[1]), 'fina')
        lam.linea((c[0], c[1] - R), (c[0], c[1] + R), 'fina')
    else:
        lam.linea((c[0] - R, c[1]), (c[0] + R, c[1]), 'eje')
        lam.linea((c[0], c[1] - R), (c[0], c[1] + R), 'eje')


def eje_linea(lam, v, P1, P2, ext=3.0, hoja=False):
    a = np.array(P1 if hoja else v.m(P1), float)
    b = np.array(P2 if hoja else v.m(P2), float)
    u = (b - a) / (np.linalg.norm(b - a) + 1e-12)
    lam.linea(tuple(a - u * ext), tuple(b + u * ext), 'eje')


def rugosidad(lam, x, y, valor='Ra 12.5', tam=2.5, ang=0, mecanizado=None):
    """Símbolo de rugosidad ISO 1302 con el vértice en (x, y). ang 0 (sobre línea
    horizontal) o 90 (sobre línea vertical, a la derecha)."""
    h = tam * 1.6
    pts = [(-h * 0.35, h * 0.6), (0, 0), (h * 0.55, h * 1.6)]
    tx = (h * 0.6, h * 0.75)
    if ang == 90:
        pts = [(-py, px) for px, py in pts]
        tx = (-tx[1], tx[0])
    lam.polilinea([(x + px, y + py) for px, py in pts], 'fina')
    if ang == 0:
        lam.texto(x + tx[0] + 0.3, y + tx[1], valor, tam, 0, 'l')
    else:
        lam.texto(x + tx[0] - 0.2, y + tx[1], valor, tam, 90, 'l')


def marca_corte(lam, v, P1, P2, letra, lado=1, hoja=False, tam=4.0):
    """Traza del plano de corte entre P1 y P2 (puntos de hoja o 3D), extremos gruesos,
    flechas perpendiculares hacia `lado` (+1 izquierda del sentido P1->P2) y letras."""
    a = np.array(P1 if hoja else v.m(P1), float)
    b = np.array(P2 if hoja else v.m(P2), float)
    u = (b - a) / np.linalg.norm(b - a)
    n = np.array([-u[1], u[0]]) * lado
    lam.linea(tuple(a - u * 2), tuple(a + u * 5), 'gruesa')
    lam.linea(tuple(b + u * 2), tuple(b - u * 5), 'gruesa')
    lam.linea(tuple(a + u * 5), tuple(b - u * 5), 'eje')
    for p in (a - u * 2, b + u * 2):
        q = p + n * 7
        lam.linea(tuple(q), tuple(p + n * 1.5), 'cota')
        lam.flecha(tuple(p + n * 1.0), tuple(-n))
        lam.texto(q[0] + n[0] * 2.5 - (0 if abs(n[0]) > 0.5 else 0), q[1] + n[1] * 2.5 - tam * 0.35, letra, tam, 0, 'c', negrita=True)


def traza(lam, v, p0, n_plano, dir_seccion, letra, margen=6, tam=4.0):
    """Traza del plano de corte (p0, n_plano) sobre la vista v, con flechas en el sentido
    de observación `dir_seccion` y letras en los extremos. Calcula todo automáticamente."""
    c = np.array(v.m(p0), float)
    nn = v.dir2d(n_plano)
    u = np.array([-nn[1], nn[0]])
    if u[1] < -1e-9 or (abs(u[1]) < 1e-9 and u[0] < 0):
        u = -u                        # t creciente = hacia arriba / hacia la derecha
    m_a, m_b = (margen, margen) if np.isscalar(margen) else margen
    x0, y0, x1, y1 = v.rect
    ts = []
    for coord, lim in ((0, x0), (0, x1), (1, y0), (1, y1)):
        if abs(u[coord]) > 1e-9:
            t = (lim - c[coord]) / u[coord]
            q = c + u * t
            if x0 - 1e-6 <= q[0] <= x1 + 1e-6 and y0 - 1e-6 <= q[1] <= y1 + 1e-6:
                ts.append(t)
    a, b = c + u * (min(ts) - m_a), c + u * (max(ts) + m_b)
    fd = v.dir2d(dir_seccion)
    lado = 1 if np.dot(np.array([-u[1], u[0]]), -fd) > 0 else -1
    marca_corte(lam, v, tuple(a), tuple(b), letra, lado=lado, hoja=True, tam=tam)


def marca_detalle(lam, v, centro3d, radio_hoja, letra, ang=45, tam=4.0):
    """Círculo fino en la vista padre con la letra del detalle."""
    c = np.array(v.m(centro3d), float)
    lam.circulo(tuple(c), radio_hoja, 'fina')
    u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    p = c + u * radio_hoja
    q = p + u * 5
    lam.linea(tuple(p), tuple(q), 'fina')
    lam.texto(q[0] + u[0] * 2.5, q[1] + u[1] * 2.5 - tam * 0.35, letra, tam, 0, 'c', negrita=True)


def titulo_vista(lam, x, y, texto, escala=None, tam=4.0):
    s = texto if escala is None else '%s  (%s)' % (texto, escala)
    lam.texto(x, y, s, tam, 0, 'c', negrita=True)
    w = lam.ancho_texto(s, tam, True)
    lam.linea((x - w / 2, y - 1.2), (x + w / 2, y - 1.2), 'fina')


def globo(lam, v, P, numero, dx, dy, r=4.0, tam=3.5, hoja=False):
    p = np.array(P if hoja else v.m(P), float)
    c = p + np.array([dx, dy])
    u = (p - c) / np.linalg.norm(p - c)
    lam.linea(tuple(c + u * r), tuple(p), 'cota')
    lam.punto(tuple(p), 0.6)
    lam.circulo(tuple(c), r, 'cota')
    lam.texto(c[0], c[1] - tam * 0.35, str(numero), tam, 0, 'c')
    return c


def tabla(lam, x, y, columnas, filas, alto=6.0, tam=2.5, cabecera=True, hacia_arriba=True):
    """Tabla con esquina inferior izquierda en (x, y); columnas: [(titulo, ancho, alinear)]."""
    anchos = [c[1] for c in columnas]
    W = sum(anchos)
    todas = ([tuple(c[0] for c in columnas)] if cabecera else []) + list(filas)
    if hacia_arriba:
        todas = todas[::-1]
    for i, fila in enumerate(todas):
        y0 = y + i * alto
        es_cab = cabecera and ((i == len(todas) - 1) if hacia_arriba else (i == 0))
        lam.polilinea([(x, y0), (x + W, y0), (x + W, y0 + alto), (x, y0 + alto)], 'fina', cerrar=True)
        cx = x
        for (tit, w, al), celda in zip(columnas, fila):
            lam.linea((cx, y0), (cx, y0 + alto), 'fina')
            s = str(celda)
            while lam.ancho_texto(s, tam) > w - 1.5 and len(s) > 3:
                s = s[:-2] + '…' if not s.endswith('…') else s[:-2] + '…'
            if al == 'c' or es_cab:
                lam.texto(cx + w / 2, y0 + alto / 2 - tam * 0.35, s, tam, 0, 'c', negrita=es_cab)
            elif al == 'r':
                lam.texto(cx + w - 0.8, y0 + alto / 2 - tam * 0.35, s, tam, 0, 'r')
            else:
                lam.texto(cx + 0.8, y0 + alto / 2 - tam * 0.35, s, tam, 0, 'l')
            cx += w
    return y + len(todas) * alto


def primer_diedro(lam, pieza, dir_frente, up, escala, centro, sep=18, ocultas=True,
                  lateral='izq', planta=True, lateral_on=True, res=None):
    """Alzado en `centro`; planta debajo; vista lateral (desde la izquierda por defecto)
    a la derecha, según primer diedro. Devuelve dict con las vistas colocadas."""
    R = hlr.base_vista(dir_frente, up)
    xv, yv = R[0], R[1]
    vistas = {}
    f = Vista(pieza, dir_frente, up, escala, ocultas, nombre='frente', res=res).colocar_centro(*centro)
    vistas['frente'] = f
    ref = pieza.malla.V.mean(axis=0)
    if planta:
        # se mira desde arriba (dir = -up); en primer diedro el fondo de la pieza queda
        # arriba de la planta, por eso su 'arriba' de hoja es +dir_frente
        p = Vista(pieza, -np.asarray(up, float), np.asarray(dir_frente, float), escala, ocultas, nombre='planta', res=res)
        p.alinear_x(f, ref)
        p.oy += (f.rect[1] - sep) - p.rect[3]
        vistas['planta'] = p
    if lateral_on:
        if lateral == 'izq':      # vista desde la izquierda, se coloca a la derecha
            d = xv
            l = Vista(pieza, d, up, escala, ocultas, nombre='lateral', res=res)
            l.alinear_y(f, ref)
            dx = (f.rect[2] + sep) - l.rect[0]
            l.ox += dx
        else:                     # vista desde la derecha, se coloca a la izquierda
            d = -xv
            l = Vista(pieza, d, up, escala, ocultas, nombre='lateral', res=res)
            l.alinear_y(f, ref)
            dx = (f.rect[0] - sep) - l.rect[2]
            l.ox += dx
        vistas['lateral'] = l
    return vistas


def iso(lam, pieza, escala, centro, dir=(-1, -1, -0.8), up=(0, 0, 1), res=None):
    v = Vista(pieza, dir, up, escala, ocultas=False, nombre='iso', res=res).colocar_centro(*centro)
    return v
