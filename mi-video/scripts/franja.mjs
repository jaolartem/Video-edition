/**
 * **La franja del subtítulo: el valor, y quién la invade.**
 *
 * Instrucción de Jaime (T-02): *«durante los tableros el subtítulo pasa a
 * estilo tradicional discreto… apoyado en el borde inferior de la zona segura
 * —no del cuadro—. Por implicación: ningún tablero baja hasta esa franja, que
 * queda reservada al subtítulo»*.
 *
 * El número vive en `src/brand/franja.json` y **sólo ahí**. Este fichero es el
 * lado de los scripts —el pedido del que compone y esta medición—; el lado del
 * render es `src/brand/franja.ts`. Dos lectores, un valor, igual que
 * `rutas.json` con `rutas.mjs` y `rutas.py`.
 *
 *   node scripts/franja.mjs        # el valor y los tableros que la invaden
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// `fileURLToPath` y no `new URL(...).pathname`: **la ruta del repo tiene
// espacios** y el pathname los trae como `%20`. Es el gotcha 1 del proyecto.
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const leer = (rel) => fs.readFileSync(path.join(RAIZ, rel), "utf8");

const J = JSON.parse(leer("src/brand/franja.json"));
const ALTURA = 1920;

export const franja = {
  suelo: J.suelo,
  techo: J.suelo - J.alto,
  alto: J.alto,
  /** Del suelo de la franja al borde inferior del cuadro: 672 px. */
  desdeAbajo: Math.round((1 - J.suelo) * ALTURA),
  /** Lo que un tablero deja libre por abajo: 872 px. */
  reserva: Math.round((1 - J.suelo + J.alto) * ALTURA),
  /** El techo, en píxeles desde arriba: 1048. */
  techoPx: Math.round((J.suelo - J.alto) * ALTURA),
  cuerpo: J.cuerpo,
};

/** La franja dicha para quien la respeta sin dibujarla: prompts e informes. */
export const enPorcentaje = () =>
  `del ${(franja.techo * 100).toFixed(1)}% al ${(franja.suelo * 100).toFixed(1)}%` +
  " de la altura";

/**
 * El párrafo que el pedido del que compone lleva dentro. **Va aquí y no en el
 * prompt** para que el número no se escriba dos veces: el prompt pone el
 * criterio, esto pone la cifra vigente.
 */
export const criterio = () =>
  `La franja ${enPorcentaje()} (${franja.techoPx}-${ALTURA - franja.desdeAbajo} px` +
  ` sobre ${ALTURA}) esta RESERVADA al subtitulo: ningun tablero baja hasta` +
  ` ahi, y debajo de ella vive la interfaz de la plataforma. El tablero dibuja` +
  ` entre el borde de arriba y ese techo — ${franja.techoPx} px de alto util.`;

/** Qué componente dibuja cada clase de tablero. Ver `src/Ad.tsx`. */
const COMPONENTE = {
  causal: "CausalChain",
  twopaths: "TwoPaths",
  comparacion: "Comparacion",
  acumulacion: "Acumulacion",
};

/**
 * Un componente **respeta la franja** si la reserva por construcción: o recorta
 * su contenido con `ZonaTablero`, o descuenta `franja.reserva` del alto útil.
 * Cualquier otra cosa es un número escrito a mano, que es como `Comparacion` y
 * `Acumulacion` acabaron dibujando a 1390, 1452 y 1570 — bajo la interfaz.
 */
export const respeta = (componente) => {
  // **Un componente que no existe no respeta nada, y eso se dice.**
  //
  // Esto reventaba con `ENOENT` sobre `Anidado.tsx`: un `kind` declarado en el
  // spec que **no dibuja nadie** —no hay componente, no esta en el despachador—
  // y que en pantalla sale como un hueco sin dar error. Reel-R2 beat 6 lo lleva.
  //
  // Que la comprobacion muriera ahi era lo peor de los dos mundos: ni se veia el
  // tablero fantasma ni se comprobaban los demas. Ahora falla como lo que es,
  // una falta, y el resto de la lista se sigue mirando.
  const f = `src/components/${componente}.tsx`;
  if (!fs.existsSync(f)) return null;
  const t = leer(f);
  return t.includes("<ZonaTablero>") || t.includes("paddingBottom: franja.reserva");
};

export const invasores = () => {
  const reels = JSON.parse(leer("src/reels.json"));
  const filas = [];
  for (const r of reels) {
    for (const b of r.boards ?? []) {
      const comp = COMPONENTE[b.kind] ?? b.kind;
      filas.push({ pieza: r.id, kind: b.kind, componente: comp, ok: respeta(comp) });
    }
  }
  return filas;
};

if (process.argv[1] && process.argv[1].endsWith("franja.mjs")) {
  console.log(`franja: ${enPorcentaje()}`);
  console.log(
    `  suelo ${franja.suelo} (borde inferior de la zona segura, ${franja.desdeAbajo} px)` +
      `\n  techo ${franja.techo.toFixed(4)} (${franja.techoPx} px)` +
      `\n  alto  ${franja.alto.toFixed(4)} (${ALTURA - franja.desdeAbajo - franja.techoPx} px)` +
      `\n  reserva del tablero: ${franja.reserva} px`,
  );
  const filas = invasores();
  const mal = filas.filter((f) => f.ok !== true);
  for (const f of filas) {
    console.log(`  ${f.ok ? "ok " : "NO "} ${f.pieza} · ${f.componente}`);
  }
  console.log(
    `\n${mal.length} de ${filas.length} tableros invaden la franja del subtitulo`,
  );
  if (mal.length) process.exit(1);
}
