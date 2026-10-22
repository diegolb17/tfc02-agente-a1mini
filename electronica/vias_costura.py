# -*- coding: utf-8 -*-
"""Vias de costura del plano de masa (revision B, Tabla H1 del Anexo H): unen las dos caras de masa junto al modulo
del actuador U6, que conmuta la corriente del motor, y junto a las entradas analogicas D34 y D35 del microcontrolador.
Sin ellas las dos caras solo se unian por los agujeros de los componentes.

Cada candidata se acepta solo si queda a la separacion de toda pista, via o isla de otra red, y fuera de los
contornos de los componentes; despues se rellenan las zonas y el comprobador de reglas confirma el resultado.
Se ejecuta con el Python de KiCad, despues de rutear.py:
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" vias_costura.py"""
import math
import os
import sys

import pcbnew

BASE = os.path.dirname(os.path.abspath(__file__))
PLACA = os.path.join(BASE, 'TFC_Remocion', 'TFC_Remocion.kicad_pcb')
D_VIA, TALADRO, SEP = 0.8, 0.4, 0.6        # mm; mayor que la separacion mas exigente, la del bus de 24 V (0.5)


def mm(v):
    return pcbnew.FromMM(v)


def log(t):
    sys.stdout.write(t + '\n')
    sys.stdout.flush()


def dist_segmento(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main():
    board = pcbnew.LoadBoard(PLACA)
    gnd = board.FindNet('GND')
    log('placa cargada')
    # las de una corrida anterior se quitan y la placa se vuelve a cargar: tras Remove() la lista de pistas de la
    # interfaz de Python queda invalida y la siguiente llamada falla
    viejas = [t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND'
              and t.GetDrillValue() == mm(TALADRO)]
    if viejas:
        for t in viejas:
            board.Remove(t)
        board.Save(PLACA)
        board = pcbnew.LoadBoard(PLACA)
        gnd = board.FindNet('GND')
        log('quitadas %d vias de una corrida anterior' % len(viejas))
    obst = []
    for t in board.GetTracks():
        if t.GetNetname() == 'GND':
            continue
        es_via = t.GetClass() == 'PCB_VIA'
        a, b = t.GetStart(), t.GetEnd()
        ancho = t.GetWidth(pcbnew.F_Cu) if es_via else t.GetWidth()
        obst.append(('seg', pcbnew.ToMM(a.x), pcbnew.ToMM(a.y), pcbnew.ToMM(b.x), pcbnew.ToMM(b.y), pcbnew.ToMM(ancho) / 2))
    cajas = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            obst.append(('caja', pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetRight()),
                         pcbnew.ToMM(bb.GetBottom()), p.GetNetname() == 'GND'))
        cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if cy.GetWidth() == 0:
            cy = fp.GetBoundingBox(False, False)
        cajas.append((pcbnew.ToMM(cy.GetX()), pcbnew.ToMM(cy.GetY()), pcbnew.ToMM(cy.GetRight()), pcbnew.ToMM(cy.GetBottom())))
    log('obstaculos: %d, contornos: %d' % (len(obst), len(cajas)))

    def libre(x, y):
        r = D_VIA / 2
        if x < 5 or y < 5 or x > 95 or y > 75:
            return False
        for (x0, y0, x1, y1) in cajas:
            if x0 - r < x < x1 + r and y0 - r < y < y1 + r:
                return False
        for o in obst:
            if o[0] == 'seg':
                if dist_segmento(x, y, o[1], o[2], o[3], o[4]) < r + o[5] + SEP:
                    return False
            else:
                x0, y0, x1, y1, es_gnd = o[1:]
                m = r + (0.1 if es_gnd else SEP)
                if x0 - m < x < x1 + m and y0 - m < y < y1 + m:
                    return False
        return True

    zonas = [('U6', [(x, y) for y in (57.5, 59.0, 67.0, 68.5) for x in [5.5 + 1.5 * k for k in range(18)]], 6),
             ('analogicas', [(x, y) for y in (13.0, 14.5, 21.5, 23.0) for x in [42.0 + 1.5 * k for k in range(12)]], 4)]
    puestas = []
    for nombre, cand, cuantas in zonas:
        n = 0
        for (x, y) in cand:
            if n >= cuantas:
                break
            if libre(x, y) and all(math.hypot(x - px, y - py) > 2.5 for px, py in puestas):
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                v.SetWidth(pcbnew.F_Cu, mm(D_VIA)) if hasattr(v, 'SetWidth') else None
                v.SetDrill(mm(TALADRO))
                v.SetNet(gnd)
                board.Add(v)
                puestas.append((x, y))
                obst.append(('caja', x - D_VIA / 2, y - D_VIA / 2, x + D_VIA / 2, y + D_VIA / 2, True))
                n += 1
        log('%s: %d vias de costura' % (nombre, n))
    log('rellenando zonas')
    if board.Zones():
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    log('guardando')
    board.Save(PLACA)
    log('total %d: %s' % (len(puestas), ', '.join('(%.1f, %.1f)' % p for p in puestas)))


if __name__ == '__main__':
    main()
