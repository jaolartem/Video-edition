// Saca FOTOGRAMAS SUELTOS de un bundle ya construido, reutilizando un solo
// Chrome para todos. Nunca renderiza un tramo de video: tres imagenes por
// escena, y cada una cuesta lo que cuesta ella.
//
// Lee de la entrada una linea por fotograma: `<composicion> <nombre> <frame>`.
// Lo llama `scripts/mirar.sh`, que es quien decide QUE frames se miran.
//
// **Por que existe.** Medido el 6-9-2026 en esta maquina, cinco fotogramas de
// Reel-R7 desde `work/bundle`:
//
//   npx remotion still --gl=swangle   5,4 s cada uno
//   npx remotion still --gl=angle     5,0 s cada uno   <- la GPU
//   un solo Chrome, angle             1,9 s cada uno
//
// O sea que el freno NO era dibujar: era **abrir un Chrome nuevo por fotograma**.
// La GPU ya estaba puesta donde si manda —el render completo va con
// `--gl=angle`— y ahi rinde porque una sola sesion dibuja miles de frames. En
// `still` el arranque se paga entero cada vez y se come dos tercios del reloj.
//
// Y eso decide si se mira o no: a 5 s, tres fotogramas por escena en una pieza
// de veinte escenas son 5 minutos y se acaba mirando menos; a 1,9 s son 2, y
// mirar deja de doler.
import { openBrowser, selectComposition, renderStill } from "@remotion/renderer";
import path from "path";
import process from "process";

const salida = process.argv[2];
if (!salida) {
  console.error("uso: node scripts/mirar.mjs <dir-salida> [bundle] < lineas");
  process.exit(2);
}
const serveUrl = path.resolve(process.argv[3] ?? "work/bundle");

const entrada = await new Promise((res) => {
  let t = "";
  process.stdin.setEncoding("utf-8");
  process.stdin.on("data", (d) => (t += d));
  process.stdin.on("end", () => res(t));
});

const trabajos = entrada
  .split("\n")
  .map((l) => l.trim())
  .filter(Boolean)
  .map((l) => {
    const [comp, nombre, frame] = l.split(/\s+/);
    return { comp, nombre, frame: Number(frame) };
  });

if (trabajos.length === 0) process.exit(0);

// `angle` es lo mismo que usa el render completo: Chrome compone por D3D11 y no
// por software. Aqui no cambia el reloj —el freno era otro— pero tampoco vale la
// pena dibujar por software teniendo la tarjeta.
const navegador = await openBrowser("chrome", { chromiumOptions: { gl: "angle" } });

// Una composicion se elige UNA vez por id: son ~0,6 s de leer el bundle y no
// dependen del frame.
const elegidas = new Map();
const composicion = async (id) => {
  if (!elegidas.has(id)) {
    elegidas.set(
      id,
      await selectComposition({ serveUrl, id, puppeteerInstance: navegador }),
    );
  }
  return elegidas.get(id);
};

let fallos = 0;
for (const t of trabajos) {
  try {
    await renderStill({
      composition: await composicion(t.comp),
      serveUrl,
      output: path.join(salida, `${t.nombre}.png`),
      frame: t.frame,
      puppeteerInstance: navegador,
    });
    process.stdout.write(".");
  } catch (e) {
    // El fallo se cuenta y se DICE: un fotograma que no sale es un fotograma que
    // nadie mira, y callarlo es el modo de fallar que este guion existe para
    // evitar. El `2>/dev/null` de antes se tragaba el motivo entero.
    fallos += 1;
    process.stdout.write("x");
    if (fallos === 1) process.stderr.write(`\n${t.nombre}: ${e.message}\n`);
  }
}

await navegador.close({ silent: true });
process.stdout.write("\n");
if (fallos) {
  console.error(`${fallos} de ${trabajos.length} fotogramas no salieron`);
  process.exit(1);
}
