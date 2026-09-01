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

export const horarioDe = (duracion?: number): Horario => {
  const total = duracion ?? POR_DEFECTO;
  const en = (fraccion: number) => Math.round(total * fraccion);
  return {
    total,
    kickerAt: en(0.05),
    promesaAt: en(0.18),
    cuestaAt: en(0.34),
    valeAt: en(0.5),
    pieAt: en(0.68),
  };
};
