/**
 * RUTA ANTIGUA — NO USAR. Encadena `assemble.py`, que recorta por presupuesto.
 *
 * Pasa `--budget 90` y eso hace que `compress_body` descarte enunciados enteros
 * para que quepan. La politica vigente es la contraria: **nada se recorta por
 * duracion durante el montaje**, el ajuste se decide al final sobre la pieza.
 *
 * La cadena viva esta en `montar.sh`.
 */
/**
 * Monta un reel de punta a punta: EDL, escenas, encuadres, gancho renderizado.
 *
 * Encadena lo que hasta ahora se corria a mano, en el orden en que cada paso
 * depende del anterior:
 *
 *   assemble.py    -> que se dice y en que orden (SELL y EDUCATE)
 *   scene-plan.mjs -> donde cambia el plano dentro del gancho
 *   punch-ins.py   -> que encuadre lleva cada escena, con la cabeza como eje
 *   render-hook.mjs-> el gancho en video, con acercamiento sobre el remate
 *
 * No decide el arranque: se le pasa. Localizarlo es `find-start.py`, y cuando
 * ese avisa de cobertura baja la decision es humana — montar sobre un arranque
 * dudoso cuesta mas que preguntarlo.
 *
 * Uso:
 *   node scripts/build-reel.mjs --reel 3 --take 20260825_224414 --desde 28.57
 */
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i === -1 ? d : process.argv[i + 1];
};

const reel = arg("reel");
const take = arg("take");
const desde = arg("desde", "0");
const budget = arg("budget", "90");
const hook = arg("hook", "7");
const every = arg("every", "3");
const zoom = arg("zoom") !== "no";

if (!reel || !take) {
  console.error("Uso: node scripts/build-reel.mjs --reel <n> --take <fichero> --desde <s>");
  process.exit(1);
}

const SRC = "G:/My Drive/Creación de videos/Brutos/Picture";
const video = path.join(SRC, `${take}.mp4`);
const slug = `reel-${String(reel).padStart(2, "0")}`;
const adsDir = `ads/${slug}`;
const scenesDir = `work/scenes/${slug}`;

const paso = (titulo, cmd, args) => {
  console.error(`\n── ${titulo} ──`);
  const r = execFileSync(cmd, args, {
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  return r;
};

try {
  const salida = paso("montaje", "python", [
    "scripts/assemble.py",
    "--transcript", `work/transcripts/${take}.json`,
    "--silence", `work/cuts/${take}.json`,
    "--reel", reel, "--budget", budget, "--desde", desde,
    "--out", adsDir,
  ]);
  void salida;
} catch (e) {
  // assemble.py escribe su informe por stderr; no es fallo.
  process.stderr.write(e.stderr ?? "");
}

paso("plan de escenas", "node", [
  "scripts/scene-plan.mjs", "--source", video,
  "--edl", `${adsDir}/edl-sell.json`,
  "--hook", hook, "--every", every, "--out", scenesDir,
]);

paso("encuadres", "python", [
  "scripts/punch-ins.py", "--source", video, "--plan", `${scenesDir}/plan.json`,
]);

if (zoom) {
  /**
   * Acercamiento sobre el ultimo tercio de la escena final del gancho: es donde
   * cae el remate de la frase. Lineal, que es lo que admite el sistema.
   */
  const plan = JSON.parse(fs.readFileSync(`${scenesDir}/plan.json`, "utf8"));
  const ultima = plan.escenas[plan.escenas.length - 1];
  if (ultima && ultima.duracion > 1.4) {
    ultima.zoom = {
      hasta: 0.76,
      desde_s: Number((ultima.duracion * 0.35).toFixed(2)),
      duracion_s: Number((ultima.duracion * 0.6).toFixed(2)),
    };
    fs.writeFileSync(`${scenesDir}/plan.json`, JSON.stringify(plan, null, 2));
    // Recalcular: el destino del zoom se ancla a la cabeza, no al centro.
    paso("destino del acercamiento", "python", [
      "scripts/punch-ins.py", "--source", video, "--plan", `${scenesDir}/plan.json`,
    ]);
  }
}

paso("render del gancho", "node", [
  "scripts/render-hook.mjs", "--source", video,
  "--plan", `${scenesDir}/plan.json`,
  "--out", `public/hook-${slug}.mp4`,
]);

const edl = JSON.parse(fs.readFileSync(`${adsDir}/edl-sell.json`, "utf8"));
console.error(
  `\n✓ Reel ${reel}\n` +
  `  SELL ${edl.duracion_montada_s}s · gancho public/hook-${slug}.mp4\n` +
  `  zonas: ${JSON.stringify(edl.zonas)}`,
);
