/**
 * Sistema visual el canon, adaptado a video vertical.
 *
 * La página es la autoridad. Aquí no se inventa nada: se traduce de superficie
 * web a superficie de video. Los valores absolutos cambian (una pantalla de
 * 1080×1920 vista en la mano no es un viewport de 1400 px), pero la paleta, los
 * roles tipográficos, los modos y las prohibiciones se respetan literalmente.
 *
 * No se usa el logo por decisión de Jaime.
 *
 * ## Por qué esto es sólo una puerta
 *
 * Llevaba dentro cuatro sistemas que no se tocan entre sí —el lienzo, la
 * paleta, la escala tipográfica y el tiempo— y cambiar una zona segura obligaba
 * a abrir el mismo fichero que declara el oro. Cada uno vive ahora en el suyo:
 *
 * | Fichero | Qué declara |
 * |---|---|
 * | [`lienzo`](./lienzo.ts) | Qué mide el cuadro, las zonas seguras, el aire |
 * | [`paleta`](./paleta.ts) | Los hex, los modos, los tonos, los acentos |
 * | [`tipografia`](./tipografia.ts) | Cuerpos, interlineados, interletrado, pesos |
 * | [`tiempo`](./tiempo.ts) | Duraciones, tiempo de lectura, curvas |
 *
 * **Y esto se queda como la puerta única**, no como un quinto sistema: es lo
 * que importan los treinta ficheros que ya existen, y partir un fichero no es
 * excusa para tocar treinta. Quien escriba algo nuevo puede entrar por el
 * módulo concreto; quien ya entraba por aquí sigue igual.
 */

export {
  layout,
  boardHeight,
  space,
  gap,
} from "./lienzo";

export {
  color,
  viz,
  mode,
  tone,
  accentChoice,
  type Mode,
  type ModeTokens,
  type Tone,
  type Accent,
} from "./paleta";

export {
  size,
  lineHeight,
  videoText,
  tracking,
  weight,
} from "./tipografia";

export {
  FPS,
  duration,
  readingFrames,
  beat,
  ease,
  seconds,
} from "./tiempo";
