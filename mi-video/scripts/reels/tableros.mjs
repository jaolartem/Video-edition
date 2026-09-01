/**
 * **Los tableros y sus paneles: qué se pone en pantalla y durante cuánto.**
 *
 * Salieron de `capas.mjs` porque son una responsabilidad propia y la mayor de
 * aquel fichero: 145 de sus 311 líneas de código. Lo demás que monta capas
 * —tarjetas, glitches, caminos, contraste— no comparte ni una regla con esto.
 *
 * La regla que gobierna, y es la del canon: **la duración la decide la
 * lectura**. Un dato que no da tiempo a leer no está en el vídeo aunque esté en
 * el frame — 0,75 s por bloque más medio segundo de respiro. Y va calculada, no
 * escrita a mano: a mano se desfasa al primer reajuste del corte y no avisa.
 */
import { FPS } from "./reloj.mjs";
import { ADELANTO, SOLAPE, duracionTablero } from "./lectura.mjs";
import { placaDe } from "./material.mjs";

/**
 * **Una tarjeta y un tablero no pueden empezar en el mismo frame.**
 *
 * Un beat sin material se ancla donde empieza el siguiente —no tiene sitio
 * propio— y si ese siguiente lleva tablero, los dos ocupan el cuadro entero a la
 * vez: se pintan uno encima del otro y la tarjeta no existe. En el reel 2 la del
 * beat 2 y el tablero del beat 3 salían los dos en 6,9 s. La tarjeta va primero
 * —es el beat anterior— y el tablero entra cuando ella termina, que además es el
 * orden del argumento.
 */
export const empujaTablero = (cartas) => (at) =>
  cartas.reduce(
    (t, c) => (c.at <= t && t < c.at + c.duration ? c.at + c.duration : t),
    at,
  );

/**
 * Los tableros con su horario. **El tablero dura lo que cuesta leerlo, no lo que
 * dura el beat.**
 *
 * Esto tomaba la duración del beat y sólo caía en el tiempo de lectura cuando el
 * beat no existía. Mientras la voz decía la comparación entera daba igual; en
 * cuanto la etapa 3 del reel-01 pasó a la toma corta —9,4 s de voz, 6,5 s de
 * escena— el tablero se quedó en 6,5 s **para ocho bloques**: premisa, dos
 * columnas con su cifra y su pie, remate y fuente. A 0,75 s por bloque más medio
 * segundo de respiro son doce, así que la mitad de la tabla pasaba sin poder
 * leerse. Jaime: *«prefiero que explique lo que tiene que explicar»*.
 *
 * Se toma el mayor de los dos y se le suma el `SOLAPE` que tapa la costura
 * siguiente, **sin pasarse del final de la composición**: si se pasa, Remotion
 * recorta el `<Sequence>` en silencio y el tablero desaparece a media
 * construcción sin que nadie se entere.
 */
export function armarTableros(bs, { slug, reloj, duracion, empuja }) {
  const fin = Math.round(duracion * FPS);
  return bs
    .map((b) => {
      const at = empuja(reloj.anclaDe(b.beat));
      const dur = Math.min(
        Math.max(reloj.duracionDe(b.beat) ?? 0,
                 duracionTablero(b.kind, b.props)) + SOLAPE,
        fin - at,
      );
      return {
        at,
        duration: dur,
        kind: b.kind,
        // La placa del beat, si la hay: **los fondos son para usarse**. El
        // collage asoma alrededor y los bloques opacos sostienen las cifras, que
        // es como lo hace el canon. Los ficheros de `public/sfx/` ya existen,
        // así que el sonido de los movimientos se enciende: niveles bajos, la
        // voz manda.
        props: { ...b.props, sound: true, placa: placaDe(slug, b.beat),
                 duracion: dur },
      };
    })
    .filter((b) => {
      if (b.duration > 0) return true;
      console.log(
        `    ojo: un tablero queda fuera de la pieza (empieza en ` +
        `${(b.at / FPS).toFixed(1)}s de ${duracion.toFixed(1)}s) y no se emite.`,
      );
      return false;
    });
}

/**
 * Los paneles tienen **dos usos**, y la diferencia la marca si su beat lleva
 * tablero:
 *
 * - **Con tablero: anuncia.** Entra `ADELANTO` frames antes y le entrega el
 *   cuadro. Un gráfico que aparece es una promesa, y el tablero la cumple.
 * - **Sin tablero: acompaña.** Es la animación detrás del hablante que
 *   ejemplifica lo que dice. **Tampoco dura el beat entero**: duraba 17,7 s en
 *   el beat 5 del reel 1 y sus tres bloques entran en el primer segundo, o sea
 *   dieciséis segundos de tres rótulos quietos. Se queda lo que tarda en
 *   escribirse más tres segundos de sostener y devuelve el cuadro, que es lo que
 *   Jaime pidió para ese tramo: *«del 45 al 65 no hay cc»*.
 *
 * **Los props del diseñador se convierten a bloques**, que es lo que el panel
 * sabe leer. Pasaba el objeto tal cual y `ADELANTO` hace `bloques.length`: con
 * un objeto eso es `undefined`, la duración salía `NaN` y **el panel desaparecía
 * sin decir nada**. Un bloque por texto declarado, en el orden en que él los
 * escribió: ése es su orden de lectura. Lo que no es texto —familia, cubre,
 * oro— es cromo y no se rotula.
 */
const NO_TEXTO = new Set(["familia", "zona", "cubre", "oro", "sound", "fondo",
                          "filete", "source", "paso", "entrada"]);

export function armarPaneles(bs, reloj, tableros) {
  return bs
    .map((b) => {
      const yaSon = Array.isArray(b.props?.bloques) ? b.props.bloques : null;
      const bloques = yaSon ?? Object.entries(b.props ?? {})
        .filter(([k, v]) => !NO_TEXTO.has(k) && typeof v === "string" && v.trim())
        .slice(0, 3)
        .map(([, v]) => ({ texto: v }));
      return { beat: b.beat, bloques };
    })
    .filter((b) => b.bloques.length)
    .map((b) => {
      const inicio = reloj.anclaDe(b.beat);
      const suyo = tableros.find((t) => t.at === inicio);
      if (suyo) {
        const dur = ADELANTO(b.bloques);
        const at = suyo.at - dur;
        return at < 0 ? null : { at, duration: dur, bloques: b.bloques };
      }
      const dur = reloj.duracionDe(b.beat);
      const tope = ADELANTO(b.bloques) + 3 * FPS;
      return dur
        ? { at: inicio, duration: Math.min(dur, tope), bloques: b.bloques }
        : null;
    })
    .filter(Boolean)
    // **Un panel cede cuando entra el siguiente.** El de acompañamiento dura el
    // beat entero, y el que anuncia un tablero entra antes de que ese beat
    // acabe: sin esto se pisaban tres segundos.
    .sort((x, y) => x.at - y.at)
    .map((x, i, todos) => {
      const sig = todos[i + 1];
      return sig && x.at + x.duration > sig.at
        ? { ...x, duration: sig.at - x.at }
        : x;
    })
    .filter((x) => {
      if (x.duration > 0) return true;
      console.log(
        `    ojo: un panel cede del todo en ${(x.at / FPS).toFixed(1)}s ` +
        `(otro entra en el mismo frame) y no se emite.`,
      );
      return false;
    });
}

