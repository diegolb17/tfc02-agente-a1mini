// Pagina de administracion del sistema de supervision y remocion (tesis, 5.5.2 a 5.5.4).
//
// El flujo es siempre saliente: el orquestador envia sus filas a /api/sincronizar
// y sus capturas a /api/imagen, con la clave del equipo. El administrador consulta
// las paginas con usuario y contrasena; la sesion vive en una cookie HttpOnly que
// caduca a las 8 horas. La pagina no envia nada al equipo: el orquestador descarga
// la configuracion desde /api/configuracion.

const SESION_HORAS = 8;
const DIA = 86400;
const PRECIO_ENTRADA = 0.75; // USD por millon de tokens de entrada, GPT-5.4 mini

const PAGINAS = [
  ["/", "Resumen"],
  ["/historial", "Historial"],
  ["/intervenciones", "Intervenciones"],
  ["/metricas", "Métricas"],
  ["/imagenes", "Imágenes"],
  ["/configuracion", "Configuración"],
];

const CONFIG = [
  ["operador_autorizado", "Operador autorizado (identificador de Telegram)"],
  ["umbral_confianza", "Umbral de confianza de la visión (0 a 1)"],
  ["posicion_enfriamiento", "Posición de enfriamiento de la plataforma"],
  ["posicion_flexion", "Posición de flexión de la plataforma"],
  ["posicion_captura", "Posición de captura de la plataforma"],
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ruta = url.pathname;
    try {
      if (ruta.startsWith("/api/")) return await api(request, env, ruta);
      if (ruta === "/login") return await login(request, env);
      if (ruta === "/salir") return redirigir("/login", "sesion=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict");
      const usuario = await sesionValida(request, env);
      if (!usuario) return redirigir("/login");
      if (ruta.startsWith("/imagen/")) return await imagen(env, decodeURIComponent(ruta.slice(8)));
      if (ruta === "/configuracion" && request.method === "POST") return await guardarConfiguracion(request, env);
      const pagina = { "/": resumen, "/historial": historial, "/intervenciones": intervenciones,
        "/metricas": metricas, "/imagenes": imagenes, "/configuracion": configuracion }[ruta];
      if (!pagina) return new Response("No encontrado", { status: 404 });
      return html(plantilla(ruta, usuario, await pagina(env, url)));
    } catch (error) {
      console.error(error);
      return new Response("Error interno", { status: 500 });
    }
  },

  // Retencion de la Tabla 22: eventos 180 dias, capturas e imagenes 90 dias.
  async scheduled(_evento, env) {
    const ahora = Date.now() / 1000;
    await env.DB.prepare("DELETE FROM eventos WHERE instante < ?").bind(ahora - 180 * DIA).run();
    const viejas = await env.DB.prepare("SELECT id, clave_imagen FROM capturas WHERE instante < ?")
      .bind(ahora - 90 * DIA).all();
    for (const c of viejas.results) if (c.clave_imagen) await env.IMAGENES.delete(c.clave_imagen);
    await env.DB.prepare("DELETE FROM capturas WHERE instante < ?").bind(ahora - 90 * DIA).run();
  },
};

// Interfaz del equipo ---------------------------------------------------------

async function api(request, env, ruta) {
  const clave = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/, "");
  if (!env.EQUIPO_CLAVE || !(await igualesSeguro(clave, env.EQUIPO_CLAVE))) {
    return json({ error: "clave del equipo invalida" }, 401);
  }
  if (ruta === "/api/sincronizar" && request.method === "POST") return await sincronizar(request, env);
  if (ruta.startsWith("/api/imagen/") && request.method === "PUT") {
    const nombre = decodeURIComponent(ruta.slice(12));
    if (!/^[A-Za-z0-9_.-]{1,80}$/.test(nombre)) return json({ error: "clave de imagen invalida" }, 400);
    const cuerpo = await request.arrayBuffer();
    if (cuerpo.byteLength > 2_000_000) return json({ error: "imagen mayor de 2 MB" }, 413);
    await env.IMAGENES.put(nombre, cuerpo, { httpMetadata: { contentType: "image/jpeg" } });
    return json({ guardada: nombre });
  }
  if (ruta === "/api/configuracion" && request.method === "GET") {
    const filas = await env.DB.prepare("SELECT clave, valor FROM configuracion").all();
    return json(Object.fromEntries(filas.results.map((f) => [f.clave, f.valor])));
  }
  return json({ error: "ruta no encontrada" }, 404);
}

const COLUMNAS = {
  trabajos: ["id", "archivo", "inicio", "fin", "resultado", "intentos", "tiempo_ciclo_s"],
  eventos: ["id", "instante", "trabajo", "tipo", "detalle"],
  capturas: ["id", "instante", "trabajo", "tipo", "resolucion", "veredicto", "confianza", "descripcion",
    "tokens", "clave_imagen"],
  intervenciones: ["id", "instante", "trabajo", "accion", "tiempo_respuesta_s", "usuario"],
};

async function sincronizar(request, env) {
  const datos = await request.json();
  const recibido = Date.now() / 1000;
  const sentencias = [];
  const aceptadas = {};
  for (const [tabla, columnas] of Object.entries(COLUMNAS)) {
    const filas = Array.isArray(datos[tabla]) ? datos[tabla].slice(0, 300) : [];
    aceptadas[tabla] = [];
    const lista = [...columnas, "recibido"];
    const marcas = lista.map(() => "?").join(", ");
    // Los trabajos se actualizan al cerrarse; el resto se descarta si ya existe.
    const sql = tabla === "trabajos"
      ? `INSERT INTO trabajos (${lista}) VALUES (${marcas}) ON CONFLICT(id) DO UPDATE SET
         archivo=excluded.archivo, fin=excluded.fin, resultado=excluded.resultado,
         intentos=excluded.intentos, tiempo_ciclo_s=excluded.tiempo_ciclo_s, recibido=excluded.recibido`
      : `INSERT OR IGNORE INTO ${tabla} (${lista}) VALUES (${marcas})`;
    for (const fila of filas) {
      if (typeof fila.id !== "string" || !/^[A-Za-z0-9]{8,64}$/.test(fila.id)) continue;
      const valores = columnas.map((c) => (fila[c] === undefined ? null : fila[c]));
      sentencias.push(env.DB.prepare(sql).bind(...valores, recibido));
      aceptadas[tabla].push(fila.id);
    }
  }
  if (sentencias.length) await env.DB.batch(sentencias);
  return json({ aceptadas });
}

// Sesion del administrador ------------------------------------------------------

async function login(request, env) {
  if (request.method !== "POST") return html(paginaLogin(""));
  const formulario = await request.formData();
  const usuario = String(formulario.get("usuario") || "");
  const contrasena = String(formulario.get("contrasena") || "");
  const usuarioOk = await igualesSeguro(usuario, env.ADMIN_USUARIO || "");
  const contrasenaOk = await verificarContrasena(contrasena, env.ADMIN_HASH || "");
  if (!(usuarioOk && contrasenaOk)) {
    await new Promise((r) => setTimeout(r, 800));
    return html(paginaLogin("Usuario o contraseña incorrectos."), 401);
  }
  const expira = Math.floor(Date.now() / 1000) + SESION_HORAS * 3600;
  const carga = `${usuario}|${expira}`;
  const firma = await hmac(env.SESION_CLAVE, carga);
  const cookie = `sesion=${b64url(new TextEncoder().encode(carga))}.${firma}; Path=/; Max-Age=${SESION_HORAS * 3600}; HttpOnly; Secure; SameSite=Strict`;
  return redirigir("/", cookie);
}

async function sesionValida(request, env) {
  const cookie = (request.headers.get("Cookie") || "").match(/(?:^|;\s*)sesion=([^;]+)/);
  if (!cookie || !env.SESION_CLAVE) return null;
  const [cargaB64, firma] = cookie[1].split(".");
  if (!cargaB64 || !firma) return null;
  let carga;
  try {
    carga = new TextDecoder().decode(desdeB64url(cargaB64));
  } catch {
    return null;
  }
  if (!(await igualesSeguro(firma, await hmac(env.SESION_CLAVE, carga)))) return null;
  const [usuario, expira] = carga.split("|");
  return Number(expira) > Date.now() / 1000 ? usuario : null;
}

// Formato del resumen: pbkdf2_sha256$iteraciones$sal_base64$resumen_base64
async function verificarContrasena(contrasena, resumen) {
  const partes = resumen.split("$");
  if (partes.length !== 4 || partes[0] !== "pbkdf2_sha256") return false;
  const iteraciones = Number(partes[1]);
  const sal = Uint8Array.from(atob(partes[2]), (c) => c.charCodeAt(0));
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(contrasena), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: sal, iterations: iteraciones }, base, 256);
  const calculado = btoa(String.fromCharCode(...new Uint8Array(bits)));
  return igualesSeguro(calculado, partes[3]);
}

async function hmac(secreto, texto) {
  const clave = await crypto.subtle.importKey("raw", new TextEncoder().encode(secreto),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64url(new Uint8Array(await crypto.subtle.sign("HMAC", clave, new TextEncoder().encode(texto))));
}

async function igualesSeguro(a, b) {
  const ca = new TextEncoder().encode(String(a));
  const cb = new TextEncoder().encode(String(b));
  if (ca.length !== cb.length) return false;
  return crypto.subtle.timingSafeEqual(ca, cb);
}

function b64url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function desdeB64url(texto) {
  const b64 = texto.replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(b64 + "===".slice((b64.length + 3) % 4)), (c) => c.charCodeAt(0));
}

// Paginas -------------------------------------------------------------------------

async function todas(env, sql, ...valores) {
  return (await env.DB.prepare(sql).bind(...valores).all()).results;
}

async function una(env, sql, ...valores) {
  return env.DB.prepare(sql).bind(...valores).first();
}

async function resumen(env) {
  const estado = await una(env, "SELECT detalle, instante FROM eventos WHERE tipo = 'cambio de estado' ORDER BY instante DESC LIMIT 1");
  const trabajo = await una(env, "SELECT * FROM trabajos ORDER BY inicio DESC LIMIT 1");
  const etapa = trabajo ? await una(env, "SELECT detalle, instante FROM eventos WHERE trabajo = ? AND tipo IN ('etapa', 'remocion', 'parada', 'pausa') ORDER BY instante DESC LIMIT 1", trabajo.id) : null;
  const captura = await una(env, "SELECT * FROM capturas ORDER BY instante DESC LIMIT 1");
  const sincronizacion = await una(env, "SELECT MAX(recibido) AS r FROM eventos");
  const atencion = await todas(env, "SELECT tipo, detalle, instante FROM eventos WHERE tipo IN ('parada', 'pausa', 'sin red', 'confirmacion vencida') ORDER BY instante DESC LIMIT 5");
  const fase = estado ? estado.detalle.split(" a ").pop() : "sin datos";
  return `
  <h1>Resumen</h1>
  <p class="nota">Última sincronización con la unidad de procesamiento: ${fecha(sincronizacion && sincronizacion.r)}</p>
  <div class="tarjetas">
    <section class="tarjeta"><h2>Impresora</h2>
      <p class="grande">${esc(FASES[fase] || fase)}</p>
      <p>Último cambio: ${estado ? detalleEvento({ tipo: "cambio de estado", detalle: estado.detalle }) : "sin datos"}</p>
      <p>${fecha(estado && estado.instante)}</p></section>
    <section class="tarjeta"><h2>Trabajo</h2>
      ${trabajo ? `<p class="grande">${esc(trabajo.archivo || "sin nombre")}</p>
      <p>Inicio: ${fecha(trabajo.inicio)}</p>
      <p>Resultado: ${esc(RESULTADOS[trabajo.resultado] || trabajo.resultado || "en curso")}${trabajo.intentos ? `, ${trabajo.intentos} intento(s)` : ""}</p>` : "<p>Sin trabajos registrados.</p>"}</section>
    <section class="tarjeta"><h2>Ciclo de remoción</h2>
      <p>${esc(etapa ? etapa.detalle : "Sin ciclo de remoción en este trabajo.")}</p>${etapa ? `<p>${fecha(etapa.instante)}</p>` : ""}</section>
  </div>
  <section class="tarjeta ancha"><h2>Última captura</h2>
    ${captura ? `<div class="captura">${miniatura(captura.clave_imagen)}
      <div><p><b>${esc(mayuscula(captura.tipo))}</b>, ${resolucion(captura.resolucion)}, ${fecha(captura.instante)}</p>
      <p>Veredicto: <b>${esc(VEREDICTOS[captura.veredicto] || captura.veredicto)}</b>, confianza ${num(captura.confianza, 2)}</p>
      <p>${esc(captura.descripcion)}</p></div></div>` : "<p>Sin capturas.</p>"}</section>
  <section class="tarjeta ancha"><h2>Eventos que requirieron atención</h2>
    ${tabla(["Fecha y hora", "Tipo", "Detalle"], atencion.map((e) => [fecha(e.instante), tipoEvento(e.tipo), detalleEvento(e)]), "Sin paradas ni pausas.")}</section>`;
}

async function historial(env) {
  const filas = await todas(env, "SELECT * FROM trabajos ORDER BY inicio DESC LIMIT 200");
  return `<h1>Historial de trabajos</h1>
  <p class="nota">Cada impresión con su resultado y el número de intentos de remoción (R-CTRL-02).</p>
  ${tabla(["Archivo", "Inicio", "Fin", "Resultado", "Intentos", "Ciclo de remoción"],
    filas.map((t) => [esc(t.archivo), fecha(t.inicio), fecha(t.fin),
      esc(RESULTADOS[t.resultado] || t.resultado || "en curso"), num(t.intentos, 0),
      t.tiempo_ciclo_s ? `${num(t.tiempo_ciclo_s / 60, 1)} min` : "sin dato"]), "Sin trabajos registrados.")}`;
}

async function intervenciones(env) {
  const filas = await todas(env, `SELECT i.*, t.archivo FROM intervenciones i LEFT JOIN trabajos t ON t.id = i.trabajo
    ORDER BY i.instante DESC LIMIT 200`);
  const paradas = await todas(env, `SELECT e.*, t.archivo FROM eventos e LEFT JOIN trabajos t ON t.id = e.trabajo
    WHERE e.tipo IN ('parada', 'pausa', 'falla no confirmada', 'sin red', 'confirmacion vencida', 'confirmacion solicitada')
    ORDER BY e.instante DESC LIMIT 100`);
  const eventos = await todas(env, "SELECT * FROM eventos ORDER BY instante DESC LIMIT 25");
  return `<h1>Intervenciones</h1>
  <h2>Acciones del operador</h2>
  ${tabla(["Fecha y hora", "Trabajo", "Acción", "Tiempo de respuesta", "Usuario"],
    filas.map((i) => [fecha(i.instante), esc(i.archivo || "sin trabajo"), esc(i.accion),
      i.tiempo_respuesta_s == null ? "sin dato" : `${num(i.tiempo_respuesta_s, 1)} s`, esc(i.usuario || "operador")]),
    "Sin intervenciones.")}
  <h2>Confirmaciones solicitadas, pausas y paradas</h2>
  ${tabla(["Fecha y hora", "Trabajo", "Tipo", "Detalle"],
    paradas.map((e) => [fecha(e.instante), esc(e.archivo || "sin trabajo"), tipoEvento(e.tipo), detalleEvento(e)]), "Sin registros.")}
  <h2>Eventos recientes del ciclo</h2>
  ${tabla(["Fecha y hora", "Tipo", "Detalle"], eventos.map((e) => [fecha(e.instante), tipoEvento(e.tipo), detalleEvento(e)]), "Sin eventos.")}`;
}

async function metricas(env) {
  const t = await una(env, `SELECT COUNT(*) AS total,
    SUM(CASE WHEN intentos > 0 THEN 1 ELSE 0 END) AS con_ciclo,
    SUM(CASE WHEN resultado IN ('retirada', 'fallida') AND intentos = 1 THEN 1 ELSE 0 END) AS primer_intento,
    AVG(tiempo_ciclo_s) AS ciclo_medio FROM trabajos`);
  const n = await una(env, "SELECT COUNT(*) AS n FROM intervenciones");
  const fallas = await una(env, "SELECT COUNT(*) AS n FROM eventos WHERE tipo = 'pausa'");
  const c = await una(env, "SELECT COUNT(*) AS n, SUM(tokens) AS tokens FROM capturas");
  const tasa = t.con_ciclo ? (100 * t.primer_intento) / t.con_ciclo : null;
  const porCien = t.total ? (100 * n.n) / t.total : null;
  const costo = ((c.tokens || 0) * PRECIO_ENTRADA) / 1e6;
  return `<h1>Métricas</h1>
  <div class="tarjetas">
    ${indicador("Trabajos registrados", num(t.total, 0))}
    ${indicador("Retiradas al primer intento", tasa == null ? "sin dato" : `${num(tasa, 0)} %`)}
    ${indicador("Tiempo medio del ciclo de remoción", t.ciclo_medio ? `${num(t.ciclo_medio / 60, 1)} min` : "sin dato")}
    ${indicador("Intervenciones por cada 100 impresiones", porCien == null ? "sin dato" : num(porCien, 0))}
    ${indicador("Fallas detectadas con pausa", num(fallas.n, 0))}
    ${indicador("Consultas al modelo", num(c.n, 0))}
    ${indicador("Tokens de entrada consumidos", num(c.tokens || 0, 0))}
  </div>
  <p class="nota">Costo de entrada estimado de las consultas registradas: ${num(costo, 4)} USD, a ${PRECIO_ENTRADA} USD por millón de tokens.</p>`;
}

async function imagenes(env) {
  const filas = await todas(env, `SELECT c.*, t.archivo FROM capturas c LEFT JOIN trabajos t ON t.id = c.trabajo
    ORDER BY c.instante DESC LIMIT 40`);
  const referencia = await env.IMAGENES.head("referencia.jpg");
  return `<h1>Imágenes</h1>
  <section class="tarjeta ancha"><h2>Referencia de la plataforma vacía</h2>
    ${referencia ? miniatura("referencia.jpg") : "<p>El operador aún no tomó la referencia.</p>"}</section>
  <div class="galeria">${filas.map((c) => `<figure>${miniatura(c.clave_imagen)}
    <figcaption><b>${esc(mayuscula(c.tipo))}</b>, ${resolucion(c.resolucion)}<br>${fecha(c.instante)}<br>
    ${esc(c.archivo || "")}<br>Veredicto: <b>${esc(VEREDICTOS[c.veredicto] || c.veredicto)}</b>, confianza ${num(c.confianza, 2)}, ${num(c.tokens, 0)} tokens<br>
    <span class="nota">${esc(c.descripcion)}</span></figcaption></figure>`).join("") || "<p>Sin capturas.</p>"}</div>`;
}

async function configuracion(env, url) {
  const filas = await todas(env, "SELECT clave, valor, actualizado FROM configuracion");
  const valores = Object.fromEntries(filas.map((f) => [f.clave, f]));
  const aviso = url.searchParams.get("guardado") ? '<p class="ok">Configuración guardada. El orquestador la descarga al arrancar y cada 5 minutos.</p>' : "";
  return `<h1>Configuración</h1>${aviso}
  <form method="post" class="tarjeta ancha">
    ${CONFIG.map(([clave, etiqueta]) => `<label>${esc(etiqueta)}
      <input name="${clave}" value="${esc(valores[clave] ? valores[clave].valor : "")}"></label>
      <p class="nota">Actualizado: ${fecha(valores[clave] && valores[clave].actualizado)}</p>`).join("")}
    <button type="submit">Guardar</button>
  </form>`;
}

async function guardarConfiguracion(request, env) {
  const origen = request.headers.get("Origin");
  if (origen && origen !== new URL(request.url).origin) return new Response("Origen no permitido", { status: 403 });
  const formulario = await request.formData();
  const umbral = Number(formulario.get("umbral_confianza"));
  if (!(umbral >= 0 && umbral <= 1)) return html(plantilla("/configuracion", "", '<p class="error">El umbral debe estar entre 0 y 1.</p>'), 400);
  const ahora = Date.now() / 1000;
  await env.DB.batch(CONFIG.map(([clave]) => env.DB.prepare(
    "INSERT INTO configuracion (clave, valor, actualizado) VALUES (?, ?, ?) ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado = excluded.actualizado",
  ).bind(clave, String(formulario.get(clave) || "").slice(0, 200), ahora)));
  return redirigir("/configuracion?guardado=1");
}

async function imagen(env, clave) {
  const objeto = await env.IMAGENES.get(clave);
  if (!objeto) return new Response("Imagen no encontrada", { status: 404 });
  return new Response(objeto.body, { headers: { "Content-Type": "image/jpeg", "Cache-Control": "private, max-age=3600" } });
}

// Utilidades de presentacion -----------------------------------------------------

const FASES = { IDLE: "En reposo", PREPARE: "Preparando", RUNNING: "Imprimiendo", PAUSE: "En pausa",
  FINISH: "Impresión terminada", FAILED: "Detenida", "sin datos": "Sin datos" };
const RESULTADOS = { retirada: "Retirada", retenida: "Retenida tras 3 intentos", "retirada manual": "Retirada a mano",
  "sin pieza": "Sin pieza", fallida: "Fallida, pieza retirada", cancelada: "Remoción cancelada por el operador" };
const VEREDICTOS = { normal: "normal", falla: "falla", pieza: "pieza presente", libre: "plataforma libre",
  anomala: "escena anómala", invalido: "sin veredicto válido" };
const TIPOS_EVENTO = { "cambio de estado": "Cambio de estado", etapa: "Etapa", remocion: "Remoción", pausa: "Pausa",
  parada: "Parada", reanudacion: "Reanudación", "mensaje del operador": "Mensaje del operador", referencia: "Referencia",
  "sin red": "Sin red", "confirmacion solicitada": "Confirmación solicitada", "confirmacion vencida": "Confirmación vencida",
  "falla no confirmada": "Falla no confirmada" };

function mayuscula(texto) {
  const s = String(texto || "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function tipoEvento(tipo) {
  return esc(TIPOS_EVENTO[tipo] || mayuscula(tipo));
}

function detalleEvento(e) {
  if (e.tipo === "cambio de estado") {
    return esc(String(e.detalle).split(" a ").map((f) => (FASES[f] || f).toLowerCase()).join(" a "));
  }
  return esc(e.detalle);
}

function resolucion(texto) {
  const m = String(texto || "").match(/^(\d+)x(\d+)$/);
  return m ? `${num(m[1], 0)} x ${num(m[2], 0)}` : esc(texto);
}

function esc(valor) {
  return String(valor == null ? "" : valor).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// Formato de la tesis: punto decimal y espacio como separador de millares.
function num(valor, decimales) {
  if (valor == null || Number.isNaN(Number(valor))) return "sin dato";
  const [entero, fraccion] = Number(valor).toFixed(decimales).split(".");
  const conEspacios = entero.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return fraccion ? `${conEspacios}.${fraccion}` : conEspacios;
}

function fecha(segundos) {
  if (!segundos) return "sin dato";
  return new Date(segundos * 1000).toLocaleString("es-PE", { timeZone: "America/Lima", dateStyle: "short", timeStyle: "medium" });
}

function miniatura(clave) {
  if (!clave) return '<div class="sin-imagen">Sin imagen</div>';
  const ruta = `/imagen/${encodeURIComponent(clave)}`;
  return `<a href="${ruta}"><img src="${ruta}" alt="Captura ${esc(clave)}" loading="lazy"></a>`;
}

function indicador(titulo, valor) {
  return `<section class="tarjeta"><h2>${esc(titulo)}</h2><p class="grande">${valor}</p></section>`;
}

function tabla(cabecera, filas, vacio) {
  if (!filas.length) return `<p class="nota">${esc(vacio)}</p>`;
  return `<div class="tabla"><table><thead><tr>${cabecera.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${filas.map((f) => `<tr>${f.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

const ESTILO = `
:root { --fondo:#f4f5f7; --tarjeta:#fff; --texto:#1d2330; --tenue:#5d6575; --borde:#d9dce3; --acento:#1f3f68; }
* { box-sizing:border-box; }
body { margin:0; font-family:"Segoe UI", system-ui, sans-serif; background:var(--fondo); color:var(--texto); font-size:15px; }
header { background:var(--acento); color:#fff; padding:12px 20px; display:flex; flex-wrap:wrap; align-items:center; gap:8px 20px; }
header .marca { font-weight:600; margin-right:auto; }
header a { color:#fff; text-decoration:none; opacity:.85; padding:4px 0; }
header a.activa { opacity:1; border-bottom:2px solid #fff; }
main { max-width:1100px; margin:0 auto; padding:20px; }
h1 { font-size:22px; margin:8px 0 12px; } h2 { font-size:15px; margin:0 0 8px; color:var(--tenue); font-weight:600; }
main > h2 { margin-top:22px; color:var(--texto); }
.tarjetas { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin-bottom:14px; }
.tarjeta { background:var(--tarjeta); border:1px solid var(--borde); border-radius:6px; padding:14px 16px; }
.tarjeta p { margin:4px 0; } .ancha { margin-bottom:14px; }
.grande { font-size:20px; font-weight:600; }
.nota { color:var(--tenue); font-size:13px; }
.captura { display:flex; flex-wrap:wrap; gap:16px; align-items:flex-start; }
.captura img { width:320px; max-width:100%; border:1px solid var(--borde); border-radius:4px; }
.tabla { overflow-x:auto; background:var(--tarjeta); border:1px solid var(--borde); border-radius:6px; }
table { border-collapse:collapse; width:100%; } th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--borde); vertical-align:top; }
th { background:#eef0f4; font-weight:600; font-size:13px; white-space:nowrap; }
td:first-child { white-space:nowrap; }
.galeria { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:14px; }
.galeria figure { margin:0; background:var(--tarjeta); border:1px solid var(--borde); border-radius:6px; padding:10px; font-size:13px; }
.galeria img, .tarjeta > a img { width:100%; max-width:420px; border-radius:4px; }
.sin-imagen { width:240px; height:150px; display:flex; align-items:center; justify-content:center; background:#eef0f4; color:var(--tenue); }
label { display:block; font-weight:600; margin-top:10px; } input { width:100%; padding:8px; margin-top:4px; border:1px solid var(--borde); border-radius:4px; font:inherit; }
button { margin-top:16px; padding:9px 18px; background:var(--acento); color:#fff; border:0; border-radius:4px; font:inherit; cursor:pointer; }
.ok { color:#1d6b35; } .error { color:#a3241d; }
.login { max-width:360px; margin:12vh auto; }
`;

function plantilla(ruta, usuario, contenido) {
  const menu = PAGINAS.map(([r, t]) => `<a href="${r}"${r === ruta ? ' class="activa"' : ""}>${t}</a>`).join("");
  return `<!doctype html><html lang="es"><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Panel de administración, Bambu Lab A1 mini</title><style>${ESTILO}</style></head>
  <body><header><span class="marca">Panel de administración, Bambu Lab A1 mini</span>${menu}
  <a href="/salir">Salir${usuario ? ` (${esc(usuario)})` : ""}</a></header><main>${contenido}</main></body></html>`;
}

function paginaLogin(error) {
  return `<!doctype html><html lang="es"><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ingreso, panel de administración</title><style>${ESTILO}</style></head><body>
  <form method="post" action="/login" class="tarjeta login">
    <h1>Panel de administración</h1><p class="nota">Sistema de supervisión y remoción para la Bambu Lab A1 mini</p>
    ${error ? `<p class="error">${esc(error)}</p>` : ""}
    <label>Usuario<input name="usuario" autocomplete="username" required></label>
    <label>Contraseña<input name="contrasena" type="password" autocomplete="current-password" required></label>
    <button type="submit">Ingresar</button></form></body></html>`;
}

function html(cuerpo, estado = 200) {
  return new Response(cuerpo, { status: estado, headers: { "Content-Type": "text/html; charset=utf-8",
    "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; img-src 'self'; form-action 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin" } });
}

function json(datos, estado = 200) {
  return new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });
}

function redirigir(destino, cookie) {
  const cabeceras = { Location: destino };
  if (cookie) cabeceras["Set-Cookie"] = cookie;
  return new Response(null, { status: 303, headers: cabeceras });
}
