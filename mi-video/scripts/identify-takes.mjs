/**
 * Identifica a qué reel pertenece cada toma grabada.
 *
 * No hace falta transcribir las tres horas de material: los hooks de los seis
 * libretos son inconfundibles, así que con los primeros 90 s de cada toma basta
 * para emparejarla. Eso baja el trabajo de 192 minutos de audio a 18.
 *
 * El emparejamiento va por marcas léxicas distintivas y no por parecido de
 * cadena: el reconocimiento de voz se equivoca con nombres propios y cifras
 * —"Brampton", "Muskoka", "53.53%"— pero acierta las palabras corrientes que
 * rodean cada tema, y son esas las que distinguen un libreto de otro.
 *
 * Uso:
 *   node scripts/identify-takes.mjs
 */
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const WHISPER = path.join(process.cwd(), "whisper.cpp", "whisper-cli.exe");
const MODEL = path.join(process.cwd(), "whisper.cpp", "ggml-medium.bin");
const AUDIO = path.join(process.cwd(), "work", "audio");

/**
 * Marcas por reel. Se eligen palabras que el ASR transcribe bien y que solo
 * aparecen en ese libreto. El peso separa las que son casi firma (`electricista`)
 * de las meramente frecuentes (`contador`, que sale en varios).
 */
const REELS = [
  {
    id: 1,
    name: "Loss Aversion",
    marks: [
      ["funcionando", 3], ["vendiendo", 3], ["mala suerte", 3],
      ["wealthsimple", 4], ["primo", 3], ["etf", 3], ["queda menos", 3],
    ],
  },
  {
    id: 2,
    name: "Prestige + Temporal Discounting",
    marks: [
      ["electricista", 5], ["brampton", 5], ["muskoka", 5], ["yate", 4],
      ["mansión", 3], ["sábados completos", 3], ["quinta generación", 4],
    ],
  },
  {
    id: 3,
    name: "Polarizing Thesis",
    marks: [
      ["se queja", 4], ["estratega", 4], ["incapacidad", 4], ["dentista", 4],
      ["muela", 4], ["salario y dividendos", 3], ["income tax act", 3],
    ],
  },
  {
    id: 4,
    name: "Belief Demolition",
    marks: [
      ["no le presta", 5], ["inmigrante", 4], ["palancas", 4], ["divorcio", 4],
      ["cónyuge", 3], ["nunca se presentó", 4], ["registros limpios", 3],
    ],
  },
  {
    id: 5,
    name: "Causal Reveal",
    marks: [
      ["trimestre", 5], ["realtor", 4], ["tres casas", 4], ["umbral", 4],
      ["plata quieta", 4], ["mejor año", 3], ["lastre", 3],
    ],
  },
  {
    id: 6,
    name: "Loss Aversion + Temporal Discounting",
    marks: [
      ["mandó una carta", 5], ["pérdida silenciosa", 5], ["no le alcanza", 4],
      ["momento dramático", 4], ["brecha", 3], ["explotado", 3],
    ],
  },
];

/** Sin acentos ni puntuación: el ASR es irregular con ambos. */
const normalize = (s) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9ñ\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const transcribe = (wav) => {
  const out = wav.replace(/\.wav$/, "");
  const txt = `${out}.txt`;
  if (!fs.existsSync(txt)) {
    execFileSync(
      WHISPER,
      ["-m", MODEL, "-l", "es", "-f", wav, "-otxt", "-of", out, "-nt"],
      { stdio: ["ignore", "ignore", "ignore"] },
    );
  }
  return fs.readFileSync(txt, "utf8");
};

const score = (text) => {
  const hay = normalize(text);
  return REELS.map((reel) => {
    const hits = reel.marks.filter(([m]) => hay.includes(normalize(m)));
    return {
      reel,
      points: hits.reduce((n, [, w]) => n + w, 0),
      hits: hits.map(([m]) => m),
    };
  }).sort((a, b) => b.points - a.points);
};

if (!fs.existsSync(MODEL)) {
  console.error(`Falta el modelo: ${MODEL}\nEjecuta antes: node scripts/setup-whisper.mjs`);
  process.exit(1);
}

const wavs = fs.readdirSync(AUDIO).filter((f) => f.endsWith(".wav")).sort();
const results = [];

for (const w of wavs) {
  const name = w.replace(/\.wav$/, "");
  process.stderr.write(`transcribiendo ${name}… `);
  const text = transcribe(path.join(AUDIO, w));
  const ranked = score(text);
  const best = ranked[0];
  const runnerUp = ranked[1];
  /** Sin ventaja clara sobre el segundo, no se afirma nada. */
  const confident = best.points >= 6 && best.points >= runnerUp.points * 2;
  results.push({ name, text: text.trim(), best, confident });
  process.stderr.write(
    confident ? `→ Reel ${best.reel.id}\n` : `→ SIN IDENTIFICAR\n`,
  );
}

console.log(JSON.stringify(results, null, 2));
