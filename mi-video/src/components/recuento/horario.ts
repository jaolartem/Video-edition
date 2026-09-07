/**
 * **El calendario del recuento, calculado de atrás hacia delante.**
 *
 * Ése es el orden que importa, y no cambia con la corrección del 6-9-2026: la
 * marca sola entra la última porque es el remate —el encargo lo dice, *«entra
 * sola, después de un silencio»*— y todo lo demás ocupa lo que queda por
 * delante. Al revés, repartiendo desde el principio, la sola caía donde acabara
 * la ráfaga y no donde se dice.
 *
 * ## Las cuatro cosas que pasan, y cada una cae donde él la dice
 *
 * Medido sobre el corte de hoy de reel-02 (tablero en 1580, 512 frames):
 *
 * | Movimiento | Frame | Lo que suena debajo |
 * |---|---|---|
 * | las marcas, de una en una | 1626 → 1858 | «búsquelas en Google… unos cuantos cursos del CRA… llenar el formulario T2» |
 * | la condición de lo que hay | 1887 | «pero las estrategias para que USTED las implemente» |
 * | la marca sola, en oro | 2032 | «en español hay uno» |
 * | el cierre | 2042 | entrega el cuadro a «este 21 de septiembre…» |
 *
 * No hay ni un frame escrito a mano: los cuatro salen de la duración del hueco.
 * Un tablero anclado a mano se desfasa al primer reajuste del corte y no avisa.
 *
 * ## Y con cinco marcas ya no hay ráfaga
 *
 * Con 63 la ráfaga llenaba el hueco entero para que el tablero se construyera en
 * vez de estar puesto. Con cinco, ese mismo hueco repartido da una marca cada
 * 1,9 s: no es una ráfaga, es **contar**, que es lo que la lámina hace ahora.
 * Por eso cada marca suena, y antes sonaba la fila.
 */

export type Horario = {
  filete: number;
  cabeceras: number;
  /** Frame de la primera marca. */
  primera: number;
  /** Frames entre una marca y la siguiente. */
  paso: number;
  /** La condición de la columna que se llena: para quién está hecho lo que hay. */
  condicion: number;
  /** La marca sola. */
  uno: number;
  /** El contraste con el que se cierra el tramo. */
  cierre: number;
};

/** Lo que se sostiene la marca sola una vez puesta: es el remate. */
const REMATE = 60;

/** El respiro entre la última marca y la condición que la califica. */
const RESPIRO = 30;

/** Lo que tarda el cierre en entrar detrás del remate. */
const TRAS_EL_REMATE = 10;

/**
 * Dónde cae la condición dentro de la construcción, en fracción del remate.
 *
 * 0,68 no es un gusto: es el punto en el que la voz pasa de enumerar lo que hay
 * a decir para quién no es. El tablero dice lo mismo en ese frame.
 */
const CONDICION = 0.68;

export const horarioDe = (dur: number, cuantos: number): Horario => {
  const primera = 46;
  const uno = Math.max(primera + 60, dur - REMATE);
  const condicion = Math.max(primera + 24, Math.round(uno * CONDICION));
  const paso = Math.max(
    6,
    Math.round((condicion - RESPIRO - primera) / Math.max(1, cuantos - 1)),
  );
  return {
    filete: 10,
    cabeceras: 22,
    primera,
    paso,
    condicion,
    uno,
    cierre: uno + TRAS_EL_REMATE,
  };
};
