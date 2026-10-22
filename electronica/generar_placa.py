# -*- coding: utf-8 -*-
"""Crea el circuito impreso a partir de la lista de redes del esquematico.

SE USA LA INTERFAZ pcbnew DE KiCad y no se escribe el formato a mano, como si se
hizo con el esquematico. Aqui la escritura a mano no aportaria control: la placa
lleva islas, redes numeradas y reglas de diseno que la propia biblioteca sabe
montar bien, y equivocarse en la numeracion de una red es un error silencioso.

TAMANO DE LA PLACA: 100 por 80 mm.
  - Cabe holgada en el vano interior de la bandeja, de 337 por 332 mm, con sus
    40 mm de altura libre.
  - Queda por debajo de los 100 por 100 mm que casi todo fabricante cobra como
    tamano base, de modo que no hay sobrecosto.
  - Es la longitud con que calculo_pistas.py dimensiona los anchos.

LOS CONVERTIDORES NO VAN SOBRE LA PLACA. Se montan en el piso de la bandeja y
llegan por cable a una tira de cuatro contactos. Asi el diseno no depende de
unas medidas que varian entre fabricantes: las fichas publican 43 por 21 mm para
el modulo del LM2596, pero la separacion de sus agujeros no esta documentada y
hay quien mide 52 por 20. Con la tira de contactos eso deja de importar, y
ademas el modulo se puede cambiar sin tocar la placa.

Se ejecuta con el Python de KiCad:
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generar_placa.py
"""
import os
import sys
import xml.etree.ElementTree as ET

import pcbnew

BASE = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.join(BASE, 'TFC_Remocion')
NETLIST = os.path.join(PROY, 'net.xml')
SALIDA = os.path.join(PROY, 'TFC_Remocion.kicad_pcb')
HUELLAS = r'C:\Program Files\KiCad\10.0\share\kicad\footprints'
HUELLAS_PROPIAS = os.path.join(PROY, 'TFC.pretty')

ANCHO_PLACA = 100.0
ALTO_PLACA = 80.0
MARGEN = 4.0        # zona libre junto al borde, donde van los taladros
HOLGURA = 1.5       # milimetros libres entre contornos de componentes
SEPARACION = 0.25   # separacion minima entre conductores

# Anchos de pista por red, de calculo_pistas.py.
ANCHOS = {
    'V24_BRUTO': 0.75, 'V24_FUS': 0.75, '+24V': 0.75, '+24V_ACT': 0.75,
    '+12V': 0.25, '+5V2': 2.00, '+5V1': 1.75, '+3V3': 0.75,
    'GND': 0.75, 'FAN_RET': 0.75, 'PELT_RET': 2.00,
    'ACT_OUT1': 0.50, 'ACT_OUT2': 0.50, 'LED_RET': 0.25,
}
ANCHO_SENAL = 0.25

# COLOCACION.
#
# Se da la posicion de CADA componente, y no se reparte por bloques dejando que
# un algoritmo apile. El primer intento lo hizo asi y salia una placa ordenada
# pero imposible de rutear: los conectores quedaban en mitad de la placa, de modo
# que todo cable al ventilador o al actuador cruzaba por encima; el excitador
# caia lejos de las puertas que gobierna; y el diodo de libre circulacion, lejos
# del transistor al que protege.
#
# Los criterios, por orden de peso:
#
#   1. TODO CONECTOR VA AL BORDE. Un cable no debe entrar por el centro.
#   2. Cada etapa de potencia, pegada al conector de la carga que gobierna.
#   3. El excitador, junto a las puertas; el diodo, junto a su transistor; la
#      resistencia de bajada, junto a la puerta que sujeta.
#   4. El microcontrolador, en el lado opuesto a la potencia, porque sus
#      entradas analogicas son lo mas sensible al ruido de conmutacion.
#
# (referencia, x, y del CENTRO del contorno, giro)
COLOCACION = {
    # REVISION B (20 oct 2026): sin Q1, R2, D2, R4, R6 ni J5; con C6 a C10, D3 y R10 a R12 (Tabla H1 del Anexo H)
    # --- borde superior: entrada de energia y derivaciones -----------------
    'J1':  (10,  8,  90),   # 24 V desde la fuente
    'F1':  (20,  8,   0),   # rearmable de 1.6 A
    'D1':  (36,  8,   0),   # proteccion contra inversion
    'J2':  (50,  8,  90),   # seta de emergencia
    'U1':  (63,  8,  90),   # convertidor de 12 V
    'U2':  (76,  8,  90),   # convertidor de 5.1 V

    # --- microcontrolador, TUMBADO ----------------------------------------
    'U4':  (60, 30,  90),

    # --- divisor de la seta y reserva de la entrada -----------------------
    'R7':  (25, 18,   0),
    'R8':  (25, 24,   0),
    'C8':  (27, 33,   0),   # 100 uF 35 V, entre la entrada y el microcontrolador

    # --- ventilador: modulacion y tacometro, columna izquierda -------------
    'R12': (12, 18,   0),   # serie de la modulacion
    'R11': (12, 24,   0),   # serie del tacometro
    'R10': (12, 30,   0),   # polarizacion del tacometro a 3.3 V
    'D3':  (12, 37,   0),   # fijacion del tacometro al riel de 3.3 V

    # --- etapa del actuador, abajo a la izquierda --------------------------
    'U6':  (16, 63,  90),   # modulo DRV8871, tira de 8
    'R3':  (36, 63,   0),   # limite de corriente, resguardo
    'C3':  (48, 55,   0),   # reserva del arranque
    'C5':  (30, 54,   0),   # filtro del cursor del potenciometro

    # --- iluminacion, centro derecha ---------------------------------------
    'U5':  (64, 54,   0),   # excitador TC4427, junto a la puerta de Q2
    'C6':  (64, 63,   0),   # desacoplo del excitador
    'C7':  (55, 63,   0),
    'Q2':  (78, 54,   0),   # IRLZ44N del dicroico
    'R1':  (78, 61,   0),   # puerta de Q2
    'R9':  (88, 48,   0),   # bajada de Q2

    # --- borde inferior: cargas -------------------------------------------
    'J4':  (11, 72,  90),   # actuador L12-P, cinco contactos
    'J3':  (26, 72,  90),   # ventilador principal, cuatro contactos
    'J6':  (44, 72,  90),   # dicroico
    'J11': (58, 72,  90),   # enlace con la Raspberry
    'J12': (72, 72,  90),   # modulo de camara, solo alimentacion
    'C9':  (90, 64,   0),   # 470 uF 16 V del riel de 5.1 V, junto a J11 y J12
    'C10': (82, 72,   0),

    # --- borde derecho ----------------------------------------------------
    'J8':  (93, 40,   0),   # ventilador de extraccion
}


def leer_netlist():
    """Devuelve (componentes, redes) del archivo de la lista de redes."""
    raiz = ET.parse(NETLIST).getroot()
    comps = {}
    for c in raiz.iter('comp'):
        fp = c.find('footprint')
        val = c.find('value')
        comps[c.get('ref')] = {
            'valor': val.text if val is not None else '',
            'huella': fp.text if fp is not None and fp.text else None,
        }
    redes = {}
    for n in raiz.iter('net'):
        nombre = n.get('name')
        if not nombre or nombre.startswith('unconnected'):
            continue
        redes[nombre] = [(nd.get('ref'), nd.get('pin')) for nd in n.iter('node')]
    return comps, redes


def cargar_huella(lib_id):
    lib, nombre = lib_id.split(':', 1)
    carpeta = (HUELLAS_PROPIAS if lib == 'TFC'
               else os.path.join(HUELLAS, lib + '.pretty'))
    fp = pcbnew.FootprintLoad(carpeta, nombre)
    if fp is None:
        raise KeyError('no se encontro la huella %s' % lib_id)
    return fp


def mm(v):
    return pcbnew.FromMM(v)


def contorno(fp, giro=0):
    """Contorno de la huella respecto de su ancla: (dx, dy, ancho, alto).

    EL ANCLA NO ESTA EN EL CENTRO. SetPosition coloca la huella por su punto de
    origen, que en un conector es la isla 1 y no el centro del cuerpo. Suponer
    que estaba centrada dejo siete contornos superpuestos y cuatro islas en
    cortocircuito, porque el rectangulo que yo reservaba no era el que el
    componente ocupaba de verdad.

    dx y dy son lo que hay que restar a la posicion deseada de la esquina
    superior izquierda para obtener donde va el ancla."""
    caja = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if caja.GetWidth() == 0:
        caja = fp.GetBoundingBox(False, False)
    dx = pcbnew.ToMM(caja.GetX())
    dy = pcbnew.ToMM(caja.GetY())
    w = pcbnew.ToMM(caja.GetWidth())
    h = pcbnew.ToMM(caja.GetHeight())
    if giro % 180:
        # girando 90 grados el rectangulo intercambia lados, y el desfase pasa
        # a medirse sobre el otro eje
        return -dy - h, dx, h, w
    return dx, dy, w, h


def main():
    comps, redes = leer_netlist()
    board = pcbnew.NewBoard(SALIDA)

    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_MinClearance = mm(SEPARACION)
    ds.m_TrackMinWidth = mm(0.25)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    # Un solo radio termico basta. La regla pide dos por defecto, pensando
    # en la resistencia mecanica de una isla de montaje superficial; aqui
    # todo es pasante, de modo que la isla la sujeta el propio taladro. Las
    # masas que devuelven corriente de potencia no dependen de esto: van
    # unidas al plano de forma solida.
    ds.m_MinResolvedSpokes = 1

    info = {}
    for nombre in sorted(redes):
        n = pcbnew.NETINFO_ITEM(board, nombre)
        board.Add(n)
        info[nombre] = n

    de_isla = {}
    for nombre, nodos in redes.items():
        for ref, pin in nodos:
            de_isla[(ref, str(pin))] = nombre

    def preparar(ref):
        """Carga la huella, le pone referencia, valor y redes."""
        fp = cargar_huella(comps[ref]['huella'])
        fp.SetReference(ref)
        fp.SetValue(comps[ref]['valor'])
        for pad in fp.Pads():
            red = de_isla.get((ref, pad.GetNumber()))
            if red:
                pad.SetNet(info[red])
        return fp

    ocupado = []          # rectangulos ya usados, en milimetros

    def libre(x, y, w, h):
        for ox, oy, ow, oh in ocupado:
            if (x < ox + ow + HOLGURA and x + w + HOLGURA > ox
                    and y < oy + oh + HOLGURA and y + h + HOLGURA > oy):
                return False
        return True

    def hueco(bx, by, ancho, alto, w, h):
        """Primer punto libre de la region, barriendo en rejilla de 1 mm."""
        y = by
        while y + h <= by + alto + 1e-9:
            x = bx
            while x + w <= bx + ancho + 1e-9:
                if libre(x, y, w, h):
                    return x, y
                x += 1.0
            y += 1.0
        return None

    puestos, sin_huella, choques, fuera = 0, [], [], []
    colocados = []

    for ref in sorted(comps):
        if not comps[ref]['huella']:
            sin_huella.append(ref)
            continue
        if ref not in COLOCACION:
            sin_huella.append('%s: sin posicion asignada' % ref)
            continue
        cx, cy, giro = COLOCACION[ref]
        try:
            fp = preparar(ref)
        except KeyError as e:
            sin_huella.append('%s: %s' % (ref, e))
            continue
        # COLOCAR, MEDIR Y CORREGIR.
        #
        # No se calcula donde debe ir el ancla para que el contorno quede
        # centrado: se coloca en el punto pedido, se MIDE donde acabo el
        # contorno de verdad y se desplaza por la diferencia. Un solo paso basta,
        # porque el contorno se mueve rigidamente con la huella.
        #
        # Se hace asi porque la aritmetica de giros fallaba: con 90 grados los
        # componentes quedaban desplazados hasta 12 mm respecto de lo pedido, y
        # el error solo se veia en el comprobador de reglas.
        fp.SetOrientationDegrees(giro)
        fp.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(cy)))
        board.Add(fp)
        caja = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if caja.GetWidth() == 0:
            caja = fp.GetBoundingBox(False, False)
        centro_real = (pcbnew.ToMM(caja.GetX()) + pcbnew.ToMM(caja.GetWidth()) / 2,
                       pcbnew.ToMM(caja.GetY()) + pcbnew.ToMM(caja.GetHeight()) / 2)
        p = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(
            p.x + mm(cx - centro_real[0]), p.y + mm(cy - centro_real[1])))
        # Las masas que devuelven corriente de potencia se unen al plano de
        # forma SOLIDA y no por radios: un radio de 0.75 mm admite 1.9 A segun
        # IPC-2221, y por el surtidor de Q3 vuelven los 2.58 A de la celda.
        if ref in ('Q2', 'U6'):
            for pad in fp.Pads():
                if pad.GetNetname() == 'GND':
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

        colocados.append(ref)
        puestos += 1

    # COMPROBACION SOBRE LA PLACA YA MONTADA, no sobre lo que yo predije.
    #
    # Predecir el contorno a partir del desfase y del giro sale mal: el primer
    # intento daba cero choques y el comprobador de reglas encontraba cinco
    # islas dentro de contorno ajeno y dos cortocircuitos. Leer la geometria que
    # KiCad tiene de verdad quita de en medio cualquier error de mi aritmetica
    # de giros.
    reales = []
    for fp in board.GetFootprints():
        caja = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if caja.GetWidth() == 0:
            caja = fp.GetBoundingBox(False, False)
        reales.append((fp.GetReference(),
                       pcbnew.ToMM(caja.GetX()), pcbnew.ToMM(caja.GetY()),
                       pcbnew.ToMM(caja.GetWidth()),
                       pcbnew.ToMM(caja.GetHeight())))
    for k, (ref, x, y, w, h) in enumerate(reales):
        for oref, ox, oy, ow, oh in reales[k + 1:]:
            if (x < ox + ow and x + w > ox and y < oy + oh and y + h > oy):
                choques.append('%s con %s' % (ref, oref))
        if (x < MARGEN or y < MARGEN or x + w > ANCHO_PLACA - MARGEN
                or y + h > ALTO_PLACA - MARGEN):
            fuera.append(ref)

    ocupado = [(x, y, w, h) for _, x, y, w, h in reales]

    # --- contorno y taladros ------------------------------------------------
    esquinas = [(0, 0), (ANCHO_PLACA, 0), (ANCHO_PLACA, ALTO_PLACA),
                (0, ALTO_PLACA), (0, 0)]
    for (x1, y1), (x2, y2) in zip(esquinas, esquinas[1:]):
        linea = pcbnew.PCB_SHAPE(board)
        linea.SetShape(pcbnew.SHAPE_T_SEGMENT)
        linea.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        linea.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        linea.SetLayer(pcbnew.Edge_Cuts)
        linea.SetWidth(mm(0.1))
        board.Add(linea)

    for cx, cy in ((3.5, 3.5), (ANCHO_PLACA - 3.5, 3.5),
                   (3.5, ALTO_PLACA - 3.5), (ANCHO_PLACA - 3.5,
                                             ALTO_PLACA - 3.5)):
        circ = pcbnew.PCB_SHAPE(board)
        circ.SetShape(pcbnew.SHAPE_T_CIRCLE)
        circ.SetStart(pcbnew.VECTOR2I(mm(cx), mm(cy)))
        circ.SetEnd(pcbnew.VECTOR2I(mm(cx + 1.6), mm(cy)))
        circ.SetLayer(pcbnew.Edge_Cuts)
        circ.SetWidth(mm(0.1))
        board.Add(circ)

    # --- plano de masa en la cara inferior ----------------------------------
    #
    # Resuelve de una vez las veintisiete conexiones de masa, que son casi la
    # mitad de la lista de redes, y de paso da camino de retorno corto a las
    # corrientes de conmutacion del ventilador y de la celda, que es donde se
    # genera el ruido que molestaria a las entradas analogicas del termistor.
    # Plano de masa en LAS DOS CARAS.
    #
    # Con plano solo abajo, la franja que queda bajo la fila de
    # convertidores se separa del resto al pasar las pistas y dejaba dos
    # islas de masa sin conectar. Con plano arriba tambien, los
    # componentes, que son todos pasantes, unen las dos caras por sus
    # propias islas y el problema desaparece sin añadir vias de cosido.
    for capa in (pcbnew.B_Cu, pcbnew.F_Cu) if 'GND' in info else ():
        zona = pcbnew.ZONE(board)
        zona.SetLayer(capa)
        zona.SetNet(info['GND'])
        zona.SetIsFilled(False)
        zona.SetLocalClearance(mm(0.3))
        zona.SetMinThickness(mm(0.25))
        zona.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        # Las islas que queden sueltas se descartan: con el plano en las dos
        # caras ya no hacen falta, y conservarlas dejaba diecisiete trozos
        # de cobre aislados, que en fabricacion son basura.
        
        zona.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        zona.SetThermalReliefGap(mm(0.3))
        zona.SetThermalReliefSpokeWidth(mm(0.75))
        contorno_zona = zona.Outline()
        contorno_zona.NewOutline()
        for px, py in ((1.0, 1.0), (ANCHO_PLACA - 1.0, 1.0),
                       (ANCHO_PLACA - 1.0, ALTO_PLACA - 1.0),
                       (1.0, ALTO_PLACA - 1.0)):
            contorno_zona.Append(mm(px), mm(py))
        board.Add(zona)
        # La zona se deja DEFINIDA PERO SIN RELLENAR. El relleno se rehace
        # despues de rutear, porque las pistas lo modifican, y ademas rellenarlo
        # ahora tapaba los taladros de sujecion: el relleno programatico no
        # descuenta los circulos que se añaden al contorno de la placa. En KiCad
        # se rellena con Editar, Rellenar todas las zonas.
        zona.SetIsFilled(False)

    board.Save(SALIDA)

    sys.stdout.write('placa generada: %.0f por %.0f mm\n'
                     % (ANCHO_PLACA, ALTO_PLACA))
    sys.stdout.write('  componentes colocados: %d de %d\n' % (puestos, len(comps)))
    sys.stdout.write('  redes: %d\n' % len(redes))
    ocupacion = sum(w * h for _, _, w, h in ocupado)
    sys.stdout.write('  ocupacion: %.0f de %.0f mm2, el %.0f por ciento\n'
                     % (ocupacion, ANCHO_PLACA * ALTO_PLACA,
                        100.0 * ocupacion / (ANCHO_PLACA * ALTO_PLACA)))
    if choques:
        sys.stdout.write('  CHOCAN: %s\n' % ', '.join(sorted(set(choques))))
    if fuera:
        sys.stdout.write('  se salen del margen de %.0f mm: %s\n'
                         % (MARGEN, ', '.join(fuera)))
    if sin_huella:
        sys.stdout.write('  PROBLEMAS: %s\n' % ', '.join(sin_huella))
    sys.stdout.write('  %s\n' % SALIDA)


if __name__ == '__main__':
    main()
