# -*- coding: utf-8 -*-
"""Genera todo lo que la tesis necesita del proyecto de KiCad.

Deja tres cosas separadas:

  revision/   para mirar el trabajo a ojo antes de dar nada por bueno
  tesis/      las figuras que entran en el documento, ya recortadas
  fabricacion/  los gerber y el taladro, que son los archivos que pide un
                fabricante de circuitos impresos. No se usan en este curso,
                porque la placa no se construye, pero se generan porque son
                la constancia de que el diseno esta cerrado.

Se ejecuta con el Python del sistema, no con el de KiCad: aqui no se usa
pcbnew sino la herramienta de linea de comandos.

    python exportar.py
"""
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.join(BASE, 'TFC_Remocion')
SCH = os.path.join(PROY, 'TFC_Remocion.kicad_sch')
PCB = os.path.join(PROY, 'TFC_Remocion.kicad_pcb')
CLI = r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'

REVISION = os.path.join(PROY, 'revision')
TESIS = os.path.join(PROY, 'tesis')
FABRI = os.path.join(PROY, 'fabricacion')

# adonde van las figuras del documento
FIGURAS = os.path.join(BASE, '..', 'TESIS_LATEX', 'Imagenes')


def correr(args, que):
    p = subprocess.run([CLI] + args, capture_output=True, text=True,
                       errors='replace')
    ok = p.returncode == 0
    sys.stdout.write('  %-34s %s\n' % (que, 'ok' if ok else 'FALLO'))
    if not ok:
        sys.stdout.write('    %s\n' % (p.stderr or p.stdout)[-300:])
    return ok


def rasterizar(pdf, png, dpi=600, margen=24):
    """Pasa la primera pagina a imagen y le quita el blanco que la rodea."""
    import fitz
    from PIL import Image
    doc = fitz.open(pdf)
    pm = doc[0].get_pixmap(dpi=dpi)
    img = Image.frombytes('RGB', (pm.width, pm.height), pm.samples)
    doc.close()
    # el recorte se calcula contra el blanco, no contra un color de fondo: la
    # hoja de KiCad es blanca y el contorno de la placa es lo primero que
    # deja de serlo
    fondo = Image.new('RGB', img.size, (255, 255, 255))
    caja = Image.new('RGB', img.size)
    caja.paste(img)
    r = caja.convert('RGB')
    from PIL import ImageChops
    caja = ImageChops.difference(r, fondo).getbbox()
    if caja:
        x0, y0, x1, y1 = caja
        img = img.crop((max(0, x0 - margen), max(0, y0 - margen),
                        min(img.width, x1 + margen),
                        min(img.height, y1 + margen)))
    img.save(png)
    sys.stdout.write('    recortado a %d por %d px\n' % img.size)


def main():
    for d in (REVISION, TESIS, FABRI):
        if not os.path.isdir(d):
            os.makedirs(d)

    sys.stdout.write('esquematico\n')
    # A2 en una sola hoja. Es el plano del Anexo H.
    correr(['sch', 'export', 'pdf', '--output',
            os.path.join(TESIS, 'esquematico.pdf'), SCH], 'plano en PDF')
    # OJO con el formato: por omision saca la forma de S-expresiones y
    # generar_placa.py lee XML. Sin --format kicadxml la placa se genera con
    # la lista de redes anterior y no da ningun error, que es la peor forma
    # de fallar.
    correr(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output',
            os.path.join(PROY, 'net.xml'), SCH], 'lista de redes')
    correr(['sch', 'export', 'bom', '--output',
            os.path.join(PROY, 'lista_componentes.csv'),
            '--fields', 'Reference,Value,Footprint,Nota',
            '--group-by', 'Value,Footprint', SCH], 'lista de componentes')

    sys.stdout.write('placa, para revisar a ojo\n')
    # una capa por pagina, con el contorno superpuesto para ubicarse
    correr(['pcb', 'export', 'pdf', '--output',
            os.path.join(REVISION, 'placa_capas.pdf'),
            '--layers', 'F.Cu,B.Cu,Edge.Cuts,F.Silkscreen',
            '--common-layers', 'Edge.Cuts', PCB], 'capas en PDF')
    for capa, nombre in (('F.Cu,F.Silkscreen,Edge.Cuts', 'cara_superior'),
                         ('B.Cu,Edge.Cuts', 'cara_inferior')):
        correr(['pcb', 'export', 'svg', '--output',
                os.path.join(REVISION, nombre + '.svg'),
                '--layers', capa, '--page-size-mode', '2', PCB], nombre)

    sys.stdout.write('placa, figuras del documento\n')
    # kicad-cli NO sabe exportar PNG de la placa: solo PDF, SVG y postscript.
    # Se saca PDF y se rasteriza aqui, recortando el blanco de la hoja, que si
    # no ocupa cuatro quintas partes de la figura.
    for capa, nombre in (('F.Cu,F.Silkscreen,Edge.Cuts', 'FIG_pcb_superior'),
                         ('B.Cu,Edge.Cuts', 'FIG_pcb_inferior'),
                         ('F.Silkscreen,F.Fab,Edge.Cuts',
                          'FIG_pcb_emplazamiento')):
        tmp = os.path.join(TESIS, '_' + nombre + '.pdf')
        if correr(['pcb', 'export', 'pdf', '--output', tmp, '--mode-single',
                   '--layers', capa, '--scale', '2', PCB], nombre):
            rasterizar(tmp, os.path.join(TESIS, nombre + '.png'))
            os.remove(tmp)
    # dos vistas del modelo, que es lo que se comprueba contra la bandeja
    for lado, nombre in (('top', 'FIG_pcb_3d_superior'),
                         ('bottom', 'FIG_pcb_3d_inferior')):
        correr(['pcb', 'render', '--output',
                os.path.join(TESIS, nombre + '.png'),
                '--side', lado, '--quality', 'high',
                '--width', '1600', '--height', '1300',
                '--background', 'opaque', PCB], nombre)

    sys.stdout.write('archivos de fabricacion\n')
    correr(['pcb', 'export', 'gerbers', '--output', FABRI, PCB], 'gerber')
    correr(['pcb', 'export', 'drill', '--output', FABRI + os.sep, PCB],
           'taladro')

    sys.stdout.write('copia a las figuras de la tesis\n')
    destino = os.path.abspath(FIGURAS)
    n = 0
    for f in sorted(os.listdir(TESIS)):
        if f.startswith('FIG_') or f == 'esquematico.pdf':
            nombre = 'FIG_esquematico.pdf' if f == 'esquematico.pdf' else f
            shutil.copy(os.path.join(TESIS, f), os.path.join(destino, nombre))
            n += 1
            sys.stdout.write('  %s\n' % nombre)
    sys.stdout.write('%d figuras en %s\n' % (n, destino))


if __name__ == '__main__':
    main()
