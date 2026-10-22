# -*- coding: utf-8 -*-
"""STL de impresion de las piezas propias, desde la geometria exportada de Fusion (_geom/*.tri, malla de calidad muy
alta, tolerancia 0.03 mm). Cada pieza se orienta como dicen las notas de su lamina, se apoya en z = 0 y se centra en
la cama de la A1 mini (180 x 180 x 180 mm). Las piezas que no caben en ese volumen no se exportan a la carpeta de
impresion: van a IMPRESION/STL_no_cabe con el aviso en el informe.
Uso: python exportar_stl.py"""
import os
import struct

import numpy as np

from motor.malla import leer_tri

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.normpath(os.path.join(AQUI, '..', 'IMPRESION'))
CAMA = 180.0

I = np.eye(3)
X_A_Z = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)      # (x, y, z) -> (y, z, x): el eje x local queda vertical
MENOS_X_A_Z = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)  # el eje -x local queda vertical
Y_A_Z = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)      # el eje y local queda vertical
INVERTIR = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float)  # giro de 180 grados alrededor de x

# codigo de lamina, nombre, copias, orientacion, nota de impresion (de la lamina)
PIEZAS = [
    ('MEC-2-01', 'Cuna_frontal_derecha', 1, I, 'Cara de apoyo sobre la bandeja hacia abajo; la cara inclinada lleva soportes.'),
    ('MEC-2-02', 'Cuna_frontal_izquierda', 1, I, 'Igual que MEC-2-01.'),
    ('MEC-2-03', 'Cuna_posterior_derecha', 1, I, 'Igual que MEC-2-01. Recibe el soporte de la cámara (ensayo K.10).'),
    ('MEC-2-04', 'Cuna_posterior_izquierda', 1, I, 'Igual que MEC-2-01.'),
    ('MEC-2-05', 'Bandeja_frontal_derecha', 1, I, 'Cara inferior sobre la cama, sin soportes.'),
    ('MEC-2-06', 'Bandeja_frontal_izquierda', 1, I, 'Igual que MEC-2-05.'),
    ('MEC-2-07', 'Bandeja_posterior_derecha', 1, I, 'Igual que MEC-2-05.'),
    ('MEC-2-08', 'Bandeja_posterior_izquierda', 1, I, 'Igual que MEC-2-05.'),
    ('MEC-2-09', 'Soporte_ventilador', 1, I, 'Base sobre la cama.'),
    ('MEC-2-10', 'Ducto_cuchilla', 1, Y_A_Z, 'Brida sobre la cama, ranura hacia arriba; sin soportes interiores.'),
    ('MEC-2-11', 'Rejilla_frontal_derecha', 1, X_A_Z, 'Cara exterior sobre la cama.'),
    ('MEC-2-11', 'Rejilla_frontal_izquierda', 1, X_A_Z, 'Cara exterior sobre la cama.'),
    ('MEC-2-12', 'Soporte_actuador', 1, MENOS_X_A_Z, 'Base sobre la cama, canal hacia arriba.'),
    ('MEC-2-13', 'Tapa_actuador', 1, X_A_Z, 'Cara de 40 x 24 sobre la cama.'),
    ('MEC-2-14', 'Soporte_camara', 1, I, 'Placa sobre la cama, tubo vertical, sin soportes.'),
    ('MEC-2-15', 'Horquilla_camara', 1, I, 'Base del collarín sobre la cama, copa hacia arriba, sin soportes.'),
    ('MEC-2-16', 'Carcasa_ESP32CAM', 1, INVERTIR, 'Techo de la caja sobre la cama; cuello y bola hacia arriba, con soportes bajo la bola.'),
    ('MEC-2-17', 'Horquilla_lampara', 1, I, 'Base de la abrazadera y del brazo sobre la cama, copa hacia arriba.'),
    ('MEC-2-18', 'Aro_lampara', 1, I, 'Aro de canto con la bola hacia abajo, con soportes bajo la bola.'),
]


def escribir_stl(ruta, tri, nombre):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    lon = np.linalg.norm(n, axis=1)
    lon[lon == 0] = 1
    n = (n / lon[:, None]).astype('<f4')
    reg = np.zeros(len(tri), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    reg['n'] = n
    reg['v'] = tri.astype('<f4')
    with open(ruta, 'wb') as f:
        f.write(('%s, mm, TFC02 Diego Luna' % nombre).encode('ascii', 'replace')[:80].ljust(80, b' '))
        f.write(struct.pack('<I', len(tri)))
        f.write(reg.tobytes())


def main():
    os.makedirs(os.path.join(SALIDA, 'STL'), exist_ok=True)
    os.makedirs(os.path.join(SALIDA, 'STL_no_cabe'), exist_ok=True)
    filas = []
    for codigo, nombre, copias, R, nota in PIEZAS:
        V, F, _ = leer_tri(os.path.join(AQUI, '_geom', nombre + '.tri'))
        V = V @ R.T
        mn, mx = V.min(axis=0), V.max(axis=0)
        V = V - np.array([(mn[0] + mx[0]) / 2 - CAMA / 2, (mn[1] + mx[1]) / 2 - CAMA / 2, mn[2]])
        dim = mx - mn
        tri = V[F]
        vol = np.einsum('ij,ij->i', tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0 / 1000.0
        cabe = bool((dim <= CAMA + 1e-6).all())
        carpeta = 'STL' if cabe else 'STL_no_cabe'
        archivo = '%s_%s.stl' % (codigo, nombre)
        escribir_stl(os.path.join(SALIDA, carpeta, archivo), tri, nombre)
        filas.append((codigo, nombre, copias, dim, vol, cabe, nota, archivo))
        print('%-9s %-28s %6.1f x %6.1f x %6.1f mm  %7.1f cm3  %s' % (codigo, nombre, dim[0], dim[1], dim[2], vol,
                                                                  'cabe' if cabe else 'NO CABE en 180 mm'))
    return filas


if __name__ == '__main__':
    main()
