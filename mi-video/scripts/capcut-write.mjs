/**
 * Genera un proyecto de CapCut listo para abrir, a partir de una lista de cortes.
 *
 * Cierra el círculo con `capcut-edl.mjs`: aquella lee el corte que hizo el
 * humano; esta escribe el corte que calculó la máquina. Jaime abre el proyecto,
 * revisa en la herramienta que ya conoce y renderiza.
 *
 * Por qué se CLONA una plantilla en vez de sintetizar el JSON
 * -----------------------------------------------------------
 * Un segmento tiene 50 campos y un material 65, con referencias cruzadas a
 * lienzos, velocidades, mapeos de canal y separación vocal — y cada segmento
 * lleva su propio juego, sin compartir. El formato no está documentado y cambia
 * entre versiones. Escribirlo de cero es frágil y un JSON malformado puede
 * dejar la lista de proyectos inservible.
 *
 * Clonando un draft que YA funciona se conserva todo el andamiaje real y solo
 * se reescribe lo que se entiende: identificadores, rutas y tiempos.
 *
 * Uso:
 *   node scripts/capcut-write.mjs --template 0416 --source "G:/.../X.mp4" \
 *        --cuts work/cuts/X.json --name "R-07 test" --out work/drafts
 *
 * Para que aparezca en CapCut hay que apuntar --out a la carpeta de proyectos.
 * No es el valor por defecto a propósito: escribir ahí modifica el estado de la
 * aplicación y eso lo autoriza el usuario, no el script.
 */
import { execFileSync } from "child_process";
import crypto from "crypto";
import fs from "fs";
import path from "path";

/**
 * CapCut puede tener varias raíces de proyectos a la vez. En esta máquina hay
 * dos: la de instalación y una en `F:/CapCut Drafts`, que es la que la
 * aplicación está usando de verdad. Se buscan las dos y se prefiere la que
 * contenga la plantilla pedida.
 */
const DRAFT_ROOTS = [
  "F:/CapCut Drafts",
  path.join(process.env.LOCALAPPDATA ?? "", "CapCut", "User Data", "Projects", "com.lveditor.draft"),
].filter((d) => fs.existsSync(d));

const findTemplate = (nombre) => {
  for (const root of DRAFT_ROOTS) {
    if (fs.existsSync(path.join(root, nombre, "draft_content.json"))) {
      return { dir: path.join(root, nombre), root };
    }
  }
  return null;
};

/**
 * Un draft es una CARPETA, no dos ficheros JSON. Además del contenido y el meta
 * hacen falta estos: sin ellos CapCut abre el proyecto a medias o no lo abre.
 * Se copian tal cual de la plantilla porque no dependen del montaje.
 */
const COPY_FILES = [
  "attachment_editing.json", "attachment_pc_common.json",
  "draft_agency_config.json", "draft_biz_config.json", "draft_settings",
  "draft_virtual_store.json", "key_value.json", "performance_opt_info.json",
  "draft.extra", "timeline_layout.json",
];
const COPY_DIRS = [
  "Resources", "adjust_mask", "common_attachment", "matting",
  "qr_upload", "smart_crop", "subdraft",
];

/** CapCut usa UUID en mayúsculas con este formato exacto. */
const uuid = () => crypto.randomUUID().toUpperCase();

const usToFrames = (us, fps) => Math.round((us / 1e6) * fps);
const sToUs = (s) => Math.round(s * 1e6);

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 ? fallback : process.argv[i + 1];
};

const template = arg("template");
const source = arg("source");
const cutsFile = arg("cuts");
const name = arg("name");
const outRoot = arg("out", path.join(process.cwd(), "work", "drafts"));
const copyDir = (from, to) => {
  if (!fs.existsSync(from)) return;
  fs.mkdirSync(to, { recursive: true });
  for (const e of fs.readdirSync(from, { withFileTypes: true })) {
    const a = path.join(from, e.name), b = path.join(to, e.name);
    if (e.isDirectory()) copyDir(a, b);
    else fs.copyFileSync(a, b);
  }
};

if (!template || !source || !cutsFile || !name) {
  console.error(
    "Faltan argumentos.\n" +
    "Uso: node scripts/capcut-write.mjs --template <proyecto> --source <mp4> " +
    "--cuts <cortes.json> --name <nombre> [--out <carpeta>]",
  );
  process.exit(1);
}

const found = findTemplate(template);
if (!found) {
  console.error(
    `La plantilla "${template}" no aparece en ninguna raíz:\n  ` +
      DRAFT_ROOTS.join("\n  "),
  );
  process.exit(1);
}
const tplDir = found.dir;
/**
 * Se avisa si la plantilla es de una versión vieja. Las diferencias de esquema
 * entre 6.x y 8.x son aditivas —no se quitó nada— así que una plantilla nueva
 * es segura y una vieja puede dejar fuera campos que la app actual espera.
 */
const tplVersion = JSON.parse(
  fs.readFileSync(path.join(tplDir, "draft_content.json"), "utf8"),
).last_modified_platform?.app_version;
if (tplVersion && parseInt(tplVersion, 10) < 8) {
  console.error(
    `AVISO: la plantilla "${template}" la guardó CapCut ${tplVersion}. ` +
    `Conviene una guardada por la versión actual.`,
  );
}
if (!fs.existsSync(source)) {
  console.error(`No existe el vídeo de origen: ${source}`);
  process.exit(1);
}

const draft = JSON.parse(fs.readFileSync(path.join(tplDir, "draft_content.json"), "utf8"));
const meta = JSON.parse(fs.readFileSync(path.join(tplDir, "draft_meta_info.json"), "utf8"));
const cuts = JSON.parse(fs.readFileSync(cutsFile, "utf8"));
const fps = draft.fps ?? 30;

/** Datos reales del vídeo: inventarlos descuadra la línea de tiempo. */
const probe = JSON.parse(execFileSync("ffprobe", [
  "-v", "error", "-select_streams", "v:0",
  "-show_entries", "stream=width,height:format=duration",
  "-of", "json", source,
], { encoding: "utf8" }));
const width = probe.streams[0].width;
const height = probe.streams[0].height;
const sourceDurationUs = Math.round(parseFloat(probe.format.duration) * 1e6);

const videoTrack = draft.tracks.find((t) => t.type === "video");
const protoSeg = videoTrack.segments[0];
const protoVid = draft.materials.videos.find((v) => v.id === protoSeg.material_id);

/**
 * Índice de los materiales auxiliares del segmento prototipo, por tipo. Cada
 * segmento nuevo necesita su propia copia de cada uno.
 */
const auxTypes = {};
for (const [kind, list] of Object.entries(draft.materials)) {
  if (!Array.isArray(list)) continue;
  for (const m of list) {
    if (m && typeof m === "object" && protoSeg.extra_material_refs.includes(m.id)) {
      auxTypes[kind] = m;
    }
  }
}

const materials = { ...draft.materials };
for (const kind of Object.keys(auxTypes)) materials[kind] = [];
materials.videos = [];

const segments = [];
let timelineUs = 0;

for (const [startS, endS] of cuts.segmentos) {
  const durUs = sToUs(endS - startS);
  if (durUs <= 0) continue;

  const vid = structuredClone(protoVid);
  vid.id = uuid();
  vid.path = source.replace(/\\/g, "/");
  vid.material_name = path.basename(source);
  vid.duration = sourceDurationUs;
  vid.width = width;
  vid.height = height;
  if ("local_material_id" in vid) vid.local_material_id = uuid();
  materials.videos.push(vid);

  const seg = structuredClone(protoSeg);
  seg.id = uuid();
  seg.material_id = vid.id;
  seg.source_timerange = { start: sToUs(startS), duration: durUs };
  seg.target_timerange = { start: timelineUs, duration: durUs };
  seg.render_index = segments.length;
  seg.extra_material_refs = [];

  for (const [kind, proto] of Object.entries(auxTypes)) {
    const aux = structuredClone(proto);
    aux.id = uuid();
    materials[kind].push(aux);
    seg.extra_material_refs.push(aux.id);
  }

  segments.push(seg);
  timelineUs += durUs;
}

draft.id = uuid();
draft.duration = timelineUs;
draft.materials = materials;
draft.tracks = [{ ...videoTrack, id: uuid(), segments }];

const outDir = path.join(outRoot, name);
fs.mkdirSync(outDir, { recursive: true });

meta.draft_id = uuid();
meta.draft_name = name;
meta.draft_fold_path = outDir.replace(/\\/g, "/");
meta.draft_root_path = outRoot.replace(/\\/g, "/");
meta.tm_duration = timelineUs;
/**
 * `draft_materials` es la lista de medios importados que muestra la interfaz.
 * Si sigue apuntando a los medios de la plantilla, CapCut enseña ficheros que
 * este proyecto no usa.
 */
if (Array.isArray(meta.draft_materials)) {
  for (const block of meta.draft_materials) {
    if (block.type === 0 && Array.isArray(block.value)) {
      const proto = block.value[0];
      block.value = proto
        ? [{ ...structuredClone(proto), id: uuid(),
             file_Path: source.replace(/\\/g, "/"),
             duration: sourceDurationUs, width, height }]
        : [];
    } else if (Array.isArray(block.value)) {
      block.value = [];
    }
  }
}

fs.writeFileSync(path.join(outDir, "draft_content.json"), JSON.stringify(draft));
fs.writeFileSync(path.join(outDir, "draft_meta_info.json"), JSON.stringify(meta));

for (const f of COPY_FILES) {
  const src = path.join(tplDir, f);
  if (fs.existsSync(src)) fs.copyFileSync(src, path.join(outDir, f));
}
for (const d of COPY_DIRS) copyDir(path.join(tplDir, d), path.join(outDir, d));

/**
 * `Timelines/` es del formato nuevo (multi-línea de tiempo). Se clona con
 * identificadores propios: si dos proyectos comparten el mismo `id` de línea de
 * tiempo, CapCut los confunde.
 */
const tlSrc = path.join(tplDir, "Timelines");
if (fs.existsSync(tlSrc)) {
  const tlOut = path.join(outDir, "Timelines");
  copyDir(tlSrc, tlOut);
  const projFile = path.join(tlOut, "project.json");
  if (fs.existsSync(projFile)) {
    const proj = JSON.parse(fs.readFileSync(projFile, "utf8"));
    const newId = uuid();
    const oldId = proj.main_timeline_id;
    proj.id = uuid();
    proj.main_timeline_id = newId;
    if (Array.isArray(proj.timelines)) {
      for (const t of proj.timelines) if (t.id === oldId) t.id = newId;
    }
    fs.writeFileSync(projFile, JSON.stringify(proj));
    const oldDir = path.join(tlOut, oldId);
    if (oldId && fs.existsSync(oldDir)) fs.renameSync(oldDir, path.join(tlOut, newId));
  }
}

/**
 * Miniatura del proyecto. Sin ella CapCut muestra el recuadro en negro, que es
 * justo como se ve un proyecto con los medios perdidos — y confundir "sin
 * portada" con "roto" cuesta un susto cada vez.
 */
try {
  const firstCut = cuts.segmentos[0]?.[0] ?? 0;
  execFileSync("ffmpeg", [
    "-v", "error", "-y", "-ss", String(firstCut + 0.5), "-i", source,
    "-frames:v", "1", "-vf", "scale=640:-1",
    path.join(outDir, "draft_cover.jpg"),
  ]);
} catch {
  console.error("AVISO: no se pudo generar la miniatura (no es bloqueante).");
}

console.error(
  `${segments.length} cortes · ${(timelineUs / 1e6 / 60).toFixed(1)} min ` +
  `(de ${(sourceDurationUs / 1e6 / 60).toFixed(1)} min) · ${fps} fps\n` +
  `→ ${outDir}\n\n` +
  `Plantilla: ${template} (CapCut ${tplVersion ?? "?"})\n` +
  `Raíces de proyectos detectadas:\n  ${DRAFT_ROOTS.join("\n  ")}\n` +
  `Para verlo en CapCut, copia esa carpeta a una de ellas.\n` +
  `Hazlo con CapCut CERRADO: la aplicación cachea la lista al arrancar.`,
);
