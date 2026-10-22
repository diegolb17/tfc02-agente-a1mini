# -*- coding: utf-8 -*-
"""Calculos del 20 de octubre de 2026: el modelo corregido para la impresion (Fusion v98, 19 oct) cambia la masa de las
piezas propias, el soporte de la camara (175 mm, placa de 10 mm, tornillos a ambos lados del tubo) y la posicion de la
camara y de la lampara. Este guion rehace con el modelo exportado (PLANOS/_geom):
  1. masas y volumenes de las 19 piezas (Tabla F1) y centro de masa de las piezas propias y del conjunto;
  2. estabilidad del conjunto sobre la mesa (seccion 5 de calculos_15oct.py, mismas ecuaciones, masa y centro nuevos);
  3. frecuencia propia del soporte de la camara con la flexion de la placa de anclaje (E.4);
  4. emplazamiento de la camara: altura, distancia, oblicuidad, visuales libres, reflejo especular y giro de rotulas (E.8);
  5. iluminancia sobre la placa con el dicroico en su posicion nueva (E.9).
Escribe _conversion/calculos_20oct.json."""
import json
import math
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
PLANOS = os.path.normpath(os.path.join(AQUI, '..', '..', 'PLANOS'))
sys.path.insert(0, PLANOS)
os.chdir(PLANOS)
from motor.malla import leer_tri          # noqa: E402
from geometria import vision, LUMENES, E_MIN, SIGMA   # noqa: E402
from _rayos import cortes                  # noqa: E402

R = {}
g = 9.81
PIEZAS = ['Cuna_frontal_derecha', 'Cuna_frontal_izquierda', 'Cuna_posterior_derecha', 'Cuna_posterior_izquierda',
          'Bandeja_frontal_derecha', 'Bandeja_frontal_izquierda', 'Bandeja_posterior_derecha', 'Bandeja_posterior_izquierda',
          'Soporte_ventilador', 'Ducto_cuchilla', 'Rejilla_frontal_derecha', 'Rejilla_frontal_izquierda',
          'Soporte_actuador', 'Tapa_actuador', 'Soporte_camara', 'Horquilla_camara', 'Carcasa_ESP32CAM',
          'Horquilla_lampara', 'Aro_lampara']


def js(n):
    return json.load(open(os.path.join(PLANOS, '_geom', n + '.json'), encoding='utf-8'))


def T(n):
    M = np.array(js(n)['transform_cm_filas'], float)
    return M[:3, :3], M[:3, 3] * 10


def centroide_volumen(n):
    """Centroide del solido cerrado (teorema de la divergencia sobre la malla), en coordenadas del ensamble."""
    V, F, _ = leer_tri(os.path.join(PLANOS, '_geom', n + '.tri'))
    Rm, t = T(n)
    W = V @ Rm.T + t
    a, b, c = W[F[:, 0]], W[F[:, 1]], W[F[:, 2]]
    v6 = np.einsum('ij,ij->i', a, np.cross(b, c))
    vol = v6.sum() / 6
    cen = ((a + b + c) * v6[:, None]).sum(axis=0) / (24 * vol)
    return abs(vol) / 1000, cen


# ------------------------------------------------------------------------------- 1. masas y centro de masa
filas, mt, vt, mom = [], 0.0, 0.0, np.zeros(3)
for n in PIEZAS:
    j = js(n)
    vol_malla, cen = centroide_volumen(n)
    filas.append((n, j['volumen_cm3'], j['masa_g'], round(vol_malla, 2)))
    mt += j['masa_g']
    vt += j['volumen_cm3']
    mom += j['masa_g'] * cen
cg = mom / mt
z_mesa = min(np.min((leer_tri(os.path.join(PLANOS, '_geom', n + '.tri'))[0] @ T(n)[0].T + T(n)[1])[:, 2])
             for n in PIEZAS if n.startswith('Bandeja'))
m_eq = 5.50
cg_eq = np.array([167.1, 225.5, 227.6])            # sobre la mesa; el mismo supuesto del 15 oct (centroide de la envolvente)
cg_prop = np.array([cg[0], cg[1], cg[2] - z_mesa])
m_c = mt / 1000 + m_eq
cg_c = (mt / 1000 * cg_prop + m_eq * cg_eq) / m_c
comerciales = 0.21 + 0.25 + 0.04
R['masas'] = {'filas': filas, 'total_g': round(mt, 1), 'vol_total_cm3': round(vt, 2), 'z_mesa': round(z_mesa, 2),
              'cg_propias_mm': [round(x, 1) for x in cg_prop], 'm_conjunto': round(m_c, 2),
              'cg_conjunto_mm': [round(x, 1) for x in cg_c], 'con_comerciales': round(m_c + comerciales, 2),
              'margen_10kg': round(10 - m_c - comerciales, 2)}

# ------------------------------------------------------------- 2. conjunto sobre la mesa (caso C, seccion 5 del 15 oct)
alfa = math.radians(20.0)
m_cama, a_cama = 1.53, 10.0
x_cg, y_cg = cg_c[0], cg_c[1]
dx_c = m_cama / m_c * 84.6
brazo_A = 324.2 - (x_cg + dx_c)
brazo_B = 340.0 - y_cg
MvA = m_cama * a_cama * 0.2498
MvB = 0.50 * a_cama * 0.4189
MrA = m_c * g * brazo_A / 1000
MrB = m_c * g * brazo_B / 1000
uC = MvA / MrA + MvB / MrB
W_c = m_c * g
k_c = 84.6 / m_c / 1000
d0_c = (324.2 - x_cg) / 1000
m_crit = W_c * d0_c / (W_c * k_c + a_cama * 0.2498)
a_crit = W_c * (d0_c - m_cama * k_c) / (m_cama * 0.2498)
Fh, Fv, Fcab = m_cama * a_cama, m_cama * a_cama * math.sin(alfa), 0.50 * a_cama
desl = {str(mu): {'solo': round(mu * (W_c - Fv) / Fh, 2), 'combinado': round(mu * (W_c - Fv) / math.hypot(Fh, Fcab), 2)}
        for mu in (0.30, 0.80)}
R['conjunto'] = {'m': round(m_c, 2), 'W': round(W_c, 2), 'dx_mm': round(dx_c, 1), 'brazo_A': round(brazo_A, 1),
                 'brazo_B': round(brazo_B, 1),
                 'A': {'Mv': round(MvA, 3), 'Mr': round(MrA, 3), 'FS': round(MrA / MvA, 2)},
                 'B': {'Mv': round(MvB, 3), 'Mr': round(MrB, 3), 'FS': round(MrB / MvB, 2)},
                 'C': {'uA': round(MvA / MrA, 3), 'uB': round(MvB / MrB, 3), 'u': round(uC, 3), 'FS': round(1 / uC, 2)},
                 'k_mm_kg': round(k_c * 1000, 3), 'd0_mm': round(d0_c * 1000, 1), 'm_crit': round(m_crit, 2),
                 'a_crit_mm_s2': round(a_crit * 1000, -1), 'deslizamiento': desl, 'Fv': round(Fv, 2), 'Fh': round(Fh, 2)}

# ------------------------------------------------------------------- 3. soporte de la camara (E.4, DM-03 resuelto)
E_pla = 3.5e9
L = 0.165                                           # voladizo libre: de la cara de la placa (z = 10) al extremo (z = 175)
I_t = math.pi / 64 * (0.040 ** 4 - 0.034 ** 4)
k_t = 3 * E_pla * I_t / L ** 3
m_tubo = math.pi / 4 * (0.040 ** 2 - 0.034 ** 2) * L * 1240        # kg
m_punta = (29.4 + 12.2 + 53.9 + 9.8) / 1000
m_ef = m_punta + 33 / 140 * m_tubo
f_rig = math.sqrt(k_t / m_ef) / (2 * math.pi)
t_pl = 0.010


def raiz(b, a):
    """Franja de placa empotrada en las dos lineas de tornillos (a cada lado del tubo, a la distancia a) con el momento
    del tubo en el centro: viga biempotrada de luz 2a, k_theta = 16 E I / (2 a) = 8 E I / a."""
    kth = 8 * E_pla * (b * t_pl ** 3 / 12) / a
    k_r = kth / L ** 2
    k = 1 / (1 / k_t + 1 / k_r)
    return kth, k_r, k, math.sqrt(k / m_ef) / (2 * math.pi)


dirs = {'flexion hacia X (tornillos a 17 mm, ancho 100 mm)': raiz(0.100, 0.017),
        'flexion hacia Y (tornillos a 35 mm, ancho 60 mm)': raiz(0.060, 0.035)}
peor = min(dirs.values(), key=lambda r: r[3])
F_p = m_punta * g
M_r = F_p * L
flecha = F_p / peor[2]
giro = F_p * L ** 2 / (2 * E_pla * I_t) + M_r / peor[0]
sigma = M_r * 0.020 / I_t
sens = {dm: round(math.sqrt(peor[2] / (m_ef + dm / 1000)) / (2 * math.pi), 1) for dm in (50, 100)}
R['soporte_camara'] = {'L_mm': L * 1000, 'I_mm4': round(I_t * 1e12, 0), 'k_tubo': round(k_t, 0), 'm_tubo_g': round(m_tubo * 1000, 1),
                       'm_punta_g': round(m_punta * 1000, 1), 'm_ef_kg': round(m_ef, 3), 'f_rigida': round(f_rig, 1),
                       'direcciones': {k: {'k_theta': round(v[0], 0), 'k_raiz': round(v[1], 0), 'k': round(v[2], 0),
                                           'f': round(v[3], 1)} for k, v in dirs.items()},
                       'f_peor': round(peor[3], 1), 'sensibilidad_masa': sens, 'flecha_mm': round(flecha * 1000, 4),
                       'giro_rad': giro, 'sigma_MPa': round(sigma / 1e6, 3), 'F_punta_N': round(F_p, 3)}

# ---------------------------------------------------------------------------------- 4. camara (E.8)
G = vision()
C, n, u, v, lente = G['centro_placa'], G['normal'], G['u'], G['v'], G['lente']
eje = (C - lente) / np.linalg.norm(C - lente)
puntos = {'centro': C}
for su in (-1, 1):
    for sv in (-1, 1):
        puntos['esquina (%+d, %+d)' % (su, sv)] = C + 90 * su * u + 90 * sv * v
cuerpos = PIEZAS + ['Equipo_A1mini']
vis = {}
for nom, P in puntos.items():
    d = P - lente
    L_v = np.linalg.norm(d)
    o = lente + 0.5 * d / L_v
    tapan = []
    for b in cuerpos:
        ts = cortes(b, o, d)
        ts = ts[ts < L_v - 1.0]                     # la placa misma (t = L) no cuenta
        if len(ts):
            tapan.append(b)
    obl = math.degrees(math.acos(abs((d / L_v) @ n)))
    vis[nom] = {'distancia': round(L_v, 1), 'oblicuidad': round(obl, 1),
                'angulo_al_eje': round(math.degrees(math.acos((d / L_v) @ eje)), 1), 'obstruida_por': tapan}
# punto de reflexion especular del aro hacia el objetivo
aro = G['aro']
aro_esp = aro - 2 * ((aro - C) @ n) * n
dd = aro_esp - lente
tt = ((C - lente) @ n) / (dd @ n)
Pr = lente + tt * dd
r_u, r_v = (Pr - C) @ u, (Pr - C) @ v
Rc, _ = T('Carcasa_ESP32CAM')
Ra, _ = T('Aro_lampara')
giro_cam = math.degrees(math.acos(np.clip((Rc @ np.array([0, 0, 1.0])) @ G['eje_tubo'], -1, 1)))
giro_aro = math.degrees(math.acos(np.clip((Ra @ np.array([0, 0, 1.0])) @ G['eje_tubo'], -1, 1)))
R['camara'] = {'h_lente': round(G['h_lente'], 1), 'd_lente': round(G['d_lente'], 1), 'oblicuidad': round(G['oblicuidad'], 1),
               'campo_necesario': round(G['campo_necesario'], 1), 'mm_por_px': round(G['mm_por_pixel'], 3),
               'px_cordon': round(G['pix_cordon'], 2), 'visuales': vis,
               'oblicuidad_max': max(x['oblicuidad'] for x in vis.values()),
               'reflejo_mm': [round(r_u, 1), round(r_v, 1)], 'reflejo_dentro_placa': bool(abs(r_u) <= 90 and abs(r_v) <= 90),
               'reflejo_dist_centro': round(float(np.hypot(r_u, r_v)), 1),
               'giro_rotula_camara': round(giro_cam, 1), 'giro_rotula_aro': round(giro_aro, 1),
               'aro_fuera_eje': round(G['aro_fuera_eje'], 1), 'diag_placa': round(math.hypot(180, 180), 1),
               'dist_min_65': round(math.hypot(180, 180) / 2 / math.tan(math.radians(32.5)), 0),
               'dist_min_120': round(math.hypot(180, 180) / 2 / math.tan(math.radians(60)), 0)}

# ---------------------------------------------------------------------------------- 5. iluminacion (E.9)
pts = G['malla_ilum']


def pc(su, sv):
    p = [q for q in pts if abs(q[0] - su) < 1e-9 and abs(q[1] - sv) < 1e-9][0]
    return {'d': round(p[2], 1), 'psi': round(p[3], 1), 'inc': round(p[4], 1), 'lx_lm': round(p[5], 2),
            'lx': round(p[5] * LUMENES, 0)}


peor_i = G['peor']
R['iluminacion'] = {'h_aro': round(G['h_aro'], 1), 'd_aro': round(G['d_aro'], 1), 'haz_vs_centro': round(G['haz_vs_centro'], 1),
                    'depresion': round(G['depresion_aro_placa'], 1), 'I0': round(G['I0'], 0), 'flujo_I0': round(G['flujo_por_I0'], 3),
                    'centro': pc(0, 0), 'esquinas': {'%+d%+d' % (a, b): pc(a, b) for a in (-1, 1) for b in (-1, 1)},
                    'peor': {'su': peor_i[0], 'sv': peor_i[1], 'd': round(peor_i[2], 1), 'psi': round(peor_i[3], 1),
                             'inc': round(peor_i[4], 1), 'lx_lm': round(peor_i[5], 2), 'lx': round(peor_i[5] * LUMENES, 0)},
                    'lm_necesarios': round(E_MIN / peor_i[5], 0), 'lm_con_margen': round(1.5 * E_MIN / peor_i[5], 0),
                    'veces': round(peor_i[5] * LUMENES / E_MIN, 1), 'uniformidad': round(G['uniformidad'], 2)}

json.dump(R, open(os.path.join(AQUI, 'calculos_20oct.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(R, ensure_ascii=False, indent=1, default=float))

# ---------------------------------------------------------------- 6. costo de las consultas con GPT-5.4 mini (6.2)
# Precios por millon de unidades (OpenAI, 2026d): entrada 0.75, entrada repetida (cache) 0.075, salida 4.50 USD.
# Conteo de imagen de la familia GPT-5.4 (OpenAI, 2026a): parches de 32 x 32 px por 1.2.
def unidades_imagen(w, h):
    return math.ceil(math.ceil(w / 32) * math.ceil(h / 32) * 1.2)


# sin descuento por repeticion: la cache del proveedor dura minutos y la supervision consulta cada 10 min
P_IN, P_CACHE, P_OUT = 0.75e-6, 0.75e-6, 4.50e-6
img_sup = unidades_imagen(800, 600)        # captura de supervision reducida
img_ver = unidades_imagen(1600, 1200)      # captura de verificacion completa
texto_fijo, texto_var = 500, 200           # instruccion de sistema (repetida) y estado del trabajo
# supervision: captura reducida + previsualizacion reducida (repetida en todo el trabajo); salida 150
sup = (img_sup + texto_var) * P_IN + (img_sup + texto_fijo) * P_CACHE + 150 * P_OUT
# verificacion: captura completa + referencia completa (repetida); salida 100
ver = (img_ver + texto_var) * P_IN + (img_ver + texto_fijo) * P_CACHE + 100 * P_OUT
# mensajes libres del operador: 10 al dia, 1 500 unidades de entrada y 200 de salida
msg = (1000 + texto_var) * P_IN + texto_fijo * P_CACHE + 200 * P_OUT
n_sup, n_ver, impresiones, mensajes = 12, 2, 180, 300
por_impresion = n_sup * sup + n_ver * ver
mes = impresiones * por_impresion + mensajes * msg
TC = 3.436                  # venta SBS del 20 oct 2026 (_precios_20oct.md)
R['opex_llm'] = {'img_sup': img_sup, 'img_ver': img_ver, 'sup_usd': round(sup, 5), 'ver_usd': round(ver, 5), 'msg_usd': round(msg, 5),
                 'por_impresion_usd': round(por_impresion, 4), 'mes_usd': round(mes, 2), 'mes_soles': round(mes * TC, 2),
                 'impresiones_usd': round(impresiones * por_impresion, 2), 'mensajes_usd': round(mensajes * msg, 2),
                 'todo_alta_usd_mes': round(impresiones * (n_sup + n_ver) * ver + mensajes * msg, 2)}
R['opex_llm']['todo_alta_soles_mes'] = round(R['opex_llm']['todo_alta_usd_mes'] * TC, 2)
energia = 2.67          # 21 oct 2026: extractor de 30 mm (0.05 A), reposo 8.40 W, 3.74 kWh al mes
R['opex_llm']['subtotal_soles'] = round(energia + R['opex_llm']['mes_soles'], 2)
json.dump(R, open(os.path.join(AQUI, 'calculos_20oct.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(R['opex_llm'], indent=1))
