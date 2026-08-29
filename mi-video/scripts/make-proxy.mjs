/**
 * Corta el bruto según el EDL y produce un proxy 1080×1920 en `public/`.
 *
 * Por qué proxy y no el bruto
 * ---------------------------
 * El original es 4K HEVC de varios gigas. Componer tableros encima obliga a
 * decodificarlo frame a frame, y la salida es 1080×1920 de todas formas: se
 * pagaría el coste de 4K para tirar tres cuartas partes de los píxeles. Además
 * Remotion sirve desde `public/`, así que el material tiene que estar ahí.
 *
 * El recorte a vertical es **centrado por defecto**, que es lo correcto cuando
 * el sujeto está compuesto al centro. Si en alguna toma Jaime no está centrado,
 * hay que pasar `--crop-x`.
 *
 * Uso:
 *   node scripts/make-proxy.mjs --source "G:/.../X.mp4" --edl ads/reel-03/edl.json \\
 *        --out reel-03.mp4 [--crop-x 0.5]
 */
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i === -1 ? d : process.argv[i + 1];
};

const source = arg("source");
const edlPath = arg("edl");
const outName = arg("out");
const cropX = parseFloat(arg("crop-x", "0.5"));

if (!source || !edlPath || !outName) {
  console.error(
    "Uso: node scripts/make-proxy.mjs --source <mp4> --edl <edl.json> --out <nombre.mp4>",
  );
  process.exit(1);
}

const edl = JSON.parse(fs.readFileSync(edlPath, "utf8"));
const cuts = edl.segmentos ?? [];
if (!cuts.length) {
  console.error("El EDL no tiene segmentos.");
  process.exit(1);
}

const publicDir = path.join(process.cwd(), "public");
fs.mkdirSync(publicDir, { recursive: true });
const outPath = path.join(publicDir, outName);

/**
 * Se construye un solo grafo de filtros con un `trim` por corte y un `concat`
 * final, en vez de exportar N ficheros y unirlos: así el vídeo se decodifica una
 * única vez. Con 98 cortes la diferencia es de minutos a horas.
 */
const parts = [];
const labels = [];
cuts.forEach(([start, end], i) => {
  parts.push(
    `[0:v]trim=start=${start}:end=${end},setpts=PTS-STARTPTS[v${i}]`,
    `[0:a]atrim=start=${start}:end=${end},asetpts=PTS-STARTPTS[a${i}]`,
  );
  labels.push(`[v${i}][a${i}]`);
});

/**
 * Recorte a 9:16 y escalado. `crop` va ANTES de `scale` para no gastar el
 * escalado en píxeles que se van a tirar.
 */
const vertical =
  `crop=w='min(iw,ih*9/16)':h=ih:x='(iw-min(iw,ih*9/16))*${cropX}':y=0,` +
  `scale=1080:1920:flags=lanczos`;

const filter =
  parts.join(";") +
  `;${labels.join("")}concat=n=${cuts.length}:v=1:a=1[vc][ac]` +
  `;[vc]${vertical}[vout]`;

const filterFile = path.join(process.cwd(), "work", "filter.txt");
fs.mkdirSync(path.dirname(filterFile), { recursive: true });
fs.writeFileSync(filterFile, filter);

const total = cuts.reduce((n, [a, b]) => n + (b - a), 0);
console.error(
  `${cuts.length} cortes · ${(total / 60).toFixed(1)} min → ${outPath}\n` +
  `Recorte vertical centrado en ${cropX}. Esto tarda: decodifica 4K entero.`,
);

execFileSync(
  "ffmpeg",
  ["-v", "warning", "-stats", "-y", "-i", source,
   /** El grafo va en fichero: con ~100 cortes supera el límite de línea de Windows. */
   "-filter_complex_script", filterFile,
   "-map", "[vout]", "-map", "[ac]",
   "-c:v", "libx264", "-preset", "medium", "-crf", "20",
   "-c:a", "aac", "-b:a", "160k",
   "-r", "30", outPath],
  { stdio: ["ignore", "inherit", "inherit"] },
);

console.error(`\nListo: public/${outName}`);
