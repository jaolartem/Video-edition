/**
 * **El tablero tiene que ser coherente con lo que se dice, no repetirlo.**
 *
 * Regla de Jaime, 7-9-2026, mirando reel-06: *«la pieza compite con el
 * mensaje»*, y al pedir la regla: *«agrega coherencia con lo que se dice como
 * parte de la regla; no que diga lo mismo, que sea coherente»*.
 *
 * Lo que se vio en el fotograma, y es lo que la regla mide:
 *
 *     b5  voz  «un dueño en Ontario que facture 180 mil sin estructura puede
 *              estar perdiendo entre 25.000 y 30.000 al año»
 *         lámina  ONTARIO · $180,000 FACTURADOS · SIN ESTRUCTURA ·
 *                 −$25,000 A $30,000 AL AÑO
 *
 * Palabra por palabra lo mismo. El ojo lee lo que el oído ya está recibiendo, y
 * no gana ninguno de los dos: **eso es competir**. Le pasaba a tres de los
 * cuatro tableros de reel-06 —el precio y la fecha, igual—.
 *
 * Y el que sí funciona enseña la otra mitad de la regla: `b3` dice
 * `MALA SUERTE → PÉRDIDA SILENCIOSA` mientras la voz dice sólo «eso suele ser
 * una pérdida silenciosa». La lámina **nombra la creencia que se sustituye**,
 * que la voz no nombra. Comparte el tema y añade una mitad.
 *
 * ## Los dos extremos, y sólo los extremos
 *
 * Se mide qué parte de la lámina ya está en la voz de su ventana:
 *
 *   todo      la lámina no añade nada — es un subtítulo con otra tipografía
 *   nada      la lámina habla de otra cosa — compite de verdad
 *   en medio  comparte el tema y aporta: es lo que se quiere
 *
 * **Sólo se avisa en los extremos**, a propósito. Dónde está el punto bueno
 * entre 0 y 1 es una decisión editorial y no la va a fijar un número; que una
 * lámina repita la frase entera o hable de otra cosa, en cambio, es medible sin
 * discutir.
 *
 * No usa una vara nueva: la comparación es la de `reels/texto.mjs`, que es el
 * dueño declarado de comparar texto en este lado. Una decimotercera forma de
 * normalizar era justo lo que la auditoría acababa de cerrar.
 */
import { CIFRA, DICE, raiz, sinTildes } from "./texto.mjs";

/** Cuántas raíces distintas hacen falta para que la medida signifique algo. */
const MINIMO = 2;

/**
 * De qué habla un texto: las raíces de sus palabras. **Sin las cifras.**
 *
 * Y eso último es la regla, no un descuido. Un tablero existe para poner la
 * cifra en pantalla —el canon lo dice: lo que hay que retener se ve—, así que
 * repetir el número no es competir: es su trabajo. Donde tiene que añadir algo
 * es en las palabras.
 *
 * Además la comparación de cifras no se sostiene sola: la lámina escribe
 * «$180,000» y él dice «180 mil». Es el mismo número y no se encuentran, así
 * que meterlas aquí haría que una lámina que repite la frase entera se salvara
 * por un separador de millar.
 */
const deQueHabla = (t) =>
  new Set(
    (sinTildes(DICE(String(t ?? ""))).match(/[a-zñ]+/g) ?? [])
      .filter((w) => w.length >= 4)
      .map(raiz),
  );

/**
 * Las láminas que repiten la voz o que hablan de otra cosa.
 *
 * @param tableros los tableros ya colocados, con `at`, `duration` y `props`.
 * @param captions los subtítulos de la pieza, con `at` en frames.
 * @param textos   de dónde sacar lo que la lámina DIBUJA — el mismo criterio
 *   que usa la puerta de lectura, para que las dos hablen de lo mismo.
 */
export function coherencia(tableros, captions, textos) {
  const faltas = [];
  for (const b of tableros ?? []) {
    const lamina = deQueHabla((textos(b.props) ?? []).join(" "));
    if (lamina.size < MINIMO) continue;
    const dentro = (captions ?? []).filter(
      (c) => c.at + c.duration > b.at && c.at < b.at + b.duration,
    );
    if (!dentro.length) continue;
    const voz = deQueHabla(dentro.map((c) => c.text).join(" "));
    const compartido = [...lamina].filter((x) => voz.has(x)).length;
    const parte = compartido / lamina.size;
    if (parte >= 1)
      faltas.push(
        `el tablero del beat ${b.beat} («${b.kind}») dice lo MISMO que la voz` +
          " en esos segundos: no añade nada y compite con lo que se está" +
          " diciendo. Un tablero acompaña el argumento, no lo subtitula.",
      );
    else if (compartido === 0)
      faltas.push(
        `el tablero del beat ${b.beat} («${b.kind}») no comparte NADA con lo` +
          " que se dice mientras está en pantalla: o va en otro sitio, o su" +
          " copy es de otra etapa.",
      );
  }
  return faltas;
}

/** Para que la puerta y quien compone hablen del mismo oro. Ver `CIFRA`. */
export const esCifra = (t) => CIFRA.test(String(t ?? ""));
