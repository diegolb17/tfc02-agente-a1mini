"""Genera las imagenes de prueba de la simulacion (1 600 x 1 200 px).

Son dibujos esquematicos de la plataforma vista desde la camara, no fotografias:
sirven para recorrer el flujo del orquestador con el modelo simulado, no para
evaluar el modelo real, que se evalua con capturas de la camara (Anexo K).
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

CARPETA = Path(__file__).resolve().parent / "imagenes"
ANCHO, ALTO = 1600, 1200
PLACA = (350, 150, 1250, 1050)        # 180 x 180 mm a 5 px/mm


def plataforma() -> Image.Image:
    img = Image.new("RGB", (ANCHO, ALTO), (38, 40, 44))
    d = ImageDraw.Draw(img)
    d.rectangle(PLACA, fill=(120, 96, 60))
    rnd = random.Random(1)
    for _ in range(9000):                      # textura de la lamina PEI
        x, y = rnd.randint(PLACA[0], PLACA[2]), rnd.randint(PLACA[1], PLACA[3])
        g = rnd.randint(-18, 18)
        d.point((x, y), fill=(120 + g, 96 + g, 60 + g))
    for i in range(0, 901, 150):               # marcas de la cuadricula
        d.line((PLACA[0] + i, PLACA[1], PLACA[0] + i, PLACA[1] + 12), fill=(90, 72, 45), width=3)
    d.rectangle(PLACA, outline=(70, 70, 74), width=6)
    return img


def con_pieza(img: Image.Image) -> Image.Image:
    d = ImageDraw.Draw(img)
    d.rectangle((715, 515, 905, 705), fill=(30, 25, 18))             # sombra
    d.rectangle((700, 500, 890, 690), fill=(150, 152, 158))
    d.rectangle((700, 500, 890, 520), fill=(175, 177, 182))
    return img


def con_espagueti(img: Image.Image) -> Image.Image:
    d = ImageDraw.Draw(img)
    d.rectangle((700, 560, 890, 690), fill=(150, 152, 158))            # pieza a medias
    rnd = random.Random(7)
    for _ in range(70):
        x, y = rnd.randint(600, 1000), rnd.randint(380, 760)
        puntos = []
        for k in range(12):
            a = rnd.uniform(0, 2 * math.pi)
            x, y = x + 25 * math.cos(a), y + 25 * math.sin(a)
            puntos.append((x, y))
        d.line(puntos, fill=(170, 172, 178), width=3)
    return img


def con_objeto(img: Image.Image) -> Image.Image:
    img = con_pieza(img)
    d = ImageDraw.Draw(img)
    d.rectangle((420, 880, 700, 910), fill=(200, 40, 35))              # mango de un destornillador
    d.rectangle((700, 888, 820, 902), fill=(190, 190, 195))
    return img


def main() -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    escenas = {"plataforma_vacia": plataforma(), "pieza_presente": con_pieza(plataforma()),
               "espagueti": con_espagueti(plataforma()), "objeto_ajeno": con_objeto(plataforma())}
    for nombre, img in escenas.items():
        img.filter(ImageFilter.GaussianBlur(0.6)).save(CARPETA / f"{nombre}.jpg", quality=88)
        print("generada", nombre)


if __name__ == "__main__":
    main()
