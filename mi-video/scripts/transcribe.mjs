/**
 * Transcribe una toma completa con timestamps por palabra.
 *
 * Es el paso posterior a `identify-takes.mjs`: aquella identifica a qué reel
 * pertenece cada toma con 90 s; esta procesa entera la toma elegida y produce
 * el artefacto del que come todo lo demás — el anclaje de los tableros, el
 * corte en frontera de frase y los subtítulos.
 *
 * Uso:
 *   node scripts/transcribe.mjs <ruta-al-mp4> <slug>
 *   node scripts/transcribe.mjs "G:/.../20260825_224414.mp4" reel-04
 */
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";
import { toCaptions, transcribe } from "@remotion/install-whisper-cpp";
import { idiomaDePieza } from "./idioma.mjs";

const WHISPER_DIR = path.join(process.cwd(), "whisper.cpp");
const WHISPER_VERSION = "1.5.5";
/** Multilingüe. Los modelos `.en` NO entienden español. */
const MODEL = process.env.WHISPER_MODEL ?? "medium";

const [, , source, slug] = process.argv;

if (!source || !slug) {
  console.error("Uso: node scripts/transcribe.mjs <ruta-al-mp4> <slug>");
  process.exit(1);
}
if (!fs.existsSync(source)) {
  console.error(`No existe el fichero: ${source}`);
  process.exit(1);
}

const outDir = path.join(process.cwd(), "ads", slug);
fs.mkdirSync(outDir, { recursive: true });
const wav = path.join(outDir, "audio.wav");

/**
 * Whisper.cpp solo acepta WAV mono a 16 kHz. Convertir antes evita un fallo
 * opaco a mitad de proceso sobre un fichero de varios gigas.
 */
if (!fs.existsSync(wav)) {
  console.error("Extrayendo audio a 16 kHz mono…");
  execFileSync(
    "ffmpeg",
    ["-v", "error", "-y", "-i", source, "-vn", "-ac", "1", "-ar", "16000",
     "-c:a", "pcm_s16le", wav],
    { stdio: ["ignore", "inherit", "inherit"] },
  );
}

console.error("Transcribiendo (velocidad ~tiempo real en CPU)…");
const whisperCppOutput = await transcribe({
  model: MODEL,
  whisperPath: WHISPER_DIR,
  whisperCppVersion: WHISPER_VERSION,
  inputPath: wav,
  language: idiomaDePieza(slug).codigo,
  /** Imprescindible: sin esto no hay anclaje de tableros ni corte por frase. */
  tokenLevelTimestamps: true,
});

const { captions } = toCaptions({ whisperCppOutput });

const outFile = path.join(outDir, "transcript.json");
fs.writeFileSync(outFile, JSON.stringify(captions, null, 2));

const seconds = captions.length ? captions[captions.length - 1].endMs / 1000 : 0;
console.error(
  `${captions.length} segmentos · ${(seconds / 60).toFixed(1)} min → ${outFile}`,
);
