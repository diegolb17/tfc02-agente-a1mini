# -*- coding: utf-8 -*-
"""Ancho de pista de cada riel del circuito impreso, segun IPC-2221.

POR QUE IPC-2221 Y NO IPC-2152. La norma vigente para capacidad de corriente es
la IPC-2152, que sustituyo a la IPC-2221 en 2009 y que, al tener en cuenta la
conductividad termica del laminado, admite anchos MENORES para el mismo
calentamiento. Aqui se dimensiona con la IPC-2221 a proposito: sus anchos son
mayores, de modo que constituye una cota conservadora. Adoptarla no exige
declarar la conductividad del laminado concreto, dato que no se tiene, y el
resultado queda del lado seguro respecto de la norma vigente.

LOS DATOS DE PARTIDA salen del inventario de cargas del Anexo E.6 de la tesis y
del reparto por riel de la Tabla 30 del capitulo 4. Ninguna corriente se estima:
todas proceden de la ficha del fabricante del elemento que la consume.

LA FORMULA de la IPC-2221, tabla 6-4, es

    A = ( I / (k * dT^0.44) )^(1/0.725)

con A la seccion en mils cuadradas, I la corriente en amperios, dT el
calentamiento admitido en grados centigrados y k igual a 0.048 para pistas
exteriores y 0.024 para interiores. El ancho sale de dividir la seccion por el
espesor del cobre.
"""
import sys

# ---------------------------------------------------------------------------
# Condiciones de dimensionamiento
# ---------------------------------------------------------------------------
ESPESOR_ONZAS = 1.0      # acabado estandar de fabricante, sin sobrecosto
MILS_POR_ONZA = 1.378    # 1 oz/ft2 = 34.8 um = 1.378 mils de espesor
K_EXTERIOR = 0.048       # IPC-2221 tabla 6-4, capas exteriores
K_INTERIOR = 0.024       # ídem, capas interiores
DT = 10.0                # calentamiento admitido sobre el ambiente interno

# La bandeja lleva ventilador de extraccion y su aire se renueva, pero el
# ambiente interno esta por encima del de la sala. Diez grados de calentamiento
# de pista sobre ese ambiente es el valor que la propia IPC-2221 propone como
# habitual para electronica de consumo, y deja margen frente al limite del
# laminado FR-4, cuya temperatura de transicion vitrea ronda los 130 grados.

RESISTIVIDAD = 1.72e-8   # cobre recocido a 20 grados, ohmios por metro
COEF_TEMP = 0.00393      # por grado centigrado

# ---------------------------------------------------------------------------
# Cargas. (nombre, riel en voltios, corriente en amperios, procedencia)
# ---------------------------------------------------------------------------
CARGAS = [
    ('Celda termoeléctrica',      5.16, 2.580, 'ficha del módulo, Anexo E.6'),
    ('Unidad de procesamiento',   5.10, 1.176, 'ficha Raspberry Pi 4 B'),
    ('Ventilador principal',     24.00, 0.650, 'ficha PFB0924GHEP6'),
    ('Microcontrolador',          3.30, 0.303, 'ficha ESP32 WROOM'),
    ('Actuador lineal',          12.00, 0.246, 'ficha del actuador, en pulsos'),
    ('Ventilador del disipador', 12.00, 0.100, 'ficha del ventilador de 40 mm'),
    ('Ventilador auxiliar',      24.00, 0.042, 'ficha del ventilador de 40 mm'),
    ('Ventilador de extracción', 24.00, 0.042, 'ficha del ventilador de 40 mm'),
]

# Corriente y caida admitida de cada riel.
#
# LA CAIDA ADMITIDA NO SE FIJA POR LA TENSION SINO POR LO QUE CUELGA DEL RIEL.
# Un primer intento aplicaba el 1 por ciento a todo riel de 5.2 V o menos, y eso
# metia a la celda termoelectrica en el mismo saco que la logica: exigia una
# pista de 3.75 mm, inmanejable. La celda no lo necesita por dos razones: no es
# logica, de modo que una caida no la lleva a reiniciarse, y su convertidor
# XL4015 regula en CORRIENTE, de modo que compensa por si mismo lo que la pista
# deje por el camino. Lo unico que cuesta esa caida es calor en la pista, y a
# 1.75 mm son 0.27 W.
#
# (nombre, tension, caida admitida en %, procedencia)
RIELES = [
    ('Bus de entrada 24 V', 24.0, 2.0,
     'Escenario de todas las cargas a la vez, 45.08 W en el bus del Anexo E.6, '
     'aunque la secuencia no lo produzca: la pista se dimensiona para lo que '
     'puede circular y no para lo que el programa pretende que circule'),
    ('Riel 12 V', 12.0, 2.0,
     'Actuador, ventilador del disipador e iluminación, ninguno de ellos lógica'),
    ('Riel 5.2 V de la celda', 5.16, 2.0,
     'Carga térmica con convertidor regulado en corriente, que compensa la caída'),
    ('Riel 5.1 V', 5.10, 1.0,
     'Unidad de procesamiento: es lógica y su margen de reinicio es estrecho'),
    ('Riel 3.3 V', 3.30, 1.0, 'Microcontrolador, ídem'),
]

ILUMINACION = 0.20   # tira de LED, 2.4 W sobre el riel de 12 V


def ancho_mm(corriente, k=K_EXTERIOR, dt=DT, onzas=ESPESOR_ONZAS):
    """Ancho minimo en milimetros segun IPC-2221."""
    area_mils2 = (corriente / (k * dt ** 0.44)) ** (1 / 0.725)
    ancho_mils = area_mils2 / (onzas * MILS_POR_ONZA)
    return ancho_mils * 0.0254


def caida_mv(corriente, ancho_mm_, largo_mm, onzas=ESPESOR_ONZAS, temp=45.0):
    """Caida de tension en milivoltios sobre un tramo de pista."""
    espesor_m = onzas * 34.8e-6
    seccion = (ancho_mm_ * 1e-3) * espesor_m
    rho = RESISTIVIDAD * (1 + COEF_TEMP * (temp - 20.0))
    r = rho * (largo_mm * 1e-3) / seccion
    return corriente * r * 1000.0, r


def ancho_por_caida(corriente, tension, largo_mm, pct, onzas=ESPESOR_ONZAS,
                    temp=45.0):
    """Ancho necesario para no pasar del porcentaje de caida admitido.

    El calentamiento no es el unico criterio, y en los rieles de baja tension no
    es el que manda: una pista de 0.5 mm aguanta sobradamente 1.18 A sin
    calentarse, pero sobre 80 mm deja 102 mV, que en un riel de 5.1 V es el 2
    por ciento y la unidad de procesamiento no lo admite. El ancho se dimensiona
    por el mas exigente de los dos criterios."""
    rho = RESISTIVIDAD * (1 + COEF_TEMP * (temp - 20.0))
    caida_max = tension * pct / 100.0
    seccion = rho * (largo_mm * 1e-3) * corriente / caida_max
    return seccion / (onzas * 34.8e-6) * 1e3


def main():
    sys.stdout.write(
        'ANCHO DE PISTA POR RIEL, IPC-2221 tabla 6-4\n'
        'cobre de %.0f oz (%.1f mils), calentamiento admitido %.0f grados\n\n'
        % (ESPESOR_ONZAS, ESPESOR_ONZAS * MILS_POR_ONZA, DT))

    # corriente de cada riel a partir de las cargas
    i_12 = 0.246 + 0.100 + ILUMINACION
    i_24_todas = 45.08 / 24.0
    corrientes = {
        'Bus de entrada 24 V': i_24_todas,
        'Riel 12 V': i_12,
        'Riel 5.2 V de la celda': 2.580,
        'Riel 5.1 V': 1.176,
        'Riel 3.3 V': 0.303,
    }

    # Longitud de pista con que se dimensiona.
    #
    # La placa se fija en 100 por 80 mm: cabe holgada en el vano interior de
    # 337 por 332 de la bandeja, y queda por debajo de los 100 por 100 que casi
    # todo fabricante cobra como tamaño base. Su diagonal son 128 mm, pero el
    # recorrido de una pista no es la diagonal en linea recta: se toma 130 mm,
    # que cubre el rodeo del trazado sin quedarse corto.
    LARGO = 130.0
    sys.stdout.write('%-26s %7s %8s %8s %9s %8s\n' % (
        'riel', 'I (A)', 'térmico', 'caída', 'adoptado', 'manda'))
    adoptados = {}
    for nombre, tension, pct, _nota in RIELES:
        i = corrientes[nombre]
        ancho_t = ancho_mm(i, K_EXTERIOR)
        ancho_c = ancho_por_caida(i, tension, LARGO, pct)
        exigido = max(ancho_t, ancho_c)
        # se redondea hacia arriba al cuarto de milimetro, que es el paso que
        # cualquier fabricante admite sin sobrecosto
        adop = max(0.25, (int(exigido / 0.25 - 1e-9) + 1) * 0.25)
        adoptados[nombre] = adop
        sys.stdout.write('%-26s %7.3f %8.3f %8.3f %9.2f %8s\n'
                         % (nombre, i, ancho_t, ancho_c, adop,
                            'térmico' if ancho_t >= ancho_c else 'caída'))

    sys.stdout.write('\nel ancho adoptado es el mayor de los dos criterios, '
                     'redondeado al cuarto\nde milímetro por exceso\n')

    sys.stdout.write('\nCOMPROBACION de la caída con el ancho adoptado, sobre '
                     '%.0f mm de pista\n' % LARGO)
    sys.stdout.write('%-26s %9s %9s %8s %8s %8s\n'
                     % ('riel', 'R (mohm)', 'caída mV', '% riel', 'admite',
                        'veredicto'))
    # El limite lo trae cada riel en su propia fila, y no una regla por tension:
    # la celda comparte tension con la logica pero no comparte exigencia.
    for nombre, tension, limite, _nota in RIELES:
        i = corrientes[nombre]
        mv, r = caida_mv(i, adoptados[nombre], LARGO)
        pct = 100.0 * (mv / 1000.0) / tension
        sys.stdout.write('%-26s %9.1f %9.1f %7.2f%% %7.1f%% %8s\n'
                         % (nombre, r * 1000, mv, pct, limite,
                            'cumple' if pct <= limite + 1e-9 else 'AMPLIAR'))
        if i * i * r > 0.2:
            sys.stdout.write('%-26s   la pista disipa %.2f W\n' % ('', i * i * r))

    sys.stdout.write('\nSEPARACION ENTRE CONDUCTORES, IPC-2221 tabla 6-1\n')
    # B1, conductores externos sin recubrimiento, hasta 3050 m de altitud
    sys.stdout.write('  rieles de hasta 30 V en continua: 0.1 mm mínimo por '
                     'norma\n')
    sys.stdout.write('  se adopta 0.25 mm en toda la placa, que es el mínimo '
                     'de fabricación\n')
    sys.stdout.write('  la entrada de red NO va en la placa: la fuente es un '
                     'módulo cerrado y\n'
                     '  a la placa solo llegan los 24 V, de modo que no hay '
                     'separación de red que\n  respetar\n')

    sys.stdout.write('\nRESISTENCIA QUE FIJA EL LIMITE DE CORRIENTE DEL '
                     'ACTUADOR (DRV8871)\n')
    # La ficha del DRV8871 fija el umbral con  Itrip[A] = 6600 / Rlim[ohm].
    #
    # OJO CON EL SENTIDO: a MAS resistencia, MENOS corriente. Para no pasar del
    # tope hay que tomar el valor normalizado por ENCIMA del calculado, no por
    # debajo. Con 51 kohm el tope quedaria en 42.1 N, esto es por encima de los
    # 40 que la seccion 4.4 admite.
    empuje_max = 40.0      # newton, tope de la seccion 4.4
    fuerza_nominal = 80.0  # newton que entrega el actuador a plena corriente
    i_nominal = 0.246
    i_tope = i_nominal * empuje_max / fuerza_nominal
    r_calc = 6600.0 / i_tope
    E24 = [43e3, 47e3, 51e3, 56e3, 62e3, 68e3]
    r_lim = next(r for r in E24 if r >= r_calc)
    i_real = 6600.0 / r_lim
    sys.stdout.write('  tope de empuje %.0f N sobre %.0f N nominales -> '
                     'corriente %.3f A\n' % (empuje_max, fuerza_nominal, i_tope))
    sys.stdout.write('  Rlim = 6600 / I = %.0f ohm; se adopta el valor E24 '
                     'inmediatamente SUPERIOR,\n  que es %.0f kohm, porque a '
                     'más resistencia menos corriente\n' % (r_calc, r_lim / 1e3))
    sys.stdout.write('  con %.0f kohm el tope real queda en %.3f A, esto es '
                     '%.1f N, por debajo de los %.0f\n'
                     % (r_lim / 1e3, i_real, i_real / i_nominal * fuerza_nominal,
                        empuje_max))
    sys.stdout.write('  SALVEDAD: la conversión de fuerza a corriente supone '
                     'proporcionalidad\n  directa, y el actuador consume '
                     'corriente incluso en vacío. El valor debe\n  confirmarse '
                     'con la medición de fuerza contra corriente pendiente en '
                     'el\n  Anexo K antes de soldar la resistencia definitiva\n')

    sys.stdout.write('\nDIVISOR DEL TERMISTOR\n')
    # NTC de 100 k a 25 grados, B = 3950 K, en divisor con 33 k hacia masa
    import math
    r25, beta, rfija = 100000.0, 3950.0, 33000.0
    sys.stdout.write('%-12s %12s %12s %12s\n'
                     % ('T (°C)', 'Rntc (kohm)', 'Vsalida (V)', 'sensib mV/°C'))
    ant = None
    for t in (25, 40, 50, 60, 80):
        rt = r25 * math.exp(beta * (1.0 / (t + 273.15) - 1.0 / 298.15))
        v = 3.3 * rfija / (rt + rfija)
        s = '' if ant is None else '%12.1f' % ((v - ant[1]) * 1000 / (t - ant[0]))
        sys.stdout.write('%-12d %12.1f %12.3f %s\n' % (t, rt / 1000, v, s))
        ant = (t, v)
    sys.stdout.write('  la sensibilidad es máxima en la banda de 40 a 60 grados,'
                     ' que es donde\n  opera el criterio de remoción\n')


if __name__ == '__main__':
    main()
