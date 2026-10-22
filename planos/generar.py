# -*- coding: utf-8 -*-
"""python generar.py MEC-2-12 [MEC-2-13 ...]   |   python generar.py --todas"""
import sys
import importlib
import laminas

for mod in ('piezas_a', 'piezas_b', 'piezas_c', 'ensambles'):
    try:
        importlib.import_module(mod)
    except ModuleNotFoundError as e:
        if mod not in str(e):
            raise

args = sys.argv[1:]
codigos = sorted(laminas.REGISTRO) if (not args or args[0] == '--todas') else args
for c in codigos:
    try:
        laminas.generar(c)
    except Exception as e:
        import traceback
        print('ERROR en', c); traceback.print_exc()
