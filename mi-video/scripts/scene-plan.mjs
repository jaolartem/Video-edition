/**
 * Plan de escenas para el gancho: dónde cambia el plano y con qué fotogramas.
 *
 * Dos modos de cambio, y la eleccion es editorial:
 *
 * - **`chain`** — el ULTIMO fotograma de un plano condiciona el siguiente. Es lo
 *   que da continuidad: cinco planos generados por separado no casan porque
 *   cambia la luz, el angulo y la textura, pero encadenados sí. El fotograma de
 *   salida es literalmente la entrada del siguiente.
 * - **`cut`** — escena distinta, sin condicionar. Un corte duro deliberado. En
 *   un gancho puede ser justo lo que hace falta: la ruptura ES el efecto.
 *
 * Este script no genera nada. Produce el **plan** y extrae los fotogramas de
 * frontera, que es lo que necesita cualquier generador —o el propio montaje— y
 * lo unico que se puede verificar sin depender de una API externa.
 *
 * Uso:
 *   node scripts/scene-plan.mjs --source "G:/.../X.mp4" --edl ads/reel-01/edl-sell.json \\
 *        --hook 16 --every 3 --out work/scenes/reel-01
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
const hookS = parseFloat(arg("hook", "16"));
const everyS = parseFloat(arg("every", "3"));
const outDir = arg("out", "work/scenes");

if (!source || !edlPath) {
  console.error(
    "Uso: node scripts/scene-plan.mjs --source <mp4> --edl <edl.json> " +
    "[--hook 16] [--every 3] [--out work/scenes/reel-01]",
  );
  process.exit(1);
}

const edl = JSON.parse(fs.readFileSync(edlPath, "utf8"));
const cortes = edl.segmentos ?? [];
if (!cortes.length) {
  console.error("El EDL no tiene segmentos.");
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });

/**
 * El gancho se mide sobre la linea de tiempo MONTADA, no sobre el bruto: es lo
 * que el espectador ve en los primeros segundos, y los cortes del EDL ya han
 * saltado el material descartado.
 */
const escenas = [];
let montado = 0;
let siguienteCambio = 0;

for (const [inicio, fin] of cortes) {
  const dur = fin - inicio;
  if (montado >= hookS) break;

  let cursor = inicio;
  while (cursor < fin && montado < hookS) {
    const restaEnCorte = fin - cursor;
    const restaEnEscena = siguienteCambio - montado;
    const paso = Math.min(restaEnCorte, restaEnEscena > 0 ? restaEnEscena : everyS,
                          hookS - montado);
    if (paso <= 0.05) break;

    escenas.push({
      indice: escenas.length,
      montado_desde: Number(montado.toFixed(3)),
      origen_desde: Number(cursor.toFixed(3)),
      origen_hasta: Number((cursor + paso).toFixed(3)),
      duracion: Number(paso.toFixed(3)),
      /**
       * La primera escena nunca encadena: no hay plano anterior del que salir.
       * A partir de ahi, encadenar por defecto — romper la continuidad tiene
       * que ser una decision, no lo que pasa por no decidir.
       */
      modo: escenas.length === 0 ? "cut" : "chain",
    });

    cursor += paso;
    montado += paso;
    siguienteCambio = montado + everyS;
  }
  void dur;
}

/**
 * Restos minusculos: se funden con la escena anterior.
 *
 * Cuando un segmento del EDL se agota justo antes del siguiente cambio queda un
 * plano de decimas de segundo que lee como parpadeo, no como corte. Medido: en
 * un gancho salieron escenas de 0,8 s y 0,4 s.
 *
 * Solo se funden si son CONTIGUAS en el origen; si no, hay un salto de material
 * de por medio y fundirlas metería audio que no va.
 */
const MIN_ESCENA = 1.2;
for (let i = escenas.length - 1; i > 0; i--) {
  const e = escenas[i];
  const prev = escenas[i - 1];
  const contigua = Math.abs(prev.origen_hasta - e.origen_desde) < 0.02;
  if (e.duracion < MIN_ESCENA && contigua) {
    prev.origen_hasta = e.origen_hasta;
    prev.duracion = Number((prev.origen_hasta - prev.origen_desde).toFixed(3));
    escenas.splice(i, 1);
  }
}
escenas.forEach((e, i) => { e.indice = i; });

/**
 * Los restos cortos que NO se pudieron fundir —porque tienen silencio eliminado
 * a los lados y unirlos meteria audio ajeno— heredan el encuadre de la escena
 * anterior. Asi el trozo sigue existiendo pero no se percibe corte: sin cambio
 * de encuadre no hay parpadeo, solo continuidad.
 */
escenas.forEach((e, i) => {
  e.hereda_encuadre = i > 0 && e.duracion < MIN_ESCENA;
});

/**
 * Fotogramas de frontera. Del final de cada escena, porque es el que condiciona
 * la siguiente; y del principio de la primera, que no tiene de quien salir.
 */
const extraer = (segundo, destino) => {
  execFileSync("ffmpeg", [
    "-v", "error", "-y", "-ss", String(Math.max(0, segundo)), "-i", source,
    "-frames:v", "1", "-vf", "scale=1080:-1", destino,
  ]);
};

for (const e of escenas) {
  const salida = path.join(outDir, `escena-${String(e.indice).padStart(2, "0")}-out.jpg`);
  // Un pelo antes del corte: justo en la frontera se puede caer en el frame siguiente.
  extraer(e.origen_hasta - 0.08, salida);
  e.fotograma_salida = path.relative(process.cwd(), salida).replace(/\\/g, "/");
}
if (escenas.length) {
  const entrada = path.join(outDir, "escena-00-in.jpg");
  extraer(escenas[0].origen_desde + 0.08, entrada);
  escenas[0].fotograma_entrada = path.relative(process.cwd(), entrada).replace(/\\/g, "/");
}

const plan = {
  source,
  gancho_s: hookS,
  cambio_cada_s: everyS,
  escenas,
  /**
   * El encadenado se declara aqui para que el generador no tenga que deducirlo:
   * cada escena en modo `chain` recibe el fotograma de salida de la anterior
   * como imagen de condicionamiento.
   */
  cadena: escenas.map((e, i) => ({
    escena: e.indice,
    modo: e.modo,
    condiciona_con: e.modo === "chain" && i > 0
      ? escenas[i - 1].fotograma_salida
      : null,
  })),
};

const planPath = path.join(outDir, "plan.json");
fs.writeFileSync(planPath, JSON.stringify(plan, null, 2));

console.error(
  `${escenas.length} escenas en ${hookS}s de gancho (cambio cada ${everyS}s)\n` +
  `${escenas.length} fotogramas de frontera extraidos → ${outDir}\n` +
  `plan → ${planPath}`,
);
for (const e of escenas) {
  console.error(
    `  ${String(e.indice).padStart(2)} ${e.modo.padEnd(5)} ` +
    `montado ${e.montado_desde.toFixed(1)}s · origen ${e.origen_desde.toFixed(1)}–${e.origen_hasta.toFixed(1)}s`,
  );
}
