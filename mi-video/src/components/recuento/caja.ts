import { franja } from "../../brand/franja";
import { layout } from "../../brand/tokens";

/**
 * **La geometría de las dos columnas.** Dónde empieza cada una, dónde cae cada
 * marca y hasta dónde llega el filete que las separa.
 *
 * Sale de `Recuento.tsx` por el reparto que pide el techo de 300 líneas: lo que
 * mide, lo que decide y lo que escribe son tres cosas. Aquí sólo se mide.
 *
 * ## La caja no declara alto, y eso es del encargo
 *
 * Empieza en 356 —debajo de la cinta y de las cabeceras— y baja lo que haga
 * falta hasta que la corta `ZonaTablero` en el techo de la franja. Con 63 marcas
 * eso era el «sigue saliéndose del encuadre» del encargo original; con cinco no
 * se sale nada, y **ésa es exactamente la corrección**: la cantidad dibujada
 * afirma algo y tiene que ser verdad.
 */

/** Ancho del pasillo donde vive el filete. */
export const PASILLO = 56;

/** Ancho de cada columna, con el pasillo en medio. */
export const COLUMNA = Math.floor(
  (layout.width - layout.safe.left * 2 - PASILLO) / 2,
);

/** Borde izquierdo de cada columna. Cabecera, marcas y condición se alinean ahí. */
export const IZQ = layout.safe.left;
export const DER = layout.safe.left + COLUMNA + PASILLO;

/** El eje del filete. */
export const MEDIO = layout.width / 2;

/** El techo de la franja del subtítulo: el tablero no baja de aquí. */
export const SUELO = franja.techoPx;

/** Las tres alturas de la lámina: filete, cabeceras y primera fila de marcas. */
export const CAJA = { filete: 250, cabeceras: 262, arriba: 356 } as const;

/**
 * Una marca, y es la misma en las dos columnas: «marcas iguales» es literal —
 * si la sola fuera más grande, el dibujo diría otra cosa que el encargo.
 */
export const MARCA = { ancho: 26, alto: 72, aire: 24, entre: 36 } as const;

const PASO_X = MARCA.ancho + MARCA.aire;
const PASO_Y = MARCA.alto + MARCA.entre;

/** Cuántas caben en una fila antes de bajar a la siguiente. */
export const POR_FILA = Math.floor((COLUMNA + MARCA.aire) / PASO_X);

/** Dónde cae la marca `i` de la columna que empieza en `x`. */
export const marcaEn = (x: number, i: number): { x: number; y: number } => ({
  x: x + (i % POR_FILA) * PASO_X,
  y: CAJA.arriba + Math.floor(i / POR_FILA) * PASO_Y,
});

/** Lo que ocupan `n` marcas hacia abajo. Justo debajo entra su condición. */
export const altoDe = (n: number): number =>
  Math.ceil(Math.max(1, n) / POR_FILA) * PASO_Y - MARCA.entre;
