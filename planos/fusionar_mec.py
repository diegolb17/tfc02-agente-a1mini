# -*- coding: utf-8 -*-
"""Une las 24 laminas MEC en Planos_MEC_Anexo_G_completo.pdf (orden de la Tabla de relacion de planos)."""
import os
import fitz

AQUI = os.path.dirname(os.path.abspath(__file__))
L = os.path.join(AQUI, 'laminas')
doc = fitz.open()
for f in sorted(x for x in os.listdir(L) if x.startswith('MEC-') and x.endswith('.pdf')):
    doc.insert_pdf(fitz.open(os.path.join(L, f)))
salida = os.path.join(AQUI, 'Planos_MEC_Anexo_G_completo.pdf')
doc.save(salida, garbage=3, deflate=True)
print(salida, doc.page_count, 'laminas')
