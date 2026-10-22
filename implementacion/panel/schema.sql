-- Base de datos del registro (Tabla 22 de la tesis). D1, Cloudflare.
-- Cada fila conserva el identificador que creo la unidad de procesamiento, de
-- modo que un reenvio no duplica filas.

CREATE TABLE IF NOT EXISTS trabajos (
  id TEXT PRIMARY KEY,
  archivo TEXT,
  inicio REAL,
  fin REAL,
  resultado TEXT,          -- retirada, retenida, retirada manual, sin pieza, cancelada o fallida
  intentos INTEGER,
  tiempo_ciclo_s REAL,
  recibido REAL
);

CREATE TABLE IF NOT EXISTS eventos (
  id TEXT PRIMARY KEY,
  instante REAL,
  trabajo TEXT,
  tipo TEXT,               -- cambio de estado, etapa, pausa, parada, sin red...
  detalle TEXT,
  recibido REAL
);

CREATE TABLE IF NOT EXISTS capturas (
  id TEXT PRIMARY KEY,
  instante REAL,
  trabajo TEXT,
  tipo TEXT,               -- supervision, confirmacion de falla, fin de impresion, verificacion
  resolucion TEXT,
  veredicto TEXT,
  confianza REAL,
  descripcion TEXT,
  tokens INTEGER,
  clave_imagen TEXT,       -- clave del archivo en R2; la imagen no se guarda en la base
  recibido REAL
);

CREATE TABLE IF NOT EXISTS intervenciones (
  id TEXT PRIMARY KEY,
  instante REAL,
  trabajo TEXT,
  accion TEXT,             -- confirmar, cancelar, reintentar, pausar o reanudar
  tiempo_respuesta_s REAL,
  usuario TEXT,
  recibido REAL
);

CREATE TABLE IF NOT EXISTS configuracion (
  clave TEXT PRIMARY KEY,
  valor TEXT,
  actualizado REAL
);

CREATE TABLE IF NOT EXISTS usuarios (
  usuario TEXT PRIMARY KEY,
  resumen TEXT,            -- PBKDF2-SHA256 con sal; nunca la contrasena en claro
  creado REAL
);

CREATE INDEX IF NOT EXISTS eventos_instante ON eventos (instante);
CREATE INDEX IF NOT EXISTS capturas_instante ON capturas (instante);
CREATE INDEX IF NOT EXISTS intervenciones_instante ON intervenciones (instante);
CREATE INDEX IF NOT EXISTS trabajos_inicio ON trabajos (inicio);

INSERT OR IGNORE INTO configuracion (clave, valor, actualizado) VALUES
  ('operador_autorizado', '', unixepoch()),
  ('umbral_confianza', '1.0', unixepoch()),
  ('posicion_enfriamiento', 'por medir en el montaje', unixepoch()),
  ('posicion_flexion', 'por medir en el montaje', unixepoch()),
  ('posicion_captura', 'por medir en el montaje', unixepoch());
