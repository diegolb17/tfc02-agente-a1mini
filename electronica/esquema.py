# -*- coding: utf-8 -*-
"""Construccion de esquematicos de KiCad 10 desde Python.

LO QUE HAY QUE SABER DE LAS COORDENADAS. En la biblioteca de simbolos el eje Y
crece hacia arriba, y en la hoja del esquematico crece hacia abajo. Un pin que
en la biblioteca esta en (px, py) aparece, con el simbolo colocado en (x, y) y
sin girar, en el punto (x + px, y - py) de la hoja. Equivocarse en ese signo
produce un esquematico que se abre y se ve bien pero cuya lista de redes esta
mal, que es el peor de los errores posibles.

Todo se apoya en una rejilla de 1.27 mm, que es la que KiCad usa para conectar:
un cable que no acabe en un multiplo de 1.27 no conecta con el pin aunque
parezca que lo toca.
"""
import math
import uuid

import sexp
from sexp import Atomo as A

REJILLA = 1.27


def _id():
    return str(uuid.uuid4())


# Simbolos a los que se les quita el NOMBRE de los pines.
#
# El diodo trae sus pines llamados A y K, y la biblioteca los escribe con
# desplazamiento cero, esto es pegados al cuerpo. En un simbolo de 7.62 mm las
# dos letras se pisan, y sobre todo sobran: la banda del catodo ya esta
# dibujada y es la forma normalizada de declarar la polaridad. El numero de pin
# se conserva, que es lo que relaciona el simbolo con su huella.
SIN_NOMBRE_DE_PIN = {'Diode:1N5822'}


def ocultar_nombres_de_pin(nodo):
    """Pone (hide yes) dentro de (pin_names ...) del simbolo de biblioteca.

    Si el simbolo no declara (pin_names ...) se le añade: la ausencia NO
    significa que los nombres esten ocultos sino todo lo contrario, que se
    dibujan con los valores por omision. El 1N5822 es de esos."""
    pns = sexp.buscar(nodo, 'pin_names')
    if not pns:
        pns = [[A('pin_names'), [A('offset'), A('0')]]]
        nodo.insert(2, pns[0])
    for pn in pns:
        if not sexp.uno(pn, 'hide'):
            pn.append([A('hide'), A('yes')])
    return nodo


def g(n):
    """Convierte unidades de rejilla en milimetros.

    TODO se coloca en multiplos de 1.27 mm. Si un simbolo se coloca en una
    coordenada que no lo es, sus pines caen fuera de la rejilla y los cables no
    conectan aunque el dibujo parezca correcto."""
    return round(n * REJILLA, 4)


def redondear(v):
    """Redondeo a la centesima de milimetro, para quitar ruido de coma flotante.

    NO se ajusta a la rejilla: hacerlo desplazaria el pin, porque la rejilla se
    ancla en el origen de la hoja y no en el simbolo. Colocando los simbolos en
    multiplos de 1.27 los pines caen solos donde deben."""
    return round(v, 2)


class Hoja:
    """Una hoja de esquematico en construccion."""

    def __init__(self, titulo='', papel='A3'):
        self.titulo = titulo
        self.papel = papel
        self.elementos = []
        self.libs = {}
        self.instancias = []
        self.uuid = _id()

    # -- primitivas ---------------------------------------------------------
    def cable(self, x1, y1, x2, y2):
        self.elementos.append(
            [A('wire'), [A('pts'), [A('xy'), A('%g' % x1), A('%g' % y1)],
                         [A('xy'), A('%g' % x2), A('%g' % y2)]],
             [A('stroke'), [A('width'), A('0')], [A('type'), A('default')]],
             [A('uuid'), _id()]])

    def etiqueta(self, texto, x, y, rot=0, global_=True):
        clase = 'global_label' if global_ else 'label'
        e = [A(clase), texto,
             [A('shape'), A('input')] if global_ else None,
             [A('at'), A('%g' % x), A('%g' % y), A('%g' % rot)],
             [A('effects'), [A('font'), [A('size'), A('1.27'), A('1.27')]],
              [A('justify'), A('left')]],
             [A('uuid'), _id()]]
        self.elementos.append([x for x in e if x is not None])

    def alimentacion(self, tipo, x, y, rot=0):
        """Simbolo de alimentacion: power:GND, power:+24V, etc."""
        lib_id = 'power:%s' % tipo
        self.usar(lib_id)
        ref = '#PWR%03d' % (len([e for e in self.instancias
                                 if e[0].startswith('#PWR')]) + 1)
        self._colocar(lib_id, ref, tipo, x, y, rot, '', oculto_ref=True)

    def componente(self, lib_id, ref, valor, x, y, rot=0, footprint='',
                   campos=None):
        self.usar(lib_id)
        self._colocar(lib_id, ref, valor, x, y, rot, footprint, campos=campos)
        return ref

    # -- interno ------------------------------------------------------------
    def usar(self, lib_id):
        # El simbolo se incrusta con la herencia YA RESUELTA.
        #
        # Se probo a guardarlo como lo guarda KiCad, con su (extends ...) y el
        # padre al lado, que es lo que quitaria el aviso de "no coincide con la
        # copia en la biblioteca". No funciona: KiCad no resuelve esa herencia
        # dentro del bloque incrustado, los simbolos derivados se quedan sin
        # pines y las redes se parten. Entre un aviso cosmetico y una lista de
        # redes rota, se prefiere el aviso.
        if lib_id not in self.libs:
            import simbolos
            s = simbolos.extraer(lib_id)
            if lib_id in SIN_NOMBRE_DE_PIN:
                ocultar_nombres_de_pin(s)
            self.libs[lib_id] = s

    def extension(self, lib_id, rot=0):
        """Alcance vertical del simbolo, del pin mas alto al mas bajo.

        Sirve para saber DONDE poner el texto de referencia y de valor. Ponerlos
        a una distancia fija, que es lo que se hacia, funciona con una
        resistencia y falla con un conector de cuatro contactos o con un
        integrado: el valor caia encima de la etiqueta del ultimo pin. Con el
        alcance real, el texto sale siempre por fuera del simbolo.

        CON EL SIMBOLO GIRADO el alcance vertical ya no es el de la biblioteca:
        un diodo tumbado mide 7.62 mm de ancho y 2 de alto, y de pie al reves.
        Tomar el de la biblioteca dejaba el valor del diodo, que es la cadena
        mas larga del plano, escrito ENCIMA de sus propios pines. Para los
        giros de 90 y 270 se toma el mayor de los dos alcances, que es una cota
        por arriba y siempre deja el texto fuera."""
        import simbolos
        ps = simbolos.pines(lib_id)
        if not ps:
            return (-2.54, 2.54)
        ys = [p[4] for p in ps]
        if rot % 180:
            r = max(max(abs(p[3]) for p in ps), max(abs(v) for v in ys))
            return (-r, r)
        return (min(ys), max(ys))

    def _colocar(self, lib_id, ref, valor, x, y, rot, footprint,
                 oculto_ref=False, campos=None):
        efectos_ocultos = [A('effects'), [A('font'),
                           [A('size'), A('1.27'), A('1.27')]], [A('hide'), A('yes')]]
        # el texto se separa segun lo alto que sea el simbolo, no a ojo
        try:
            ymin, ymax = self.extension(lib_id, rot)
        except Exception:
            ymin, ymax = -2.54, 2.54
        arriba = y - max(ymax, 2.54) - 2.54
        abajo = y + max(-ymin, 2.54) + 2.54
        # EL GIRO DEL TEXTO SE CANCELA. KiCad suma el giro del simbolo al de su
        # campo, de modo que con el angulo en cero el valor de una resistencia
        # tumbada salia escrito en vertical. Restandolo, la referencia y el
        # valor se leen siempre en horizontal, que es como se lee un plano.
        ang = A('%g' % ((360 - rot) % 360))
        props = [
            [A('property'), 'Reference', ref, [A('at'), A('%g' % x),
             A('%g' % arriba), ang],
             efectos_ocultos if oculto_ref else
             [A('effects'), [A('font'), [A('size'), A('1.27'), A('1.27')]]]],
            [A('property'), 'Value', valor, [A('at'), A('%g' % x),
             A('%g' % abajo), ang],
             [A('effects'), [A('font'), [A('size'), A('1.27'), A('1.27')]]]],
            [A('property'), 'Footprint', footprint,
             [A('at'), A('%g' % x), A('%g' % y), A('0')], efectos_ocultos],
            [A('property'), 'Datasheet', '',
             [A('at'), A('%g' % x), A('%g' % y), A('0')], efectos_ocultos],
        ]
        for k, v in (campos or {}).items():
            props.append([A('property'), k, v,
                          [A('at'), A('%g' % x), A('%g' % y), A('0')],
                          efectos_ocultos])

        s = [A('symbol'), [A('lib_id'), lib_id],
             [A('at'), A('%g' % x), A('%g' % y), A('%g' % rot)],
             [A('unit'), A('1')],
             [A('exclude_from_sim'), A('no')],
             [A('in_bom'), A('yes')], [A('on_board'), A('yes')],
             [A('dnp'), A('no')],
             [A('uuid'), _id()]] + props
        # las instancias son lo que da a KiCad la referencia por hoja
        s.append([A('instances'), [A('project'), '',
                  [A('path'), '/' + self.uuid,
                   [A('reference'), ref], [A('unit'), A('1')]]]])
        self.elementos.append(s)
        self.instancias.append((ref, lib_id, valor, footprint))

    # -- utilidades de conexion --------------------------------------------
    def pin_xy(self, lib_id, x, y, rot, numero):
        """Punto de la hoja donde queda un pin del simbolo colocado."""
        import simbolos
        for num, _nom, _tipo, px, py, _o in simbolos.pines(lib_id):
            if num == str(numero):
                a = math.radians(rot)
                # giro en el sistema de la biblioteca, con Y hacia arriba
                rx = px * math.cos(a) - py * math.sin(a)
                ry = px * math.sin(a) + py * math.cos(a)
                return redondear(x + rx), redondear(y - ry)
        raise KeyError('%s no tiene pin %s' % (lib_id, numero))

    def no_conectado(self, lib, xy, rot, num):
        """Marca un pin como deliberadamente sin conectar.

        Sirve para que la comprobacion de reglas distinga la patilla que se deja
        libre a proposito de la que se olvido conectar, que es justo lo que esa
        comprobacion existe para encontrar."""
        px, py = self.pin_xy(lib, xy[0], xy[1], rot, num)
        self.elementos.append(
            [A('no_connect'), [A('at'), A('%g' % px), A('%g' % py)],
             [A('uuid'), _id()]])

    def bandera(self, red, x, y):
        """Bandera de alimentacion sobre una red, con su etiqueta.

        Declara que esa red esta alimentada desde fuera de la placa. Sin ella la
        comprobacion de reglas da por no alimentado todo riel que entre por un
        conector, que aqui son los cinco."""
        self.usar('power:PWR_FLAG')
        n = len([e for e in self.instancias if e[0].startswith('#FLG')]) + 1
        self._colocar('power:PWR_FLAG', '#FLG%03d' % n, 'PWR_FLAG',
                      x, y, 0, '', oculto_ref=True)
        # el rabo es de SEIS unidades y no de dos: el texto "PWR_FLAG" del
        # propio simbolo se dibuja justo debajo de el, y con dos unidades la
        # etiqueta de la red, que va en vertical, le pasaba por encima
        px, py = self.pin_xy('power:PWR_FLAG', x, y, 0, '1')
        # El rotulo va HORIZONTAL y colgado de un rabo de diez unidades. En
        # vertical, que es lo natural para un cable que baja, el recuadro de la
        # etiqueta crece hacia arriba desde su punta y tapaba el texto
        # "PWR_FLAG" del propio simbolo, en las siete banderas a la vez.
        self.cable(px, py, px, py + REJILLA * 10)
        self.etiqueta(red, px, py + REJILLA * 10, 0)

    def texto(self, t, x, y, tam=2.0):
        self.elementos.append(
            [A('text'), t, [A('exclude_from_sim'), A('no')],
             [A('at'), A('%g' % x), A('%g' % y), A('0')],
             [A('effects'), [A('font'), [A('size'), A('%g' % tam),
              A('%g' % tam)], [A('bold'), A('yes')]],
              [A('justify'), A('left')]],
             [A('uuid'), _id()]])

    # -- salida -------------------------------------------------------------
    def a_sexp(self):
        return ([A('kicad_sch'),
                 [A('version'), A('20251024')],
                 [A('generator'), 'tfc_generador'],
                 [A('generator_version'), '10.0'],
                 [A('uuid'), self.uuid],
                 [A('paper'), self.papel],
                 [A('title_block'), [A('title'), self.titulo],
                  [A('company'), 'PUCP  Diego Manuel Luna Baldwin  20211878']],
                 [A('lib_symbols')] + list(self.libs.values())]
                + self.elementos
                + [[A('sheet_instances'),
                    [A('path'), '/', [A('page'), '1']]]])

    def guardar(self, ruta):
        sexp.guardar(ruta, self.a_sexp())
