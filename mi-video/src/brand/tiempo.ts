import lecturaJson from "./lectura.json";
import { Easing } from "remotion";

/**
 * **El tiempo del sistema**: cuánto dura un movimiento, cuánto se tarda en leer
 * y con qué curva llega lo que entra.
 *
 * Estas tres cosas son las que gobiernan «cuándo pasa», que es lo que manda en
 * video y no en la web. Quien las usa para armar el calendario de una pieza es
 * `horario`; aquí sólo se declaran.
 */

export const FPS = 30;

/**
 * Duraciones de ANIMACIÓN en frames.
 *
 * **No hay techo.** La duracion la decide el tiempo de lectura: si una entrada
 * necesita 15 frames para leerse, lleva 15. Lo que si es regla, y es de
 * registro y no de duracion, es que no haya rebote ni micro-animacion
 * juguetona. Estos valores son el ritmo por defecto, no un limite.
 */
export const duration = {
  /**
   * 0,15 s — la transición estándar del sistema.
   *
   * No se llama `transition`: el linter de Remotion toma esa propiedad por una
   * transición CSS y avisa de animación no pura, que aquí sería un falso
   * positivo — esto es una constante en frames, no un estilo.
   */
  standard: 5,
  /** 0,27 s — entrada de un elemento en video. */
  entry: 8,
  /** 0,2 s — entrada rapida, para lo que no lleva texto que leer. */
  max: 6,
} as const;

/**
 * Frames que un texto necesita para poder LEERSE en pantalla.
 *
 * Es la diferencia de medio mas importante: la web es
 * autopaso — el lector decide cuánto mira — y el video no. Un dato que no da
 * tiempo a leer no está en el video aunque esté en el frame.
 *
 * ~2,8 palabras/segundo es cómodo cuando el espectador además está escuchando.
 * En montaje final estos tiempos los sustituye el anclaje al transcript; esto es
 * el suelo por defecto, no el objetivo.
 */
export const readingFrames = (text: string): number => {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(
    lecturaJson.sueloFrames,
    Math.ceil((words / lecturaJson.palabrasPorSegundo) * FPS),
  );
};

/**
 * Ritmo de CORTE en frames. Es montaje, no animación: no le aplica el techo de
 * 0,2 s, que regula cuánto dura el movimiento de un elemento.
 */
export const beat = {
  /** Cambio de toma por defecto: 3 s. */
  default: 90,
  /** CONNECT sostiene el plano — cortar cada 3 s destruye la intimidad. */
  connect: 180,
  /** Separación entre entradas encadenadas dentro de un mismo plano. */
  stagger: 10,
  /**
   * Silencio antes del remate. Estructuralmente el último elemento de una
   * cadena no es uno más: es la consecuencia. Entra después de una pausa
   * porque una cadena que informa a ritmo constante no aprieta.
   */
  hold: 22,
} as const;

/**
 * Easing.
 *
 * El sistema admite **linear o ease-out, y nada más**. Quedan prohibidos el
 * rebote, el wiggle y cualquier micro-animación juguetona; también el
 * ease-in-out, que no está en la lista. Todo movimiento llega y se queda.
 */
export const ease = {
  linear: Easing.linear,
  /** easeOutCubic. La curva de salida del sistema. */
  out: Easing.bezier(0.33, 1, 0.68, 1),
} as const;

/** Segundos → frames. Usar solo en el borde del sistema (props, EDL). */
export const seconds = (s: number): number => Math.round(s * FPS);
