/**
 * **La frase que suena dos veces se ve distinta la primera.**
 *
 * Jaime, 7-9-2026, rehaciendo el gancho de reel-03: *«le cambiamos el gancho por
 * la frase más fuerte... sin quitar el gancho y repitiendo la frase en donde
 * originalmente va»*, y con una condición: *«si no hay escena, entonces en
 * blanco y negro la parte que dice "a mí no me diga que su contador tenía que
 * saberlo"»*.
 *
 * La condición es la clave y vale para cualquier pieza, no sólo para ésa. Traer
 * una frase de más adelante al principio significa que **el mismo plano se ve
 * dos veces**, y sin marcarlo el espectador no lee una cita: lee un fallo de
 * montaje. El blanco y negro lo separa del cuerpo de la pieza —es lo que ya
 * hace la marca de humanidad— sin necesitar material que no se grabó.
 *
 * ## Cuál de las dos se apaga
 *
 * La **primera**, que es la que se trajo. La segunda está en su sitio, en color,
 * contando lo que la pieza cuenta; la primera es el anticipo. Al revés se leería
 * como si la pieza terminara en gris.
 *
 * ## Qué cuenta como repetida
 *
 * El mismo trozo de la misma cinta, solapado con otro por más de medio segundo.
 * No se compara texto: dos tomas distintas de la misma frase son material
 * distinto y ahí no hay eco que marcar — el eco es el mismo fotograma.
 */
/** Cuánto se tienen que pisar dos tramos para que sea el mismo plano, en s. */
const PISA = 0.5;

const solapa = (a, b) =>
  a.toma === b.toma &&
  Math.min(a.hasta, b.hasta) - Math.max(a.desde, b.desde) > PISA;

/**
 * Las ventanas en frames que van en blanco y negro por repetirse después.
 *
 * **El sitio lo dan los cortes del montaje, no la resta del EDL.** Sumar lo que
 * dura cada tramo en la cinta da un reloj parecido y no el mismo: entre el EDL y
 * lo que se pega hay costuras y recortes, y en reel-03 la diferencia del primer
 * tramo era de 145 frames contra 70. Un blanco y negro corrido cuatro segundos
 * apaga el plano que no era.
 *
 * @param edl el `edl-sell.json` de la pieza, con `segmentos` y `detalle`.
 * @param cortes los frames donde el montaje corta (`reloj.cortes`), que son los
 *   límites acumulados de cada tramo.
 * @returns `[{at, duration}]`, listo para `pieza.desatura`.
 */
export function eco(edl, cortes = []) {
  const segs = (edl?.segmentos ?? []).map((r, i) => ({
    desde: r[0], hasta: r[1],
    toma: edl.detalle?.[i]?.toma ?? null,
    at: i ? cortes[i - 1] : 0,
    dura: (cortes[i] ?? 0) - (i ? cortes[i - 1] : 0),
  })).filter((s) => s.dura > 0);
  const fuera = [];
  for (let i = 0; i < segs.length; i++)
    if (segs.slice(i + 1).some((o) => solapa(segs[i], o)))
      fuera.push({ at: segs[i].at, duration: segs[i].dura });
  return fuera;
}
