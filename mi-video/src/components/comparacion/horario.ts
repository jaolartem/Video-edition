import { duration, readingFrames } from "../../brand/tokens";
import type { ComparacionProps } from "./tipos";

/**
 * Cuándo entra cada cosa, **repartido sobre la escena que el tablero
 * reemplaza**.
 *
 * Jaime: *«el tablero reemplaza la escena»* y *«se tiene que presentar poco a
 * poco y durar toda la escena»*. Con un horario fijo el tablero se montaba en
 * 10 s y se quedaba quieto el resto, que es justo lo que hace que un tablero se
 * sienta relleno. Repartido en proporciones, cada elemento entra cuando el
 * anterior ya se pudo leer y hay algo entrando hasta el final.
 *
 * Las columnas entran **de una en una**, no a la vez. Ver las dos juntas es un
 * dato; verlas aparecer una tras otra es una comparación — el espectador tiene
 * tiempo de leer la primera antes de que llegue la que la desmiente.
 */

export type Horario = {
  /** Sobre cuántos frames se reparte todo. */
  total: number;
  entraIzq: number;
  entraDer: number;
  finColumnas: number;
  /** El remate llega cuando las dos columnas ya se compararon. */
  remateAt: number;
  /** La banda de fuente y condición: letra pequeña, y va la última. */
  pieAt: number;
};

/**
 * El suelo por tiempo de lectura: lo que tardan en entrar las dos columnas y en
 * poder leerse sus cifras.
 *
 * **Estaba escrito dos veces** —aquí dentro y otra vez en `duracionDe`— con la
 * misma expresión copiada. Que coincidieran era suerte: el spec podía reservar
 * un hueco de un largo y el tablero repartirse sobre otro.
 */
const minimo = ({
  izquierda,
  derecha,
}: Pick<ComparacionProps, "izquierda" | "derecha">): number =>
  duration.entry * 2 +
  Math.max(20, readingFrames(izquierda.cifra)) +
  Math.max(20, readingFrames(derecha.cifra));

export const horarioDe = (
  props: Pick<ComparacionProps, "izquierda" | "derecha" | "duracion">,
): Horario => {
  // Sin `duracion` cae al horario mínimo por tiempo de lectura, que es lo que
  // hace falta para una vista suelta.
  const total = Math.max(props.duracion ?? 0, minimo(props) + 40);
  const finColumnas = Math.round(total * 0.62);
  return {
    total,
    entraIzq: Math.round(total * 0.14),
    entraDer: Math.round(total * 0.38),
    finColumnas,
    remateAt: finColumnas + 6,
    pieAt: Math.round(total * 0.78),
  };
};

/** Cuánto dura el tablero completo, en frames. El spec pregunta, no supone. */
export const duracionDe = (props: ComparacionProps): number =>
  minimo(props) + readingFrames(props.condicion) + 24;
