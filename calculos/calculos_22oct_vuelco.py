# -*- coding: utf-8 -*-
"""Memoria de calculo de la retencion y el vuelco de la impresora en la cavidad inclinada (22 oct 2026).

Responde a Denis Pena (reunion del 22 oct): el analisis se ordena en cuatro situaciones, cada una con su
objetivo, ecuacion, datos y resultado:
  1. Rozamiento: si hace falta una pared de retencion.
  2. Vuelco estatico: altura minima de pared con la impresora detenida.
  3. Vuelco dinamico: altura minima con la inercia de la plataforma (eje longitudinal) y del cabezal
     (eje transversal).
  4. Corte y flexion de la pared: que la pared de 5 mm no se rompa.
Ademas fija la ventana del angulo de inclinacion: minimo por deslizamiento de la pieza y maximo por vuelco.
Los datos son los mismos de calculos_15oct.py (Anexo F); aqui solo se reordenan y se completan.
"""
import json
import math
import os

G = 9.81
# Datos (Tabla E26, Anexo F)
m_imp = 6.72          # kg, equipo y un rollo
W = m_imp * G         # N
alfa = 20.0           # grados
e_G = 215.6           # mm, altura del centro de masa sobre el piso de la cavidad (hipotesis desfavorable)
d_cen = 157.5         # mm, G a la cara frontal sobre la pendiente, plataforma centrada
d_baja = 137.0        # mm, plataforma en su posicion mas baja (adelanta G 20.5 mm)
d_alta = 178.0        # mm
e_p = 90.12           # mm, plano de la plataforma
m_p = 1.53            # kg, masa movil de la plataforma (cota superior)
a = 10.0              # m/s2, aceleracion maxima del equipo
F_i = m_p * a         # N
h = 5.0               # mm, pared adoptada
t = 4.0               # mm, espesor de la pared
b = 195.0             # mm, ancho de contacto (ancho del cuerpo base)
sy = 49.9             # MPa, fluencia del PLA (Tabla E27)
m_cab = 0.50          # kg, masa movil del cabezal (estimada, como en F.5)
z_cab = e_p + 180.0   # mm, cabezal en su posicion mas alta sobre la base
FS_din_min = 1.2      # criterio para cargas laterales transitorias, por analogia con E.030 (2026), art. 64.2
mu_pla = (0.12, 0.38) # rozamiento estatico del PLA impreso, Santana, Alves y Netto (2021)

r = math.radians(alfa)


def fs_vuelco(d, h_, din, alfa_g=alfa):
    ra = math.radians(alfa_g)
    Mr = W * math.cos(ra) * d / 1000
    Mv = W * math.sin(ra) * (e_G - h_) / 1000 + (F_i * (e_p - h_) / 1000 if din else 0.0)
    return Mr, Mv, Mr / Mv


def h_min(d, din, fs_obj):
    # FS = Mr / Mv(h) es creciente en h; se despeja h para FS = fs_obj
    Mr = W * math.cos(r) * d / 1000
    A = W * math.sin(r) * e_G / 1000 + (F_i * e_p / 1000 if din else 0.0)
    B = W * math.sin(r) / 1000 + (F_i / 1000 if din else 0.0)
    return (A - Mr / fs_obj) / B    # mm


def alfa_max(fs_obj, d=d_baja):
    lo, hi = 1.0, 60.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if fs_vuelco(d, h, True, mid)[2] > fs_obj:
            lo = mid
        else:
            hi = mid
    return lo


res = {}
# 1. Rozamiento
res['tan_alfa'] = math.tan(r)
res['mu_necesario_estatico'] = math.tan(r)
T = W * math.sin(r) + F_i
N = W * math.cos(r)
res['W'] = W
res['W_sen'] = W * math.sin(r)
res['W_cos'] = N
res['F_i'] = F_i
res['T'] = T
res['mu_necesario_dinamico'] = T / N
res['alfa_lim_mu_min'] = math.degrees(math.atan(mu_pla[0]))
res['alfa_lim_mu_max'] = math.degrees(math.atan(mu_pla[1]))
# 2. Vuelco estatico
for nombre, d in (('cen', d_cen), ('baja', d_baja)):
    Mr, Mv, fs = fs_vuelco(d, h, False)
    res['est_' + nombre] = {'Mr': Mr, 'Mv': Mv, 'FS': fs, 'FS_h0': fs_vuelco(d, 0, False)[2]}
res['h_min_est_FS1'] = h_min(d_baja, False, 1.0)
# 3. Vuelco dinamico
for nombre, d in (('alta', d_alta), ('baja', d_baja)):
    Mr, Mv, fs = fs_vuelco(d, h, True)
    res['din_' + nombre] = {'Mr': Mr, 'Mv': Mv, 'FS': fs}
res['din_baja_h0'] = fs_vuelco(d_baja, 0, True)[2]
res['h_min_din_FS1'] = h_min(d_baja, True, 1.0)
res['h_min_din_FS12'] = h_min(d_baja, True, FS_din_min)
res['h_para_FS15'] = h_min(d_baja, True, 1.5)
res['barrido_h'] = {hh: round(fs_vuelco(d_baja, hh, True)[2], 2) for hh in (0, 2, 5, 8, 10)}
res['barrido_alfa'] = {aa: round(fs_vuelco(d_baja, h, True, aa)[2], 2) for aa in (10, 15, 20, 25, 30)}
res['alfa_max_FS12'] = alfa_max(FS_din_min)
res['alfa_max_FS1'] = alfa_max(1.0)
# Vuelco transversal por el cabezal (eje X), G supuesto centrado en el ancho del cuerpo base
F_cab = m_cab * a
Mr_lat = W * math.cos(r) * (b / 2) / 1000
Mv_lat = F_cab * z_cab / 1000
res['lat'] = {'F_cab': F_cab, 'z_cab': z_cab, 'Mr': Mr_lat, 'Mv': Mv_lat, 'FS': Mr_lat / Mv_lat}
# 4. Pared de retencion
tau = T / (b * t)
sigma = 6 * (T / b) * h / t ** 2
res['pared'] = {'tau': tau, 'sigma': sigma, 'tau_adm': sy / 2, 'FS_corte': (sy / 2) / tau, 'FS_flexion': sy / sigma}
# Ventana del angulo
res['ventana'] = {'alfa_min_mu038': res['alfa_lim_mu_max'], 'mu_cubierto_20': math.tan(r),
                  'alfa_max_FS12': res['alfa_max_FS12'], 'alfa_max_FS1': res['alfa_max_FS1']}

if __name__ == '__main__':
    for k, v in res.items():
        print(k, v)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calculos_22oct_vuelco.json')
    json.dump(res, open(out, 'w', encoding='utf-8'), indent=1, default=str)
