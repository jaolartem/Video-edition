/**
 * Bloque de verificación por ad, como artefacto de build.
 *
 * El playbook lo exige y `CLAUDE.md` lo dice literal: *«debe ser un artefacto de
 * build, no un paso manual que se olvide»*. Un paso manual que se olvida en un
 * lote de 16–50 anuncios se olvida cincuenta veces.
 *
 * No inventa nada: lee lo que hay en el EDL, en el spec y en los libretos, y
 * marca lo que falta. **Un dato ausente sale como ausente**, no como aprobado.
 *
 *   node scripts/verificacion.mjs
 */
import fs from "fs";
import { rutas } from "./rutas.mjs";
import { slugDe } from "./reels/material.mjs";

const LIBRETOS = "../docs/libretos.md";
const FPS = 30;

/**
 * **Indicaciones de duración, no topes.** Jaime: *«puede durar 120 s máximo… el
 * reel 90 s máximo… o dependiendo, porque la duración varía dependiendo de lo
 * que se quiera»*, y *«respeta el guion; si hay necesidad de recortar lo
 * definimos al final»*.
 *
 * Por eso esto **informa y no corta**. Estas piezas son ADS: 120 s. El de 90 s
 * es el límite del formato reel, y aplica cuando la pieza se publique como tal.
 */
const INDICACION = { ad: 120, reel: 90, dulce: 60 };
const LIMITE = (r) => {
  const d = r.duracion;
  if (d > INDICACION.ad) {
    return `🛑 **${(d - INDICACION.ad).toFixed(1)} s sobre los ${INDICACION.ad} s de un ad.** El ajuste se decide al final, sobre el montaje.`;
  }
  if (d > INDICACION.reel) {
    return `⚠️ cabe como ad (${INDICACION.ad} s) pero **no como reel** (${INDICACION.reel} s).`;
  }
  if (d > INDICACION.dulce) {
    return `· por encima del punto dulce de 30–${INDICACION.dulce} s, y eso está bien si cada segundo se gana su sitio.`;
  }
  return "";
};

const libro = fs.readFileSync(LIBRETOS, "utf8");
const spec = JSON.parse(fs.readFileSync("src/reels.json", "utf8"));

/**
 * Cifras que aparecen en un texto, normalizadas para poder compararlas.
 *
 * Tres trampas, las tres encontradas en el propio material:
 *
 * - **«millones» empieza por «mil».** La primera version convertia
 *   «$300,000 millones» en «300000000 000» y luego reportaba que faltaba una
 *   cifra inventada. El `\b(?!lones)` lo corta.
 * - **Se dicen en palabras.** El reel 6 dice «trescientos mil», no «300.000».
 * - **Se redondean al hablar.** El libreto dice 14.300 y en la toma suena
 *   «14 mil». Se acepta la aproximacion a mil.
 *
 * Un bloque de verificacion que avisa de lo que no pasa deja de leerse, y
 * entonces tampoco avisa de lo que si.
 */
const PALABRAS = {
  cien: 100, doscientos: 200, trescientos: 300, cuatrocientos: 400,
  quinientos: 500, seiscientos: 600, setecientos: 700, ochocientos: 800,
  novecientos: 900, veinte: 20, treinta: 30, cuarenta: 40, cincuenta: 50,
  sesenta: 60, setenta: 70, ochenta: 80, noventa: 90,
};

const cifras = (t) => {
  const out = new Set();
  let norm = t.toLowerCase();
  // «doscientos cincuenta mil» -> 250000
  norm = norm.replace(
    /\b(cien|doscientos|trescientos|cuatrocientos|quinientos|seiscientos|setecientos|ochocientos|novecientos)(?:\s+(veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa))?\s+mil\b(?!lones)/g,
    (_, c, d) => `${(PALABRAS[c] + (d ? PALABRAS[d] : 0)) * 1000} `,
  );
  norm = norm.replace(/(\d+)\s*mil\b(?!lones)/g, (_, n) => `${n}000 ${n}`);
  for (const m of norm.matchAll(/\$?\s?(\d[\d.,]*)/g)) {
    const n = m[1].replace(/[.,]/g, "");
    if (n.length >= 2) out.add(n);
  }
  // Redondeo al hablar: si se dijo 14000, vale por el 14300 del libreto.
  for (const n of [...out]) {
    if (n.length >= 4 && n.endsWith("000")) out.add(String(Number(n)));
  }
  return out;
};

/** ¿La cifra del libreto está dicha, aceptando redondeo a mil? */
const estaDicha = (pedida, hay) => {
  if (hay.has(pedida)) return true;
  const v = Number(pedida);
  if (!Number.isFinite(v) || v < 1000) return false;
  const redondeada = String(Math.round(v / 1000) * 1000);
  return hay.has(redondeada);
};

const bloqueLibreto = (n) => {
  const partes = libro.split(/\n## /);
  return partes.find((p) => p.startsWith(`Reel ${n} `)) ?? "";
};

for (const r of spec) {
  const slug = slugDe(r.id);
  const n = Number(slug.slice(-2));
  const edl = JSON.parse(fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"));
  const dicho = edl.detalle.map((u) => u.texto).join(" ");
  const guion = bloqueLibreto(n);

  const pedidas = [...cifras(guion)].filter((x) => !["20", "21"].includes(x));
  /**
   * Una cifra cuenta como presente si **se dice o se ve**.
   *
   * Antes sólo se miraba lo hablado y por eso salían como ausentes cifras que
   * están en pantalla con su fuente — el 32% del R3, los $14.300 del R5, los
   * $250.000 del R6. Justo las de los beats que van con tablero **porque no
   * tienen toma**: el sitio donde por definición no hay voz que las diga.
   *
   * Marcarlas como agujero convertía el informe en ruido, y un informe que
   * grita de más se deja de leer — que es como se cuela el aviso que sí valía.
   */
  const enPantalla = [...r.boards, ...r.tarjetas]
    .map((b) => JSON.stringify(b.props ?? {}))
    .join(" ");
  const hay = cifras(`${dicho} ${enPantalla}`);
  const soloDicho = cifras(dicho);
  const faltan = pedidas.filter((x) => !estaDicha(x, hay));

  // Toda cifra que se muestra en un tablero lleva fuente: el tipo lo exige, así
  // que aquí sólo hay que listarlas para que se puedan comprobar.
  const fuentes = r.boards
    .map((b) => b.props?.difference)
    .filter(Boolean)
    .map((d) => `- \`${d.figure}\` — ${d.source}`);

  const cta = r.cta
    ? [
        `- Fecha declarada: **${r.cta.fecha}**`,
        `- Precio en pantalla: ${r.cta.precio ? `**${r.cta.precio}**` : "**no se declara** (sube pronto)"}`,
        `- Acción: **${r.cta.accion ?? "Link abajo"}**`,
        `- Aparece en el segundo ${r.cta.at.toFixed(1)} de ${r.duracion.toFixed(1)}`,
      ]
    : ["- Sin CTA."];

  const md = `# Verificación · ${r.id}

Generado por \`scripts/verificacion.mjs\`. **No es una aprobación**: es la lista
de lo que hay que comprobar antes de publicar.

## Pieza

- Duración: **${r.duracion.toFixed(1)} s** ${LIMITE(r)}
- Subtítulos: ${r.captions.length} ${r.captions.length ? "" : "⚠️ ninguno"}
- Rótulo entra en el segundo ${(r.entra / FPS).toFixed(1)}
- Tableros: ${r.boards.length} · Paneles: ${r.paneles.length}

## CTA

${cta.join("\n")}

Un SELL lleva **exactamente uno**. ${r.cta ? "✅ uno" : "⚠️ ninguno"}

## Cifras del libreto

${pedidas.length ? pedidas.map((x) => `- \`${x}\` ${soloDicho.has(x) ? "✅ se dice" : hay.has(x) ? "✅ en tablero" : "⚠️ **ni se dice ni se ve**"}`).join("\n") : "- El libreto no declara cifras."}

${faltan.length ? `**Faltan ${faltan.length}.** Una cifra que el libreto declara y la pieza ni dice ni enseña es un agujero en el argumento, no una omisión de estilo.` : ""}

## Fuentes en pantalla

${fuentes.length ? fuentes.join("\n") : "- Ningún tablero muestra cifras."}

## Pendiente de confirmar por quien conoce el hecho

- ¿Las cifras dichas coinciden con las del libreto? Una discrepancia entre guion
  y grabación **no dice cuál de los dos está mal**.
- ¿Hay permiso para todo lo que aparece en cuadro?
- ¿Sigue vigente el estado de la oferta (fecha, capacidad, cierre)?
`;

  const out = `${rutas.destino}/${r.id}.verification.md`;
  fs.mkdirSync(rutas.destino, { recursive: true });
  fs.writeFileSync(out, md);
  console.log(
    // **Se dice que CABE, no sólo dónde no cabe.** Ponía «(no cabe como reel)»
    // a secas y eso se lee como un defecto: yo mismo se lo reporté a Jaime
    // como problema en tres piezas y su respuesta fue *«son ads, están bien»*.
    // Lo eran, y el código ya lo sabía —el 🛑 sólo salta por encima de los
    // 120 s de un ad—; lo que fallaba era la frase. Un aviso que se lee como
    // alarma cuando no lo es enseña a ignorar los avisos.
    `${r.id}: ${r.duracion.toFixed(1)}s${r.duracion > INDICACION.ad ? " 🛑 pasa de ad" : r.duracion > INDICACION.reel ? " (ad sí, reel no)" : ""} · CTA ${r.cta ? "1" : "0"} · ` +
      `cifras ${pedidas.length - faltan.length}/${pedidas.length}` +
      `${faltan.length ? ` ⚠️ faltan ${faltan.join(", ")}` : ""}`,
  );
}
