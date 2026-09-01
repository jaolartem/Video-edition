import type { Tramo } from "./tipos";

/**
 * **La geometría del tablero**, en un sitio.
 *
 * El panel, el eje y la barra los usan el componente y el dibujo de la barra, y
 * estaban declarados donde cayó el primero que los necesitó. Un número de caja
 * repetido es lo mismo que una regla repetida: se cambia uno y el otro sigue
 * dibujando donde estaba.
 */

/** Caja del panel sobre el que se apoya todo. */
export const PANEL = { x: 46, y: 300, w: 988, h: 1090 } as const;
/** Caja del gráfico, en coordenadas del panel. */
export const EJE = { x: 60, y: 230, alto: 640 } as const;
/** Ancho de la barra. */
export const BARRA = 330;
/** Base del gráfico: la línea sobre la que crece todo. */
export const SUELO = EJE.y + EJE.alto;

/** Fracción de la altura total del gráfico → píxeles. Sujeta a 0–1. */
export const aPx = (f: number): number =>
  Math.min(1, Math.max(0, f)) * EJE.alto;

/** Dónde empieza cada tramo, acumulando los de debajo. */
export const basesDe = (tramos: Tramo[]): number[] => {
  const bases: number[] = [];
  let suma = 0;
  for (const tr of tramos) {
    bases.push(suma);
    suma += tr.alto;
  }
  return bases;
};

/**
 * El tramo en el que la acumulación cruza la raya, o −1 si no la cruza.
 *
 * Es el momento del argumento: hasta ahí sólo hay una barra creciendo, y a
 * partir de ahí hay una barra que pasó un límite. Por eso lo pregunta también
 * el sonido.
 */
export const cruzaEn = (
  tramos: Tramo[],
  umbral: { en: number } | undefined,
): number => {
  if (!umbral) {
    return -1;
  }
  const bases = basesDe(tramos);
  return tramos.findIndex((tr, i) => bases[i] + tr.alto > umbral.en);
};
