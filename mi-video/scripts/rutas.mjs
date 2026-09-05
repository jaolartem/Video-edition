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

/**
 * Los VIDEOS que componen una grabacion, en orden. Uno solo si es plana.
 *
 * Jaime, al ver que dos camaras a la vez ya casi se podian montar: *«para eso,
 * de aca en adelante subo cada video grabado de esta forma en una carpeta con
 * los videos que lo componen»*.
 *
 * Una grabacion deja de ser un fichero y pasa a ser **una carpeta con angulos
 * dentro**. Las dos formas conviven: las siete cintas de agosto son ficheros
 * planos y siguen siendo grabaciones de un angulo, que es lo que son.
 *
 * El orden es alfabetico y **el primero es el principal**: de el sale todo lo
 * que hoy pide «la cinta». La copia Python vive en `scripts/rutas.py`.
 */
export const angulos = (toma) => {
  const d = `${rutas.origen}/${toma}`;
  if (!fs.existsSync(d) || !fs.statSync(d).isDirectory()) {
    const plano = `${rutas.origen}/${toma}.mp4`;
    return fs.existsSync(plano) ? [plano] : [];
  }
  return fs
    .readdirSync(d)
    .filter((f) => /\.(mp4|mov|mkv)$/i.test(f))
    .sort()
    .map((f) => `${d}/${f}`);
};

/** El video principal de una grabacion, sea fichero suelto o carpeta. */
export const cinta = (toma) => {
  const a = angulos(toma);
  if (!a.length)
    throw new Error(
      `no encuentro la grabacion ${toma} en ${rutas.origen}` +
        ` (ni ${toma}.mp4 ni carpeta ${toma}/)`,
    );
  return a[0];
};

/** Ruta del bruto de un reel, resuelta contra `origen`. */
export const bruto = (reel) => {
  const toma = rutas.tomas[reel];
  if (!toma) throw new Error(`sin toma declarada para ${reel} en rutas.json`);
  return cinta(toma);
};

/** Ruta de salida dentro de `destino`, creando la carpeta si hace falta. */
export const salida = (...partes) => {
  const p = path.join(rutas.destino, ...partes);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  return barras(p);
};
