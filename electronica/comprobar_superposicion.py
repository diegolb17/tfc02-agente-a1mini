# -*- coding: utf-8 -*-
"""Busca textos superpuestos en el PDF del esquemático.

POR QUE EXISTE. KiCad coloca la referencia y el valor a una distancia fija del
símbolo y no comprueba si caen encima de otra cosa. Mirar el plano a ojo no
sirve: en una hoja A2 con 41 símbolos los choques son de milímetros y se
escapan. Aquí se leen las cajas de todos los textos del PDF y se cruzan todas
contra todas.

    python comprobar_superposicion.py
"""
import os
import sys

import fitz

BASE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(BASE, 'TFC_Remocion', 'tesis', 'esquematico.pdf')

# Un solape de menos de esto es contacto de bordes y no estorba a la lectura.
TOLERANCIA = 0.6        # puntos de PDF


def cajas(pagina):
    """Las cajas de todos los textos, sin repetidos.

    KiCad emite algunos tramos del dibujo DOS VECES en el flujo del PDF, de
    modo que el mismo texto aparece dos veces en la misma posicion. Es
    invisible al mirar el plano, pero sin descartarlo cada uno de esos textos
    figuraria como superpuesto consigo mismo."""
    vistos = set()
    out = []
    for b in pagina.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].strip()
                if not t:
                    continue
                clave = (t, round(s['bbox'][0], 1), round(s['bbox'][1], 1))
                if clave in vistos:
                    continue
                vistos.add(clave)
                out.append((fitz.Rect(s['bbox']), t))
    return out


def main():
    if not os.path.exists(PDF):
        sys.stdout.write('no existe %s, corre antes exportar.py\n' % PDF)
        return 1
    doc = fitz.open(PDF)
    total = 0
    for n, pagina in enumerate(doc):
        cs = cajas(pagina)
        # el marco de la hoja lleva numeros de casilla en los bordes: no son
        # texto del circuito y se descartan por posicion
        borde = 25
        util = [(r, t) for r, t in cs
                if r.x0 > borde and r.x1 < pagina.rect.width - borde
                and r.y0 > borde and r.y1 < pagina.rect.height - borde]
        # lo que se sale del marco. El marco de KiCad esta a 10 mm del papel y
        # el cajetin ocupa la esquina inferior derecha
        fuera = [(r, t) for r, t in cs
                 if r.x0 < borde or r.x1 > pagina.rect.width - borde
                 or r.y0 < borde or r.y1 > pagina.rect.height - borde]
        # los numeros y letras de casilla del propio marco no cuentan
        fuera = [(r, t) for r, t in fuera if len(t) > 2]
        if fuera:
            sys.stdout.write('  %d textos FUERA DEL MARCO\n' % len(fuera))
            for r, t in fuera[:10]:
                sys.stdout.write('    %-24s en (%.0f, %.0f)\n' % (t[:24], r.x0,
                                                                 r.y0))
        choques = []
        for i in range(len(util)):
            ri, ti = util[i]
            for j in range(i + 1, len(util)):
                rj, tj = util[j]
                c = ri & rj
                if c.is_valid and c.width > TOLERANCIA and c.height > TOLERANCIA:
                    choques.append((c.width * c.height, ti, tj, ri))
        choques.sort(key=lambda c: -c[0])
        total += len(choques)
        sys.stdout.write('página %d: %d textos, %d superposiciones\n'
                         % (n + 1, len(util), len(choques)))
        for area, ti, tj, r in choques[:40]:
            sys.stdout.write('  %6.1f pt2  %-22s  x  %-22s  en (%.0f, %.0f)\n'
                             % (area, ti[:22], tj[:22], r.x0, r.y0))
    sys.stdout.write('\ntotal: %d\n' % total)
    return 0 if total == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
