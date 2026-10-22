# -*- coding: utf-8 -*-
"""Calculos de la revision del 15 de octubre de 2026 (observaciones de Denis Pena y de Christihan Laurel).

1. Vuelco de la impresora en la cavidad inclinada (DCL, momentos sobre el borde de la pared de retencion).
2. Enfriamiento en el orden pedido: tiempo maximo -> coeficiente -> velocidad -> ranura -> ventilador.
3. Piso de la cavidad con la carga en las patas de la impresora (sustituye al analisis por elementos finitos).
4. Actuador: fuerza requerida frente al punto de maxima potencia y duracion de la etapa 2.
5. Vuelco del conjunto sobre la mesa, caso C con los numeros.
6. Costo de operacion.
7. Raiz del soporte de la camara y rigidez minima del material amortiguador (DM-03).
Todos los datos de entrada salen del documento o de las fichas citadas; los supuestos se declaran en SUPUESTOS.
Escribe _conversion/calculos_15oct.json y las figuras en Imagenes/.
"""
import json
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyArrowPatch, Circle, Rectangle

AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.normpath(os.path.join(AQUI, '..', 'Imagenes'))
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'],
                     'font.size': 10, 'axes.titlesize': 10, 'axes.labelsize': 10, 'legend.fontsize': 9,
                     'xtick.labelsize': 9, 'ytick.labelsize': 9, 'mathtext.fontset': 'stix'})
R = {}
g = 9.81

# ----------------------------------------------------------------------------------------------- 1. vuelco
alfa = math.radians(20.0)
m_eq, m_rollo, m_cama = 5.50, 1.22, 1.53          # Tabla E: masa del equipo, rollo con carrete, masa movil
a_cama = 10.0                                      # m/s2, aceleracion maxima (Bambu Lab, 2026a)
prof, alto_env = 0.315, 0.365                      # profundidad del cuerpo base (medida) y altura de la envolvente
e_eq = alto_env / 2                                # centro de masa del equipo en el centroide de su envolvente
e_rollo = alto_env                                 # cota superior: rollo en la cara superior de la envolvente
d_eq = prof / 2
recorrido = 0.180                                  # recorrido de la plataforma en el eje de la pendiente
e_cama = 0.09012                                   # altura del plano de la plataforma sobre la base (medida)
m = m_eq + m_rollo
W = m * g
e_G = (m_eq * e_eq + m_rollo * e_rollo) / m
dd = m_cama / m * recorrido / 2                    # desplazamiento del centro de masa por el viaje de la cama
F_i = m_cama * a_cama


def fs_vuelco(h, alfa_r, d, dinamico=True):
    Mr = W * math.cos(alfa_r) * d
    Mv = W * math.sin(alfa_r) * (e_G - h) + (F_i * (e_cama - h) if dinamico else 0.0)
    return Mr, Mv, Mr / Mv


casos = []
for nombre, d, din in (('estático, plataforma centrada', d_eq, False),
                       ('dinámico, plataforma en su posición más alta', d_eq + dd, True),
                       ('dinámico, plataforma en su posición más baja', d_eq - dd, True)):
    Mr, Mv, fs = fs_vuelco(0.005, alfa, d, din)
    casos.append({'caso': nombre, 'd_mm': round(d * 1000, 1), 'Mr': round(Mr, 3), 'Mv': round(Mv, 3), 'FS': round(fs, 2)})
barrido_h = []
for h_mm in (0, 2, 5, 8, 10, 15, 20):
    Mr, Mv, fs = fs_vuelco(h_mm / 1000, alfa, d_eq - dd, True)
    barrido_h.append({'h_mm': h_mm, 'Mv': round(Mv, 3), 'FS': round(fs, 2)})
barrido_a = []
for a_deg in (10, 15, 20, 25, 30, 35):
    Mr, Mv, fs = fs_vuelco(0.005, math.radians(a_deg), d_eq - dd, True)
    barrido_a.append({'alfa': a_deg, 'Mr': round(Mr, 3), 'Mv': round(Mv, 3), 'FS': round(fs, 2)})
# angulo limite (FS = 1) con h = 5 mm y plataforma en la posicion mas baja
lo, hi = 10.0, 60.0
for _ in range(60):
    mid = (lo + hi) / 2
    if fs_vuelco(0.005, math.radians(mid), d_eq - dd, True)[2] > 1:
        lo = mid
    else:
        hi = mid
# retencion por la pared: fuerza paralela a la pendiente sin contar el rozamiento
T_est = W * math.sin(alfa)
T_din = T_est + F_i
b_contacto, t_pared, h_pared = 0.195, 0.004, 0.005
sig_pared = 6 * (T_din / b_contacto) * h_pared / t_pared ** 2 / 1e6
R['vuelco'] = {'m': m, 'W': round(W, 2), 'e_G_mm': round(e_G * 1000, 1), 'dd_mm': round(dd * 1000, 1),
               'F_i': round(F_i, 2), 'e_cama_mm': e_cama * 1000, 'casos': casos, 'barrido_h': barrido_h,
               'barrido_alfa': barrido_a, 'alfa_limite': round(lo, 1), 'N': round(W * math.cos(alfa), 2),
               'T_est': round(T_est, 2), 'T_din': round(T_din, 2), 'sigma_pared_MPa': round(sig_pared, 3),
               'FS_pared': round(50 / sig_pared, 0)}

# ------------------------------------------------------------------------------------------ 2. enfriamiento
C_pl, A_pl, L_pl = 294.7, 0.0324, 0.180            # Tabla de capacidad termica; lado de la plataforma
T0, Tf, Tinf = 60.0, 40.0, 25.0
lnr = math.log((T0 - Tinf) / (Tf - Tinf))
eps, sigma_sb = 0.90, 5.67e-8
Tm = (T0 + Tf) / 2 + 273.15
Tk = Tinf + 273.15
h_rad = eps * sigma_sb * (Tm ** 2 + Tk ** 2) * (Tm + Tk)
h_nat = 8.0
v_ref, h_ref = 14.5, 36.0                          # anclaje de la correlacion de placa plana del documento


def h_conv(v):
    return h_ref * math.sqrt(max(v, 0) / v_ref)


def t_enfr(h_total, Tfin=Tf):
    tau = C_pl / (h_total * A_pl)
    return tau, tau * math.log((T0 - Tinf) / (Tfin - Tinf))


t_max = 240.0                                      # s, presupuesto de enfriamiento del requerimiento R-FUNC-02
tau_max = t_max / lnr
h_min = C_pl / (A_pl * tau_max)
hc_min = h_min - h_rad
v_min = v_ref * (hc_min / h_ref) ** 2

rho = 1.18
L_s = 0.149                                        # largo de la ranura (MEC-2-10)
A_in = math.pi * 0.044 ** 2                        # brida de 88 mm (MEC-2-09 y MEC-2-10)
z_ent, z_cont, f_fr, L_tr = 0.5, 0.05, 0.03, 0.070  # coeficientes de perdida (Idelchik, 1986)


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
    """velocidad media sobre la cama respecto de la de salida, chorro de pared plano: um/U0 = 3.5/sqrt(x/b0)."""
    xc = 12.25 * H
    if xc >= L_pl:
        return 1.0
    integ = xc + 3.5 * math.sqrt(H) * 2 * (math.sqrt(L_pl) - math.sqrt(xc))
    return integ / L_pl


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
                     'h_min': round(h_min, 1), 'hc_min': round(hc_min, 1), 'v_min': round(v_min, 2),
                     'A_in_mm2': round(A_in * 1e6, 1), 'A_out_mm2': round(L_s * H_sel * 1e6, 1),
                     'contraccion': round(A_in / (L_s * H_sel), 2), 'K_sel': round(K_ducto(H_sel), 0),
                     'f_sel': round(factor_decaimiento(H_sel), 3), 'barrido_H': barrido_H, 'seleccion': sel,
                     'natural': {'solo_conv_min': round(t_nat0 / 60, 1), 'con_rad_min': round(t_nat / 60, 1),
                                 'dos_caras_min': round(t_nat2 / 60, 1), 'tau_con_rad': round(tau_nat, 0)},
                     'Q_min_m3s_H128': round(v_min / factor_decaimiento(H_sel) * L_s * H_sel, 5)}
R['enfriamiento']['Q_min_cfm_H128'] = round(R['enfriamiento']['Q_min_m3s_H128'] / CFM, 1)

# ---------------------------------------------------------------------------------- 3. piso con cargas puntuales
E_pla, nu, t_piso = 3.5e9, 0.36, 0.004
D = E_pla * t_piso ** 3 / (12 * (1 - nu ** 2))
N = W * math.cos(alfa)
P_pata = N / 3                                     # cinco patas, se supone que tres comparten la carga
b_panel = 0.0674                                   # separacion entre nervaduras (E.1)
alfa_p = 0.01695                                   # placa apoyada, a/b >= 2, carga puntual central (Timoshenko)
w_panel = alfa_p * P_pata * b_panel ** 2 / D
I_nerv, L_nerv, c_nerv = 2.0904e-8, 0.332, 0.0231  # seccion en T de la nervadura (E.1)
P_nerv = P_pata / 2
w_nerv = P_nerv * L_nerv ** 3 / (48 * E_pla * I_nerv)
M_nerv = P_nerv * L_nerv / 4
sig_nerv = M_nerv * c_nerv / I_nerv / 1e6
A_pata = math.pi * 0.015 ** 2
p_pata = P_pata / A_pata / 1e6
R['piso'] = {'N': round(N, 2), 'P_pata': round(P_pata, 2), 'D': round(D, 3), 'w_panel_mm': round(w_panel * 1000, 3),
             'P_nerv': round(P_nerv, 2), 'w_nerv_mm': round(w_nerv * 1000, 3), 'w_total_mm': round((w_panel + w_nerv) * 1000, 3),
             'sigma_nerv_MPa': round(sig_nerv, 3), 'FS_nerv': round(50 / sig_nerv, 0), 'p_pata_MPa': round(p_pata, 3),
             'FS_aplast': round(60 / p_pata, 0), 'w_fluencia_mm': round(3 * (w_panel + w_nerv) * 1000, 2)}

# ------------------------------------------------------------------------------------------------ 4. actuador
F_flex, F_mag = 5.79, 21.0
F_req = F_flex + F_mag
v0, F_pp, v_pp, F_max = 6.5, 62.0, 3.2, 80.0       # Actuonix (2019), p. 1, reduccion 210:1
F_stall = F_pp * v0 / (v0 - v_pp)
v_op = v0 * (1 - F_req / F_stall)
t_etapa2 = 35.0 / v_op
lamina = []
E_ac, t_l, b_l = 200e9, 0.0005, 0.180
I_l = b_l * t_l ** 3 / 12
for a_mm in (180, 150, 120, 100, 95, 80):
    a = a_mm / 1000
    d_ = 0.030
    sig = 3 * E_ac * d_ * t_l / (2 * a ** 2) / 1e6
    Rr = a ** 2 / (3 * d_) * 1000
    P = 3 * E_ac * I_l * d_ / a ** 3
    lamina.append({'a_mm': a_mm, 'sigma_MPa': round(sig, 1), 'R_mm': round(Rr, 0), 'P_N': round(P, 1)})
R['actuador'] = {'F_req': round(F_req, 2), 'F_stall_ext': round(F_stall, 1), 'v_op': round(v_op, 2),
                 't_etapa2_s': round(t_etapa2, 1), 'margen_pp': round(F_pp / F_req, 2), 'margen_max': round(F_max / F_req, 2),
                 'lamina_vs_a': lamina}

# ----------------------------------------------------------------------------- 5. conjunto sobre la mesa, caso C
m_c = 8.89                                         # conjunto con el equipo, sin rollo (Anexo F)
x_cg, y_cg = 165.2, 198.3
dx_c = m_cama / m_c * 84.6
brazo_A = 324.2 - (x_cg + dx_c)
brazo_B = 340.0 - y_cg
MvA = m_cama * a_cama * 0.2498
MvB = 0.50 * a_cama * 0.4189
MrA = m_c * g * brazo_A / 1000
MrB = m_c * g * brazo_B / 1000
uC = MvA / MrA + MvB / MrB
W_c = m_c * g
k_c = 84.6 / m_c / 1000                            # m por kg de masa movil
d0_c = (324.2 - x_cg) / 1000
m_crit = W_c * d0_c / (W_c * k_c + a_cama * 0.2498)
a_crit = W_c * (d0_c - m_cama * k_c) / (m_cama * 0.2498)
Fh, Fv, Fcab = m_cama * a_cama, m_cama * a_cama * math.sin(alfa), 0.50 * a_cama
desl = {}
for mu in (0.30, 0.80):
    desl[str(mu)] = {'solo': round(mu * (W_c - Fv) / Fh, 2), 'combinado': round(mu * (W_c - Fv) / math.hypot(Fh, Fcab), 2)}
# vuelco hacia atras de la impresora en la cavidad, con la plataforma en su posicion mas alta
Mr_atras = W * math.cos(alfa) * (prof - (d_eq + dd)) + W * math.sin(alfa) * e_G
Mv_atras = F_i * e_cama
R['conjunto'] = {'m': m_c, 'W': round(W_c, 2), 'dx_mm': round(dx_c, 1), 'brazo_A': round(brazo_A, 1), 'brazo_B': round(brazo_B, 1),
                 'A': {'Mv': round(MvA, 3), 'Mr': round(MrA, 3), 'FS': round(MrA / MvA, 2)},
                 'B': {'Mv': round(MvB, 3), 'Mr': round(MrB, 3), 'FS': round(MrB / MvB, 2)},
                 'C': {'uA': round(MvA / MrA, 3), 'uB': round(MvB / MrB, 3), 'u': round(uC, 3), 'FS': round(1 / uC, 2)},
                 'k_mm_kg': round(k_c * 1000, 3), 'd0_mm': round(d0_c * 1000, 1), 'm_crit': round(m_crit, 2),
                 'a_crit_mm_s2': round(a_crit * 1000, -1), 'deslizamiento': desl, 'Fv': round(Fv, 2), 'Fh': round(Fh, 2)}
R['vuelco']['atras'] = {'Mr': round(Mr_atras, 3), 'Mv': round(Mv_atras, 3), 'FS': round(Mr_atras / Mv_atras, 1)}

# -------------------------------------------------------------------------------------------- 6. costo de operacion
P_reposo, P_enf, P_flex, P_cap = 8.21, 23.33, 11.57, 15.03     # Tabla de escenarios del Anexo E.6 (bus)
eta_f = 0.85
horas_dia, imp_dia, dias = 12, 6, 30
t_enf = sel['Delta PFB0924GHEP6']['t38_min'] * 60
E_ciclo = ((P_enf - P_reposo) * t_enf + (P_flex - P_reposo) * 40 + (P_cap - P_reposo) * 10) / 3600 / eta_f   # Wh
E_dia = P_reposo * horas_dia / eta_f + E_ciclo * imp_dia
E_mes = E_dia * dias / 1000
tarifa = 0.714                                     # S/ por kWh, BT5B (Pluz Energia Peru, 2026)
c_energia = E_mes * tarifa
tok_alto, tok_bajo = 25501, 2833                   # tokens por imagen de 1 600 x 1 200, detalle alto y bajo
p_in, p_out = 0.15e-6, 0.60e-6                     # dolares por token (OpenAI, 2026b), modelo de referencia
sup_por_imp = 12                                   # una consulta de supervision cada 10 minutos en 2 horas
ver_por_imp = 2
tok_sup = sup_por_imp * (2 * tok_bajo + 300)
tok_ver = ver_por_imp * (2 * tok_alto + 300)
usd_imp = (tok_sup + tok_ver) * p_in + (sup_por_imp + ver_por_imp) * 150 * p_out
usd_mes = usd_imp * imp_dia * dias
tc = 3.60
R['operacion'] = {'E_ciclo_Wh': round(E_ciclo, 2), 'E_dia_Wh': round(E_dia, 1), 'E_mes_kWh': round(E_mes, 2),
                  'tarifa': tarifa, 'c_energia': round(c_energia, 2), 'tok_sup': tok_sup, 'tok_ver': tok_ver,
                  'usd_imp': round(usd_imp, 4), 'usd_mes': round(usd_mes, 2), 'soles_api_mes': round(usd_mes * tc, 2),
                  'tc': tc, 'imp_mes': imp_dia * dias, 'total_sin_mant': round(c_energia + usd_mes * tc, 2),
                  'usd_imp_todo_alto': round(((sup_por_imp + ver_por_imp) * (2 * tok_alto + 300)) * p_in, 4)}
R['operacion']['soles_api_mes_todo_alto'] = round(R['operacion']['usd_imp_todo_alto'] * imp_dia * dias * tc, 2)

# ------------------------------------------------------- 7. raiz del soporte de la camara y material amortiguador (DM-03)
# Geometria de MEC-2-14 (PLANOS/_geom/Soporte_camara.json): placa de 60 x 100 x 6 mm, tubo de 40/34 mm centrado,
# cuatro tornillos M3 en x = -24.5 y -17.0 (franja junto a un borde), es decir a 20.75 mm del eje del tubo en promedio.
E_pla = 3.5e9
L_tubo = 0.200
I_tubo = math.pi / 64 * (0.040 ** 4 - 0.034 ** 4)
k_tubo = 3 * E_pla * I_tubo / L_tubo ** 3
m_ef = 0.126                                        # masa efectiva del Anexo E.4
b_pl, t_pl, L_pl = 0.100, 0.006, 0.02075


def f_soporte(k_theta):
    k_raiz = k_theta / L_tubo ** 2                  # giro de la raiz -> desplazamiento en el extremo
    k = 1 / (1 / k_tubo + 1 / k_raiz)
    return k, math.sqrt(k / m_ef) / (2 * math.pi)


kth_voladizo = E_pla * (b_pl * t_pl ** 3 / 12) / L_pl              # franja en voladizo con momento en el extremo
kth_ambos = 8 * E_pla * (b_pl * t_pl ** 3 / 12) / L_pl             # tornillos a ambos lados del tubo
kth_10mm = 8 * E_pla * (b_pl * 0.010 ** 3 / 12) / L_pl             # idem con placa de 10 mm
f_rigida = math.sqrt(k_tubo / m_ef) / (2 * math.pi)
# material amortiguador: la componente del peso empuja siempre la impresora contra la pared frontal y la inercia
# de la plataforma oscila sobre esa precarga; el desplazamiento relativo no debe superar un pixel en la plataforma
px_mm = 0.4 / 0.9                                   # un cordon de 0.4 mm ocupa 0.9 pixeles (Anexo E.8)
Fi = 15.3
W_par = 6.72 * g * math.sin(math.radians(20))
k_min = Fi / px_mm                                  # N/mm
A_cont = 195 * 3                                    # mm2: 195 mm de contacto por los 3 mm de cuerpo que toma la pared
R['soporte_camara'] = {
    'k_tubo': round(k_tubo, 0), 'f_rigida': round(f_rigida, 1),
    'kth_voladizo_Nm_rad': round(kth_voladizo, 1), 'k_voladizo': round(f_soporte(kth_voladizo)[0], 0),
    'f_voladizo': round(f_soporte(kth_voladizo)[1], 1),
    'f_ambos': round(f_soporte(kth_ambos)[1], 1), 'f_10mm': round(f_soporte(kth_10mm)[1], 1),
    'W_par': round(W_par, 2), 'px_mm': round(px_mm, 3), 'k_min_N_mm': round(k_min, 1), 'A_cont': A_cont,
    'E_min_2mm_MPa': round(k_min * 2 / A_cont, 3), 'E_min_3mm_MPa': round(k_min * 3 / A_cont, 3)}

with open(os.path.join(AQUI, 'calculos_15oct.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=1)


# =============================================================================================== FIGURAS
def flecha(ax, p0, p1, txt=None, off=(0, 0), color='k', lw=1.3, ha='center', va='center'):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>', mutation_scale=11, lw=lw, color=color))
    if txt:
        ax.text(p1[0] + off[0], p1[1] + off[1], txt, ha=ha, va=va, fontsize=10.5)


def cota(ax, p0, p1, txt, off, ha='center'):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='<|-|>', mutation_scale=8, lw=0.7, color='0.25'))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], txt, ha=ha, va='center', fontsize=10)


def rot(p, ang=alfa):
    c, s = math.cos(ang), math.sin(ang)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


# --- figura de cuerpo libre del vuelco, en el marco de la pendiente (frente abajo a la derecha); no a escala
fig, ax = plt.subplots(figsize=(6.2, 4.3))
A = -alfa
U = (math.cos(A), math.sin(A))
V_ = (-math.sin(A), math.cos(A))


def P(s, n):
    return (s * U[0] + n * V_[0], s * U[1] + n * V_[1])


def txt(p, t, dx=0, dy=0, **kw):
    ax.text(p[0] + dx, p[1] + dy, t, fontsize=11, ha=kw.get('ha', 'center'), va=kw.get('va', 'center'),
            bbox=dict(facecolor='white', edgecolor='none', pad=0.6), zorder=8)


Lb, Hb, hw, pata = 3.15, 2.75, 0.32, 0.08
# apoyo inclinado con rayado
ax.plot(*zip(P(-0.9, 0), P(Lb + 1.5, 0)), color='k', lw=1.4)
for i in range(24):
    s0 = -0.85 + i * (Lb + 2.3) / 24
    ax.plot(*zip(P(s0, 0), P(s0 - 0.16, -0.16)), color='0.45', lw=0.6)
# pared de retencion, apartada del cuerpo libre (gris)
ax.add_patch(Polygon([P(Lb, 0), P(Lb, hw), P(Lb + 0.22, hw), P(Lb + 0.22, 0)], closed=True,
                     facecolor='0.88', edgecolor='0.55', lw=0.8))
# cuerpo libre: impresora sobre dos patas
ax.add_patch(Polygon([P(0, pata), P(Lb, pata), P(Lb, Hb), P(0, Hb)], closed=True, fill=False, edgecolor='k', lw=1.3))
for s0 in (0.25, Lb - 0.55):
    ax.add_patch(Polygon([P(s0, 0), P(s0 + 0.3, 0), P(s0 + 0.3, pata), P(s0, pata)], closed=True, facecolor='0.3', lw=0))
O = P(Lb, hw)
ax.add_patch(Circle(O, 0.06, facecolor='white', edgecolor='k', lw=1.1, zorder=9))
txt(O, 'O', dx=-0.2, dy=0.2)
sG, nG = Lb - 1.35, 1.75
G = P(sG, nG)
ax.add_patch(Circle(G, 0.08, facecolor='k', zorder=9))
txt(G, 'G', dx=-0.25, dy=0.12)
# peso vertical
ax.add_patch(FancyArrowPatch(G, (G[0], G[1] - 1.05), arrowstyle='-|>', mutation_scale=12, lw=1.4, color='k', zorder=7))
txt((G[0], G[1] - 1.05), r'$W$', dx=0.28, dy=0.05)
# inercia de la plataforma, paralela a la pendiente y hacia el frente
sp, np_ = 0.35, 0.72
ax.add_patch(FancyArrowPatch(P(sp, np_), P(sp + 1.05, np_), arrowstyle='-|>', mutation_scale=12, lw=1.4, color='k'))
txt(P(sp + 0.5, np_ + 0.28), r'$F_i = m_p\,a$')
# normales y rozamientos
for i, s0 in enumerate((0.40, Lb - 0.40)):
    ax.add_patch(FancyArrowPatch(P(s0, -0.75), P(s0, -0.02), arrowstyle='-|>', mutation_scale=11, lw=1.2, color='k'))
    txt(P(s0, -0.92), r'$N_%d$' % (i + 1))
    ax.add_patch(FancyArrowPatch(P(s0 - 0.02, -0.12), P(s0 - 0.6, -0.12), arrowstyle='-|>', mutation_scale=10, lw=1.0, color='k'))
    txt(P(s0 - 0.42, -0.38), r'$f_%d$' % (i + 1))
# reaccion de la pared
ax.add_patch(FancyArrowPatch(P(Lb + 0.75, hw * 0.5), P(Lb + 0.02, hw * 0.5), arrowstyle='-|>', mutation_scale=11, lw=1.2, color='k', zorder=7))
txt(P(Lb + 0.55, hw + 0.3), r'$R_p$')
# cotas
def cota2(p0, p1, t, d0=0, d1=0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='<|-|>', mutation_scale=8, lw=0.7, color='0.3'))
    txt(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), t, dx=d0, dy=d1)

def ext(p0, p1):
    ax.plot(*zip(p0, p1), color='0.55', lw=0.5, ls=':')

ext(G, P(sG, Hb + 0.5)); ext(P(Lb, Hb), P(Lb, Hb + 0.5))
cota2(P(sG, Hb + 0.38), P(Lb, Hb + 0.38), r'$d$')
ext(G, P(-0.75, nG)); cota2(P(-0.6, 0), P(-0.6, nG), r'$e_G$')
ext(P(sp, np_), P(-1.15, np_)); cota2(P(-1.0, 0), P(-1.0, np_), r'$e_p$')
ext(P(Lb + 0.22, hw), P(Lb + 1.2, hw)); cota2(P(Lb + 1.08, 0), P(Lb + 1.08, hw), r'$h$', d0=0.25, d1=0.05)
# angulo
q = P(Lb + 1.5, 0)
ax.plot([q[0] - 1.5, q[0] + 0.15], [q[1], q[1]], color='0.5', lw=0.6, ls='--')
txt((q[0] - 0.75, q[1] + 0.12), r'$\alpha$')
ax.set_aspect('equal'); ax.axis('off')
xs = [P(s, n)[0] for s in (-1.2, Lb + 1.6) for n in (-1, Hb + 0.6)]
ys = [P(s, n)[1] for s in (-1.2, Lb + 1.6) for n in (-1, Hb + 0.6)]
ax.set_xlim(min(xs) - 0.1, max(xs) + 0.2); ax.set_ylim(min(ys) - 0.1, max(ys) + 0.1)
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_dcl_vuelco.png'), dpi=300, bbox_inches='tight', pad_inches=0.04)
plt.close(fig)

# --- tiempo de enfriamiento en funcion del alto de la ranura
fig, ax = plt.subplots(figsize=(6.0, 3.0))
Hs = [x / 2 for x in range(8, 61)]
estilos = {'Sunon PMD2409PMB1-A': (':', 'Sunon PMD2409PMB1-A'), 'Delta PFB0924EHEP6': ('--', 'Delta PFB0924EHEP6'),
           'Delta PFB0924GHEP6': ('-', 'Delta PFB0924GHEP6, adoptado')}
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
ax.text(13.2, 2.25, 'alto adoptado,\n12.8 mm', fontsize=9, va='bottom')
ax.set_xlabel('Alto de la ranura de salida H (mm)')
ax.set_ylabel('Enfriamiento de 60 a 40 °C (min)')
ax.set_xlim(4, 30)
ax.set_ylim(2.2, 4.4)
ax.legend(loc='upper left', frameon=False)
ax.grid(True, color='0.88', lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_enfriamiento_ranura.png'), dpi=300)
plt.close(fig)

# --- curvas de enfriamiento
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

# --- punto de trabajo
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

# --- diagrama de valor VDI 2225
fig, ax = plt.subplots(figsize=(4.6, 4.2))
pts = {'C.S. 1': (0.94, 0.88), 'C.S. 2': (0.78, 0.68), 'C.S. 3': (0.59, 0.54), 'Ideal': (1.0, 1.0)}
ax.plot([0, 1], [0, 1], color='0.5', lw=0.8, ls='--')
ax.text(0.32, 0.36, 'recta de equilibrio', rotation=45, fontsize=8.5, color='0.35')
ax.add_patch(Rectangle((0.7, 0.7), 0.3, 0.3, facecolor='0.92', edgecolor='0.6', lw=0.6, zorder=0))
ax.text(0.99, 0.712, 'zona de buena\nsolución', fontsize=8.5, va='bottom', ha='right', color='0.3')
for k, (x, y) in pts.items():
    ax.plot([x], [y], 'o' if k != 'Ideal' else 's', color='k', ms=6 if k != 'Ideal' else 5)
    if k in ('C.S. 2', 'C.S. 3'):
        ax.annotate('%s (%.2f; %.2f)' % (k, x, y), (x, y), xytext=(x + 0.03, y - 0.045), fontsize=9, ha='left')
    elif k == 'Ideal':
        ax.annotate('%s (%.2f; %.2f)' % (k, x, y), (x, y), xytext=(x - 0.02, y - 0.06), fontsize=9, ha='right')
    else:
        ax.annotate('%s (%.2f; %.2f)' % (k, x, y), (x, y), xytext=(x - 0.03, y - 0.06), fontsize=9, ha='right')
ax.set_xlabel('Valor técnico, $X_i$')
ax.set_ylabel('Valor económico, $Y_i$')
ax.set_xlim(0, 1.05)
ax.set_ylim(0, 1.05)
ax.set_aspect('equal')
ax.grid(True, color='0.9', lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_vdi2225.png'), dpi=300)
plt.close(fig)

# --- figura de cuerpo libre del piso: nervadura con la carga de una pata en el centro del vano
fig, ax = plt.subplots(figsize=(6.0, 1.9))
ax.plot([0, 10], [0, 0], color='k', lw=3)
for x in (0, 10):
    ax.add_patch(Polygon([(x, 0), (x - 0.35, -0.55), (x + 0.35, -0.55)], closed=True, fill=False, lw=1.0))
flecha(ax, (5, 1.6), (5, 0.08), None)
ax.text(5.25, 1.35, r'$P_n = P_{pata}/2$', fontsize=10.5, ha='left')
flecha(ax, (0, -1.5), (0, -0.6), r'$P_n/2$', off=(0.25, -0.55), ha='left')
flecha(ax, (10, -1.5), (10, -0.6), r'$P_n/2$', off=(-0.25, -0.55), ha='right')
cota(ax, (0, 0.55), (10, 0.55), r'$L = 332$ mm', (-2.6, 0.25))
ax.set_xlim(-1, 11)
ax.set_ylim(-1.8, 1.9)
ax.set_aspect('equal')
ax.axis('off')
fig.tight_layout()
fig.savefig(os.path.join(IMG, 'FIG_dcl_piso.png'), dpi=300, bbox_inches='tight', pad_inches=0.04)
plt.close(fig)

print(json.dumps(R, ensure_ascii=False, indent=1))
