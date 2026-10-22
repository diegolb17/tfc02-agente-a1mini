# -*- coding: utf-8 -*-
"""Crea el simbolo y la huella de la placa ESP32 DevKit V1 de 30 contactos.

POR QUE SE DIBUJA A MANO. KiCad no trae esta placa en sus bibliotecas, y es la
que se vende en Lima por 35 soles. El riesgo de dibujarla es numerar mal su tira
de contactos, porque un numero equivocado no lo detecta ninguna comprobacion: el
esquematico se ve bien y la placa sale mal.

COMO SE ELIMINA ESE RIESGO. La numeracion NO se adivina: se define aqui, en una
sola tabla, y de esa misma tabla salen el simbolo y la huella. Mientras los dos
se generen juntos, el contacto numero N del simbolo y la isla numero N de la
huella son el mismo punto fisico por construccion, sea cual sea el criterio de
numeracion que se haya elegido.

EL ORDEN es el de circuito integrado: del 1 al 15 bajando por la columna
izquierda y del 16 al 30 subiendo por la derecha, con la toma de USB abajo. Los
nombres se leyeron de la serigrafia de la placa que Diego va a comprar.
"""
import io
import os
import sys
import uuid

import sexp
from sexp import Atomo as A

BASE = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.join(BASE, 'TFC_Remocion')

# (numero, nombre, tipo electrico). Con la toma de USB abajo:
#   1 a 15   columna izquierda, de arriba abajo
#   16 a 30  columna derecha, de abajo arriba
IZQUIERDA = [
    ('D23', 'bidirectional'), ('D22', 'bidirectional'),
    ('TX0', 'bidirectional'), ('RX0', 'bidirectional'),
    ('D21', 'bidirectional'), ('D19', 'bidirectional'),
    ('D18', 'bidirectional'), ('D5', 'bidirectional'),
    ('TX2', 'bidirectional'), ('RX2', 'bidirectional'),
    ('D4', 'bidirectional'), ('D2', 'bidirectional'),
    ('D15', 'bidirectional'), ('GND', 'power_in'), ('3V3', 'power_out'),
]
DERECHA = [
    ('VIN', 'power_in'), ('GND', 'power_in'),
    ('D13', 'bidirectional'), ('D12', 'bidirectional'),
    ('D14', 'bidirectional'), ('D27', 'bidirectional'),
    ('D26', 'bidirectional'), ('D25', 'bidirectional'),
    ('D33', 'bidirectional'), ('D32', 'bidirectional'),
    ('D35', 'input'), ('D34', 'input'),
    ('VN', 'input'), ('VP', 'input'), ('EN', 'input'),
]

PASO = 2.54          # separacion entre contactos
ANCHO_FILAS = 25.4   # separacion entre las dos tiras, una pulgada
ALTO = 2.54 * 16     # alto del rectangulo del simbolo


def _id():
    return str(uuid.uuid4())


def construir_simbolo():
    mitad = ALTO / 2.0
    ancho = 25.4
    pines = []

    # columna izquierda, del 1 al 15, de arriba abajo
    for k, (nombre, tipo) in enumerate(IZQUIERDA):
        y = mitad - PASO * (k + 1)
        pines.append([A('pin'), A(tipo), A('line'),
                      [A('at'), A('%g' % (-ancho / 2 - 5.08)), A('%g' % y),
                       A('0')],
                      [A('length'), A('5.08')],
                      [A('name'), nombre,
                       [A('effects'), [A('font'),
                        [A('size'), A('1.27'), A('1.27')]]]],
                      [A('number'), str(k + 1),
                       [A('effects'), [A('font'),
                        [A('size'), A('1.27'), A('1.27')]]]]])

    # columna derecha, del 16 al 30, de abajo arriba
    for k, (nombre, tipo) in enumerate(DERECHA):
        y = -mitad + PASO * (k + 1)
        pines.append([A('pin'), A(tipo), A('line'),
                      [A('at'), A('%g' % (ancho / 2 + 5.08)), A('%g' % y),
                       A('180')],
                      [A('length'), A('5.08')],
                      [A('name'), nombre,
                       [A('effects'), [A('font'),
                        [A('size'), A('1.27'), A('1.27')]]]],
                      [A('number'), str(k + 16),
                       [A('effects'), [A('font'),
                        [A('size'), A('1.27'), A('1.27')]]]]])

    cuerpo = [A('symbol'), 'ESP32-DevKitV1-30_0_1',
              [A('rectangle'),
               [A('start'), A('%g' % (-ancho / 2)), A('%g' % mitad)],
               [A('end'), A('%g' % (ancho / 2)), A('%g' % -mitad)],
               [A('stroke'), [A('width'), A('0.254')], [A('type'), A('default')]],
               [A('fill'), [A('type'), A('background')]]]]
    unidad = [A('symbol'), 'ESP32-DevKitV1-30_1_1'] + pines

    def prop(nombre, valor, y, oculto=False):
        ef = [A('effects'), [A('font'), [A('size'), A('1.27'), A('1.27')]]]
        if oculto:
            ef.append([A('hide'), A('yes')])
        return [A('property'), nombre, valor,
                [A('at'), A('0'), A('%g' % y), A('0')], ef]

    return [A('symbol'), 'ESP32-DevKitV1-30',
            [A('pin_names'), [A('offset'), A('1.016')]],
            [A('exclude_from_sim'), A('no')],
            [A('in_bom'), A('yes')], [A('on_board'), A('yes')],
            prop('Reference', 'U', mitad + 2.54),
            prop('Value', 'ESP32-DevKitV1-30', -mitad - 2.54),
            prop('Footprint', 'TFC:ESP32_DevKitV1_30pin', 0, True),
            prop('Datasheet', '', 0, True),
            prop('Description', 'Placa ESP32 DevKit V1, 30 contactos', 0, True),
            cuerpo, unidad]


def construir_huella():
    """Huella de dos tiras de quince contactos separadas una pulgada."""
    mitad = PASO * 14 / 2.0
    islas = []

    def isla(num, x, y):
        forma = 'rect' if num == 1 else 'circle'
        return [A('pad'), str(num), A('thru_hole'), A(forma),
                [A('at'), A('%g' % x), A('%g' % y)],
                [A('size'), A('1.7'), A('1.7')],
                [A('drill'), A('1.0')],
                [A('layers'), '*.Cu', '*.Mask'],
                [A('uuid'), _id()]]

    for k in range(15):
        islas.append(isla(k + 1, -ANCHO_FILAS / 2, -mitad + PASO * k))
    for k in range(15):
        islas.append(isla(k + 16, ANCHO_FILAS / 2, mitad - PASO * k))

    # contorno de la placa, 51.5 por 28.3 segun el fabricante
    bx, by = 28.3 / 2, 51.5 / 2
    contorno = []
    esquinas = [(-bx, -by), (bx, -by), (bx, by), (-bx, by), (-bx, -by)]
    for (x1, y1), (x2, y2) in zip(esquinas, esquinas[1:]):
        contorno.append(
            [A('fp_line'), [A('start'), A('%g' % x1), A('%g' % y1)],
             [A('end'), A('%g' % x2), A('%g' % y2)],
             [A('stroke'), [A('width'), A('0.12')], [A('type'), A('default')]],
             [A('layer'), 'F.SilkS'], [A('uuid'), _id()]])

    def texto(tipo, valor, y, capa):
        return [A('property'), tipo, valor,
                [A('at'), A('0'), A('%g' % y), A('0')],
                [A('layer'), capa], [A('uuid'), _id()],
                [A('effects'), [A('font'), [A('size'), A('1'), A('1')],
                 [A('thickness'), A('0.15')]]]]

    return ([A('footprint'), 'ESP32_DevKitV1_30pin',
             [A('version'), A('20241229')],
             [A('generator'), 'tfc_generador'],
             [A('layer'), 'F.Cu'],
             [A('descr'), 'Placa ESP32 DevKit V1 de 30 contactos, dos tiras '
                          'de 15 separadas 25.4 mm'],
             [A('attr'), A('through_hole')],
             texto('Reference', 'REF**', 0, 'F.SilkS'),  # al centro: fuera, chocaba con la serigrafía de Q1 (12 oct 2026)
             texto('Value', 'ESP32_DevKitV1_30pin', by + 2, 'F.Fab')]
            + contorno + islas)


def main():
    if not os.path.isdir(PROY):
        os.makedirs(PROY)

    lib = [A('kicad_symbol_lib'), [A('version'), A('20251024')],
           [A('generator'), 'tfc_generador'],
           [A('generator_version'), '10.0'], construir_simbolo()]
    ruta_sym = os.path.join(PROY, 'TFC.kicad_sym')
    sexp.guardar(ruta_sym, lib)

    carpeta = os.path.join(PROY, 'TFC.pretty')
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    ruta_fp = os.path.join(carpeta, 'ESP32_DevKitV1_30pin.kicad_mod')
    sexp.guardar(ruta_fp, construir_huella())

    # tablas de bibliotecas del proyecto, para que KiCad las encuentre
    io.open(os.path.join(PROY, 'sym-lib-table'), 'w', encoding='utf-8').write(
        '(sym_lib_table\n  (version 7)\n'
        '  (lib (name "TFC")(type "KiCad")(uri "${KIPRJMOD}/TFC.kicad_sym")'
        '(options "")(descr "Símbolos propios del TFC"))\n)\n')
    io.open(os.path.join(PROY, 'fp-lib-table'), 'w', encoding='utf-8').write(
        '(fp_lib_table\n  (version 7)\n'
        '  (lib (name "TFC")(type "KiCad")(uri "${KIPRJMOD}/TFC.pretty")'
        '(options "")(descr "Huellas propias del TFC"))\n)\n')

    # el modelo tridimensional, y la huella apuntando a el
    ruta_3d = escribir_modelo()
    fp = sexp.cargar(ruta_fp)
    fp.append([A('model'), '${KIPRJMOD}/TFC.3dshapes/ESP32_DevKitV1_30pin.wrl',
               [A('offset'), [A('xyz'), A('0'), A('0'), A('0')]],
               [A('scale'), [A('xyz'), A('1'), A('1'), A('1')]],
               [A('rotate'), [A('xyz'), A('0'), A('0'), A('0')]]])
    sexp.guardar(ruta_fp, fp)

    sys.stdout.write('símbolo, huella y modelo 3D del DevKit creados\n')
    sys.stdout.write('  %s\n' % ruta_3d)
    sys.stdout.write('  %s\n  %s\n' % (ruta_sym, ruta_fp))
    sys.stdout.write('  contactos: %d izquierda, %d derecha\n'
                     % (len(IZQUIERDA), len(DERECHA)))




# ---------------------------------------------------------------------------
# Modelo tridimensional de la placa, en VRML
#
# Ninguna de las paginas de modelos, GrabCAD y demas, tiene esta placa generica
# de 35 soles, y las que la tienen exigen cuenta. No hace falta: para lo que el
# modelo sirve aqui, que es comprobar que el conjunto cabe en la bandeja y no
# choca con nada, basta el volumen que ocupa. Se compone de tres cajas: la placa,
# el modulo metalico y el conector de USB.
#
# VRML se escribe en unidades de 0.1 pulgada, que es lo que KiCad espera con
# escala unidad, de modo que cada medida en milimetros se divide por 2.54.
# ---------------------------------------------------------------------------
PULGADA = 2.54

CAJAS = [
    # (nombre, ancho, fondo, alto, desplazamiento en z, color rgb)
    ('placa', 28.3, 51.5, 1.6, 0.8, (0.05, 0.25, 0.12)),
    ('modulo', 18.0, 25.5, 3.2, 3.2, (0.72, 0.70, 0.66)),
    ('usb', 7.6, 5.8, 2.6, 2.9, (0.55, 0.55, 0.58)),
]


def construir_modelo():
    partes = []
    for nombre, w, d, h, z, (r, g, b) in CAJAS:
        # el modulo y el conector no van centrados sino a un extremo
        dy = 0.0
        if nombre == 'modulo':
            dy = 8.0
        elif nombre == 'usb':
            dy = -51.5 / 2 + 2.0
        partes.append("""  Transform {
    translation %.4f %.4f %.4f
    children [
      Shape {
        appearance Appearance { material Material {
          diffuseColor %.3f %.3f %.3f
          specularColor 0.1 0.1 0.1
        } }
        geometry Box { size %.4f %.4f %.4f }
      }
    ]
  }""" % (0.0, dy / PULGADA, z / PULGADA, r, g, b,
          w / PULGADA, d / PULGADA, h / PULGADA))
    return ('#VRML V2.0 utf8\n'
            '# Placa ESP32 DevKit V1 de 30 contactos\n'
            '# Generado por generar_devkit.py para el TFC de Diego Luna\n'
            'Transform {\n  children [\n%s\n  ]\n}\n' % '\n'.join(partes))


def escribir_modelo():
    ruta = os.path.join(PROY, 'TFC.3dshapes')
    if not os.path.isdir(ruta):
        os.makedirs(ruta)
    destino = os.path.join(ruta, 'ESP32_DevKitV1_30pin.wrl')
    io.open(destino, 'w', encoding='utf-8').write(construir_modelo())
    return destino


if __name__ == '__main__':
    main()
