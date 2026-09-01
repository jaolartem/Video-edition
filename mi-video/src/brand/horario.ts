import { interpolate, useCurrentFrame } from "remotion";
import { duration, ease, readingFrames } from "./tokens";

/**
 * **Calcular el horario**: cuándo entra cada bloque y cuánto se le deja leer.
 *
 * Es la segunda de las tres cosas que hace un tablero, y la que más se copiaba:
 * los seis componentes grandes tenían su propio `enter` / `p` / `nodeProgress`
 * escribiendo el mismo `interpolate` con los mismos dos `clamp`, y cuatro de
 * ellos llevaban además su propio cursor avanzando por tiempo de lectura.
 *
 * Aquí viven las dos piezas de esa cuenta. El **tiempo de lectura** en sí no:
 * ése es `readingFrames` y vive en `tokens`, porque es una regla del canon —el
 * vídeo no es autopaso y un dato que no da tiempo a leer no está en la pieza.
 */

/** Una curva de easing. El sistema admite linear o ease-out, y nada más. */
export type Curva = (input: number) => number;

/**
 * Progreso 0→1 de algo que entra en `desde`. **Llega y se queda**: los dos
 * extremos van sujetos, así que antes vale 0 y después vale 1 para siempre.
 */
export type Entrada = (desde: number, dura?: number, curva?: Curva) => number;

/**
 * El horario de este frame.
 *
 * Se usa igual para lo que entra —`ease.out`, la curva de salida del sistema— y
 * para lo que se traza —`ease.linear`, porque el avance del tiempo no acelera
 * ni frena y un raíl que acelera miente sobre lo que dibuja.
 */
export const useEntrada = (): Entrada => {
  const frame = useCurrentFrame();
  return (desde, dura = duration.entry, curva = ease.out) =>
    interpolate(frame, [desde, desde + dura], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: curva,
    });
};

/**
 * Un cursor de frames que **avanza por tiempo de lectura**.
 *
 * Reparte a intervalos iguales y unos enunciados salen ilegibles y otros
 * muertos; reparte por lo que cuesta leer cada uno y el tablero respira solo.
 * Era el mismo bucle escrito cuatro veces, y en `Acumulacion` estaba escrito
 * **dos veces dentro del mismo fichero** —el horario del componente y su
 * `duracionDe`— con el riesgo de que el spec reservara un tiempo y el tablero
 * usara otro.
 */
export class Reloj {
  private t: number;

  constructor(desde = 0) {
    this.t = desde;
  }

  /** El frame en el que está ahora. */
  get ahora(): number {
    return this.t;
  }

  /** Lo planta en un frame concreto: el anclaje al transcript manda. */
  en(frame: number): this {
    this.t = frame;
    return this;
  }

  /** Deja pasar frames sin más: una pausa, un silencio antes del remate. */
  espera(frames: number): this {
    this.t += frames;
    return this;
  }

  /**
   * Deja leer `texto`. `suelo` es el mínimo para lo que además tiene que
   * terminar de moverse, aunque sean dos palabras.
   */
  lee(texto: string, suelo = 0): this {
    this.t += Math.max(suelo, readingFrames(texto));
    return this;
  }
}
