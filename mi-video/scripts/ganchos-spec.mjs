/**
 * Emite `src/ganchos.json` desde los planes de escena.
 *
 * Por que generado y no escrito a mano: la duracion del gancho y el instante en
 * que cede el rotulo **son consecuencias del montaje**, no decisiones sueltas.
 * Estaban a mano en `Ganchos.tsx` y al cambiar los cortes quedaron desfasadas al
 * instante — el rotulo cedia en un corte que ya no estaba ahi.
 *
 * Lo que si es decision humana —el texto del rotulo— se queda escrito en
 * `LINEAS`. Lo derivable se deriva.
 *
 *   node scripts/ganchos-spec.mjs
 */
import fs from "fs";
import { idDe } from "./reels/material.mjs";

const FPS = 30;

/** Ancla del gancho: la idea en las menos palabras posibles, no la transcripcion. */
const LINEAS = {
  "reel-01": ["No es", "mala suerte"],
  "reel-02": ["Trabaja más.", "Le queda menos"],
  "reel-03": ["Su contador", "no es estratega"],
  "reel-04": ["No es por", "ser inmigrante"],
  "reel-05": ["Empieza el año", "con lastre"],
  "reel-06": ["Nadie le mandó", "una carta"],
};

const TOMA = {
  "reel-01": "20260825_135637", "reel-02": "20260825_144010",
  "reel-03": "20260825_224414", "reel-04": "20260825_225808",
  "reel-05": "20260825_151758", "reel-06": "20260825_231706",
};

/** Suelo de lectura de un rotulo de dos lineas, en segundos. */
const LEIDO = 2.4;
/**
 * Margen despues de decir la frase antes de que el rotulo pueda irse. Sin el,
 * el rotulo desaparece sobre la palabra y el espectador no llega a juntar las
 * dos cosas.
 */
const REMATE = 0.5;

const sinTildes = (t) =>
  t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const palabras = (t) => sinTildes(t).match(/[a-z]+/g) ?? [];

/**
 * Segundo de la linea de tiempo en que se termina de decir la frase del rotulo.
 *
 * Es el dato que faltaba. La regla era «cede en el primer cambio de plano», y
 * medido sobre los seis **fallaba en los seis**: el rotulo se iba antes de que
 * Jaime dijera la frase. En el reel 1 la decia en el 6,5 y el rotulo se retiraba
 * en el 3,0 — «tiene un no es mala suerte excepto en el momento en que lo digo».
 *
 * Un rotulo que no esta puesto cuando suena su frase no refuerza nada: compite
 * con lo que venga despues.
 */
function seDiceEn(reel, esc, cuando = "fin") {
  const words = JSON.parse(
    fs.readFileSync(`work/transcripts/${TOMA[reel]}.json`, "utf8"),
  ).segmentos;
  const clave = new Set(
    LINEAS[reel].flatMap(palabras).filter((w) => w.length > 3),
  );
  let t = 0, ultimo = null;
  for (const e of esc) {
    for (const w of words) {
      if (w.start >= e.origen_desde && w.start < e.origen_hasta) {
        if (palabras(w.text).some((p) => clave.has(p))) {
          const at = t + w.start - e.origen_desde;
          if (cuando === "inicio") {
            if (ultimo === null) ultimo = at;
          } else {
            ultimo = at;
          }
        }
      }
    }
    t += e.duracion;
  }
  return ultimo;
}

/**
 * Primer cambio de encuadre que llega con el rotulo **leido y ya dicho**.
 *
 * Si no hay ninguno, el rotulo se queda hasta el final: antes eso que retirarlo
 * justo cuando hace falta.
 */
function cedeEn(esc, dicho) {
  const cortes = [];
  let t = 0;
  for (const e of esc.slice(0, -1)) {
    t += e.duracion;
    cortes.push(t);
  }
  const suelo = Math.max(LEIDO, (dicho ?? 0) + REMATE);
  return cortes.find((c) => c >= suelo) ?? null;
}

const spec = Object.entries(LINEAS).map(([reel, lineas]) => {
  const plan = JSON.parse(fs.readFileSync(`work/scenes/${reel}/plan.json`, "utf8"));
  const esc = plan.escenas;
  const duracion = esc.reduce((s, e) => s + e.duracion, 0);
  const dicho = seDiceEn(reel, esc);
  // El rotulo ENTRA cuando empieza a decirse la frase, no antes: anunciarla
  // gasta el remate. Ver el comentario de `BigTitle`.
  const empieza = seDiceEn(reel, esc, "inicio");
  const corte = cedeEn(esc, dicho);
  return {
    id: idDe(reel).replace("Reel-", "Gancho-"),
    video: `hook-${reel}.mp4`,
    duracion: Number(duracion.toFixed(3)),
    dicho: dicho === null ? null : Number(dicho.toFixed(2)),
    corte: corte === null ? null : Number(corte.toFixed(3)),
    entra: Math.max(0, Math.round((empieza ?? 0) * FPS)),
    escenas: esc.length,
    lineas,
  };
});

fs.writeFileSync("src/ganchos.json", JSON.stringify(spec, null, 2) + "\n");
for (const g of spec) {
  console.log(
    `${g.id}  ${g.duracion.toFixed(2)}s  entra en ${(g.entra / FPS).toFixed(1)}s  ` +
    `${JSON.stringify(g.lineas)}`,
  );
}
