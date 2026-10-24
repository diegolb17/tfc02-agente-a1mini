# -*- coding: utf-8 -*-
"""Costo de un año de operación de una granja de N impresoras con y sin el sistema (pedido de Diego, 24 oct 2026).

Escenarios, todos con jornada de 8 horas y seis días por semana (300 días al año):
  A. Sin el sistema y con cobertura de 24 horas: tres turnos de operador (dos diurnos y uno nocturno).
  B. Con el sistema en cada impresora y un solo turno diurno: la plataforma se libera sola fuera del turno y el
     siguiente trabajo se lanza a distancia, de modo que la producción iguala a la del escenario A.
  C. Sin el sistema y un solo turno diurno (situación de partida): solo se imprime lo que el turno alcanza a retirar.
Un operador por turno atiende toda la flota, hasta 20 impresoras, como en el arquetipo de la sección 3.1.

Costo laboral con la remuneración mínima vital de 1 230 soles, en el régimen de la pequeña empresa de la Ley 32353
(art. 44.3 y 57.2), que es el del arquetipo:
  sueldos 12 x RMV; dos gratificaciones de media remuneración, más la bonificación extraordinaria del 9 % (Ley 30334);
  CTS de quince remuneraciones diarias al año, con un sexto de la gratificación; EsSalud 9 % de los sueldos (Ley 26790);
  el turno nocturno con la remuneración mínima más 35 % (D.S. 007-2002-TR, art. 8, citado por SERVIR, 2021).
Como sensibilidad se calcula también el régimen general (gratificaciones completas, Ley 27735, y CTS de un sueldo).
El sistema cuesta 1 150 soles por impresora (sección 6.1). Su operación se escala con la producción de 24 horas a
partir de las bases de la sección 6.2: energía, consultas por impresión y mensajes del operador. El mantenimiento
queda fuera, salvo en la sensibilidad con el tope de R-MANT-01.
No se incluye el material, que es el mismo por pieza en los tres escenarios.
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
                     'font.size': 10, 'axes.labelsize': 10, 'legend.fontsize': 8.5,
                     'xtick.labelsize': 9, 'ytick.labelsize': 9})

RMV = 1230.0
DIAS = 300
TRABAJO_H = 2.0
POR_OPERADOR = 20
CAPEX = 1150.0
IMPR_DIA_24H = 24 / TRABAJO_H          # 12 impresiones al día con la plataforma siempre libre
IMPR_DIA_TURNO = 8 / TRABAJO_H + 1     # 4 en el turno y 1 que se deja corriendo al cierre

# Bases de la sección 6.2
REPOSO_W = 8.40            # consumo en reposo, antes de la fuente
RENDIMIENTO = 0.85
CICLO_WH = 1.02            # energía añadida por ciclo de remoción, ya en la red
TARIFA = 0.714             # soles por kWh, BT5B con impuesto
USD_IMPRESION = 0.033      # consultas al modelo por impresión
USD_MENSAJES_MES = 0.65    # diez mensajes libres al día durante 30 días
TC = 3.436                 # soles por dólar
MANT_TOPE_MES = 100.0      # R-MANT-01


def costo_operador(rmv, regimen='pequena'):
    sueldos = 12 * rmv
    if regimen == 'pequena':
        grat = 2 * (rmv / 2) * 1.09
        cts = (rmv + (rmv / 2) / 6) / 2
    else:
        grat = 2 * rmv * 1.09
        cts = rmv + rmv / 6
    essalud = 0.09 * sueldos
    return {'sueldos': sueldos, 'gratificaciones': grat, 'cts': cts, 'essalud': essalud,
            'total': sueldos + grat + cts + essalud}


def opex_anual_24h():
    energia_dia = REPOSO_W * 24 / RENDIMIENTO + IMPR_DIA_24H * CICLO_WH
    energia = energia_dia * DIAS / 1000 * TARIFA
    consultas = IMPR_DIA_24H * DIAS * USD_IMPRESION * TC
    mensajes = USD_MENSAJES_MES / 30 * DIAS * TC
    return {'energia_kwh': energia_dia * DIAS / 1000, 'energia': energia, 'consultas': consultas, 'mensajes': mensajes,
            'total': energia + consultas + mensajes}


OPEX = opex_anual_24h()


def escenarios(n, regimen='pequena', mant=0.0):
    dia = costo_operador(RMV, regimen)['total']
    noche = costo_operador(RMV * 1.35, regimen)['total']
    grupos = math.ceil(n / POR_OPERADOR)
    sis2 = OPEX['total'] + 12 * mant
    a = grupos * (2 * dia + noche)
    b1 = grupos * dia + n * (CAPEX + sis2)
    b2 = grupos * dia + n * sis2
    c = grupos * dia
    prod_24 = n * IMPR_DIA_24H * DIAS
    prod_turno = n * IMPR_DIA_TURNO * DIAS
    return {'n': n, 'A': a, 'B1': b1, 'B2': b2, 'C': c, 'prod_24h': prod_24, 'prod_turno': prod_turno,
            'A_imp': a / prod_24, 'B1_imp': b1 / prod_24, 'B2_imp': b2 / prod_24, 'C_imp': c / prod_turno}


def cruce(filas, clave):
    """Primera flota en que el costo por impresión del escenario B supera al de C."""
    return next((f['n'] for f in filas if f[clave] > f['C_imp']), None)


def impresiones_equilibrio(n, regimen='pequena', mant=0.0, anio=2):
    """Impresiones diarias por impresora con que B iguala el costo por impresión de C."""
    f = escenarios(n, regimen, mant)
    costo_b = f['B1'] if anio == 1 else f['B2']
    return costo_b / (f['C_imp'] * n * DIAS)


N = list(range(1, 21))
filas = [escenarios(n) for n in N]
R = {'operador_dia': costo_operador(RMV), 'operador_noche': costo_operador(RMV * 1.35),
     'operador_dia_general': costo_operador(RMV, 'general'), 'operador_noche_general': costo_operador(RMV * 1.35, 'general'),
     'opex_anual_24h': OPEX, 'impresiones_dia_24h': IMPR_DIA_24H, 'impresiones_dia_turno': IMPR_DIA_TURNO,
     'cruce_B1_C': cruce(filas, 'B1_imp'), 'cruce_B2_C': cruce(filas, 'B2_imp'),
     'cruce_B1_C_general': cruce([escenarios(n, 'general') for n in N], 'B1_imp'),
     'equilibrio_20_anio2': impresiones_equilibrio(20), 'equilibrio_20_anio1': impresiones_equilibrio(20, anio=1),
     'equilibrio_20_anio2_mant_tope': impresiones_equilibrio(20, mant=MANT_TOPE_MES),
     'tabla': {n: escenarios(n) for n in (1, 5, 10, 15, 20)},
     'tabla_general': {n: escenarios(n, 'general') for n in (5, 20)},
     'tabla_mant_tope': {n: escenarios(n, mant=MANT_TOPE_MES) for n in (5, 20)}}
json.dump(R, open(os.path.join(AQUI, 'calculos_24oct_costo_anual.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.3))
ax1.plot(N, [f['A'] / 1000 for f in filas], '-', color='0.55', lw=1.4, label='A. Sin el sistema, tres turnos (24 h)')
ax1.plot(N, [f['B1'] / 1000 for f in filas], '-', color='k', lw=1.6, label='B. Con el sistema, un turno: primer año')
ax1.plot(N, [f['B2'] / 1000 for f in filas], '--', color='k', lw=1.1, label='B. Con el sistema, un turno: años siguientes')
ax1.plot(N, [f['C'] / 1000 for f in filas], ':', color='k', lw=1.3, label='C. Sin el sistema, un turno (8 h)')
ax1.set_xlabel('Impresoras en la granja')
ax1.set_ylabel('Costo anual (miles de soles)')
ax1.set_xlim(1, 20)
ax1.set_ylim(0, 70)
ax1.set_xticks([1, 5, 10, 15, 20])
ax1.grid(True, color='0.9', lw=0.5)
ax1.set_title('(a) Costo de un año', fontsize=10)
ax2.plot(N, [f['A_imp'] for f in filas], '-', color='0.55', lw=1.4)
ax2.plot(N, [f['B1_imp'] for f in filas], '-', color='k', lw=1.6)
ax2.plot(N, [f['B2_imp'] for f in filas], '--', color='k', lw=1.1)
ax2.plot(N, [f['C_imp'] for f in filas], ':', color='k', lw=1.3)
ax2.set_xlabel('Impresoras en la granja')
ax2.set_ylabel('Costo por impresión (soles)')
ax2.set_xlim(1, 20)
ax2.set_xticks([1, 5, 10, 15, 20])
ax2.set_yscale('log')
ax2.set_yticks([0.5, 1, 2, 5, 10, 20])
ax2.set_yticklabels(['0.5', '1', '2', '5', '10', '20'])
ax2.grid(True, color='0.9', lw=0.5, which='both')
ax2.set_title('(b) Costo por impresión', fontsize=10)
fig.legend(loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.13, 1, 1))
fig.savefig(os.path.join(IMG, 'FIG_costo_anual.png'), dpi=300)
plt.close(fig)

if __name__ == '__main__':
    for k in ('operador_dia', 'operador_noche', 'operador_dia_general', 'operador_noche_general'):
        print(k, {a: round(b, 1) for a, b in R[k].items()})
    print('opex 24 h', {a: round(b, 2) for a, b in OPEX.items()})
    print('cruces', R['cruce_B1_C'], R['cruce_B2_C'], 'general', R['cruce_B1_C_general'])
    print('equilibrio 20 impresoras: año 2 %.2f, año 1 %.2f, año 2 con mant. tope %.2f' % (
        R['equilibrio_20_anio2'], R['equilibrio_20_anio1'], R['equilibrio_20_anio2_mant_tope']))
    for n in (1, 5, 10, 15, 20):
        f = escenarios(n)
        print(n, {k: round(v, 2) for k, v in f.items() if k != 'n'})
    for n in (5, 20):
        print('general', n, {k: round(v, 2) for k, v in escenarios(n, 'general').items() if k != 'n'})
        print('mant tope', n, {k: round(v, 2) for k, v in escenarios(n, mant=MANT_TOPE_MES).items() if k != 'n'})
