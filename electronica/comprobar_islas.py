# -*- coding: utf-8 -*-
"""Comprueba que cada pin del esquemático que pertenece a una red tenga una isla en la placa.

Existe porque el 12 oct 2026 el pin 8 (OUT2) del DRV8871 no tenía isla: la huella era una tira de 6
contactos. La red ACT_OUT2 quedaba con una sola isla (J4:2), y ni el ERC ni el DRC lo detectaban,
porque una red de una isla no tiene nada que conectar. Se ejecuta con el Python del sistema:
    python comprobar_islas.py"""
import os
import re
import sys
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
NET = os.path.join(BASE, 'TFC_Remocion', 'net.xml')
PCB = os.path.join(BASE, 'TFC_Remocion', 'TFC_Remocion.kicad_pcb')

raiz = ET.parse(NET).getroot()
nodos = []
for net in raiz.iter('net'):
    nombre = net.get('name')
    miembros = [(n.get('ref'), n.get('pin')) for n in net.iter('node')]
    if len(miembros) >= 1 and not nombre.startswith('unconnected-'):
        nodos += [(nombre, r, p) for r, p in miembros]

pcb = open(PCB, encoding='utf-8').read()
islas = set()
for m in re.finditer(r'\(footprint "[^"]+"(.*?)\n\t\)', pcb, re.S):
    cuerpo = m.group(1)
    ref = re.search(r'\(property "Reference" "([^"]+)"', cuerpo)
    if not ref:
        continue
    for p in re.finditer(r'\(pad "([^"]*)"', cuerpo):
        islas.add((ref.group(1), p.group(1)))

faltan = [(n, r, p) for n, r, p in nodos if (r, p) not in islas and not r.startswith('#')]
# los pines expuestos (EP) de un símbolo montado como módulo no tienen isla propia: se aceptan si
# su red ya tiene otra isla del mismo componente
acept = []
for n, r, p in faltan:
    otras = [(r2, p2) for n2, r2, p2 in nodos if n2 == n and r2 == r and (r2, p2) in islas]
    if otras:
        acept.append((n, r, p))
reales = [x for x in faltan if x not in acept]
print('pines en redes: %d | sin isla: %d | aceptados por tener otra isla en la misma red: %d' % (
    len(nodos), len(faltan), len(acept)))
for n, r, p in acept:
    print('  aceptado  %s:%s en %s' % (r, p, n))
for n, r, p in reales:
    print('  FALTA     %s:%s en %s' % (r, p, n))
sys.exit(1 if reales else 0)
