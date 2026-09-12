/**
 * La capa: el reloj con el que entra y el sonido que la acompaña.
 *
 * Es lo mínimo que comparten los cinco caminos, y por eso no vive en ninguno.
 * Estaba dentro de `caminos.mjs` porque fue el primero que lo necesitó, y el
 * gancho —que ahora vive aparte, porque es distinto— lo usa igual.
 *
 * No decide nada: mide frames y envuelve un sonido. Lo que se pone en pantalla
 * lo deciden los caminos; qué figura y qué efecto existen, `escena.mjs`.
 */

/** Los frames por segundo de la pieza. Todo lo que dura se cuenta en frames. */
export const FPS = 30;

/** De segundos a frames, que es la única unidad en la que se monta. */
export const frames = (s) => Math.round(s * FPS);

/**
 * Reparte n entradas dentro de una ventana, empezando pronto y espaciándolas.
 *
 * No es decorativo que empiece al principio de la ventana: el gancho se pierde
 * en el primer segundo, así que la primera cosa que se mueve no puede esperar a
 * que la anterior termine. A partir de ahí, aire igual entre entradas.
 */
export const reparte = (n, desde, hasta) => {
  const paso = (hasta - desde) / Math.max(1, n);
  return Array.from({ length: n }, (_, i) => Math.round(desde + paso * i));
};

/**
 * El sonido de una entrada, o nada.
 *
 * Devuelve una lista y no un objeto a propósito: **sin movimiento reconocido no
 * hay capa de sonido**, y `[]` se derrama en el `push` sin que quien llama
 * tenga que preguntar. La regla del proyecto es que el sonido sigue al
 * movimiento, y aquí eso es que un `motion` nulo no produce nada.
 */
export const sonar = (motion, at) =>
  // **Y sin frame tampoco.** El gancho de reel-08 sin filete daba `at + regla`
  // = NaN, el spec lo guardaba como `null` y el render moría en el frame 1
  // («"from" … must be a number», 12-9, C-420).
  motion && Number.isFinite(at) ? [{ tipo: "sonido", at, props: { motion } }] : [];
