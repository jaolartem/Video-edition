/**
 * **La tarjeta de cierre.** Un SELL lleva exactamente una; el resto de pilares,
 * cero.
 *
 * Tres reglas la gobiernan y las tres tienen un vídeo detrás:
 *
 * 1. **Dura lo que tarda en leerse**, no una constante. Jaime: *«todo el panel
 *    final pasa muy rápido, conviene bajarle la velocidad a esa parte»*.
 * 2. **Es el último frame de la pieza**, así que no puede ser un plano negro
 *    quieto: lleva placa recortada y reparte su horario sobre su duración.
 * 3. **Nada se pinta por debajo de ella.** Un tablero que se mete bajo la
 *    tarjeta no lo ve nadie, y encima falsea la cuenta de presencia.
 */
import { FPS } from "./reloj.mjs";
import { CUENTA, PRECIO, PROMESA } from "./copy.mjs";
import { placaDe } from "./material.mjs";

/**
 * Suelo de duración. 5,5 s y no 4: Jaime pidió que el último tablero entre
 * **desde el 1:10**, y con 4 s entraba en 71,2 y se montaba entero en el primer
 * medio segundo. Con 5,5 entra en 69,7 y reparte su horario sobre toda su vida.
 */
const CTA_S = 5.5;

/**
 * **La duración se deriva de lo que lleva dentro**, que es la misma regla que
 * gobierna paneles y tableros: medio segundo de entrada, segundo y medio para la
 * promesa, 1,2 s por fila y un segundo de sostener al final. Con cuatro filas
 * salen 7,8 s en vez de 5,5.
 *
 * Era literal el problema: `CtaCard` reparte kicker, promesa y filas sobre su
 * propia duración, así que con 5,5 s y cuatro filas cada dato entraba y se iba
 * antes de leerse. El primer intento fue darle el beat de registro entero, y lo
 * tumbó el detector de mudos: en el reel 5 eso tapaba 15 s de subtítulo. La
 * tarjeta ilustra el cierre, no lo sustituye.
 */
export function ctaDe(slug, marco, duracion) {
  const filas = 2 + (CUENTA[slug] ? 2 : 0);
  const CTA_DUR = Math.min(15, Math.max(CTA_S, 0.5 + 1.5 + filas * 1.2 + 1));
  return {
    at: Number((duracion - CTA_DUR).toFixed(3)),
    dur: Number(CTA_DUR.toFixed(3)),
    cuenta: CUENTA[slug],
    precio: PRECIO[slug],
    promesa: PROMESA[slug],
    fecha: "21 de septiembre",
    duracion: Math.round(CTA_DUR * FPS),
    placa: placaDe(slug, marco.beats.length),
  };
}

/**
 * **Ningún tablero pasa del arranque del CTA.**
 *
 * En reel-06 uno se estiraba treinta segundos y se comía el final, y la
 * comprobación de presencia bloqueaba la pieza diciendo que Jaime no aparecía —
 * tenía razón: no aparecía porque había un tablero encima. Se acota aquí y no
 * donde se construyen los tableros porque el CTA se calcula después: su sitio
 * depende de la duración del corte, no del plan.
 *
 * El suelo de 2,5 s es para que un tablero recortado siga siendo legible en vez
 * de un parpadeo; si con eso se mete bajo la tarjeta, el que avisa es el
 * detector de presencia, que es quien sabe cuánto se está tapando en total.
 */
export function acotarAlCta(tableros, cta) {
  const topeCta = Math.round(cta.at * FPS);
  for (const b of tableros) {
    if (b.at + b.duration > topeCta) {
      b.duration = Math.max(Math.round(2.5 * FPS), topeCta - b.at);
      b.props = { ...b.props, duracion: b.duration };
    }
  }
}
