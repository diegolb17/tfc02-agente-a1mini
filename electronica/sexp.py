# -*- coding: utf-8 -*-
"""Lectura y escritura de las expresiones simbolicas de KiCad.

Todos los formatos de KiCad, tanto el esquematico como la placa y las
bibliotecas de simbolos, son listas anidadas entre parentesis con atomos que
pueden ir entre comillas. No hace falta mas que esto para leerlos y escribirlos
sin perder nada.
"""
import io
import re


class Atomo(str):
    """Atomo sin comillas, del tipo de un nombre de orden o un numero.

    Hereda de str para poder compararlo y usarlo como cadena, pero se distingue
    de una cadena normal para que al escribir NO se le pongan comillas: en KiCad
    no es lo mismo (at 0 0) que (at "0" "0")."""
    __slots__ = ()


def leer(texto):
    """Devuelve la primera expresion del texto como listas anidadas."""
    i = 0
    n = len(texto)

    def saltar():
        nonlocal i
        while i < n:
            if texto[i] in ' \t\r\n':
                i += 1
            elif texto[i] == ';':          # comentario hasta fin de linea
                while i < n and texto[i] != '\n':
                    i += 1
            else:
                return

    def expr():
        nonlocal i
        saltar()
        if i >= n:
            raise ValueError('expresión incompleta')
        if texto[i] == '(':
            i += 1
            out = []
            while True:
                saltar()
                if i >= n:
                    raise ValueError('falta un paréntesis de cierre')
                if texto[i] == ')':
                    i += 1
                    return out
                out.append(expr())
        if texto[i] == '"':
            i += 1
            trozos = []
            while i < n and texto[i] != '"':
                if texto[i] == '\\':
                    trozos.append(texto[i + 1])
                    i += 2
                else:
                    trozos.append(texto[i])
                    i += 1
            i += 1
            return ''.join(trozos)
        j = i
        while i < n and texto[i] not in ' \t\r\n()':
            i += 1
        return Atomo(texto[j:i])

    return expr()


def _escribir_atomo(a):
    if isinstance(a, Atomo):
        return str(a)
    s = str(a).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return '"%s"' % s


def escribir(e, sangria=0):
    """Compone el texto de una expresion, con la sangria de tabuladores que usa
    KiCad para que los archivos se puedan comparar con los suyos."""
    if not isinstance(e, list):
        return _escribir_atomo(e)
    if not e:
        return '()'
    # las expresiones cortas de solo atomos caben en una linea
    if all(not isinstance(x, list) for x in e):
        return '(' + ' '.join(_escribir_atomo(x) for x in e) + ')'
    tab = '\t' * (sangria + 1)
    partes = ['(' + _escribir_atomo(e[0])]
    resto = e[1:]
    # los atomos que siguen al nombre de la orden se quedan en su misma linea
    k = 0
    while k < len(resto) and not isinstance(resto[k], list):
        partes[0] += ' ' + _escribir_atomo(resto[k])
        k += 1
    for x in resto[k:]:
        partes.append(tab + escribir(x, sangria + 1))
    return '\n'.join(partes) + '\n' + '\t' * sangria + ')'


def buscar(e, nombre):
    """Las sublistas de e cuyo primer elemento es nombre."""
    return [x for x in e if isinstance(x, list) and x and x[0] == nombre]


def uno(e, nombre):
    """La primera sublista con ese nombre, o None."""
    r = buscar(e, nombre)
    return r[0] if r else None


def cargar(ruta):
    return leer(io.open(ruta, encoding='utf-8').read())


def guardar(ruta, e):
    io.open(ruta, 'w', encoding='utf-8', newline='\n').write(escribir(e) + '\n')
