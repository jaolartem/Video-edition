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

const LOCAL = "F:/Edicion de video/brutos";
const aDrive = process.argv.includes("--drive");
const DRIVE = "G:/My Drive/Creación de videos/Brutos/Picture";

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
  const nuevo = aDrive ? `${DRIVE}/${toma}` : `${LOCAL}/${toma}`;
  if (nuevo === p.source) continue;
  if (!aDrive && !fs.existsSync(nuevo)) {
    console.log(`  falta en local, se deja: ${toma}`);
    continue;
  }
  p.source = nuevo;
  fs.writeFileSync(f, JSON.stringify(p, null, 1));
  console.log(`${f} → ${nuevo}`);
}
