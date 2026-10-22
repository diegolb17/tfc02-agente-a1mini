# -*- coding: utf-8 -*-
"""Cliente minimo del MCP de Fusion 360 por HTTP.

Existe porque el servidor MCP arranca cuando Diego abre Fusion, y si la sesion de
Claude Code ya estaba en marcha las herramientas fusion_mcp_* no quedan
registradas. Hablarle directo al endpoint evita tener que reiniciar la sesion.

    python fusion_cli.py tools
    python fusion_cli.py call fusion_mcp_read '{"readType":"document"}'
    python fusion_cli.py script mi_script.py          # lo envuelve en execute/script
"""
import json
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

URL = 'http://127.0.0.1:27183/mcp'
_sid = [None]


def rpc(method, params=None, rid=1):
    body = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json, text/event-stream')
    if _sid[0]:
        req.add_header('Mcp-Session-Id', _sid[0])
    r = urllib.request.urlopen(req, timeout=1500)
    if not _sid[0]:
        _sid[0] = r.headers.get('Mcp-Session-Id')
    raw = r.read().decode('utf8', errors='replace')
    # el transporte puede responder como SSE: se toma la ultima linea data:
    if raw.lstrip().startswith('event:') or '\ndata:' in raw:
        trozos = [l[5:].strip() for l in raw.splitlines() if l.startswith('data:')]
        raw = trozos[-1] if trozos else raw
    return json.loads(raw)


def notificar(method):
    """Notificacion JSON-RPC: SIN campo id. El servidor exige la de
    notifications/initialized antes de aceptar tools/list o tools/call; si se le
    manda con id la trata como peticion y la sesion queda sin inicializar."""
    req = urllib.request.Request(URL, method='POST',
                                 data=json.dumps({"jsonrpc": "2.0", "method": method}).encode())
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json, text/event-stream')
    if _sid[0]:
        req.add_header('Mcp-Session-Id', _sid[0])
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass


def conectar():
    rpc('initialize', {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "tfc-cli", "version": "1"}})
    notificar('notifications/initialized')


def llamar(nombre, args):
    res = rpc('tools/call', {"name": nombre, "arguments": args}, rid=2)
    if 'error' in res:
        return 'ERROR ' + json.dumps(res['error'], ensure_ascii=False)
    salida = []
    for c in res.get('result', {}).get('content', []):
        salida.append(c.get('text', json.dumps(c, ensure_ascii=False)))
    return '\n'.join(salida) if salida else json.dumps(res.get('result'), ensure_ascii=False)


def main():
    conectar()
    modo = sys.argv[1] if len(sys.argv) > 1 else 'tools'
    if modo == 'tools':
        res = rpc('tools/list', {}, rid=2)
        for t in res.get('result', {}).get('tools', []):
            print('==', t['name'])
            print('   ', (t.get('description') or '').strip().replace('\n', ' ')[:300])
            print('    args:', json.dumps(t.get('inputSchema', {}).get('properties', {}),
                                          ensure_ascii=False)[:900])
    elif modo == 'call':
        print(llamar(sys.argv[2], json.loads(sys.argv[3])))
    elif modo == 'script':
        codigo = open(sys.argv[2], encoding='utf-8').read()
        solo_lectura = '--rw' not in sys.argv
        # el script va DENTRO de 'object', no al nivel de los argumentos
        print(llamar('fusion_mcp_execute',
                     {"featureType": "script",
                      "object": {"script": codigo, "readOnly": solo_lectura}}))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
