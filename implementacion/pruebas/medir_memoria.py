# -*- coding: utf-8 -*-
"""Mide la memoria residente y el uso de procesador del orquestador en modo simulado con consola.

Sirve para estimar si la Raspberry Pi Zero 2 W (512 MB) basta. Se ejecuta el orquestador durante un tiempo fijo,
con Telegram sustituido por la consola para no chocar con el bot en vivo, y se muestrea cada segundo.
"""
import subprocess
import sys
import time
from pathlib import Path

import psutil

RAIZ = Path(__file__).resolve().parents[1]
DURACION = int(sys.argv[1]) if len(sys.argv) > 1 else 60
p = subprocess.Popen([sys.executable, '-m', 'orquestador', '--simular', '--consola', '--duracion', str(DURACION)],
                     cwd=RAIZ, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
proc = psutil.Process(p.pid)
rss, cpu = [], []
proc.cpu_percent(None)
inicio = time.time()
while p.poll() is None and time.time() - inicio < DURACION + 10:
    try:
        rss.append(proc.memory_info().rss / 2**20)
        cpu.append(proc.cpu_percent(None))
    except psutil.NoSuchProcess:
        break
    time.sleep(1)
if p.poll() is None:
    p.terminate()
salida = RAIZ / 'pruebas' / 'salida_memoria.txt'
texto = ('Orquestador en modo simulado con consola, %d s, %d muestras\n'
         'Memoria residente: media %.1f MB, maxima %.1f MB\n'
         'Procesador (un nucleo = 100 %%): media %.1f %%, maximo %.1f %%\n'
         'Python %s en %s\n') % (DURACION, len(rss), sum(rss) / max(len(rss), 1), max(rss or [0]),
                                sum(cpu[1:]) / max(len(cpu) - 1, 1), max(cpu[1:] or [0]), sys.version.split()[0], sys.platform)
salida.write_text(texto, encoding='utf-8')
print(texto)
