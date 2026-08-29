/**
 * Convierte un proyecto de CapCut en el EDL del pipeline.
 *
 * Hallazgo que ahorra el mayor compromiso del proyecto: **el draft de CapCut ES
 * un EDL**. `draft_content.json` guarda, por cada corte, el fichero de origen,
 * el punto de entrada y la duración, todo en microsegundos. Así el humano corta
 * donde corta bien —eligiendo la mejor toma a ojo y oído— y el montaje sigue
 * siendo reproducible en código, que era lo que parecía irreconciliable.
 *
 * Uso:
 *   node scripts/capcut-edl.mjs                 # lista los proyectos
 *   node scripts/capcut-edl.mjs 0416            # vuelca el EDL por stdout
 *   node scripts/capcut-edl.mjs 0416 ads/x/edl.json
 */
import fs from "fs";
import path from "path";

const DRAFTS = path.join(
  process.env.LOCALAPPDATA ?? "",
  "CapCut",
  "User Data",
  "Projects",
  "com.lveditor.draft",
);

/** CapCut trabaja en microsegundos; el pipeline, en frames. */
const usToFrames = (us, fps) => Math.round((us / 1_000_000) * fps);

const listDrafts = () =>
  fs
    .readdirSync(DRAFTS, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .filter((e) => fs.existsSync(path.join(DRAFTS, e.name, "draft_content.json")))
    .map((e) => {
      const file = path.join(DRAFTS, e.name, "draft_content.json");
      return { name: e.name, modified: fs.statSync(file).mtime };
    })
    .sort((a, b) => b.modified - a.modified);

export const readCapCutEdl = (draftName) => {
  const file = path.join(DRAFTS, draftName, "draft_content.json");
  if (!fs.existsSync(file)) {
    throw new Error(`No existe el proyecto "${draftName}" en ${DRAFTS}`);
  }
  const draft = JSON.parse(fs.readFileSync(file, "utf8"));

  /**
   * El fps del proyecto de CapCut manda: convertir con otro desplazaría cada
   * corte y el desfase se acumularía a lo largo del montaje.
   */
  const fps = draft.fps ?? 30;

  const media = new Map(
    (draft.materials?.videos ?? []).map((v) => [v.id, v.path]),
  );

  const videoTrack = (draft.tracks ?? []).find((t) => t.type === "video");
  if (!videoTrack) {
    throw new Error(`El proyecto "${draftName}" no tiene pista de vídeo.`);
  }

  const cuts = videoTrack.segments
    .map((s) => ({
      media: media.get(s.material_id) ?? null,
      sourceStart: usToFrames(s.source_timerange.start, fps),
      duration: usToFrames(s.source_timerange.duration, fps),
      targetStart: usToFrames(s.target_timerange.start, fps),
      speed: s.speed ?? 1,
    }))
    .sort((a, b) => a.targetStart - b.targetStart);

  const missing = cuts.filter((c) => c.media === null).length;
  const totalFrames = cuts.reduce((n, c) => Math.max(n, c.targetStart + c.duration), 0);

  return { draft: draftName, fps, totalFrames, cuts, missing };
};

const [, , draftName, outPath] = process.argv;

if (!draftName) {
  const drafts = listDrafts();
  console.log(`${drafts.length} proyectos en CapCut. Los 15 más recientes:\n`);
  for (const d of drafts.slice(0, 15)) {
    console.log(`  ${d.name.padEnd(28)} ${d.modified.toISOString().slice(0, 10)}`);
  }
  console.log("\nUso: node scripts/capcut-edl.mjs <proyecto> [salida.json]");
  process.exit(0);
}

const edl = readCapCutEdl(draftName);

if (edl.missing > 0) {
  console.error(
    `AVISO: ${edl.missing} cortes sin fichero de origen resoluble. ` +
      `Suele significar que el medio se movió o vive en la nube de CapCut.`,
  );
}

const json = JSON.stringify(edl, null, 2);
if (outPath) {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, json);
  console.error(
    `${edl.cuts.length} cortes · ${(edl.totalFrames / edl.fps).toFixed(1)}s · ${edl.fps} fps → ${outPath}`,
  );
} else {
  console.log(json);
}
