import { franja } from "../../brand/franja";
import type { Tramo } from "./tipos";

/**
 * **La geometría del tablero**, en un sitio.
 *
 * El eje, la barra y los sitios del texto los usan el componente y el dibujo de
 * la barra, y estaban declarados donde cayó el primero que los necesitó. Un
 * número de caja repetido es lo mismo que una regla repetida: se cambia uno y el
 * otro sigue dibujando donde estaba.
 *
 * ## Aquí hubo un panel opaco de 988×680 y se retiró
 *
 * Era el suelo de todo lo que se dibuja, y en el fotograma se veía lo que Jaime
 * dijo mirándolo: *«la caja negra se come el cuadro»* — la placa asomando sólo
 * por los bordes, la mitad derecha del panel vacía y el gráfico arrinconado
 * abajo a la izquierda. La lámina aprobada el 6-9-2026 —`PanelDentro`— hace lo
 * contrario y es de donde se copia: **la placa a sangre y el negro sólo bajo lo
 * que hay que leer**. Así que el panel se fue y quedaron tres negros que abrazan
 * su texto: el bloque del título, la ficha de cada etiqueta y la banda del pie.
 */

/** La cinta de encabezado: el marco del dato, arriba y en claro. */
export const CINTA = { y: 108 } as const;

/**
 * El bloque del título. **Sangra por la izquierda**, como la premisa de la
 * lámina aprobada: un bloque negro que entra desde el borde ancla la
 * composición sin tener que dibujar una caja alrededor de todo.
 */
export const TITULO = { y: 188, ancho: 916, relleno: 34, tope: 92 } as const;

/**
 * El gráfico: la columna que crece y, a su derecha, la columna de las fichas.
 *
 * La barra pasó de 330 a 430 px de ancho y el alto de 370 a 470 al quedarse sin
 * panel que la encajonara. No es cosmética: la figura **es** el argumento —una
 * cantidad que se apila— y ocupando un tercio del hueco parecía una leyenda.
 */
export const EJE = { x: 90, barra: 430, hueco: 28 } as const;

/** Alto total del gráfico, en píxeles. */
export const ALTO = 470;

/**
 * Base del gráfico: la línea sobre la que crece todo.
 *
 * **Va referida al techo de la franja, no a un número escrito a mano.** Es la
 * relación que C-214 puso en su sitio: el panel medía 300–1390 y el suelo del
 * gráfico caía en 1170, o sea bajo la interfaz de la plataforma, donde no se ve
 * mal — no se ve. Los 148 px que quedan por debajo son lo que ocupa la ficha
 * del primer tramo, que se centra en su bloque y sobresale por abajo.
 */
export const SUELO = franja.techoPx - 148;

/** Techo del gráfico: donde acaba la pila cuando está entera. */
export const TECHO = SUELO - ALTO;

/** La ficha negra que sostiene la etiqueta de un tramo. */
export const FICHA = { x: EJE.x + EJE.barra + EJE.hueco, cuerpo: 40 } as const;

/** Fracción de la altura total del gráfico → píxeles. Sujeta a 0–1. */
export const aPx = (f: number): number =>
  Math.min(1, Math.max(0, f)) * ALTO;

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
 * **Dónde está el único acento de oro.**
 *
 * Jaime, sobre el tablero de reel-02 e3: *«cuatro bloques navy iguales, el ojo
 * no sabe dónde mirar; el oro dice "mira aquí" y aquí no lo dice nadie»*. El
 * canon ya lo tenía escrito —*«el oro reservado a aquello que el espectador debe
 * atender»*— y aquí no había nada reservado.
 *
 * Y cuál es ese sitio lo dice la figura, no el gusto:
 *
 * - **Con umbral**, lo que hay que mirar es lo que asoma por encima de la raya.
 *   Eso ya lo repartía `Barra` tramo a tramo y no cambia.
 * - **Sin umbral**, lo que hay que mirar es **el último tramo**: es el que
 *   cierra la acumulación y el que se lleva la cifra encima. Los cuatro de
 *   debajo son el camino hasta él.
 *
 * Es la misma regla dicha una vez, así que ninguna pieza tiene que elegir.
 */
export const acentua = (
  tramos: Tramo[],
  umbral: { en: number } | undefined,
  i: number,
): boolean => !umbral && i === tramos.length - 1;

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
