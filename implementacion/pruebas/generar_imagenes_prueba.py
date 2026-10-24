"""Imagenes de prueba vistas desde la camara del diseno (1 600 x 1 200 px).

Trazado de rayos sencillo con la pose del modelo de Fusion (PLANOS/geometria.py,
funcion vision): el objetivo queda a 123 mm sobre la plataforma y a 214 mm de su
centro, con 55 grados de oblicuidad, en el lado alto y hacia el soporte del
cuarto posterior derecho; la plataforma esta inclinada 20 grados respecto de la
mesa. El objetivo angular de 120 grados se modela como proyeccion equidistante
(ojo de pez), que reproduce la curvatura de un gran angular. La luz sale del aro
de la lampara. Son imagenes sinteticas para recorrer el flujo, no para evaluar
el modelo de vision.

  python pruebas/generar_imagenes_prueba.py
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CARPETA = Path(__file__).resolve().parent / "imagenes"
ANCHO, ALTO = 1600, 1200
FOCAL = (ANCHO / 2) / math.radians(60)        # equidistante: 120 grados en el ancho

# Marco de la plataforma: origen en el centro de su cara superior, x cuesta arriba,
# z normal a la plataforma. Valores de geometria.vision() del modelo revision C.
LENTE = np.array([108.8, -137.4, 123.0])
LAMPARA = np.array([72.2, -194.8, 107.4])
ARRIBA = np.array([0.342, 0.0, 0.940])         # vertical del mundo en este marco
ALTURA_CENTRO = 156.5                          # mm del centro de la plataforma sobre la mesa


def _normal(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def rayos():
    adelante = _normal(-LENTE)
    derecha = _normal(np.cross(adelante, ARRIBA))
    abajo = np.cross(adelante, derecha)
    py, px = np.mgrid[0:ALTO, 0:ANCHO].astype(np.float32)
    dx, dy = px + 0.5 - ANCHO / 2, py + 0.5 - ALTO / 2
    r = np.hypot(dx, dy)
    theta, phi = r / FOCAL, np.arctan2(dy, dx)
    st = np.sin(theta)[..., None]
    d = (np.cos(theta)[..., None] * adelante + st * (np.cos(phi)[..., None] * derecha
                                                     + np.sin(phi)[..., None] * abajo))
    return d.astype(np.float32), (adelante, derecha, abajo)


def proyectar(p, base):
    """Punto del marco de la plataforma a pixel, con la misma proyeccion equidistante."""
    adelante, derecha, abajo = base
    v = _normal(np.asarray(p, dtype=float) - LENTE)
    theta = np.arccos(np.clip(v @ adelante, -1, 1))
    x, y = v @ derecha, v @ abajo
    phi = np.arctan2(y, x)
    r = FOCAL * theta
    return np.stack([ANCHO / 2 + r * np.cos(phi), ALTO / 2 + r * np.sin(phi)], axis=-1)


def caja(o, d, mn, mx):
    """Interseccion rayo-caja alineada: distancia y normal; inf si no corta."""
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / np.where(np.abs(d) < 1e-9, 1e-9, d)
        t1, t2 = (mn - o) * inv, (mx - o) * inv
        tmin, tmax = np.minimum(t1, t2), np.maximum(t1, t2)
        entra, sale = tmin.max(axis=-1), tmax.min(axis=-1)
    golpe = (sale >= np.maximum(entra, 0)) & (entra > 1e-3)
    t = np.where(golpe, entra, np.inf)
    eje = tmin.argmax(axis=-1)
    normal = np.zeros(d.shape, dtype=np.float32)
    signo = -np.sign(np.take_along_axis(d, eje[..., None], axis=-1))[..., 0]
    for k in range(3):
        normal[..., k] = np.where(eje == k, signo, 0)
    return t, normal


def plano(o, d, n, c):
    """Plano n.p + c = 0."""
    den = d @ n
    with np.errstate(divide="ignore", invalid="ignore"):
        t = -(o @ n + c) / den
    return np.where((t > 1e-3) & np.isfinite(t), t, np.inf)


def textura_pei(rng):
    """Lamina texturizada oscura, como la de la camara real de la A1 mini."""
    base = rng.normal(0, 1, (720, 720)).astype(np.float32)
    grano = Image.fromarray(((base * 18) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    g = (np.asarray(grano, dtype=np.float32) - 128) / 255
    color = np.array([46, 43, 40], dtype=np.float32) / 255
    return np.clip(color + g[..., None] * 0.35, 0, 1)


def render(escena: str, semilla: int = 3) -> Image.Image:
    rng = np.random.default_rng(semilla)
    d, base = rayos()
    o = LENTE.astype(np.float32)
    objetos = []   # (t, normal, color rgb 0..1 por pixel o constante)

    # Lamina de la plataforma con textura.
    t_pl = plano(o, d, np.array([0, 0, 1.0]), 0.0)
    p = o + d * np.where(np.isfinite(t_pl), t_pl, 0)[..., None]
    dentro = (np.abs(p[..., 0]) <= 90) & (np.abs(p[..., 1]) <= 90)
    t_pl = np.where(dentro, t_pl, np.inf)
    tex = textura_pei(rng)
    iu = ((p[..., 0] + 90) / 180 * 719).clip(0, 719).astype(int)
    iv = ((p[..., 1] + 90) / 180 * 719).clip(0, 719).astype(int)
    objetos.append((t_pl, np.broadcast_to(np.array([0, 0, 1.0], np.float32), d.shape), tex[iv, iu]))

    def agregar_caja(mn, mx, color):
        t, n = caja(o, d, np.array(mn, np.float32), np.array(mx, np.float32))
        objetos.append((t, n, np.broadcast_to(np.array(color, np.float32) / 255, d.shape)))
        return (mn, mx)

    agregar_caja([-93, -93, -7], [93, 93, -0.01], [70, 72, 76])            # cama calefactada
    agregar_caja([-175, -160, -75], [175, 150, -22], [150, 152, 156])      # base del equipo
    agregar_caja([-25, 140, -75], [30, 172, 270], [215, 216, 218])         # columna del eje Z
    agregar_caja([-14, -120, 205], [14, 150, 228], [60, 62, 66])           # brazo del eje X
    agregar_caja([-32, 82, 150], [32, 128, 228], [222, 222, 224])          # cabezal en reposo
    ocluyentes = []
    if escena in ("pieza_presente", "objeto_ajeno"):
        ocluyentes.append(agregar_caja([-20, -26, 0], [22, 16, 28], [170, 172, 178]))
    if escena == "espagueti":
        ocluyentes.append(agregar_caja([-20, -26, 0], [22, 16, 7], [170, 172, 178]))
    if escena == "objeto_ajeno":
        # Destornillador olvidado sobre la plataforma, del lado cercano a la camara.
        ocluyentes.append(agregar_caja([28, -74, 0], [64, -60, 13], [196, 38, 32]))   # mango
        agregar_caja([-22, -69, 4.5], [28, -65, 8.5], [185, 188, 192])                  # varilla metalica

    # Mesa (horizontal en el mundo) y pared del fondo.
    t_mesa = plano(o, d, ARRIBA, ALTURA_CENTRO)
    objetos.append((t_mesa, np.broadcast_to(ARRIBA.astype(np.float32), d.shape),
                    np.broadcast_to(np.array([168, 140, 104], np.float32) / 255, d.shape)))
    pared_n = np.array([0.940, 0.0, -0.342])
    t_pared = plano(o, d, pared_n, 64 + 380)
    objetos.append((t_pared, np.broadcast_to(pared_n.astype(np.float32), d.shape),
                    np.broadcast_to(np.array([92, 96, 104], np.float32) / 255, d.shape)))

    # Lo mas cercano gana.
    ts = np.stack([ob[0] for ob in objetos])
    cual = ts.argmin(axis=0)
    t = np.take_along_axis(ts, cual[None], axis=0)[0]
    normal = np.zeros(d.shape, np.float32)
    color = np.zeros(d.shape, np.float32)
    for k, (_, n, c) in enumerate(objetos):
        m = cual == k
        normal[m] = n[m]
        color[m] = c[m]
    fondo = ~np.isfinite(t)
    p = o + d * np.where(fondo, 0, t)[..., None]

    # Iluminacion: la lampara del aro con caida por distancia, mas luz ambiente.
    hacia = LAMPARA - p
    dist = np.linalg.norm(hacia, axis=-1)
    hacia = hacia / dist[..., None]
    lamb = np.clip((normal * hacia).sum(-1), 0, 1)
    caida = np.clip((200 / np.maximum(dist, 1)) ** 2, 0, 1.2)
    sombra = np.ones(t.shape, np.float32)
    for mn, mx in ocluyentes:
        ts_, _ = caja(p + normal * 0.05, hacia, np.array(mn, np.float32), np.array(mx, np.float32))
        sombra = np.where(np.isfinite(ts_) & (ts_ < dist), 0.35, sombra)
    luz = 0.40 + 0.62 * lamb * caida * sombra
    img = np.clip(color * luz[..., None], 0, 1)
    img[fondo] = np.array([0.30, 0.31, 0.34])

    imagen = Image.fromarray((img * 255).astype(np.uint8))
    if escena == "espagueti":
        imagen = _espagueti(imagen, base, rng)
    # Vineteado, ruido de sensor y desenfoque leve de un objetivo economico.
    yy, xx = np.mgrid[0:ALTO, 0:ANCHO]
    vin = 1 - 0.35 * (((xx - ANCHO / 2) / (ANCHO / 2)) ** 2 + ((yy - ALTO / 2) / (ALTO / 2)) ** 2) / 2
    arr = np.asarray(imagen, np.float32) * vin[..., None]
    arr += rng.normal(0, 3.0, arr.shape)
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))


def _espagueti(imagen, base, rng):
    """Filamento suelto: caminos aleatorios en 3D sobre la pieza a medio imprimir."""
    dibujo = ImageDraw.Draw(imagen)
    azar = random.Random(11)
    for _ in range(45):
        punto = np.array([azar.uniform(-35, 35), azar.uniform(-45, 35), azar.uniform(4, 22)])
        trazo = []
        for _ in range(28):
            punto = punto + np.array([azar.uniform(-6, 6), azar.uniform(-6, 6), azar.uniform(-2.5, 2.5)])
            punto[2] = min(max(punto[2], 0.5), 30)
            trazo.append(punto.copy())
        pix = proyectar(np.array(trazo), base)
        tono = azar.randint(165, 200)
        dibujo.line([tuple(q) for q in pix], fill=(tono, tono + 2, tono + 6), width=2)
    return imagen


def main() -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    for escena in ("plataforma_vacia", "pieza_presente", "espagueti", "objeto_ajeno"):
        render(escena).save(CARPETA / f"{escena}.jpg", quality=88)
        print("generada", escena)


if __name__ == "__main__":
    main()
