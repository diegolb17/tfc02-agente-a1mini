# -*- coding: utf-8 -*-
"""Escribe las clases de red del proyecto con los anchos calculados.

POR QUE HACE FALTA. El ruteador automatico no adivina los anchos: los lee de las
clases de red que declara el proyecto, y si no hay ninguna rutea todo con el
ancho por omision. Eso es lo que paso al primer intento: la placa quedo ruteada
entera pero con 180 avisos de ancho de pista, porque el riel de la celda, que
necesita 2 mm, salio con 0.2.

Los anchos son los de calculo_pistas.py, que los dimensiona por el mas exigente
de dos criterios, el calentamiento segun IPC-2221 y la caida de tension admitida
segun lo que cuelga de cada riel.

La separacion de 0.25 mm es el minimo de fabricacion. Se sube a 0.4 en el riel
de 24 V, que es el de mayor tension de la placa, y a 0.5 en el bus de entrada.
"""
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.join(BASE, 'TFC_Remocion', 'TFC_Remocion.kicad_pro')

# (nombre, ancho de pista, separacion, redes que la usan)
# Los anchos salen de calc_balance_potencia.py, en TESIS_LATEX/_calculos, que
# es lo que alimenta la tabla de anchos de pista del apartado 4.7.3. Si uno de
# los dos cambia hay que cambiar el otro: el documento y la placa no pueden
# decir cosas distintas.
CLASES = [
    # REVISION B: 1.6 mm para soportar con 10 grados de calentamiento los 3.3 A que la fuente entrega antes de
    # protegerse (Tabla H1); FAN_RET desaparece al retirar el transistor del ventilador
    ('Bus24', 1.60, 0.50,
     ['V24_BRUTO', 'V24_FUS', '+24V', '+24V_ACT']),
    # 2.50 mm no es capricho: con 1.789 A y un limite de caida del 1 por ciento
    # sobre 130 mm de rodeo, el criterio electrico exige 2.48 y se redondea al
    # cuarto. La corriente subio al colgar del riel de 5.1 tambien el modulo de
    # camara y el microcontrolador, cuyo regulador es LINEAL y pasa por tanto la
    # misma corriente que entrega.
    ('R5V1', 2.50, 0.30, ['+5V1']),
    # el +3V3 de la placa alimenta el potenciometro del actuador y la polarizacion del tacometro, menos de 1 mA
    ('R3V3', 0.25, 0.25, ['+3V3']),
    ('R12V', 0.25, 0.30, ['+12V', 'LED_RET', 'ACT_OUT1', 'ACT_OUT2']),
    ('Masa', 0.75, 0.25, ['GND']),
]
ANCHO_SENAL = 0.25          # todo lo que no figure arriba


def plantilla(base, nombre, ancho, separacion):
    c = dict(base)
    c['name'] = nombre
    c['track_width'] = ancho
    c['clearance'] = separacion
    # la via se dimensiona con la pista: una via estrecha estrangula un riel
    # ancho y se convierte en el punto caliente
    c['via_diameter'] = max(0.8, round(ancho + 0.6, 2))
    c['via_drill'] = max(0.4, round(ancho * 0.5, 2))
    c['priority'] = 10
    return c


def main():
    d = json.load(io.open(PROY, encoding='utf-8'))
    ns = d['net_settings']
    base = next(c for c in ns['classes'] if c['name'] == 'Default')

    # la clase por omision gobierna la señal
    base['track_width'] = ANCHO_SENAL
    base['clearance'] = 0.25

    ns['classes'] = [base] + [plantilla(base, n, a, s) for n, a, s, _ in CLASES]

    # cada red se asigna a su clase por patron exacto
    patrones = []
    for nombre, _, _, redes in CLASES:
        for red in redes:
            patrones.append({'netclass': nombre, 'pattern': red})
    ns['netclass_patterns'] = patrones

    io.open(PROY, 'w', encoding='utf-8').write(
        json.dumps(d, indent=2, ensure_ascii=False))

    sys.stdout.write('clases de red escritas\n')
    sys.stdout.write('%-10s %8s %10s %8s  %s\n'
                     % ('clase', 'pista', 'separac.', 'vía', 'redes'))
    sys.stdout.write('%-10s %8.2f %10.2f %8s  %s\n'
                     % ('Default', ANCHO_SENAL, 0.25, '0.60', 'el resto'))
    for nombre, ancho, sep, redes in CLASES:
        sys.stdout.write('%-10s %8.2f %10.2f %8.2f  %s\n'
                         % (nombre, ancho, sep, max(0.8, round(ancho + 0.6, 2)),
                            ', '.join(redes)))
    sys.stdout.write('\ntotal de redes asignadas: %d\n' % len(patrones))


if __name__ == '__main__':
    main()
