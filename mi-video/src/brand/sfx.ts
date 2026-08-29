import { staticFile } from "remotion";

/**
 * Sonido de las animaciones.
 *
 * Ley: **el sonido sigue al movimiento, literalmente.** Si el texto se teclea,
 * suena el tecleo. Si una línea se traza, suena el trazo. Si algo aterriza,
 * suena el golpe.
 *
 * La regla no es "prohibido el whoosh": es **prohibido el sonido sin
 * movimiento que lo justifique**. Un cambio de toma o un desplazamiento de
 * cámara son movimiento, y ahí el barrido es coherente. Lo que sobra es el
 * efecto puesto encima de algo que no se mueve.
 *
 * Cada efecto se emite en el MISMO frame que el movimiento que lo produce, así
 * que quien conoce el frame de la animación es quien emite el sonido. Por eso
 * vive en los componentes de tablero y no en una pista aparte del montaje: una
 * pista aparte se desincroniza en cuanto cambia un tiempo de lectura.
 *
 * **Restricción de mezcla:** la voz de Jaime es el audio principal. Estos
 * efectos van cortos y por debajo — si compiten con la voz, sobran. El volumen
 * por defecto es deliberadamente bajo.
 */

export type Motion =
  /** Un marcador cuadrado que aparece. Clic seco. */
  | "mark"
  /** Una línea que se traza: conector, raíl. Trazo corto y continuo. */
  | "draw"
  /** La bifurcación abriéndose. Trazo doble. */
  | "fork"
  /** El remate: la consecuencia o el resultado. Golpe grave. */
  | "land"
  /** Texto que se teclea. Solo si el texto efectivamente se teclea. */
  | "type"
  /**
   * Barrido. Legítimo en un CAMBIO DE TOMA o en un desplazamiento de cámara —
   * ahí hay movimiento real que lo sostiene. Nunca sobre un elemento quieto.
   */
  | "whoosh"
  /**
   * La distorsión que tapa un corte. Chasquido de televisor antiguo al cambiar
   * de canal — Jaime: *«un efecto glitch que distorsione la imagen y el sonido,
   * durante poco tiempo, con el respectivo ruido»*.
   *
   * Cumple la regla del proyecto: **el sonido sigue al movimiento.** Aquí lo
   * que se mueve es la imagen entera durante tres frames.
   */
  | "glitch";

/**
 * Ficheros de `public/sfx/`. **Los genera `scripts/sfx.sh`**, sintetizados: son
 * transitorios cortos y salen mejor generados que buscados, porque así duran
 * exactamente lo que dura el movimiento que los produce.
 *
 * Los nombres los fija ESTE fichero, no el script. Cuando no coincidían, el
 * render salía sin un aviso y sin un sonido — `staticFile` no comprueba que el
 * fichero exista. Ver C-06 en `docs/correcciones.md`.
 */
export const sfxFile: Record<Motion, string> = {
  mark: "sfx/mark.wav",
  draw: "sfx/draw.wav",
  fork: "sfx/fork.wav",
  land: "sfx/land.wav",
  type: "sfx/type.wav",
  whoosh: "sfx/whoosh.wav",
  glitch: "sfx/glitch.wav",
};

/** Nivel por defecto de cada efecto. Bajo a propósito: la voz manda. */
export const sfxVolume: Record<Motion, number> = {
  mark: 0.18,
  draw: 0.14,
  fork: 0.2,
  land: 0.3,
  type: 0.16,
  whoosh: 0.22,
  glitch: 0.26,
};

export const sfxSrc = (motion: Motion): string => staticFile(sfxFile[motion]);
