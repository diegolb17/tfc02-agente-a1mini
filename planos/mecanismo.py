# -*- coding: utf-8 -*-
"""MEC-1-05, lámina de detalle del mecanismo de remoción (22 oct 2026, P12 del acta).

El actuador es comercial y no está en el modelo: se representa por su envolvente simplificada (Actuonix, 2019,
p. 4: 18 x 15 de sección, 102 mm entre agujeros recogido, agujeros Ø4.25 que admiten M4), con el agujero
posterior en el eje del canal del soporte (X -15.5, Y 294) a Z 9, donde lo retiene el tornillo M4 x 55."""
import math
import numpy as np
from laminas import lamina, Pieza, Lamina, Vista, cota, nota, titulo_vista, tabla, iso, X, Y, Z
from motor.malla import Malla, rasgos
from motor.hoja import traza, eje_circulo
from ensambles import pieza_ens, s20, _fantasma, _ensamble_datos

ACT_X, ACT_Y, ACT_Z = -15.5, 294.0, 9.0                # agujero posterior del actuador
ACT_ENTRE_AGUJEROS = 102.0                             # recogido, carrera de 50
ACT_PUNTA = ACT_Z + ACT_ENTRE_AGUJEROS + 4.5           # extremo de la horquilla: radio 4.5 sobre su agujero
FLEXION = 30.0                                         # flecha impuesta a la lámina (sección de flexión)
Z_LAMINA_MODELO = 85.12                                # cara inferior de la lámina en el marco de la impresora


def _caja(x0, x1, y0, y1, z0, z1, fid):
    V = np.array([[x, y, z] for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)], float)
    c = V.mean(axis=0)
    F, FI, bordes = [], [], {}
    for k, (a, b, cc, d) in enumerate([(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]):
        if np.dot(np.cross(V[b] - V[a], V[cc] - V[a]), V[a] - c) < 0:
            b, d = d, b
        F += [(a, b, cc), (a, cc, d)]
        FI += [fid + k, fid + k]
        for i, j in ((a, b), (b, cc), (cc, d), (d, a)):
            bordes.setdefault(tuple(sorted((i, j))), []).append(fid + k)
    return V, np.array(F), np.array(FI), [{'pts': V[[i, j]], 'f': f, 'suave': False} for (i, j), f in bordes.items()]


def _cilindro_z(cx, cy, r, z0, z1, fid, n=48):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ab = np.c_[cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z0)]
    ar = ab.copy()
    ar[:, 2] = z1
    V = np.vstack([ab, ar, [[cx, cy, z0], [cx, cy, z1]]])
    F, FI = [], []
    for i in range(n):
        j = (i + 1) % n
        F += [(i, j, n + j), (i, n + j, n + i), (2 * n, j, i), (2 * n + 1, n + i, n + j)]
        FI += [fid, fid, fid + 1, fid + 2]
    ars = [{'pts': np.vstack([ab, ab[:1]]), 'f': [fid, fid + 1], 'suave': False},
           {'pts': np.vstack([ar, ar[:1]]), 'f': [fid, fid + 2], 'suave': False}]
    return V, np.array(F), np.array(FI), ars


def actuador_envolvente():
    partes = [_caja(ACT_X - 4.5, ACT_X + 4.5, ACT_Y - 4, ACT_Y + 4, ACT_Z - 4.5, ACT_Z + 6, 9000),   # orejeta
              _caja(-24.5, -6.5, ACT_Y - 7.5, ACT_Y + 7.5, ACT_Z + 6, 93.0, 9010),                # cuerpo
              _cilindro_z(ACT_X, ACT_Y, 3.0, 93.0, ACT_PUNTA, 9020)]                              # vástago
    Vs, Fs, FIs, ars, base = [], [], [], [], 0
    for V, F, FI, A in partes:
        Vs.append(V)
        Fs.append(F + base)
        FIs.append(FI)
        ars += A
        base += len(V)
    return Pieza(malla=Malla(np.vstack(Vs), np.vstack(Fs), np.concatenate(FIs)), aristas_=ars)


def geometria():
    """Altura de la cara inferior de la lámina en el eje del vástago, aproximación y recorrido (mm)."""
    s, c = math.sin(math.radians(20)), math.cos(math.radians(20))
    xl = (ACT_X + Z_LAMINA_MODELO * s) / c
    z_lamina = s20(xl, ACT_Y, Z_LAMINA_MODELO)[2]
    aprox = z_lamina - ACT_PUNTA
    return z_lamina, aprox, aprox + FLEXION


@lamina('MEC-1-05', 'Sub', 'SUBCONJUNTO DEL MECANISMO DE REMOCIÓN')
def mec_1_05(codigo, nombre, titulo):
    act = actuador_envolvente()
    pz = Pieza.unir([pieza_ens('Soporte_actuador'), pieza_ens('Tapa_actuador')])
    todo = Pieza.unir([pz, act])
    lam = Lamina('A3')
    z_lamina, aprox, recorrido = geometria()
    zt = ACT_PUNTA + recorrido

    # --- corte C-C por el eje del actuador (Y 294), mirando hacia +Y
    va = Vista(pz, Y, Z, 1.0, ocultas=False, corte=((0, ACT_Y, 0), (0, 1, 0)), nombre='corteC', res=0.05)
    va.colocar_punto((0, ACT_Y, 0), x=92, y=78)
    va.dibujar(lam)
    # el actuador es un elemento comercial: no se raya, se dibuja entero por delante del corte
    vaa = Vista(act, Y, Z, 1.0, ocultas=False, nombre='actC', res=0.05)
    vaa.colocar_punto((0, ACT_Y, 0), x=92, y=78)
    vaa.dibujar(lam, rayado=False)
    _fantasma(lam, va, [s20(10, ACT_Y, 85.12), s20(75, ACT_Y, 85.12), s20(75, ACT_Y, 87.62), s20(10, ACT_Y, 87.62),
                        s20(10, ACT_Y, 85.12)])
    _fantasma(lam, va, [(ACT_X - 3, ACT_Y, 93), (ACT_X - 3, ACT_Y, zt), (ACT_X + 3, ACT_Y, zt), (ACT_X + 3, ACT_Y, 93)])
    lam.circulo(va.m((ACT_X, ACT_Y, ACT_Z)), 2.0, 'visible')
    eje_circulo(lam, va, (ACT_X, ACT_Y, ACT_Z), 2.0)
    x1 = va.rect[0] - 8
    cota(lam, va, (-24, ACT_Y, 0), (ACT_X, ACT_Y, ACT_Z), x1, 'v', texto='9')
    cota(lam, va, (ACT_X, ACT_Y, ACT_Z), (ACT_X, ACT_Y, ACT_Z + ACT_ENTRE_AGUJEROS), x1, 'v', texto='102')
    cota(lam, va, (ACT_X, ACT_Y, ACT_PUNTA), (ACT_X, ACT_Y, z_lamina), x1 - 10, 'v', texto='%.1f' % aprox)
    cota(lam, va, (ACT_X, ACT_Y, ACT_PUNTA), (ACT_X, ACT_Y, zt), x1 - 20, 'v', texto='%.1f' % recorrido)
    cota(lam, va, (ACT_X, ACT_Y, ACT_Z), (0, ACT_Y, 0), va.rect[1] - 8, 'h', texto='15.5')
    nota(lam, va, (ACT_X + 1.5, ACT_Y, ACT_Z - 1.5), ['TORNILLO ISO 4762 M4 x 55,', 'EJE DEL AGUJERO POSTERIOR'], -18, -32, tam=2.8)
    nota(lam, va, s20(45, ACT_Y, 86.4), ['LÁMINA FLEXIBLE DE LA A1 MINI', '(línea de trazo y dos puntos)'], 22, -22, tam=2.8)
    nota(lam, va, (ACT_X + 3, ACT_Y, zt - 3), ['VÁSTAGO AL FINAL DE LA FLEXIÓN', '(%.0f mm sobre la lámina)' % FLEXION], 34, 10, tam=2.8)
    nota(lam, va, (ACT_X + 3, ACT_Y, ACT_PUNTA - 6), 'VÁSTAGO RECOGIDO', 40, -8, tam=2.8)
    traza(lam, va, (ACT_X, ACT_Y, 60), (1, 0, 0), (1, 0, 0), 'D', margen=(13, 6))
    titulo_vista(lam, (va.rect[0] + va.rect[2]) / 2, va.rect[1] - 31, 'CORTE C-C', '1:1')

    # --- corte D-D por el eje del actuador (X -15.5), mirando hacia +X: el tornillo y su inserto
    vd = Vista(pz, X, Z, 1.0, ocultas=False, corte=((ACT_X, 0, 0), (1, 0, 0)), nombre='corteD', res=0.05)
    vd.colocar_punto((ACT_X, 324, 0), x=152, y=78)
    vd.dibujar(lam)
    vda = Vista(act, X, Z, 1.0, ocultas=False, nombre='actD', res=0.05)
    vda.colocar_punto((ACT_X, 324, 0), x=152, y=78)
    vda.dibujar(lam, rayado=False)
    xs = ACT_X

    def rect(y0, y1, z0, z1, estilo):
        pts = [(xs, y0, z0), (xs, y1, z0), (xs, y1, z1), (xs, y0, z1), (xs, y0, z0)]
        for a, b in zip(pts[:-1], pts[1:]):
            lam.linea(vd.m(a), vd.m(b), estilo)
    rect(264.0, 319.0, ACT_Z - 2, ACT_Z + 2, 'visible')       # caña del tornillo
    rect(260.0, 264.0, ACT_Z - 3.5, ACT_Z + 3.5, 'visible')   # cabeza
    rect(314.0, 324.0, ACT_Z - 2.8, ACT_Z + 2.8, 'fina')      # inserto M4 x 10
    cota(lam, vd, (xs, 264, ACT_Z), (xs, 319, ACT_Z), vd.rect[1] - 8, 'h', texto='55')
    cota(lam, vd, (xs, 313, ACT_Z), (xs, 324, ACT_Z), vd.rect[1] - 15, 'h', texto='11')
    nota(lam, vd, (xs, 317, ACT_Z + 2.8), ['Ø5.6 x 11 PARA INSERTO M4 x 10', 'Ø4.5 PASANTE EN LAS DOS PAREDES'], -10, 74, tam=2.8)
    traza(lam, vd, (ACT_X, ACT_Y, 60), (0, 1, 0), (0, 1, 0), 'C', margen=(22, 6))
    titulo_vista(lam, (vd.rect[0] + vd.rect[2]) / 2, vd.rect[1] - 31, 'CORTE D-D', '1:1')

    # --- isométrica del subconjunto
    vi = iso(lam, todo, 0.5, (340, 232), dir=(-1, -1, -0.7), up=Z)
    vi.dibujar(lam)
    titulo_vista(lam, 340, vi.rect[1] - 7, 'ISOMÉTRICA', '1:2')

    m13, m14 = rasgos('Soporte_actuador')['masa_g'], rasgos('Tapa_actuador')['masa_g']
    col = [('POS', 10, 'c'), ('ELEMENTO', 104, 'l'), ('CANT', 12, 'c'), ('PLANO / OBS.', 34, 'c')]
    filas = [(13, 'Soporte del actuador lineal, PLA, %.1f g' % m13, 1, 'MEC-2-12'),
             (14, 'Tapa del soporte del actuador, PLA, %.1f g' % m14, 1, 'MEC-2-13'),
             (23, 'Actuador lineal Actuonix L12-50-210-12-P (envolvente)', 1, 'comercial'),
             (28, 'Inserto roscado de latón M4 x 10', 5, '4 tapa, 1 eje'),
             (32, 'Tornillo ISO 4762 M4 x 12 (tapa)', 4, 'apriete 5.5'),
             (33, 'Tornillo ISO 4762 M4 x 30 (soporte a la cara frontal de MEC-2-02)', 4, 'apriete 24'),
             (34, 'Tornillo ISO 4762 M4 x 55 (eje del agujero posterior)', 1, 'apriete 49')]
    base = 132
    tabla(lam, 248, base, col, filas, alto=5.0, tam=2.8)
    lam.texto(248, base + 5.0 * (len(filas) + 1) + 2, 'ELEMENTOS DEL SUBCONJUNTO (posiciones de MEC-0-02)', 2.6, 0, 'l', negrita=True)
    notas = ['El actuador queda apretado entre el fondo del canal y la tapa; el tornillo M4 x 55 atraviesa su agujero '
             'posterior Ø4.25 y rosca en el inserto de la pared opuesta: el canal guía y el tornillo retiene.',
             'Recogido, el vástago queda %.1f mm bajo la lámina flexible; la flexión de %.0f mm lleva el recorrido a %.1f '
             'mm de los 50 de carrera.' % (aprox, FLEXION, recorrido),
             'Actuador representado por su envolvente simplificada (Actuonix, hoja de datos, p. 4). La lámina de la '
             'impresora, en línea de trazo y dos puntos, no forma parte del sistema.',
             'El soporte se atornilla a la cara frontal del cuarto frontal izquierdo de la estructura (MEC-2-02), sobre sus '
             'insertos a Z 18 y Z 34; no apoya en la bandeja.']
    lam.estampar(_ensamble_datos(codigo, titulo, '1:1'), notas)
    return lam
