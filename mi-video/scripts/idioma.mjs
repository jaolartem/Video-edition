/**
 * La lengua de una cinta, del lado de JS. Lee los mismos ficheros que
 * `dominio/idioma.py` (`scripts/idiomas/<código>.json`): dos lectores de un
 * solo dato, no dos copias de la lista.
 */
import fs from "fs";
import { rutas } from "./rutas.mjs";

const POR_DEFECTO = "es";
const cargadas = new Map();

/** La lengua `codigo`, con cada lista como `Set`. */
export const idioma = (codigo = POR_DEFECTO) => {
  if (!cargadas.has(codigo)) {
    const ruta = `scripts/idiomas/${codigo}.json`;
    if (!fs.existsSync(ruta))
      throw new Error(`no hay ${ruta}: declara la lengua o quita la entrada de \`idiomas\` en rutas.json`);
    const d = JSON.parse(fs.readFileSync(ruta, "utf8"));
    cargadas.set(codigo, {
      codigo: d.whisper,
      colgantes: new Set(d.colgantes),
      noCierra: new Set(d.no_cierra),
      vacias: new Set(d.vacias),
      llanas: new Set(d.llanas),
      /** Lo que cuenta como cifra en esta lengua (C-710); sin declarar, la del español. */
      cifra: d.cifra ? new RegExp(d.cifra, "gi") : null,
    });
  }
  return cargadas.get(codigo);
};

/** La de la grabación `toma`. */
export const idiomaDeCinta = (toma) => idioma(rutas.idiomas[toma] ?? POR_DEFECTO);

/** La de una pieza, que es la de su cinta. */
export const idiomaDePieza = (slug) => idiomaDeCinta(rutas.tomas[slug] ?? slug);
