# -*- coding: utf-8 -*-
"""Resumen legible de los rasgos de una pieza para decidir el acotado.
    python -m motor.resumen Soporte_actuador"""
import sys, json, numpy as np
from . import malla

def eje_nombre(v):
    v = np.asarray(v, float); i = int(np.argmax(np.abs(v)))
    return ('-' if v[i] < 0 else '+') + 'XYZ'[i] if abs(abs(v[i]) - 1) < 1e-3 else str(np.round(v, 3))

def resumen(nombre):
    d = malla.rasgos(nombre); r = d['rasgos']
    print('== %s | masa %.1f g | material %s | cuerpos %d' % (nombre, d['masa_g'], d['material'], len(d['cuerpos'])))
    for c in d['cuerpos']:
        print('   bbox', c['bbox'][0], '->', c['bbox'][1])
    print('-- planos grandes (normal, extensión, origen):')
    pl = sorted(r['planos'], key=lambda p: -p['area_mm2'])
    for p in pl[:40]:
        b = np.array(p['bbox']); print('   n=%-3s area %8.0f  x %6.1f..%-6.1f y %6.1f..%-6.1f z %6.1f..%-6.1f' % (
            eje_nombre(p['normal']), p['area_mm2'], b[0,0], b[1,0], b[0,1], b[1,1], b[0,2], b[1,2]))
    print('-- cilindros agrupados por (radio, eje):')
    grupos = {}
    for c in r['cilindros']:
        b = np.array(c['bbox']); ejev = np.asarray(c['eje']); i = int(np.argmax(np.abs(ejev)))
        o = np.asarray(c['origen'])
        # centro proyectado en el plano perpendicular al eje (coordenadas de las otras dos)
        otros = [k for k in range(3) if k != i]
        clave = (round(c['radio'], 2), eje_nombre(c['eje']))
        grupos.setdefault(clave, []).append((tuple(np.round(o[otros], 2)), (round(b[0,i],1), round(b[1,i],1)), 'XYZ'[otros[0]] + 'XYZ'[otros[1]]))
    for (rad, eje), lst in sorted(grupos.items()):
        centros = sorted(set(x[0] for x in lst))
        print('   r=%-6.2f (Ø%.1f) eje %-3s  n=%2d  centros(%s)=%s  extensión=%s' % (
            rad, 2*rad, eje, len(lst), lst[0][2], centros[:12], sorted(set(x[1] for x in lst))[:6]))
    if r['esferas']:
        print('-- esferas:'); [print('   r=%.2f centro=%s' % (e['radio'], e['centro'])) for e in r['esferas']]
    if r['conos']:
        print('-- conos:'); [print('   r=%.2f semiang=%.1f eje=%s origen=%s' % (c['radio'], c['semiangulo'], eje_nombre(c['eje']), c['origen'])) for c in r['conos'][:10]]
    if r['toros']:
        print('-- toros:'); [print('   R=%.2f r=%.2f eje=%s origen=%s' % (t['radio_mayor'], t['radio_menor'], eje_nombre(t['eje']), t['origen'])) for t in r['toros'][:10]]

if __name__ == '__main__':
    for n in sys.argv[1:]:
        resumen(n)
