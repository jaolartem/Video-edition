/**
 * **El lienzo de una pieza, del lado de los scripts.**
 *
 * Los números viven en `src/brand/lienzos.json` y **sólo ahí**; el lado del
 * render es `src/brand/lienzo.ts`. Dos lectores, un valor, igual que
 * `franja.json` con `franja.ts` y `franja.mjs` (C-670).
 *
 * Una pieza lo elige con `formato` en `ads/frames.json`; sin declararlo, el
 * vertical, que es lo que han sido siempre. Uno que no existe para la línea:
 * adivinar un cuadro es renderizar una pieza entera en el que no era.
 *
 *   node scripts/lienzo.mjs        # los lienzos declarados
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// `fileURLToPath` y no `new URL(...).pathname`: la ruta del repo tiene espacios.
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const J = JSON.parse(
  fs.readFileSync(path.join(RAIZ, "src/brand/lienzos.json"), "utf8"),
);

/** Los formatos declarados. Las claves con `_` son notas, no lienzos. */
export const FORMATOS = Object.keys(J).filter((k) => !k.startsWith("_"));

/** El vertical: el formato de una pieza que no declara otro. */
export const POR_DEFECTO = "vertical";

/**
 * El lienzo de un formato: ancho, alto, zona segura, banda de subtítulos y
 * columna libre, tal como los declara `lienzos.json`.
 *
 * @throws si el formato no está declarado.
 */
export const lienzoDe = (formato) => {
  const f = formato ?? POR_DEFECTO;
  if (!FORMATOS.includes(f))
    throw new Error(
      `formato «${f}»: no está en src/brand/lienzos.json (hay ${FORMATOS.join(", ")})`,
    );
  return { formato: f, ...J[f] };
};

if (process.argv[1] && process.argv[1].endsWith("lienzo.mjs")) {
  for (const f of FORMATOS) {
    const l = lienzoDe(f);
    console.log(
      `${f}: ${l.width}x${l.height} · seguro ${l.safe.top}/${l.safe.bottom}/` +
        `${l.safe.left}/${l.safe.right} · banda ${l.captionBand} a ${l.captionBottom}`,
    );
  }
}
