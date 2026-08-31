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

/**
 * Nivel de cada efecto, **derivado del pico real de su fichero**.
 *
 * Era un número por efecto puesto a ojo, con la regla correcta detrás —*«la voz
 * manda»*— y el resultado equivocado: Jaime, viendo el reel-01 montado, *«el
 * tablero sin sonido»*. Y tenía razón, con la aritmética delante:
 *
 *   `mark.wav` pica a −17,5 dBFS · a 0,18 son −14,9 dB · en la mezcla, −32,4
 *
 * Después `musica.sh` normaliza a −14 LUFS con la voz mandando, así que el clic
 * quedaba **unos 20 dB por debajo de la voz, durando 140 ms, encima de una
 * frase hablada**. Eso no es «por debajo de la voz»: es inaudible. La prueba
 * cruzada estaba en el propio lote — `glitch.wav` pica a −7,4 dB, diez más
 * alto, y ése sí se oía.
 *
 * El fallo de fondo es que el número no dependía del fichero. Los efectos los
 * sintetiza `scripts/sfx.sh` y cada uno sale con su propio pico —de −7,4 a
 * −17,5, diez decibelios de diferencia entre ellos—, así que un volumen fijo
 * por efecto significa siete niveles distintos sin querer.
 *
 * Ahora cada nivel se calcula para dejar el efecto en un pico objetivo, y el
 * objetivo se declara al lado. La regla de Jaime sigue mandando: todos quedan
 * por debajo de la voz, que en el máster pica alrededor de −12 dBFS.
 */
const PICO_DEL_FICHERO: Record<Motion, number> = {
  // Medido con `ffmpeg -af volumedetect` sobre `public/sfx/`. Si se regeneran
  // los efectos, se vuelve a medir: es lo que hace que el nivel signifique algo.
  mark: -17.5,
  draw: -16.5,
  fork: -15.6,
  land: -12.6,
  type: -9.6,
  whoosh: -15.5,
  glitch: -7.4,
};

/**
 * Dónde tiene que picar cada efecto en la mezcla, en dBFS. Un transitorio se
 * oye entre 8 y 12 dB por debajo de la voz; por debajo de 20 desaparece.
 */
const PICO_OBJETIVO: Record<Motion, number> = {
  mark: -21,      // el clic de cada entrada: tiene que leerse, no destacar
  draw: -22,      // continuo y largo, molesta antes que el clic
  fork: -21,
  land: -18,      // el remate: es el que cierra el tablero
  type: -24,      // se repite mucho, así que va más abajo
  whoosh: -21,
  glitch: -14,    // tapa un corte: es el único que puede pisar la voz
};

const nivel = (m: Motion): number =>
  Math.min(1, 10 ** ((PICO_OBJETIVO[m] - PICO_DEL_FICHERO[m]) / 20));

export const sfxVolume: Record<Motion, number> = {
  mark: nivel("mark"),
  draw: nivel("draw"),
  fork: nivel("fork"),
  land: nivel("land"),
  type: nivel("type"),
  whoosh: nivel("whoosh"),
  glitch: nivel("glitch"),
};

export const sfxSrc = (motion: Motion): string => staticFile(sfxFile[motion]);
