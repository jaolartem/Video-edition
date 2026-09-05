#!/usr/bin/env node
/**
 * **Reescribe el estado medido de `docs/bitacora.md`.**
 *
 * La bitácora es para quien monta, y la mitad de arriba —qué se está haciendo y
 * por qué— se escribe a mano porque es criterio. La de abajo, no: son números
 * que ya existen en `src/reels.json`, y un número copiado a mano se queda viejo
 * en el primer render.
 *
 * Es el aprendizaje 24 aplicado a la documentación de trabajo: **un fichero no
 * se entera de que arreglaste el bug**. Aquí se entera, porque se vuelve a
 * escribir en cada montaje.
 *
 *   node scripts/bitacora.mjs
 */
import fs from "node:fs";
import path from "node:path";

/** Igual que en `reels-spec.mjs`: los .mjs no pueden importar los tokens .ts. */
const FPS = 30;

const RAIZ = path.resolve(process.cwd(), "..");
const DOC = path.join(RAIZ, "docs/bitacora.md");
const ABRE = "<!-- estado:inicio -->";
const CIERRA = "<!-- estado:fin -->";

const spec = JSON.parse(fs.readFileSync("src/reels.json", "utf8"));
const log = fs.readFileSync(path.join(RAIZ, "docs/correcciones.md"), "utf8");
const correcciones = [...log.matchAll(/^### C-(\d+)/gm)].length;
const guardas = [...log.matchAll(/`[^`]+`\s*(?:::|!:)\s*`[^`]+`/g)].length;

const s = (f) => (f / FPS).toFixed(1);

/** El hueco mudo más largo, con el mismo criterio que aplica `Reel.tsx`. */
const mudo = (r) => {
  const tapan = [
    ...r.tarjetas,
    ...r.cortinillas,
    ...(r.cta ? [{ at: r.cta.at * FPS, duration: r.cta.dur * FPS }] : []),
  ];
  const vis = r.captions
    .filter(
      (c) =>
        tapan.reduce(
          (n, b) =>
            n +
            Math.max(
              0,
              Math.min(c.at + c.duration, b.at + b.duration) - Math.max(c.at, b.at),
            ),
          0,
        ) <= c.duration / 2,
    )
    .sort((x, y) => x.at - y.at);
  let peor = 0;
  let t = 0;
  for (const c of vis) {
    peor = Math.max(peor, c.at - t);
    t = Math.max(t, c.at + c.duration);
  }
  return { peor: Math.max(peor, Math.round(r.duracion * FPS) - t), vis: vis.length };
};

const filas = spec.map((r) => {
  const m = mudo(r);
  return `| **${r.id}** | ${r.duracion.toFixed(1)} s | ${m.vis}/${r.captions.length} | ${r.compuestos} | ${s(m.peor)} s | ${r.paneles.length} | ${r.boards.length} | ${r.tarjetas.length} | ${r.cta ? r.cta.at.toFixed(1) + " s" : "—"} |`;
});

const hoy = new Date().toISOString().slice(0, 10);

const bloque = `${ABRE}

*Generado por \`scripts/bitacora.mjs\` en cada montaje. No editar a mano.*
**${hoy}** · ${correcciones} correcciones en el log, ${guardas} guardas en pie.

| Pieza | Dura | cc visibles | cc compuestos | Mudo más largo | Paneles | Tableros | Tarjetas | CTA |
|---|---|---|---|---|---|---|---|---|
${filas.join("\n")}

**Cómo se lee esta tabla.**

- **cc visibles** — subtítulos que llegan a pantalla, sobre los que trae el
  montaje. La diferencia son los que caen bajo una tarjeta o bajo el CTA, que
  llevan su propio texto. Si la diferencia crece sin que hayas añadido tarjetas,
  algo está tapando de más.
- **Mudo más largo** — el hueco más largo sin una palabra en pantalla. Por
  encima de 10 s el montaje **para**: el argumento tiene que funcionar sin
  audio.
- **cc compuestos** — remates a dos renglones o en grande. Salen de las frases
  con coma; cero no es un error, es que esa pieza se habla de corrido.

${CIERRA}`;

const doc = fs.readFileSync(DOC, "utf8");
const i = doc.indexOf(ABRE);
const j = doc.indexOf(CIERRA);
if (i < 0 || j < 0) {
  throw new Error(
    `docs/bitacora.md no tiene las marcas ${ABRE} … ${CIERRA}. Sin ellas no se ` +
    `sabe qué trozo es generado y cuál escribió una persona.`,
  );
}
fs.writeFileSync(DOC, doc.slice(0, i) + bloque + doc.slice(j + CIERRA.length));
console.log(`bitacora: ${spec.length} piezas · ${correcciones} correcciones`);
