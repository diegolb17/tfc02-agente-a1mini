# -*- coding: utf-8 -*-
"""Vista explosionada del conjunto para la sección 4.1 de la tesis (marca de Diego del 13 oct 2026: "una foto
entera de toda la estructura y la vista explotada también"). Usa los mismos desplazamientos que la lámina MEC-0-02,
pero con llamadas por módulo en lugar de globos, para que se lea sin la lista de piezas.
Salida: TESIS_LATEX/Imagenes/fig_cap4_despiece.png (300 dpi, fondo blanco, sin cajetín)."""
import numpy as np

from ensambles import PIEZAS, DESPIECE, conjunto, centroide
from figuras_cap4 import recortar_y_guardar, Z
from motor.hoja import Lamina, Vista, nota


def punto(nombre):
    return tuple(centroide(nombre) + np.asarray(DESPIECE.get(nombre, (0, 0, 0)), float))


def fig_despiece():
    pz = conjunto([p[1] for p in PIEZAS], desplazar=DESPIECE)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.62), Z, 0.30, ocultas=False, nombre='iso', res=0.15).colocar_centro(212, 160)
    v.dibujar(lam)
    T = 7.4      # 15 oct: rotulos mas grandes (Denis Pena); a ancho de pagina quedan cerca de 9 puntos
    nota(lam, v, punto('Cuna_posterior_izquierda'), ['Estructura inclinada', '(cuatro cuartos)'], -40, 40, tam=T)
    nota(lam, v, punto('Bandeja_posterior_izquierda'), ['Bandeja de la electrónica', '(cuatro cuartos)'], -30, -20, tam=T)
    nota(lam, v, punto('Rejilla_frontal_derecha'), 'Rejillas de admisión', 34, -24, tam=T)
    nota(lam, v, punto('Soporte_actuador'), 'Soporte del actuador', -22, -54, tam=T)
    nota(lam, v, punto('Soporte_ventilador'), ['Módulo de enfriamiento', '(soporte del ventilador y ducto)'], 30, -30, tam=T)
    nota(lam, v, punto('Carcasa_ESP32CAM'), ['Unidad de visión', '(tubo, horquilla y carcasa)'], -40, 14, tam=T)
    nota(lam, v, punto('Aro_lampara'), ['Unidad de iluminación', '(horquilla y aro del dicroico)'], 30, 12, tam=T)
    recortar_y_guardar(lam, 'fig_cap4_despiece')


def fig_general():
    """Vista general con el equipo, llamadas legibles a ancho de página (reemplaza a fig_cap4_21)."""
    todos = [p[1] for p in PIEZAS] + ['Equipo_A1mini']
    pz = conjunto(todos)
    lam = Lamina('A3')
    v = Vista(pz, (1, -1, -0.7), Z, 0.40, ocultas=False, nombre='iso', res=0.15).colocar_centro(210, 150)
    v.dibujar(lam)
    T = 5.6
    nota(lam, v, (139, 60, 327), ['Unidad de visión: cámara ESP32-CAM', 'sobre rótula y soporte tubular'], 40, 22, tam=T)
    nota(lam, v, (87, 43, 271), ['Unidad de iluminación', '(dicroico MR16 sobre rótula)'], 64, -2, tam=T)
    nota(lam, v, (100, 60, 120), ['Módulo de enfriamiento', 'en la bahía lateral'], 46, -40, tam=T)
    nota(lam, v, (-12, 294, 22), 'Soporte del actuador lineal', -40, -26, tam=T)
    nota(lam, v, tuple(centroide('Equipo_A1mini')), 'Impresora Bambu Lab A1 mini', -90, 40, tam=T)
    recortar_y_guardar(lam, 'fig_cap4_21')


if __name__ == '__main__':
    fig_despiece()
    # fig_general() ya no se usa: la vista general la genera figuras_cap4_15oct.py con la impresora en gris
