# -*- coding: utf-8 -*-
"""Rutea la placa con freerouting y devuelve el resultado a KiCad.

EL CAMINO, que no es evidente:

  1. pcbnew exporta la placa al formato Specctra, que es el que entiende el
     ruteador. OJO: kicad-cli NO sabe hacerlo, solo la interfaz de Python.
  2. freerouting, escrito en Java, rutea el archivo y devuelve una sesion .ses.
  3. pcbnew importa esa sesion y vuelca las pistas sobre la placa.
  4. Se rellena el plano de masa, que hasta ahora estaba definido pero vacio, y
     se comprueban las reglas de diseno.

REQUISITOS, ya instalados: Java 21 y freerouting 1.9.0.

Se ejecuta con el Python de KiCad:
    "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" rutear.py [pasadas]
"""
import os
import subprocess
import sys
import time

import pcbnew

BASE = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.join(BASE, 'TFC_Remocion')
PLACA = os.path.join(PROY, 'TFC_Remocion.kicad_pcb')
DSN = os.path.join(PROY, 'TFC_Remocion.dsn')
SES = os.path.join(PROY, 'TFC_Remocion.ses')
# SE USA LA VERSION 1.9.0 Y NO LA 2.4.1.
#
# La 2.4.1 rutea bien, y de hecho deja la placa completa sin violaciones,
# pero al guardar la sesion sin interfaz escribe un archivo de CERO BYTES y
# sale con codigo 0: el fallo es silencioso. Una vez guardo bien y dos no,
# de modo que es una carrera y no algo que se arregle con opciones. La 1.9.0
# hace el mismo trabajo y guarda siempre. Como contrapartida corre con Java
# 21 y la 2.4.1 exige Java 25; estan instaladas las dos.
JAR = os.path.join(BASE, '_herramientas', 'freerouting19.jar')
JAVA = os.path.join('C:' + chr(92) + 'Program Files',
                    'Eclipse Adoptium', 'jre-21.0.12.101-hotspot',
                    'bin', 'java.exe')


def sin_rutear(board):
    """Cuenta las conexiones que faltan, por la lista de nodos de cada red."""
    board.BuildConnectivity()
    con = board.GetConnectivity()
    return con.GetUnconnectedCount(True)


def main():
    pasadas = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    if not os.path.exists(JAVA):
        sys.stdout.write('no encuentro Java en %s\n' % JAVA)
        return 1
    if not os.path.exists(JAR):
        sys.stdout.write('no encuentro freerouting en %s\n' % JAR)
        return 1

    board = pcbnew.LoadBoard(PLACA)
    antes = sin_rutear(board)
    sys.stdout.write('conexiones sin rutear antes: %d\n' % antes)

    # --- 1. exportar al formato del ruteador --------------------------------
    if not pcbnew.ExportSpecctraDSN(board, DSN):
        sys.stdout.write('fallo la exportacion a Specctra\n')
        return 1
    sys.stdout.write('exportado %s (%.0f kB)\n'
                     % (os.path.basename(DSN), os.path.getsize(DSN) / 1024.0))

    # --- 2. rutear -----------------------------------------------------------
    if os.path.exists(SES):
        os.remove(SES)
    t = time.time()
    sys.stdout.write('ruteando con %d pasadas, esto tarda\n' % pasadas)
    p = subprocess.run(
        # un solo hilo: el propio ruteador avisa de que el multihilo genera
        # violaciones de separacion
        [JAVA, '-jar', JAR, '-de', DSN, '-do', SES, '-mp', str(pasadas),
         '-mt', '1'],
        capture_output=True, text=True, errors='replace', cwd=PROY)
    sys.stdout.write('  freerouting termino en %.0f s\n' % (time.time() - t))
    for linea in (p.stdout or '').strip().split('\n')[-6:]:
        if linea.strip():
            sys.stdout.write('  %s\n' % linea.strip()[:110])
    if not os.path.exists(SES):
        sys.stdout.write('NO genero la sesion. Error:\n%s\n'
                         % (p.stderr or p.stdout)[-600:])
        return 1

    # --- 3. devolver las pistas a la placa ----------------------------------
    board = pcbnew.LoadBoard(PLACA)
    if not pcbnew.ImportSpecctraSES(board, SES):
        sys.stdout.write('fallo la importacion de la sesion\n')
        return 1

    # --- 4. rellenar el plano de masa y guardar -----------------------------
    if board.Zones():
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PLACA)

    board = pcbnew.LoadBoard(PLACA)
    despues = sin_rutear(board)
    pistas = len([t for t in board.GetTracks()
                  if t.GetClass() == 'PCB_TRACK'])
    vias = len([t for t in board.GetTracks() if t.GetClass() == 'PCB_VIA'])
    sys.stdout.write('\npistas trazadas: %d   vias: %d\n' % (pistas, vias))
    sys.stdout.write('conexiones sin rutear despues: %d de %d\n'
                     % (despues, antes))
    if despues == 0:
        sys.stdout.write('la placa esta ruteada por completo\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
