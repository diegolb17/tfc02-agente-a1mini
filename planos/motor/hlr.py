# -*- coding: utf-8 -*-
"""Proyección ortográfica con eliminación de líneas ocultas y cortes.

Las líneas salen de las aristas exactas del B-Rep (no tangentes) más las siluetas
de la malla; la malla sólo decide la visibilidad (z-buffer con sesgo por pendiente).
Convención: `dir` es la dirección de observación (del ojo hacia la pieza) y `up` el
vector del modelo que debe verse hacia arriba. Coordenadas de vista: x derecha,
y arriba, z hacia el observador."""
import math
import numpy as np
from numba import njit

from .malla import Malla


def base_vista(dir, up):
    z = -np.asarray(dir, float)
    z = z / np.linalg.norm(z)
    up = np.asarray(up, float)
    x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-9:
        raise ValueError('up paralelo a dir')
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    return np.vstack([x, y, z])


@njit(cache=True)
def _zbuffer(P, F, res, x0, y0, W, H):
    zb = np.full((H, W), -1e30, np.float32)
    ib = np.full((H, W), -1, np.int32)
    sb = np.zeros((H, W), np.float32)
    for k in range(F.shape[0]):
        i0, i1, i2 = F[k, 0], F[k, 1], F[k, 2]
        ax, ay, az = P[i0, 0], P[i0, 1], P[i0, 2]
        bx, by, bz = P[i1, 0], P[i1, 1], P[i1, 2]
        cx, cy, cz = P[i2, 0], P[i2, 1], P[i2, 2]
        det = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
        if abs(det) < 1e-9:
            continue
        gx = ((bz - az) * (cy - ay) - (cz - az) * (by - ay)) / det
        gy = ((bx - ax) * (cz - az) - (cx - ax) * (bz - az)) / det
        pend = math.sqrt(gx * gx + gy * gy)
        if pend > 80.0:
            pend = 80.0
        mnx = int(math.floor((min(ax, min(bx, cx)) - x0) / res))
        mxx = int(math.ceil((max(ax, max(bx, cx)) - x0) / res))
        mny = int(math.floor((min(ay, min(by, cy)) - y0) / res))
        mxy = int(math.ceil((max(ay, max(by, cy)) - y0) / res))
        if mnx < 0: mnx = 0
        if mny < 0: mny = 0
        if mxx > W - 1: mxx = W - 1
        if mxy > H - 1: mxy = H - 1
        for j in range(mny, mxy + 1):
            py = y0 + (j + 0.5) * res
            for i in range(mnx, mxx + 1):
                px = x0 + (i + 0.5) * res
                l1 = ((bx - px) * (cy - py) - (cx - px) * (by - py)) / det
                l2 = ((cx - px) * (ay - py) - (ax - px) * (cy - py)) / det
                l3 = 1.0 - l1 - l2
                if l1 >= -1e-6 and l2 >= -1e-6 and l3 >= -1e-6:
                    z = l1 * az + l2 * bz + l3 * cz
                    if z > zb[j, i]:
                        zb[j, i] = z
                        ib[j, i] = k
                        sb[j, i] = pend
    return zb, ib, sb


@njit(cache=True)
def _muestrear(S, TA, FA, FI, zb, ib, sb, res, x0, y0, W, H, paso,
               salida_e, salida_t0, salida_t1, salida_v):
    n_out = 0
    for e in range(S.shape[0]):
        ax, ay, az = S[e, 0, 0], S[e, 0, 1], S[e, 0, 2]
        bx, by, bz = S[e, 1, 0], S[e, 1, 1], S[e, 1, 2]
        L = math.hypot(bx - ax, by - ay)
        n = int(L / paso) + 1
        if n < 2:
            n = 2
        if n > 4000:
            n = 4000
        prev = -1
        t_ini = 0.0
        for s in range(n):
            t = (s + 0.5) / n
            px = ax + t * (bx - ax)
            py = ay + t * (by - ay)
            pz = az + t * (bz - az)
            i = int((px - x0) / res)
            j = int((py - y0) / res)
            vis = 1
            if 0 <= i < W and 0 <= j < H:
                k = ib[j, i]
                if k != -1 and k != TA[e, 0] and k != TA[e, 1]:
                    zc = zb[j, i]
                    eps = 3.0 * res + 1.5 * res * sb[j, i]
                    if eps > 2.0:
                        eps = 2.0
                    zmin = 1e30
                    for jj in range(max(0, j - 1), min(H, j + 2)):
                        for ii in range(max(0, i - 1), min(W, i + 2)):
                            if zb[jj, ii] < zmin:
                                zmin = zb[jj, ii]
                    fk = FI[k] if k >= 0 else -9
                    if (fk == FA[e, 0] or fk == FA[e, 1]) and zc - pz < 1.5:
                        vis = 1
                    elif pz >= zmin - eps:
                        vis = 1
                    else:
                        vis = 0
            if prev == -1:
                prev = vis
                t_ini = 0.0
            elif vis != prev:
                t_fin = s / n
                if n_out < salida_e.shape[0]:
                    salida_e[n_out] = e; salida_t0[n_out] = t_ini; salida_t1[n_out] = t_fin; salida_v[n_out] = prev
                    n_out += 1
                prev = vis
                t_ini = t_fin
        if n_out < salida_e.shape[0]:
            salida_e[n_out] = e; salida_t0[n_out] = t_ini; salida_t1[n_out] = 1.0; salida_v[n_out] = prev
            n_out += 1
    return n_out


@njit(cache=True)
def _rellenar_tapa(zb, ib, segs, zcap, res, x0, y0, W, H):
    """Rellena en el z-buffer los polígonos (segmentos 2D del corte) a profundidad zcap."""
    for j in range(H):
        py = y0 + (j + 0.5) * res
        # cruces de la línea horizontal con los segmentos
        xs = np.empty(segs.shape[0])
        n = 0
        for s in range(segs.shape[0]):
            ax, ay = segs[s, 0, 0], segs[s, 0, 1]
            bx, by = segs[s, 1, 0], segs[s, 1, 1]
            if (ay <= py) != (by <= py):
                xs[n] = ax + (py - ay) / (by - ay) * (bx - ax)
                n += 1
        if n < 2:
            continue
        xs_s = np.sort(xs[:n])
        for q in range(0, n - 1, 2):
            i0 = int(math.ceil((xs_s[q] - x0) / res - 0.5))
            i1 = int(math.floor((xs_s[q + 1] - x0) / res - 0.5))
            if i0 < 0: i0 = 0
            if i1 > W - 1: i1 = W - 1
            for i in range(i0, i1 + 1):
                if zcap > zb[j, i]:
                    zb[j, i] = zcap
                    ib[j, i] = -2


def fusionar_colineales(segs, tol_ang=0.5, tol_off=0.02):
    """Une segmentos colineales y solapados (p. ej. círculos vistos de canto)."""
    if len(segs) == 0:
        return segs
    segs = np.asarray(segs, float)
    d = segs[:, 1] - segs[:, 0]
    L = np.linalg.norm(d, axis=1)
    ok = L > 1e-9
    segs, d, L = segs[ok], d[ok], L[ok]
    u = d / L[:, None]
    flip = (u[:, 0] < 0) | ((np.abs(u[:, 0]) < 1e-9) & (u[:, 1] < 0))
    u[flip] *= -1
    ang = np.degrees(np.arctan2(u[:, 1], u[:, 0]))
    n = np.stack([-u[:, 1], u[:, 0]], axis=1)
    off = np.einsum('ij,ij->i', segs[:, 0], n)
    clave_a = np.round(ang / tol_ang).astype(np.int64)
    clave_o = np.round(off / tol_off).astype(np.int64)
    orden = np.lexsort((clave_o, clave_a))
    out = []
    i = 0
    ka, ko = clave_a[orden], clave_o[orden]
    while i < len(orden):
        j = i
        while j < len(orden) and ka[j] == ka[i] and ko[j] == ko[i]:
            j += 1
        grupo = orden[i:j]
        if len(grupo) == 1:
            out.append(segs[grupo[0]])
        else:
            uu = u[grupo[0]]
            t0 = np.einsum('ij,j->i', segs[grupo, 0], uu)
            t1 = np.einsum('ij,j->i', segs[grupo, 1], uu)
            lo, hi = np.minimum(t0, t1), np.maximum(t0, t1)
            o = np.argsort(lo)
            lo, hi = lo[o], hi[o]
            base = segs[grupo[0], 0] - uu * np.dot(segs[grupo[0], 0], uu)
            a, b = lo[0], hi[0]
            for k in range(1, len(lo)):
                if lo[k] <= b + 0.02:
                    b = max(b, hi[k])
                else:
                    out.append(np.array([base + uu * a, base + uu * b]))
                    a, b = lo[k], hi[k]
            out.append(np.array([base + uu * a, base + uu * b]))
        i = j
    return np.array(out)


def cerrar_lazos(polis, hueco=0.6):
    """Cierra las polilíneas cuyos extremos quedan a menos de `hueco` mm."""
    out = []
    for p in polis:
        if len(p) >= 3 and np.linalg.norm(p[0] - p[-1]) < hueco and not np.allclose(p[0], p[-1]):
            p = np.vstack([p, p[:1]])
        out.append(p)
    return out


def encadenar(segs, tol=2e-3):
    """Une segmentos (N,2,2) que comparten extremos en polilíneas (arrays (k,2))."""
    if len(segs) == 0:
        return []
    segs = np.asarray(segs)
    pts = segs.reshape(-1, 2)
    clave = np.round(pts / tol).astype(np.int64)
    _, inv = np.unique(clave, axis=0, return_inverse=True)
    inv = inv.ravel().reshape(-1, 2)
    # descarta duplicados (mismo par de nodos) y degenerados
    par = np.sort(inv, axis=1)
    _, primero = np.unique(par, axis=0, return_index=True)
    keep = np.zeros(len(inv), bool); keep[primero] = True
    keep &= inv[:, 0] != inv[:, 1]
    segs, inv = segs[keep], inv[keep]
    pts = segs.reshape(-1, 2)
    nodos = {}
    for s, (a, b) in enumerate(inv):
        nodos.setdefault(int(a), []).append(s)
        nodos.setdefault(int(b), []).append(s)
    usado = np.zeros(len(segs), bool)
    coord = np.zeros((int(inv.max()) + 1, 2))
    coord[inv.ravel()] = pts
    polis = []
    for s0 in range(len(segs)):
        if usado[s0] or inv[s0, 0] == inv[s0, 1]:
            usado[s0] = True
            continue
        usado[s0] = True
        cadena = [int(inv[s0, 0]), int(inv[s0, 1])]
        for adelante in (True, False):
            while True:
                nodo = cadena[-1] if adelante else cadena[0]
                vecinos = nodos[nodo]
                if len(vecinos) != 2:
                    break
                cand = [s for s in vecinos if not usado[s]]
                if len(cand) != 1:
                    break
                s = cand[0]
                usado[s] = True
                nxt = int(inv[s, 1]) if inv[s, 0] == nodo else int(inv[s, 0])
                if adelante:
                    cadena.append(nxt)
                else:
                    cadena.insert(0, nxt)
                if cadena[0] == cadena[-1]:
                    break
        polis.append(coord[np.array(cadena)])
    return polis


@njit(cache=True)
def _cortar_nb(V, F, FI, d, Vout, Fout, FIout, Lout):
    nv = V.shape[0]
    nf = 0
    nl = 0
    for k in range(F.shape[0]):
        i0, i1, i2 = F[k, 0], F[k, 1], F[k, 2]
        d0, d1, d2 = d[i0], d[i1], d[i2]
        ins = (d0 >= 0) + (d1 >= 0) + (d2 >= 0)
        if ins == 3:
            Fout[nf, 0] = i0; Fout[nf, 1] = i1; Fout[nf, 2] = i2; FIout[nf] = FI[k]; nf += 1
            continue
        if ins == 0:
            continue
        if ins == 1:
            if d0 >= 0: a, b, c = i0, i1, i2
            elif d1 >= 0: a, b, c = i1, i2, i0
            else: a, b, c = i2, i0, i1
        else:
            if d0 < 0: a, b, c = i0, i1, i2
            elif d1 < 0: a, b, c = i1, i2, i0
            else: a, b, c = i2, i0, i1
        da, db, dc = d[a], d[b], d[c]
        tab = da / (da - db)
        tac = da / (da - dc)
        for q in range(3):
            Vout[nv, q] = V[a, q] + tab * (V[b, q] - V[a, q])
            Vout[nv + 1, q] = V[a, q] + tac * (V[c, q] - V[a, q])
        pab, pac = nv, nv + 1
        nv += 2
        if ins == 1:
            Fout[nf, 0] = a; Fout[nf, 1] = pab; Fout[nf, 2] = pac; FIout[nf] = FI[k]; nf += 1
        else:
            Fout[nf, 0] = b; Fout[nf, 1] = c; Fout[nf, 2] = pac; FIout[nf] = FI[k]; nf += 1
            Fout[nf, 0] = b; Fout[nf, 1] = pac; Fout[nf, 2] = pab; FIout[nf] = FI[k]; nf += 1
        for q in range(3):
            Lout[nl, 0, q] = Vout[pab, q]
            Lout[nl, 1, q] = Vout[pac, q]
        nl += 1
    return nv, nf, nl


def cortar_malla(malla, p0, n):
    """Conserva la parte con (v-p0)·n >= 0. Devuelve (Malla, lazos 3D (k,2,3))."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    d = (malla.V - np.asarray(p0, float)) @ n
    Vout = np.zeros((len(malla.V) + 2 * len(malla.F), 3))
    Vout[:len(malla.V)] = malla.V
    Fout = np.zeros((2 * len(malla.F), 3), np.int64)
    FIout = np.zeros(2 * len(malla.F), np.int64)
    Lout = np.zeros((len(malla.F), 2, 3))
    nv, nf, nl = _cortar_nb(malla.V, malla.F, malla.FI, d, Vout, Fout, FIout, Lout)
    return Malla(Vout[:nv], Fout[:nf], FIout[:nf]), Lout[:nl]


def cortar_polilineas(aristas, p0, n):
    """Recorta las aristas B-Rep al semiespacio (v-p0)·n >= 0."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    p0 = np.asarray(p0, float)
    out = []
    for a in aristas:
        P = a['pts']
        d = (P - p0) @ n
        actual = []
        for i in range(len(P) - 1):
            da, db = d[i], d[i + 1]
            if da >= 0 and db >= 0:
                if not actual:
                    actual.append(P[i])
                actual.append(P[i + 1])
            elif da >= 0 and db < 0:
                if not actual:
                    actual.append(P[i])
                t = da / (da - db)
                actual.append(P[i] + t * (P[i + 1] - P[i]))
                out.append({'pts': np.array(actual), 'f': a['f'], 'suave': a['suave']})
                actual = []
            elif da < 0 and db >= 0:
                t = da / (da - db)
                actual = [P[i] + t * (P[i + 1] - P[i]), P[i + 1]]
        if len(actual) >= 2:
            out.append({'pts': np.array(actual), 'f': a['f'], 'suave': a['suave']})
    return out


class Proyeccion:
    """Proyecta una Pieza: polilíneas visibles/ocultas 2D (mm modelo) y lazos de corte."""

    def __init__(self, pieza, dir, up, ocultas=True, res=None, corte=None, tangentes=False):
        self.R = base_vista(dir, up)
        malla, aristas = pieza.malla, pieza.aristas
        lazos3d = np.zeros((0, 2, 3))
        if corte is not None:
            p0, n = corte
            malla, lazos3d = cortar_malla(malla, p0, n)
            aristas = cortar_polilineas(aristas, p0, n)
        P = np.ascontiguousarray(malla.V @ self.R.T)
        mn, mx = P[:, :2].min(axis=0), P[:, :2].max(axis=0)
        self.bbox = (mn, mx)
        tam = float(max(mx - mn))
        if res is None:
            res = max(0.025, tam / 4200.0)
        self.res = res
        margen = 3 * res
        x0, y0 = mn[0] - margen, mn[1] - margen
        W = int((mx[0] - x0 + margen) / res) + 2
        H = int((mx[1] - y0 + margen) / res) + 2
        zb, ib, sb = _zbuffer(P, malla.F, res, x0, y0, W, H)
        # se guardan para ubicar puntos visibles de cada pieza (globos de los ensambles)
        self.ib, self.x0, self.y0, self.W, self.H = ib, x0, y0, W, H
        if len(lazos3d):
            L2 = np.ascontiguousarray((lazos3d @ self.R.T)[:, :, :2])
            zcap = float((lazos3d[0, 0] @ self.R.T)[2])
            _rellenar_tapa(zb, ib, L2, zcap, res, x0, y0, W, H)
        # 1) aristas B-Rep (no tangentes, salvo que se pidan)
        S, TA, FA = [], [], []
        for a in aristas:
            if a['suave'] and not tangentes:
                continue
            pts = a['pts'] @ self.R.T
            if len(pts) < 2:
                continue
            seg = np.stack([pts[:-1], pts[1:]], axis=1)
            S.append(seg)
            TA.append(np.full((len(seg), 2), -1, np.int64))
            f = a['f'] + [-1, -1]
            FA.append(np.tile(np.array(f[:2], np.int64), (len(seg), 1)))
        # 2) siluetas de la malla (aristas interiores con cambio de signo de nz)
        nz = malla.N @ self.R[2]
        EF = malla.EF
        interior = EF[:, 1] >= 0
        sil = np.zeros(len(EF), bool)
        f0, f1 = EF[interior, 0], EF[interior, 1]
        cambio = (nz[f0] >= 0) != (nz[f1] >= 0)     # facetas con nz=0 cuentan como frontales
        # descarta slivers invertidos por el cosido de vértices y pares casi opuestos
        validos = (malla.area[f0] > 2e-3) & (malla.area[f1] > 2e-3)
        cosd = np.einsum('ij,ij->i', malla.N[f0], malla.N[f1])
        sil[interior] = cambio & validos & (cosd > -0.7)
        Es = malla.E[sil]
        if len(Es):
            S.append(np.stack([P[Es[:, 0]], P[Es[:, 1]]], axis=1))
            TA.append(EF[sil])
            FA.append(np.stack([malla.FI[EF[sil, 0]], malla.FI[EF[sil, 1]]], axis=1))
        # 3) lazos del corte (siempre visibles, se dibujan aparte)
        self.lazos = []
        if len(lazos3d):
            L2 = lazos3d @ self.R.T
            # tolerancia amplia: las mallas por cara no están cosidas y dejan huecos de ~0.05 mm
            self.lazos = cerrar_lazos(encadenar(L2[:, :, :2], tol=0.08))
        if not S:
            self.visibles, self.ocultas = [], []
            return
        S = np.ascontiguousarray(np.vstack(S))
        TA = np.ascontiguousarray(np.vstack(TA))
        FA = np.ascontiguousarray(np.vstack(FA))
        tope = max(len(S) * 6, 10)
        se = np.zeros(tope, np.int64); t0 = np.zeros(tope); t1 = np.zeros(tope); sv = np.zeros(tope, np.int8)
        n = _muestrear(S, TA, FA, malla.FI, zb, ib, sb, res, x0, y0, W, H, 1.5 * res, se, t0, t1, sv)
        se, t0, t1, sv = se[:n], t0[:n], t1[:n], sv[:n]
        A = S[se, 0, :2]
        B = S[se, 1, :2]
        S0 = A + t0[:, None] * (B - A)
        S1 = A + t1[:, None] * (B - A)
        segs = np.stack([S0, S1], axis=1)
        largo = np.linalg.norm(S1 - S0, axis=1) > 1e-4
        self.visibles = encadenar(fusionar_colineales(segs[(sv == 1) & largo]))
        self.ocultas = encadenar(fusionar_colineales(segs[(sv == 0) & largo])) if ocultas else []

    def proyectar(self, p):
        """Punto 3D del modelo -> 2D de la vista (mm)."""
        return (self.R @ np.asarray(p, float))[:2]
