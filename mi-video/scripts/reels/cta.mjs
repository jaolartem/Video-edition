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
import { ANTES, pideLeer } from "./lectura.mjs";
import { CUENTA, PRECIO, PROMESA } from "./copy.mjs";
import { evento, placaDe } from "./material.mjs";

/** El dia del evento, una vez por corrida. */
const EVENTO = evento();

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
//: Piezas cuyo CTA no se pudo construir, con lo que les falta. Lo recoge
//: `reels-spec.mjs` igual que las figuras sin dibujo.
export const ctasSinDatos = [];

export function ctaDe(slug, marco, duracion) {
  // **Un CTA al que le faltan datos NO se emite.**
  //
  // `PROMESA` y `CUENTA` son mapas por pieza, o sea un `if (slug === …)` con
  // otra forma: una pieza que no este en ellos sale con `promesa: undefined`.
  // Y `CtaCard` hace `promesa.split(" ")`, asi que eso no es una tarjeta
  // incompleta: es el render entero muerto. reel-07 lo hizo dos veces en el
  // frame 1202 —los 40,05 s del `at` del CTA— despues de veinte minutos de
  // trabajo, y el error hablaba de `split`, no de que faltara una promesa.
  //
  // Sin promesa no hay tarjeta. `Reel.tsx` ya sabe no dibujarla, la pieza sale
  // entera y la falta se nombra: ausencia visible en vez de caida tardia. Es
  // la misma regla que el catalogo de figuras — lo que no se sabe trazar no se
  // traza (C-168).
  //
  // **Solo `promesa`.** `cuenta` es opcional a proposito —`CtaCard` la envuelve
  // en un ternario y la tarjeta se ajusta a dos filas en vez de cuatro—, y
  // exigirla dejaba sin cierre a reel-02..06, que lo tenian bien. Lo que se
  // exige es lo que el componente usa sin guarda, ni un campo mas.
  const falta = [];
  if (!PROMESA[slug]) falta.push("promesa");
  if (falta.length) {
    ctasSinDatos.push({ slug, falta });
    return null;
  }
  const filas = 2 + (CUENTA[slug] ? 2 : 0);
  const CTA_DUR = Math.min(15, Math.max(CTA_S, 0.5 + 1.5 + filas * 1.2 + 1));
  return {
    at: Number((duracion - CTA_DUR).toFixed(3)),
    dur: Number(CTA_DUR.toFixed(3)),
    cuenta: CUENTA[slug],
    precio: PRECIO[slug],
    promesa: PROMESA[slug],
    // **Derivada, no escrita.** Ver `verdad.py`: el dia vive en el ultimo
    // escalon de la tabla `precio` y aqui solo se lee. Si la escalera se
    // mueve, la tarjeta se mueve con ella.
    fecha: EVENTO?.dice ?? "",
    duracion: Math.round(CTA_DUR * FPS),
    placa: placaDe(slug),
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
  // Sin CTA no hay tope al que acotar: la pieza acaba donde acaba el corte.
  if (!cta) return;
  const topeCta = Math.round(cta.at * FPS);
  for (const b of tableros) {
    if (b.at + b.duration > topeCta) {
      b.duration = Math.max(Math.round(2.5 * FPS), topeCta - b.at);
      // **Y si al acotarlo deja de dar tiempo a leerse, ENTRA ANTES.**
      //
      // Jaime: *«se les puede dar mas tiempo separando la voz y dando espacio a
      // la lectura, pero solo si hay beneficio en el argumento»*. Aqui lo hay: el
      // ultimo tablero es el que enfrenta la cuenta justo antes de pedir la
      // accion, y es precisamente el que el CTA recorta.
      //
      // Retroceder no cuesta voz —el tablero se monta sobre el final de la linea
      // anterior, que es un L-cut y ya se hace por el otro lado con `SOLAPE`—.
      // Alargar el beat si costaria: en reel-01 no hay silencio despues de «550
      // dolares semanales», sigue con «por no saber algo», que ademas repite lo
      // que la propia frase acaba de decir.
      //
      // El intento anterior puso esto en `armarTableros` y no hizo nada: alli el
      // tablero todavia llega hasta el final de la pieza y no sabe que el CTA se
      // lo va a comer. **El sitio donde se compensa una perdida es donde se
      // pierde.**
      const falta = pideLeer(b.props) - b.duration;
      if (falta > 0) {
        const antes = Math.min(ANTES, falta, b.at);
        b.at -= antes;
        b.duration += antes;
      }
      b.props = { ...b.props, duracion: b.duration };
    }
  }
}

/**
 * Las piezas que se quedan sin tarjeta de cierre: las marca y las cuenta.
 *
 * Vive aqui y no en `reels-spec.mjs` porque el cierre es de este fichero, y
 * porque alli son catorce lineas que pasaban el techo de 300 — que es un
 * contrato, no una recomendacion.
 *
 * Marca `bloqueado` **y** anota la falta en la misma pasada. Anotar aparte
 * costaba una linea mas arriba y otra mas abajo, y la de abajo se comio la
 * aguja de C-139 al fusionarla: una guarda rota por hacer sitio.
 */
/**
 * Cierres que salen sobre negro plano.
 *
 * `placaDe` buscaba una placa cuya lista `sirve` incluyera `pieza:beat`, y la
 * tabla de `ads/fondos.json` no llegaba al cierre de cinco de las siete piezas:
 * R1 y R2 cerraban con su composicion y las demas sobre negro. La diferencia se
 * ve a simple vista y no la decia nadie — un hueco en una tabla de asignacion
 * no es un error, asi que no fallaba; simplemente entregaba peor. Desde que la
 * placa es **de la pieza** el hueco no puede existir por beats: o la pieza
 * declara la suya y el cierre la hereda, o no la declara y falla aqui.
 *
 * **Aqui no se elige placa.** Cual va en cada pieza es diseno y se declara en
 * `ads/fondos.json`. Esto solo agota el catalogo diciendo que se agoto (C-168).
 */
export function cierreSinPlaca(spec, faltas) {
  for (const r of spec) {
    if (r.cta && !r.cta.placa) {
      faltas.push(`${r.id}: el CTA cierra SIN PLACA de fondo — la pieza no ` +
        "tiene placa declarada en `ads/fondos.json`, asi que sale sobre negro " +
        "plano.");
    }
  }
}

/**
 * Todo lo que le falta al cierre de una pieza, en una sola pasada: el copy que
 * impide dibujar la tarjeta y la placa que no se le asigno. Dos preguntas
 * distintas, la misma respuesta para quien lee el parte — «este cierre no esta
 * entero» — asi que se contestan juntas y `reels-spec` las pide una vez.
 */
export function faltasDelCierre(spec, faltas) {
  cierreSinPlaca(spec, faltas);
  for (const c of ctasSinDatos) {
    const p = spec.find((r) => r.id === `Reel-R${Number(c.slug.slice(-2))}`);
    if (p) (p.bloqueado ||= []).push(`sin tarjeta de cierre: falta ${c.falta.join(" y ")}`);
    faltas.push(`${c.slug}: se queda SIN TARJETA DE CIERRE — falta ` +
      `${c.falta.join(" y ")} en \`scripts/reels/copy.mjs\`. La pieza sale entera ` +
      "y sin CTA; antes esto mataba el render en el frame del cierre.");
  }
}
