/**
 * Reapunta los planes a los brutos locales.
 *
 * Los planes guardan la ruta de origen, y esa ruta es la de Google Drive. Una
 * vez copiado el material con `traer-brutos.sh`, esto cambia el `source` de cada
 * plan sin tocar nada más — los tiempos son los mismos, es el mismo fichero.
 *
 *   node scripts/usar-brutos-locales.mjs          # a local
 *   node scripts/usar-brutos-locales.mjs --drive  # volver a Drive
 */
import fs from "fs";
import path from "path";

// Las dos rutas salen de `rutas.json`; escritas aqui seguian en G: cuando
// Drive ya estaba en I: (C-548). En Drive cada lote vive en su subcarpeta.
const { rutas } = await import("./rutas.mjs");
const LOCAL = rutas.origen;
const aDrive = process.argv.includes("--drive");
const DRIVE = JSON.parse(fs.readFileSync("rutas.json", "utf8")).fuentes.drive;
const enDrive = (toma) => {
  const pila = [DRIVE];
  while (pila.length) {
    const d = pila.pop();
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const r = `${d}/${e.name}`;
      if (e.isDirectory()) pila.push(r);
      else if (e.name === toma) return r;
    }
  }
  return null;
};

const planes = [];
for (const d of fs.readdirSync("work/scenes")) {
  const dir = path.join("work/scenes", d);
  if (!fs.statSync(dir).isDirectory()) continue;
  for (const f of fs.readdirSync(dir)) {
    if (f.startsWith("plan") && f.endsWith(".json")) {
      planes.push(path.join(dir, f));
    }
  }
}

for (const f of planes) {
  const p = JSON.parse(fs.readFileSync(f, "utf8"));
  if (!p.source) continue;
  // La ruta puede venir con barras invertidas: se normaliza antes de comparar.
  const toma = path.basename(p.source.split(/[\\/]/).pop());
  const nuevo = aDrive ? enDrive(toma) : `${LOCAL}/${toma}`;
  if (!nuevo) {
    console.log(`  no esta en Drive, se deja: ${toma}`);
    continue;
  }
  if (nuevo === p.source) continue;
  if (!aDrive && !fs.existsSync(nuevo)) {
    console.log(`  falta en local, se deja: ${toma}`);
    continue;
  }
  p.source = nuevo;
  fs.writeFileSync(f, JSON.stringify(p, null, 1));
  console.log(`${f} → ${nuevo}`);
}
