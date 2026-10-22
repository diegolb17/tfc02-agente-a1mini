# -*- coding: utf-8 -*-
"""Carga de la geometría exportada desde Fusion (mm, coordenadas locales de la pieza).

  Malla: V (n,3), F (m,3), FI (m) id de cara B-Rep, N (m,3), aristas E/EF.
  Aristas B-Rep: lista de dict {pts (k,3), f (2 caras), suave}.
"""
import os
import json
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
GEOM = os.path.normpath(os.path.join(AQUI, '..', '_geom'))


def leer_tri(ruta):
    with open(ruta, 'rb') as f:
        n = int(np.frombuffer(f.read(4), '<i4')[0])
        tri = np.frombuffer(f.read(n * 36), '<f4').reshape(n, 3, 3).astype(np.float64)
        fid = np.frombuffer(f.read(n * 4), '<i4').astype(np.int64)
    pts = tri.reshape(-1, 3)
    clave = np.round(pts, 3)
    V, inv = np.unique(clave, axis=0, return_inverse=True)
    F = inv.ravel().reshape(-1, 3)
    ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    return V, F[ok], fid[ok]


class Malla:
    def __init__(self, V, F, FI=None):
        self.V = np.ascontiguousarray(V, dtype=np.float64)
        self.F = np.ascontiguousarray(F, dtype=np.int64)
        self.FI = np.zeros(len(F), np.int64) if FI is None else np.ascontiguousarray(FI, dtype=np.int64)
        self._topologia()

    def _topologia(self):
        V, F = self.V, self.F
        e1 = V[F[:, 1]] - V[F[:, 0]]
        e2 = V[F[:, 2]] - V[F[:, 0]]
        n = np.cross(e1, e2)
        lon = np.linalg.norm(n, axis=1)
        self.area = lon / 2.0
        lon[lon == 0] = 1
        self.N = n / lon[:, None]
        m = len(F)
        E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        caras = np.tile(np.arange(m), 3)
        Es = np.sort(E, axis=1)
        uniq, inv = np.unique(Es, axis=0, return_inverse=True)
        inv = inv.ravel()
        orden = np.argsort(inv, kind='stable')
        inv_o = inv[orden]
        caras_o = caras[orden]
        primera = np.searchsorted(inv_o, np.arange(len(uniq)))
        pos = np.arange(len(inv_o)) - primera[inv_o]
        EF = np.full((len(uniq), 2), -1, dtype=np.int64)
        sel0 = pos == 0
        sel1 = pos == 1
        EF[inv_o[sel0], 0] = caras_o[sel0]
        EF[inv_o[sel1], 1] = caras_o[sel1]
        self.E = np.ascontiguousarray(uniq, dtype=np.int64)
        self.EF = EF

    @property
    def bbox(self):
        return self.V.min(axis=0), self.V.max(axis=0)

    def transformada(self, R, t=None):
        V = self.V @ np.asarray(R, float).T
        if t is not None:
            V = V + np.asarray(t, float)
        return Malla(V, self.F, self.FI)

    @staticmethod
    def unir(mallas):
        Vs, Fs, Is, base, cbase = [], [], [], 0, 0
        for m in mallas:
            Vs.append(m.V)
            Fs.append(m.F + base)
            Is.append(m.FI + cbase)
            base += len(m.V)
            cbase += int(m.FI.max()) + 1 if len(m.FI) else 0
        return Malla(np.vstack(Vs), np.vstack(Fs), np.concatenate(Is))


_cache = {}


def cargar(nombre):
    """Malla de la pieza (coordenadas locales, mm)."""
    if nombre not in _cache:
        V, F, FI = leer_tri(os.path.join(GEOM, nombre + '.tri'))
        _cache[nombre] = Malla(V, F, FI)
    return _cache[nombre]


def aristas(nombre):
    """Aristas B-Rep: lista de dict con pts (np.array k,3), f (lista de caras) y suave."""
    with open(os.path.join(GEOM, nombre + '.edges.json'), encoding='utf-8') as f:
        datos = json.load(f)
    for a in datos:
        a['pts'] = np.asarray(a['pts'], float)
    return datos


def aristas_transformadas(lista, R, t=None, desplazar_caras=0):
    R = np.asarray(R, float)
    out = []
    for a in lista:
        p = a['pts'] @ R.T
        if t is not None:
            p = p + np.asarray(t, float)
        out.append({'pts': p, 'f': [c + desplazar_caras for c in a['f']], 'suave': a['suave']})
    return out


def rasgos(nombre):
    with open(os.path.join(GEOM, nombre + '.json'), encoding='utf-8') as f:
        return json.load(f)


def transform_ensamble(nombre):
    """(R 3x3, t mm) que lleva la pieza de coordenadas locales a las del ensamble."""
    d = rasgos(nombre)
    T = np.array(d['transform_cm_filas'], dtype=float)
    return T[:3, :3], T[:3, 3] * 10.0


class Pieza:
    """Malla + aristas B-Rep de una pieza, opcionalmente llevadas a otro sistema."""

    def __init__(self, nombre=None, malla=None, aristas_=None):
        if nombre is not None:
            self.malla = cargar(nombre)
            self.aristas = aristas(nombre)
        else:
            self.malla, self.aristas = malla, aristas_

    def transformada(self, R, t=None):
        return Pieza(malla=self.malla.transformada(R, t), aristas_=aristas_transformadas(self.aristas, R, t))

    def en_ensamble(self, nombre):
        R, t = transform_ensamble(nombre)
        return self.transformada(R, t)

    @staticmethod
    def unir(piezas):
        mallas, ars, cbase = [], [], 0
        for p in piezas:
            mallas.append(p.malla)
            ars.extend(aristas_transformadas(p.aristas, np.eye(3), None, cbase))
            cbase += int(p.malla.FI.max()) + 1
        return Pieza(malla=Malla.unir(mallas), aristas_=ars)
