# -*- coding: utf-8 -*-
"""Localiza y extrae simbolos de las bibliotecas que trae KiCad.

Un esquematico de KiCad no referencia las bibliotecas: lleva DENTRO, en su
bloque lib_symbols, una copia completa de cada simbolo que usa. Por eso hace
falta sacarlos de las bibliotecas e incrustarlos, y por eso el esquematico sigue
abriendose aunque cambien las bibliotecas del sistema.
"""
import glob
import os
import sys

import sexp

KICAD = r'C:\Program Files\KiCad\10.0\share\kicad'
LIBS = os.path.join(KICAD, 'symbols')

_cache = {}


# La biblioteca propia del proyecto, con los simbolos que KiCad no trae.
PROPIA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'TFC_Remocion', 'TFC.kicad_sym')


def cargar_lib(nombre):
    if nombre not in _cache:
        ruta = PROPIA if nombre == 'TFC' else os.path.join(
            LIBS, nombre + '.kicad_sym')
        _cache[nombre] = sexp.cargar(ruta) if os.path.exists(ruta) else None
    return _cache[nombre]


def buscar(patron, limite=40):
    """Busca un simbolo por subcadena en todas las bibliotecas."""
    p = patron.lower()
    out = []
    for ruta in sorted(glob.glob(os.path.join(LIBS, '*.kicad_sym'))):
        lib = os.path.splitext(os.path.basename(ruta))[0]
        try:
            e = sexp.cargar(ruta)
        except Exception:
            continue
        for s in sexp.buscar(e, 'symbol'):
            if p in str(s[1]).lower():
                out.append('%s:%s' % (lib, s[1]))
                if len(out) >= limite:
                    return out
    return out


def _crudo(lib, nombre):
    e = cargar_lib(lib)
    if e is None:
        raise KeyError('no existe la biblioteca %s' % lib)
    for s in sexp.buscar(e, 'symbol'):
        if str(s[1]) == nombre:
            return s
    raise KeyError('no existe el símbolo %s:%s' % (lib, nombre))


def para_incrustar(lib_id):
    """Devuelve las definiciones a meter en el bloque lib_symbols del esquematico.

    KiCad no resuelve la herencia al incrustar: guarda el simbolo hijo CON su
    declaracion (extends ...) y guarda tambien el padre. Si en su lugar se mete
    el hijo ya resuelto, el esquematico funciona y la lista de redes es correcta,
    pero KiCad avisa de que "el simbolo no coincide con la copia en la
    biblioteca" cada vez que se abre, porque compara contra el original heredado.

    Se devuelve una lista, de uno o de dos elementos segun haya herencia.
    """
    lib, nombre = lib_id.split(':', 1)
    s = _crudo(lib, nombre)
    ext = sexp.uno(s, 'extends')
    hijo = [x for x in s]
    hijo[1] = lib_id
    if ext is None:
        return [(lib_id, hijo)]
    padre_id = '%s:%s' % (lib, ext[1])
    padre = [x for x in _crudo(lib, str(ext[1]))]
    padre[1] = padre_id
    return [(padre_id, padre), (lib_id, hijo)]


def extraer(lib_id):
    """Devuelve la definicion del simbolo lista para incrustar.

    KiCad exige que dentro del esquematico el simbolo se llame "Lib:Nombre" y no
    solo "Nombre", que es como figura en la biblioteca.

    RESUELVE LA HERENCIA. Muchos simbolos no definen nada y se limitan a
    declarar (extends "Otro"): el IRLZ44N, por ejemplo, hereda del Q_NMOS_GSD
    todos sus pines y su dibujo, y leido sin resolver la herencia aparece SIN UN
    SOLO PIN. Aqui se copian del padre las unidades, que es donde viven los
    pines y los trazos, y se conservan del hijo sus propiedades, que son las que
    llevan el nombre y el encapsulado correctos.
    """
    lib, nombre = lib_id.split(':', 1)
    s = _crudo(lib, nombre)
    ext = sexp.uno(s, 'extends')
    copia = [x for x in s]
    if ext is not None:
        padre = _crudo(lib, str(ext[1]))
        # fuera la declaracion de herencia, que ya no hace falta
        copia = [x for x in copia
                 if not (isinstance(x, list) and x and x[0] == 'extends')]
        # las unidades del hijo, si las hubiera, no se conservan: son del padre
        copia = [x for x in copia
                 if not (isinstance(x, list) and x and x[0] == 'symbol')]
        propias = {str(p[1]) for p in sexp.buscar(copia, 'property')}
        for p in sexp.buscar(padre, 'property'):
            if str(p[1]) not in propias:
                copia.append(p)
        for u in sexp.buscar(padre, 'symbol'):
            unidad = [x for x in u]
            # la unidad se llama "Padre_1_1" y hay que rebautizarla
            unidad[1] = str(u[1]).replace(str(ext[1]), nombre, 1)
            copia.append(unidad)
    copia[1] = lib_id
    return copia


def pines(lib_id):
    """Los pines del simbolo: (numero, nombre, tipo, x, y, giro).

    Se recorren tambien las unidades, porque en KiCad los pines no cuelgan del
    simbolo padre sino de sus subsimbolos de unidad."""
    s = extraer(lib_id)
    out = []

    def recorrer(nodo):
        for p in sexp.buscar(nodo, 'pin'):
            at = sexp.uno(p, 'at')
            num = sexp.uno(p, 'number')
            nom = sexp.uno(p, 'name')
            out.append((str(num[1]) if num else '?',
                        str(nom[1]) if nom else '?',
                        str(p[1]), float(at[1]), float(at[2]),
                        float(at[3]) if len(at) > 3 else 0.0))
        for sub in sexp.buscar(nodo, 'symbol'):
            recorrer(sub)

    recorrer(s)
    return out


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for q in sys.argv[1:]:
            sys.stdout.write('=== %s ===\n' % q)
            for r in buscar(q):
                sys.stdout.write('  %s\n' % r)
