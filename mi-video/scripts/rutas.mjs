/**
 * Las carpetas del proyecto, en un solo sitio.
 *
 * Antes cada script llevaba su ruta escrita dentro —`G:/My Drive/…` aparecía en
 * seis— y cambiar de disco significaba buscarlas todas. Ahora se declaran en
 * `rutas.json` y los scripts preguntan.
 *
 * Orden de precedencia, de más fuerte a más débil:
 *
 *   1. `--origen` / `--destino` en la línea de comandos
 *   2. `VIDEO_ORIGEN` / `VIDEO_DESTINO` en el entorno
 *   3. `rutas.json`
 *
 * Así se puede decidir al final sin tocar el fichero: una tanda concreta se
 * redirige con una variable y ya.
 */
import fs from "fs";
import path from "path";

const cfg = JSON.parse(fs.readFileSync("rutas.json", "utf8"));

const deArg = (nombre) => {
  const i = process.argv.indexOf(`--${nombre}`);
  return i === -1 ? undefined : process.argv[i + 1];
};

const barras = (p) => p.split(path.sep).join("/").replace(/\/+$/, "");

export const rutas = {
  /** Dónde vive el material bruto que se monta. */
  origen: barras(deArg("origen") ?? process.env.VIDEO_ORIGEN ?? cfg.origen),
  /** Dónde se escriben los renders. */
  destino: barras(deArg("destino") ?? process.env.VIDEO_DESTINO ?? cfg.destino),
  /**
   * Todo lo temporal. **Nunca C:** — es el disco de arranque y lo llena un
   * render a 1800×3200. El aviso que da entonces es «Chrome rejecting the
   * request because the disk space is low», que ni menciona el disco del
   * sistema.
   */
  temporal: barras(
    deArg("tmp") ?? process.env.VIDEO_TMP ?? cfg.temporal ?? "tmp",
  ),
  trabajo: cfg.trabajo ?? "work",
  publico: cfg.publico ?? "public",
  fuentes: cfg.fuentes ?? {},
  tomas: cfg.tomas ?? {},
};

/** Carpeta temporal propia, creada si hace falta. Nunca en C:. */
export const temporal = (...partes) => {
  const p = path.join(rutas.temporal, ...partes);
  fs.mkdirSync(p, { recursive: true });
  return barras(p);
};

/** Ruta del bruto de un reel, resuelta contra `origen`. */
export const bruto = (reel) => {
  const toma = rutas.tomas[reel];
  if (!toma) throw new Error(`sin toma declarada para ${reel} en rutas.json`);
  return `${rutas.origen}/${toma}.mp4`;
};

/** Ruta de salida dentro de `destino`, creando la carpeta si hace falta. */
export const salida = (...partes) => {
  const p = path.join(rutas.destino, ...partes);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  return barras(p);
};
