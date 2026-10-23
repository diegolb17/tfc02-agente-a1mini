# -*- coding: utf-8 -*-
"""Cadena del enfriamiento recalculada el 22 oct 2026 (acta P15 y P16).

Cambios respecto de calculos_15oct.py, seccion 2:
- Propiedades del aire a la temperatura de pelicula, (50 + 25) / 2 = 37.5 grados, interpoladas de la tabla de
  aire a presion atmosferica (Incropera et al., 300 K y 350 K): nu = 1.696e-5 m2/s, k = 0.02709 W/(m K),
  Pr = 0.7055. Antes se usaban nu = 1.60e-5 y k = 0.0271, que no corresponden a una misma temperatura.
- Largo de la transicion del ducto de 74 mm, el del modelo, en lugar de 70.
El resto del modelo (capacidad termica, radiacion, decaimiento del chorro, curvas de los ventiladores) es el mismo.
Escribe calculos_22oct_enfriamiento.json y regenera FIG_enfriamiento_ranura.png, FIG_curva_enfriamiento.png y
FIG_punto_trabajo.png con el mismo formato que calculos_15oct.py.
"""
import json
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.normpath(os.path.join(AQUI, '..', 'Imagenes'))
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
                     'font.size': 10, 'axes.titlesize': 10, 'axes.labelsize': 10, 'legend.fontsize': 9,
                     'xtick.labelsize': 9, 'ytick.labelsize': 9, 'mathtext.fontset': 'stix'})

C_pl, A_pl, L_pl = 294.7, 0.0324, 0.180
T0, Tf, Tinf = 60.0, 40.0, 25.0
lnr = math.log((T0 - Tinf) / (Tf - Tinf))
eps, sigma_sb = 0.90, 5.67e-8
Tm = (T0 + Tf) / 2 + 273.15
Tk = Tinf + 273.15
h_rad = eps * sigma_sb * (Tm ** 2 + Tk ** 2) * (Tm + Tk)
h_nat = 8.0

# propiedades del aire a la temperatura de pelicula
T_pel = ((T0 + Tf) / 2 + Tinf) / 2 + 273.15
fr = (T_pel - 300.0) / 50.0
nu_a = (15.89 + fr * (20.92 - 15.89)) * 1e-6
k_a = (26.3 + fr * (30.0 - 26.3)) * 1e-3
Pr_a = 0.707 + fr * (0.700 - 0.707)
v_ref = 14.5
Re_ref = v_ref * L_pl / nu_a
Nu_ref = 0.664 * Re_ref ** 0.5 * Pr_a ** (1 / 3)
h_ref = Nu_ref * k_a / L_pl


def h_conv(v):
    return h_ref * math.sqrt(max(v, 0) / v_ref)


def t_enfr(h_total, Tfin=Tf):
    tau = C_pl / (h_total * A_pl)
    return tau, tau * math.log((T0 - Tinf) / (Tfin - Tinf))


t_max = 240.0
tau_max = t_max / lnr
h_min = C_pl / (A_pl * tau_max)
hc_min = h_min - h_rad
v_min = v_ref * (hc_min / h_ref) ** 2

rho = 1.18
L_s = 0.149
A_in = math.pi * 0.044 ** 2
z_ent, z_cont, f_fr, L_tr = 0.5, 0.05, 0.03, 0.074


def K_ducto(H):
    A_out = L_s * H
    Dh = 4 * A_out / (2 * (L_s + H))
    zs = 1.0 + z_cont + f_fr * L_tr / Dh
    return rho / 2 * (zs / A_out ** 2 + z_ent / A_in ** 2)


VENT = {'Sunon PMD2409PMB1-A': (177.0, 120.2, 12.2, False),
        'Delta PFB0924EHEP6': (172.0, 103.7, 13.0, True),
        'Delta PFB0924GHEP6': (250.0, 124.1, 15.6, True)}
CFM = 0.000471947


def punto(H, dp_max, V_max_cfm):
    Vm = V_max_cfm * CFM
    K = K_ducto(H)
    V = math.sqrt(dp_max / (K + dp_max / Vm ** 2))
    return V, K * V ** 2, V / (L_s * H)


def factor_decaimiento(H):
    xc = 12.25 * H
    if xc >= L_pl:
        return 1.0
    integ = xc + 3.5 * math.sqrt(H) * 2 * (math.sqrt(L_pl) - math.sqrt(xc))
    return integ / L_pl


R = {'aire': {'T_pelicula_C': round(T_pel - 273.15, 2), 'nu': nu_a, 'k': round(k_a, 5), 'Pr': round(Pr_a, 4),
              'Re_ref': round(Re_ref, 0), 'Nu_ref': round(Nu_ref, 1), 'h_ref': round(h_ref, 2)}}
barrido_H = []
for H_mm in (6, 8, 10, 12.8, 16, 20, 25):
    H = H_mm / 1000
    fila = {'H_mm': H_mm, 'A_mm2': round(L_s * H * 1e6, 1), 'f': round(factor_decaimiento(H), 3)}
    for nombre, (dp, vm, _, _) in VENT.items():
        V, dp_op, v = punto(H, dp, vm)
        v_ef = v * factor_decaimiento(H)
        tau, t = t_enfr(h_conv(v_ef) + h_rad)
        fila[nombre] = {'Q_cfm': round(V / CFM, 1), 'dp': round(dp_op, 0), 'v': round(v, 1), 'v_ef': round(v_ef, 1),
                        't_min': round(t / 60, 2)}
    barrido_H.append(fila)
H_sel = 0.0128
sel = {}
for nombre, (dp, vm, P, pwm) in VENT.items():
    V, dp_op, v = punto(H_sel, dp, vm)
    v_ef = v * factor_decaimiento(H_sel)
    hc = h_conv(v_ef)
    tau, t = t_enfr(hc + h_rad)
    tau38, t38 = t_enfr(hc + h_rad, 38.7)
    sel[nombre] = {'Q_cfm': round(V / CFM, 1), 'Q_m3s': V, 'dp': round(dp_op, 0), 'v': round(v, 1), 'v_ef': round(v_ef, 1),
                   'h_conv': round(hc, 1), 'tau': round(tau, 0), 't_min': round(t / 60, 2), 't38_min': round(t38 / 60, 2),
                   'P_aire_W': round(V * dp_op, 2), 'P_elec_W': P, 'rend': round(V * dp_op / P * 100, 1)}
tau_nat, t_nat = t_enfr(h_nat + h_rad)
tau_nat0, t_nat0 = t_enfr(h_nat)
tau_nat2, t_nat2 = t_enfr(2 * (h_nat + h_rad))
R['enfriamiento'] = {'h_rad': round(h_rad, 2), 'lnr': round(lnr, 4), 't_max_min': t_max / 60, 'tau_max': round(tau_max, 0),
                     'h_min': round(h_min, 2), 'hc_min': round(hc_min, 2), 'v_min': round(v_min, 2),
                     'A_in_mm2': round(A_in * 1e6, 1), 'A_out_mm2': round(L_s * H_sel * 1e6, 1),
                     'contraccion': round(A_in / (L_s * H_sel), 2), 'K_sel': round(K_ducto(H_sel), 0),
                     'f_sel': round(factor_decaimiento(H_sel), 3), 'barrido_H': barrido_H, 'seleccion': sel,
                     'natural': {'solo_conv_min': round(t_nat0 / 60, 1), 'con_rad_min': round(t_nat / 60, 1),
                                 'dos_caras_min': round(t_nat2 / 60, 1), 'tau_con_rad': round(tau_nat, 0)},
                     'Q_min_m3s_H128': round(v_min / factor_decaimiento(H_sel) * L_s * H_sel, 5)}
R['enfriamiento']['Q_min_cfm_H128'] = round(R['enfriamiento']['Q_min_m3s_H128'] / CFM, 1)
with open(os.path.join(AQUI, 'calculos_22oct_enfriamiento.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=1)

# --- figuras, con el mismo formato que calculos_15oct.py
estilos = {'Sunon PMD2409PMB1-A': (':', 'Sunon PMD2409PMB1-A'), 'Delta PFB0924EHEP6': ('--', 'Delta PFB0924EHEP6'),
           'Delta PFB0924GHEP6': ('-', 'Delta PFB0924GHEP6, adoptado')}
fig, ax = plt.subplots(figsize=(6.0, 3.0))
Hs = [x / 2 for x in range(8, 61)]
for nombre, (dp, vm, _, _) in VENT.items():
    ts = []
    for H_mm in Hs:
        H = H_mm / 1000
        V, dpo, v = punto(H, dp, vm)
        ts.append(t_enfr(h_conv(v * factor_decaimiento(H)) + h_rad)[1] / 60)
    ax.plot(Hs, ts, estilos[nombre][0], color='k', lw=1.2, label=estilos[nombre][1])
ax.axhline(t_max / 60, color='0.4', lw=0.8)
ax.text(29.5, t_max / 60 + 0.04, 'tiempo máximo, 4 min', ha='right', va='bottom', fontsize=9)
ax.axvline(12.8, color='0.4', lw=0.8, ls='-.')
ax.text(13.2, 2.35, 'alto adoptado,\n12.8 mm', fontsize=9, va='bottom')
ax.set_xlabel('Alto de la ranura de salida H (mm)')
ax.set_ylabel('Enfriamiento de 60 a 40 °C (min)')
ax.set_xlim(4, 30)
ax.set_ylim(2.3, 4.5)
ax.legend(loc='upper left', frameon=False)
ax.grid(True, color='0.88', lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_enfriamiento_ranura.png'), dpi=300)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.0, 3.1))
ts = [i * 5 for i in range(0, 241)]
hc_sel = sel['Delta PFB0924GHEP6']['h_conv']
for htot, est, lab in ((hc_sel + h_rad, '-', 'con el módulo (convección forzada y radiación)'),
                       (h_nat + h_rad, '--', 'sin el módulo (convección natural y radiación)'),
                       (h_nat, ':', 'sin el módulo, solo convección natural')):
    tau = C_pl / (htot * A_pl)
    ax.plot([t / 60 for t in ts], [Tinf + (T0 - Tinf) * math.exp(-t / tau) for t in ts], est, color='k', lw=1.2, label=lab)
ax.axhspan(40, 60, color='0.92', zorder=0)
ax.axhline(38.7, color='0.4', lw=0.7, ls='-.')
ax.text(11.2, 39.1, 'umbral, 38.7 °C', ha='left', va='bottom', fontsize=9)
ax.text(19.8, 58.2, 'ventana de remoción, 60 a 40 °C', ha='right', va='top', fontsize=9)
ax.set_xlabel('Tiempo desde el fin de la impresión (min)')
ax.set_ylabel('Temperatura de la plataforma (°C)')
ax.set_xlim(0, 20)
ax.set_ylim(25, 61)
ax.legend(loc='upper right', bbox_to_anchor=(1.0, 0.86), frameon=False)
ax.grid(True, color='0.88', lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_curva_enfriamiento.png'), dpi=300)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.0, 3.1))
for nombre, (dp, vm, _, _) in VENT.items():
    qs = [vm * i / 100 for i in range(0, 101)]
    ax.plot(qs, [dp * (1 - (q / vm) ** 2) for q in qs], estilos[nombre][0], color='k', lw=1.1, label=estilos[nombre][1])
K = K_ducto(H_sel)
qs = [i for i in range(0, 76)]
ax.plot(qs, [K * (q * CFM) ** 2 for q in qs], color='0.45', lw=1.6, label='impedancia del módulo, ranura de 149 × 12.8 mm')
s = sel['Delta PFB0924GHEP6']
ax.plot([s['Q_cfm']], [s['dp']], 'o', color='k', ms=5)
ax.annotate('%.1f CFM; %d Pa' % (s['Q_cfm'], s['dp']), (s['Q_cfm'], s['dp']), xytext=(4, 196), ha='left',
            fontsize=9, arrowprops=dict(arrowstyle='-', lw=0.6))
ax.set_xlabel('Caudal (CFM)')
ax.set_ylabel('Presión estática (Pa)')
ax.set_xlim(0, 130)
ax.set_ylim(0, 330)
ax.legend(loc='upper right', frameon=False)
ax.grid(True, color='0.88', lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_punto_trabajo.png'), dpi=300)
plt.close(fig)

if __name__ == '__main__':
    print(json.dumps(R['aire'], indent=1))
    e = R['enfriamiento']
    for k in ('h_min', 'hc_min', 'v_min', 'K_sel', 'Q_min_cfm_H128'):
        print(k, e[k])
    for n, d in e['seleccion'].items():
        print(n, d)
    for f in e['barrido_H']:
        print(f['H_mm'], f['A_mm2'], f['f'], {n: (d['Q_cfm'], d['dp'], d['v'], d['v_ef'], d['t_min']) for n, d in f.items() if isinstance(d, dict)})
