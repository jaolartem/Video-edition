/**
 * **¿Se puede dibujar este tablero?** La misma regla que `rompe` en el montaje,
 * preguntada cuando llega la respuesta del diseñador y no tres pasos después.
 * C-562.
 *
 * reel-19 y reel-21 dieron 18 vueltas el 18-10 porque «Cover sin `sujeto`» se
 * descubría al montar, cuando ya no había a quién preguntarle. La regla vive en
 * `formas.mjs` (`revisarTablero`, `sinSujeto`); esto sólo la expone a Python.
 *
 *   echo '{"cara":true,"tableros":[{"etapa_orden":1,"kind":"Cover","props":{}}]}' \
 *     | node scripts/dibujable.mjs
 *   → {"1":["«Cover» va a pleno sin `sujeto`…"]}
 */
import fs from "fs";
import { DEJAN_SITIO, canonico, revisarTablero, sinSujeto } from "./formas.mjs";
import { bloquesDePanel } from "./reels/tableros.mjs";

// El tope de un bloque de panel, leido de donde lo declara el componente
// (`src/brand/copy.ts`), no copiado aqui (C-572).
const TOPE_PANEL = Number((fs.readFileSync("src/brand/copy.ts", "utf8")
  .match(/panel:\s*(\d+)/) || [])[1] || 24);
const panelLargo = (props) => (props?.cubre === "panel" ? bloquesDePanel(props) : [])
  .filter((b) => String(b?.texto ?? "").length > TOPE_PANEL)
  .map((b) => `panel: «${b.texto}» tiene ${String(b.texto).length} caracteres y el`
    + ` maximo es ${TOPE_PANEL}; partelo en otro bloque o acortalo`);

// `--con-su-cara`: las formas que dibujan a pleno dejandole la columna. Va en
// el pedido para que el diseñador no elija una que el montaje va a rechazar.
if (process.argv.includes("--con-su-cara")) {
  console.log(JSON.stringify([...DEJAN_SITIO].sort()));
  process.exit(0);
}
const { cara, tableros } = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
const faltas = {};
for (const t of tableros || []) {
  if (!t || t.retirar || !t.kind) continue;
  const kind = canonico(t.kind);
  const props = t.props || {};
  const suyas = [...revisarTablero(kind, props), ...(cara ? sinSujeto(kind, props) : []),
                 ...panelLargo(props)];
  if (suyas.length) faltas[t.etapa_orden ?? t.etapa ?? t.beat] = suyas;
}
console.log(JSON.stringify(faltas));
