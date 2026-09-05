/**
 * Cuándo entra cada bloque del cierre, **repartido sobre lo que dura la
 * tarjeta**.
 *
 * Jaime: *«todo el panel final pasa muy rápido»*. La duración la calcula el
 * spec a partir de lo que la tarjeta lleva dentro, y el horario se reparte
 * encima en proporciones — así una tarjeta de 3 s y otra de 6 s reparten igual
 * de bien en vez de amontonar la misma cadena de frames fijos.
 *
 * Están escritas como fracciones y no como frames porque lo que se conserva es
 * el **orden y el aire relativo**: antetítulo, promesa, la cuenta que duele, la
 * cuenta que salva, y el pie con la fecha.
 */

export type Horario = {
  /** Frames que dura la tarjeta entera. */
  total: number;
  kickerAt: number;
  promesaAt: number;
  /** La cuenta de no saberlo: navy, la que ya está pasando. */
  cuestaAt: number;
  /** La cuenta del bootcamp: oro, donde el canon manda mirar. */
  valeAt: number;
  pieAt: number;
};

/** Duración por defecto: 4 s. Sólo para una vista suelta sin spec detrás. */
const POR_DEFECTO = 120;

/**
 * **La tarjeta se arma en un tiempo fijo, no en un porcentaje de lo que dure.**
 *
 * Estaba en fracciones —el pie al 68 %— y eso significa que **cuanto más larga
 * es la tarjeta, más tarda en construirse**, que es exactamente al revés de lo
 * que hace falta: una tarjeta larga tiene que dar más tiempo de LEER, no de
 * montarse.
 *
 * Medido en reel-01, con el CTA a 7,8 s: la línea que pide la acción no
 * aparecía hasta el segundo **5,3**, y a 88,65 y 89,55 s el cuadro estaba casi
 * negro. La revisión del diseñador lo vio en los fotogramas: *«la tarjeta de
 * cierre se construye muy lenta, justo donde se pide la acción»*.
 *
 * Con el tope, la tarjeta está entera a los 2,4 s y el resto es lectura.
 */
const TOPE = { kicker: 6, promesa: 15, cuesta: 33, vale: 51, pie: 72 };

export const horarioDe = (duracion?: number): Horario => {
  const total = duracion ?? POR_DEFECTO;
  // La fracción sigue mandando en una tarjeta corta —donde el tope caería
  // después del final— y el tope manda en cuanto la tarjeta da de sí.
  const en = (fraccion: number, tope: number) =>
    Math.min(Math.round(total * fraccion), tope);
  return {
    total,
    kickerAt: en(0.05, TOPE.kicker),
    promesaAt: en(0.18, TOPE.promesa),
    cuestaAt: en(0.34, TOPE.cuesta),
    valeAt: en(0.5, TOPE.vale),
    pieAt: en(0.68, TOPE.pie),
  };
};
