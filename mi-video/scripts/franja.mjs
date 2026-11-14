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
import { lienzoDe } from "./lienzo.mjs";

// `fileURLToPath` y no `new URL(...).pathname`: **la ruta del repo tiene
// espacios** y el pathname los trae como `%20`. Es el gotcha 1 del proyecto.
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const leer = (rel) => fs.readFileSync(path.join(RAIZ, rel), "utf8");

const J = JSON.parse(leer("src/brand/franja.json"));

/**
 * **La franja de un lienzo**, derivada como dice `_derivacion` de `franja.json`:
 * el suelo es el borde inferior de su zona segura y el alto, su banda. La misma
 * cuenta que `franjaDe` en `src/brand/franja.ts` (C-670); la altura ya no es un
 * 1920 escrito aquí, es la de `lienzos.json`.
 */
export const franjaDe = (lienzo = lienzoDe()) => {
  const ALTURA = lienzo.height;
  const suelo = 1 - lienzo.safe.bottom / ALTURA;
  const alto = lienzo.captionBand / ALTURA;
  return {
    suelo,
    techo: suelo - alto,
    alto,
    /** Del suelo de la franja al borde inferior del cuadro: 672 px en vertical. */
    desdeAbajo: Math.round((1 - suelo) * ALTURA),
    /** Lo que un tablero deja libre por abajo: 872 px en vertical. */
    reserva: Math.round((1 - suelo + alto) * ALTURA),
    /** El techo, en píxeles desde arriba: 1048 en vertical. */
    techoPx: Math.round((suelo - alto) * ALTURA),
    cuerpo: J.cuerpo,
  };
};

/** La del vertical, que es la de toda pieza que no declara otro lienzo. */
export const franja = franjaDe();

/**
 * **Y la que declara `franja.json` tiene que ser ésa.** Su `suelo` y su `alto`
 * los leen todavía los scripts de Python; derivada aquí del lienzo, una franja
 * que no casara con ellos serían dos franjas — y se para, no se avisa.
 */
if (franja.suelo !== J.suelo || franja.alto !== J.alto)
  throw new Error(
    `franja.json (${J.suelo} / ${J.alto}) no casa con el lienzo vertical ` +
      `(${franja.suelo} / ${franja.alto}): una de las dos se tocó sin la otra`,
  );

/** La franja dicha para quien la respeta sin dibujarla: prompts e informes. */
export const enPorcentaje = (f = franja) =>
  `del ${(f.techo * 100).toFixed(1)}% al ${(f.suelo * 100).toFixed(1)}%` +
  " de la altura";

/**
 * El párrafo que el pedido del que compone lleva dentro. **Va aquí y no en el
 * prompt** para que el número no se escriba dos veces: el prompt pone el
 * criterio, esto pone la cifra vigente.
 */
export const criterio = (lienzo = lienzoDe()) => {
  const f = franjaDe(lienzo);
  const ALTURA = lienzo.height;
  return `La franja ${enPorcentaje(f)} (${f.techoPx}-${ALTURA - f.desdeAbajo} px` +
    ` sobre ${ALTURA}) esta RESERVADA al subtitulo: ningun tablero baja hasta` +
    ` ahi, y debajo de ella vive la interfaz de la plataforma. El tablero dibuja` +
    ` entre el borde de arriba y ese techo — ${f.techoPx} px de alto util.`;
};

/**
 * Qué componente dibuja cada clase de tablero. **Es el mismo reparto que
 * `dibuja()` en `src/Ad.tsx`**, y por eso las formas que comparten componente
 * aparecen aquí apuntando al mismo fichero: cuatro de las siete que no dibujaba
 * nadie eran la misma idea con otro nombre.
 */
const COMPONENTE = {
  causal: "CausalChain",
  twopaths: "TwoPaths",
  comparacion: "Comparacion",
  acumulacion: "Acumulacion",
  Anidado: "Anidado",
  fusion: "Fusion",
  desvio: "Desvio",
  Fichas: "Fichas",
  EvidenceCard: "Fichas",
  BandaFecha: "Fichas",
  ListaNumerada: "Fichas",
};

/**
 * Un componente **respeta la franja** si la reserva por construcción: o recorta
 * su contenido con `ZonaTablero`, o descuenta `franja.reserva` del alto útil
 * —directamente o a través de `Marco`, que es quien lo hace por todos los que
 * lo usan—. Cualquier otra cosa es un número escrito a mano, que es como
 * `Comparacion` y `Acumulacion` acabaron dibujando a 1390, 1452 y 1570 — bajo
 * la interfaz.
 *
 * `<Marco` cuenta desde que `Canon.tsx` lee `franja.reserva` en vez de sumar
 * `layout.safe.bottom + layout.captionBand`. Antes no podía contar: era la
 * cuarta copia del número, y una copia no es una reserva.
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
  return t.includes("<ZonaTablero>") ||
    t.includes("paddingBottom: franja.reserva") ||
    t.includes("<Marco");
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
      `\n  alto  ${franja.alto.toFixed(4)} (${lienzoDe().height - franja.desdeAbajo - franja.techoPx} px)` +
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
