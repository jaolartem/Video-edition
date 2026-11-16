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
import { panelLargo, pieLargo } from "./reels/tableros.mjs";
import { lienzoDe } from "./lienzo.mjs";

// `--con-su-cara`: las formas que dibujan a pleno dejandole la columna. Va en
// el pedido para que el diseñador no elija una que el montaje va a rechazar.
if (process.argv.includes("--con-su-cara")) {
  console.log(JSON.stringify([...DEJAN_SITIO].sort()));
  process.exit(0);
}
const { cara, tableros, formato } = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
// **Y sólo las formas compuestas para su cuadro** (C-716): en el horizontal,
// `causal` y `fusion` salían en negro y pegadas a la izquierda.
const formas = lienzoDe(formato ?? undefined).tablero?.formas;
const enSuCuadro = (kind) => !formas || formas.includes(kind) ? [] :
  [`«${kind}» no está compuesta para el cuadro ${formato}: aquí se dibujan ${formas.join(", ")}`];
const faltas = {};
for (const t of tableros || []) {
  if (!t || t.retirar || !t.kind) continue;
  const kind = canonico(t.kind);
  const props = t.props || {};
  const suyas = [...enSuCuadro(kind),
                 ...revisarTablero(kind, props), ...(cara ? sinSujeto(kind, props) : []),
                 ...panelLargo(props), ...pieLargo(t)];
  if (suyas.length) faltas[t.etapa_orden ?? t.etapa ?? t.beat] = suyas;
}
console.log(JSON.stringify(faltas));
