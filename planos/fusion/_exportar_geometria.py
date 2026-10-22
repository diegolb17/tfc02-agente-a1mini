# -*- coding: utf-8 -*-
"""Exporta, por ocurrencia del diseño TFC_Sistema_A1mini_v3 (coordenadas LOCALES del
componente, mm):
  <nombre>.tri         malla por caras: int32 n, float32 n*9 (xyz x3), int32 n (id de cara)
  <nombre>.edges.json  aristas B-Rep: polilíneas exactas, caras adyacentes y si son tangentes
  <nombre>.json        masa, material, transform al ensamble y rasgos (cilindros, esferas...)
Salida: TFC02/PLANOS/_geom/"""
import adsk.core, adsk.fusion, traceback, json, struct, math, os, time

DEST = 'C:/Users/Diego/Desktop/PUCP 26.2/TFC/TFC02/PLANOS/_geom'
OMITIR = ('Auxiliar_', '_tmp_')
app = adsk.core.Application.get()
out = []
t0 = time.time()


def v3(p):  # cm -> mm
    return [round(p.x * 10, 4), round(p.y * 10, 4), round(p.z * 10, 4)]


def malla_cara(face, dev_grados):
    calc = face.meshManager.createMeshCalculator()
    calc.setQuality(adsk.fusion.TriangleMeshQualityOptions.VeryHighQualityTriangleMesh)
    calc.maxNormalDeviation = math.radians(dev_grados)
    calc.surfaceTolerance = 0.003
    m = calc.calculate()
    if m is None:
        return []
    co = m.nodeCoordinatesAsDouble
    idx = m.nodeIndices
    tris = []
    for i in range(0, len(idx), 3):
        a, b, c = idx[i], idx[i + 1], idx[i + 2]
        tris.append((co[3*a]*10, co[3*a+1]*10, co[3*a+2]*10,
                     co[3*b]*10, co[3*b+1]*10, co[3*b+2]*10,
                     co[3*c]*10, co[3*c+1]*10, co[3*c+2]*10))
    return tris


def aristas_cuerpo(body, id_cara, tol_cm=0.0005):
    res = []
    for e in body.edges:
        ev = e.evaluator
        ok, t0_, t1_ = ev.getParameterExtents()
        ok, pts = ev.getStrokes(t0_, t1_, tol_cm)
        if not ok or len(pts) < 2:
            continue
        caras = [id_cara[f.tempId] for f in e.faces if f.tempId in id_cara]
        suave = False
        if len(caras) == 2 and e.faces.count == 2:
            pm = pts[len(pts) // 2]
            n = []
            for f in e.faces:
                okn, nv = f.evaluator.getNormalAtPoint(pm)
                n.append(nv if okn else None)
            if n[0] is not None and n[1] is not None:
                ang = math.degrees(n[0].angleTo(n[1]))
                suave = ang < 12.0
        res.append({'f': caras, 'suave': suave, 'pts': [v3(p) for p in pts]})
    return res


def rasgos_cuerpo(body):
    r = {'cilindros': [], 'esferas': [], 'planos': [], 'circulos': [], 'conos': [], 'toros': []}
    for f in body.faces:
        g = f.geometry
        bb = f.boundingBox
        ent = {'area_mm2': round(f.area * 100, 2), 'bbox': [v3(bb.minPoint), v3(bb.maxPoint)]}
        t = g.surfaceType
        if t == adsk.core.SurfaceTypes.CylinderSurfaceType:
            c = adsk.core.Cylinder.cast(g)
            ent.update(origen=v3(c.origin), eje=[round(x, 5) for x in c.axis.asArray()], radio=round(c.radius * 10, 3))
            r['cilindros'].append(ent)
        elif t == adsk.core.SurfaceTypes.SphereSurfaceType:
            s = adsk.core.Sphere.cast(g)
            ent.update(centro=v3(s.origin), radio=round(s.radius * 10, 3))
            r['esferas'].append(ent)
        elif t == adsk.core.SurfaceTypes.PlaneSurfaceType:
            p = adsk.core.Plane.cast(g)
            if f.area * 100 < 20:
                continue
            ent.update(origen=v3(p.origin), normal=[round(x, 5) for x in p.normal.asArray()])
            r['planos'].append(ent)
        elif t == adsk.core.SurfaceTypes.ConeSurfaceType:
            c = adsk.core.Cone.cast(g)
            ent.update(origen=v3(c.origin), eje=[round(x, 5) for x in c.axis.asArray()], radio=round(c.radius * 10, 3),
                       semiangulo=round(math.degrees(c.halfAngle), 2))
            r['conos'].append(ent)
        elif t == adsk.core.SurfaceTypes.TorusSurfaceType:
            tt = adsk.core.Torus.cast(g)
            ent.update(origen=v3(tt.origin), eje=[round(x, 5) for x in tt.axis.asArray()],
                       radio_mayor=round(tt.majorRadius * 10, 3), radio_menor=round(tt.minorRadius * 10, 3))
            r['toros'].append(ent)
    for e in body.edges:
        g = e.geometry
        if g.curveType == adsk.core.Curve3DTypes.Circle3DCurveType:
            c = adsk.core.Circle3D.cast(g)
            r['circulos'].append({'centro': v3(c.center), 'radio': round(c.radius * 10, 3),
                                  'normal': [round(x, 5) for x in c.normal.asArray()]})
        elif g.curveType == adsk.core.Curve3DTypes.Arc3DCurveType:
            c = adsk.core.Arc3D.cast(g)
            r['circulos'].append({'centro': v3(c.center), 'radio': round(c.radius * 10, 3),
                                  'normal': [round(x, 5) for x in c.normal.asArray()],
                                  'arco_deg': round(math.degrees(c.endAngle - c.startAngle), 1)})
    return r


def transform_mundo(occ):
    T = occ.transform2.copy()
    padre = occ.assemblyContext
    while padre is not None:
        T.transformBy(padre.transform2)
        padre = padre.assemblyContext
    return T


try:
    os.makedirs(DEST, exist_ok=True)
    # Puede haber varias copias abiertas (por ejemplo v74 y v76): se toma la de versión más alta,
    # que es la última guardada. Tomar la última de la lista exportó una copia vieja el 12 oct 2026.
    import re as _re
    doc = None
    _mejor = -1
    for d in app.documents:
        if d.name.startswith('TFC_Sistema_A1mini_v3') and 'Dibujo' not in d.name:
            _m = _re.search(r' v(\d+)$', d.name)
            _v = int(_m.group(1)) if _m else 0
            if _v > _mejor:
                doc, _mejor = d, _v
    if doc is None:
        raise RuntimeError('no encuentro el documento de diseño abierto')
    design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
    root = design.rootComponent
    out.append('diseño: %s | ocurrencias: %d' % (doc.name, root.allOccurrences.count))
    indice = []
    vistos = set()
    for occ in root.allOccurrences:
        comp = occ.component
        nombre = comp.name
        if any(nombre.startswith(p) for p in OMITIR) or nombre in vistos:
            continue
        cuerpos_vis = [b for b in comp.bRepBodies]   # 19 oct: la visibilidad depende de lo que Diego aisle en la interfaz
        if not cuerpos_vis:
            continue
        vistos.add(nombre)
        dev = 8.0 if nombre == 'Ducto_cuchilla' else 4.0
        m = transform_mundo(occ).asArray()
        tris, ids, aristas = [], [], []
        rasgos = {'cilindros': [], 'esferas': [], 'planos': [], 'circulos': [], 'conos': [], 'toros': []}
        cuerpos = []
        masa_g = vol = 0.0
        id_cara = {}
        k = 0
        for b in cuerpos_vis:
            for f in b.faces:
                id_cara[f.tempId] = k
                t = malla_cara(f, dev)
                tris.extend(t)
                ids.extend([k] * len(t))
                k += 1
            aristas.extend(aristas_cuerpo(b, id_cara))
            bb = b.boundingBox
            cuerpos.append({'nombre': b.name, 'volumen_cm3': round(b.volume, 3),
                            'masa_g': round(b.physicalProperties.mass * 1000, 2),
                            'material': b.material.name if b.material else '',
                            'bbox': [v3(bb.minPoint), v3(bb.maxPoint)]})
            masa_g += b.physicalProperties.mass * 1000
            vol += b.volume
            rb = rasgos_cuerpo(b)
            for key in rasgos:
                rasgos[key].extend(rb[key])
        if not tris:
            continue
        seguro = nombre.replace(' ', '_')
        with open(os.path.join(DEST, seguro + '.tri'), 'wb') as f:
            f.write(struct.pack('<i', len(tris)))
            for t in tris:
                f.write(struct.pack('<9f', *t))
            f.write(struct.pack('<%di' % len(ids), *ids))
        with open(os.path.join(DEST, seguro + '.edges.json'), 'w', encoding='utf-8') as f:
            json.dump(aristas, f, ensure_ascii=False)
        info = {'componente': nombre, 'ocurrencia': occ.fullPathName,
                'transform_cm_filas': [m[0:4], m[4:8], m[8:12], m[12:16]],
                'masa_g': round(masa_g, 2), 'volumen_cm3': round(vol, 3),
                'material': cuerpos[0]['material'], 'cuerpos': cuerpos, 'caras': k, 'rasgos': rasgos}
        with open(os.path.join(DEST, seguro + '.json'), 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
        indice.append({'componente': nombre, 'masa_g': round(masa_g, 2), 'material': info['material'],
                       'triangulos': len(tris), 'caras': k, 'aristas': len(aristas), 'cuerpos': len(cuerpos)})
        out.append('%-28s %7.1f g %-8s tris %6d caras %4d aristas %4d  %s' % (
            nombre, masa_g, info['material'][:8], len(tris), k, len(aristas), occ.fullPathName[:40]))
    with open(os.path.join(DEST, '_indice.json'), 'w', encoding='utf-8') as f:
        json.dump(indice, f, ensure_ascii=False, indent=1)
    out.append('listo | %d componentes | %.0f s' % (len(indice), time.time() - t0))
except Exception:
    out.append('EXC ' + traceback.format_exc())
print('\n'.join(out))

def run(context=None):
    pass
