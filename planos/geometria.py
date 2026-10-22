# -*- coding: utf-8 -*-
"""Medidas del modulo de vision e iluminacion leidas del modelo exportado (_geom), para que las figuras, las laminas
y los apartados E.8 y E.9 usen las mismas cifras. Uso directo: python geometria.py (imprime el resumen)."""
import json
import os

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
LUMENES = 480.0                  # Dixon Lighting TOP6WGU5.312VLF
SIGMA = 25.5                     # haz gaussiano que cae a la mitad a 30 grados del eje (haz de 60)
E_MIN = 432.0                    # iluminancia exigida (E.9, ISO 2720)
CAMPO_OBJETIVO = 120.0           # objetivo angular del ESP32-CAM
PIX_ANCHO = 1600                 # UXGA


def _T(n):
    j = json.load(open(os.path.join(AQUI, '_geom', n + '.json'), encoding='utf-8'))
    M = np.array(j['transform_cm_filas'], float)
    return M[:3, :3], M[:3, 3] * 10


def _flujo_por_I0():
    """Flujo del haz gaussiano por candela en el eje, integrado sobre el hemisferio."""
    psi = np.radians(np.linspace(0, 90, 9001))
    s = np.radians(SIGMA)
    return np.trapezoid(np.exp(-psi ** 2 / (2 * s ** 2)) * 2 * np.pi * np.sin(psi), psi)


def vision():
    Re, te = _T('Equipo_A1mini')
    C = Re @ np.array([100, 225.5, 87.62]) + te          # centro de la cara superior de la plataforma
    n = Re @ np.array([0, 0, 1.0])
    u, v = Re @ np.array([1.0, 0, 0]), Re @ np.array([0, 1.0, 0])
    Rc, tc = _T('Carcasa_ESP32CAM')
    lente = Rc @ np.array([14.0, 0, 37.25]) + tc          # cara frontal del agujero del objetivo
    Ra, ta = _T('Aro_lampara')
    aro = Ra @ np.array([0, 0, 44.0]) + ta
    haz = Ra @ np.array([1.0, 0, 0])
    Rs, ts = _T('Soporte_camara')
    base, eje = ts.copy(), Rs @ np.array([0, 0, 1.0])
    d = C - lente
    h = float(-(d @ n))
    eje_opt = d / np.linalg.norm(d)
    esquinas = [C + 90 * su * u + 90 * sv * v for su in (-1, 1) for sv in (-1, 1)]
    campo = 2 * max(np.degrees(np.arccos(((P - lente) / np.linalg.norm(P - lente)) @ eje_opt)) for P in esquinas)
    w = (aro - lente) / np.linalg.norm(aro - lente)
    da = C - aro
    res = {
        'centro_placa': C, 'normal': n, 'u': u, 'v': v, 'lente': lente, 'aro': aro, 'haz': haz,
        'soporte_base': base, 'eje_tubo': eje,
        'h_lente': h, 'd_lente': float(np.linalg.norm(d)), 'oblicuidad': float(np.degrees(np.arccos(h / np.linalg.norm(d)))),
        'campo_necesario': float(campo),
        'h_aro': float(-(da @ n)), 'd_aro': float(np.linalg.norm(da)),
        'aro_fuera_eje': float(np.degrees(np.arccos(w @ eje_opt))),
        'haz_vs_centro': float(np.degrees(np.arccos(haz @ (da / np.linalg.norm(da))))),
        'depresion_aro_placa': float(np.degrees(np.arcsin(-(haz @ n)))),
    }
    # resolucion: ancho cubierto a la distancia del centro con el objetivo de 120 grados
    res['mm_por_pixel'] = 2 * res['d_lente'] * np.tan(np.radians(CAMPO_OBJETIVO / 2)) / PIX_ANCHO
    res['pix_cordon'] = 0.4 / res['mm_por_pixel']
    # fotometria sobre una malla de la placa
    I0 = LUMENES / _flujo_por_I0()
    res['I0'] = I0
    res['flujo_por_I0'] = _flujo_por_I0()
    pts = []
    for su in np.linspace(-1, 1, 37):
        for sv in np.linspace(-1, 1, 37):
            P = C + 90 * su * u + 90 * sv * v
            r = P - aro
            dist = np.linalg.norm(r)
            rh = r / dist
            psi = np.degrees(np.arccos(np.clip(rh @ haz, -1, 1)))
            inc = np.degrees(np.arccos(abs(rh @ n)))
            lx_lm = np.exp(-np.radians(psi) ** 2 / (2 * np.radians(SIGMA) ** 2)) / res['flujo_por_I0'] * np.cos(np.radians(inc)) / (dist / 1000) ** 2
            pts.append((su, sv, dist, psi, inc, lx_lm))
    pts = np.array(pts)
    res['malla_ilum'] = pts
    k = int(np.argmin(pts[:, 5]))
    res['peor'] = pts[k]
    res['mejor'] = pts[int(np.argmax(pts[:, 5]))]
    res['uniformidad'] = float(pts[:, 5].min() / pts[:, 5].max())
    return res


def punto_control(G, su, sv):
    for p in G['malla_ilum']:
        if abs(p[0] - su) < 1e-9 and abs(p[1] - sv) < 1e-9:
            return p
    return None


if __name__ == '__main__':
    G = vision()
    print('lente %s; placa %s' % (G['lente'].round(1), G['centro_placa'].round(1)))
    print('objetivo: %.1f mm sobre la placa, %.1f al centro, oblicuidad %.1f; campo necesario %.1f' % (
        G['h_lente'], G['d_lente'], G['oblicuidad'], G['campo_necesario']))
    print('resolucion %.3f mm/px; cordon de 0.4 = %.2f px' % (G['mm_por_pixel'], G['pix_cordon']))
    print('aro: %.1f mm sobre la placa, %.1f al centro; haz a %.1f grados del centro; depresion respecto de la placa %.1f;'
          ' fuera del eje optico %.1f' % (G['h_aro'], G['d_aro'], G['haz_vs_centro'], G['depresion_aro_placa'], G['aro_fuera_eje']))
    print('I0 %.0f cd (flujo = %.3f I0)' % (G['I0'], G['flujo_por_I0']))
    nombres = {(0, 0): 'centro', (-1, -1): 'esq --', (-1, 1): 'esq -+', (1, -1): 'esq +-', (1, 1): 'esq ++'}
    for (su, sv), nom in nombres.items():
        p = punto_control(G, su, sv)
        print('  %-7s d %.1f psi %.1f inc %.1f  lx/lm %.2f  lx %.0f' % (nom, p[2], p[3], p[4], p[5], p[5] * LUMENES))
    p = G['peor']
    print('peor punto (%.2f, %.2f): d %.1f psi %.1f inc %.1f lx/lm %.2f -> %.0f lx (%.1f veces %d); lm necesarios %.0f' % (
        p[0], p[1], p[2], p[3], p[4], p[5], p[5] * LUMENES, p[5] * LUMENES / E_MIN, E_MIN, E_MIN / p[5]))
    print('uniformidad %.2f' % G['uniformidad'])
