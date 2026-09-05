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
export function armarTableros(bs, { slug, reloj, duracion, empuja, captions }) {
  const fin = Math.round(duracion * FPS);
  return bs
    .map((b) => {
      // **El tablero arranca con la palabra, no con la etapa.**
      //
      // Regla de Jaime, sobre el primer render: *«el tablero inicia con lo que
      // se dice, y lo que se dice queda repartido por el tablero, siempre; se
      // puede cortar el texto por la mitad o dejar más espacio, pero el
      // arranque no se negocia»*.
      //
      // Esto anclaba al inicio del beat. Medido en reel-03 e6: el precio se dice
      // en 54,7 s y la etapa empieza en 47,93 s — **6,8 s** de tablero puesto
      // antes de que nadie diga lo que rotula. Desde el diseño no había forma de
      // corregirlo, y por eso el paso lo declara: `props.anclas` trae el segundo
      // exacto de cada bloque.
      //
      // Si no viene declarado, se ancla al beat como siempre: una pieza vieja no
      // se rompe porque el mecanismo nuevo exista.
      const at = empuja(_anclaDeclarada(b, reloj, captions) ?? reloj.anclaDe(b.beat));
      // **Y no se come la etapa siguiente.**
      //
      // El `Math.max` dejaba que un tablero durase lo que su forma pide aunque
      // su beat fuera mas corto: una forma sin componente propio recibe 8,5 s
      // fijos, y con eso el tablero de reel-06 e3 se comia la etapa 4 entera y
      // el de e7 la etapa 8. **Esa es la causa mecanica de «estan sobrepuestos»**
      // — no una decision de nadie, un maximo mal puesto.
      //
      // Lo que dura una etapa es lo que dura: el tablero se estira hasta ella y
      // hasta `SOLAPE`, que son los 0,8 s deliberados con los que se esconde la
      // costura. Si su forma pide mas tiempo del que hay, lo que sobra es la
      // forma, y eso lo dice la puerta de legibilidad — no se roba del beat de
      // al lado, donde se esta diciendo otra cosa.
      const suyo = reloj.duracionDe(b.beat) ?? duracionTablero(b.kind, b.props);
      const dur = Math.min(suyo + SOLAPE, fin - at);
      return {
        at,
        duration: dur,
        // **El beat viaja con el tablero.** `armarPaneles` lo buscaba por
        // `t.at === inicio`, o sea suponiendo que un tablero empieza donde
        // empieza su etapa. Desde que puede anclarse a la palabra eso deja de
        // ser cierto, y el panel que anuncia un tablero no encontraba el suyo:
        // caia al camino de acompanamiento y se colocaba solo, ocho segundos
        // antes de que nadie dijera lo que anuncia (reel-06 e2).
        beat: b.beat,
        kind: b.kind,
        // La placa del beat, si la hay: **los fondos son para usarse**. El
        // collage asoma alrededor y los bloques opacos sostienen las cifras, que
        // es como lo hace el canon. Los ficheros de `public/sfx/` ya existen,
        // así que el sonido de los movimientos se enciende: niveles bajos, la
        // voz manda.
        // **Y la que ELIGE el diseñador gana.** Esto ponia `placaDe()`
        // DESPUES de sus props, asi que una placa declarada no llegaba nunca:
        // el mismo dia que las catorce placas empezaron a viajar en el pedido
        // —para que se pudiera elegir— el codigo seguia imponiendo la del
        // `sirve`. Declarar sin poder aplicar es no declarar.
        //
        // `placaDe` se queda de respaldo, que es lo que era: la asignacion
        // pensada de antemano para ese beat.
        props: { ...b.props, sound: true,
                 placa: b.props?.placa ?? placaDe(slug, b.beat),
                 // **A cuadro completo la placa LLENA el cuadro.**
                 //
                 // El recorte geometrico —cuna, columna, esquina— es canon
                 // cuando la placa compone sobre un fondo de color: *«en el
                 // canon la fotografia nunca cubre el cuadro entero»*. Pero un
                 // tablero a `pleno` no tiene fondo de color detras: tiene el
                 // VIDEO. La diagonal dejaba ver lo que hubiera, y lo que hay
                 // depende de donde cayera el encuadre — en la sesion de noche,
                 // las rodillas.
                 //
                 // Jaime, viendolo: *«se ve feo ese tablero; el objetivo era
                 // mantener mi cara en el mismo espacio de mis pies, no abrir
                 // espacio para ver mi cara; mejor dejar el tablero sin
                 // video»*.
                 //
                 // Se aplica solo a `pleno`, y solo si el diseno no dijo otra
                 // cosa: los que acompanan siguen recortados, que ahi la placa
                 // convive con el plano en vez de sustituirlo.
                 recorte: b.props?.recorte
                   ?? ((b.props?.cubre ?? "pleno") === "pleno" ? "lleno" : undefined),
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
// **`figura` es el nombre de un dibujo, no una linea de copy.** Un panel sin
// `bloques` explicitos deriva sus rotulos de los props string, asi que
// `figura: "ceda"` acababa rotulando «ceda» en pantalla — el nombre interno de
// una senal de trafico, en versales, delante del espectador. Es el mismo
// accidente que el «430» de `duracion` en `TableroDeclarado`, y por la misma
// puerta: una clave escrita para otro consumidor tratada como si fuera texto.
//
// `sfx` y `camara` entran con ella: las tres las escribe quien compone para que
// las lea el motor, no la pantalla.
const NO_TEXTO = new Set(["familia", "zona", "cubre", "oro", "sound", "fondo",
                          "filete", "source", "paso", "entrada",
                          "figura", "sfx", "camara",
                          "recorte", "fuerza", "deriva", "placa"]);

export function armarPaneles(bs, reloj, tableros, captions) {
  return bs
    .map((b) => {
      const yaSon = Array.isArray(b.props?.bloques) ? b.props.bloques : null;
      const bloques = yaSon ?? Object.entries(b.props ?? {})
        .filter(([k, v]) => !NO_TEXTO.has(k) && typeof v === "string" && v.trim())
        .slice(0, 3)
        .map(([, v]) => ({ texto: v }));
      // **La placa tambien en el panel, no solo a pleno.** `SidePanel` sabe
      // pintarla desde hace tiempo —la mete detras del bloque al 50% para que
      // el collage asome sin comerse el texto— y esto no se la pasaba nunca:
      // una placa declarada en un tablero `panel` se perdia aqui.
      //
      // Quien compuso reel-01 lo vio y **se nego a declararla** por eso mismo,
      // que es lo correcto: declarar sin poder aplicar es la averia de la casa.
      // Va en UN bloque —el fuerte, o el primero—, no en los tres: tres
      // fotomontajes apilados es papel pintado, no collage.
      const placa = b.props?.placa;
      if (placa && bloques.length) {
        const i = Math.max(0, bloques.findIndex((x) => x.fuerte));
        bloques[i] = { ...bloques[i], placa };
      }
      return { beat: b.beat, bloques };
    })
    .filter((b) => b.bloques.length)
    .map((b) => {
      const inicio = reloj.anclaDe(b.beat);
      // Se busca **por etapa**, no por el frame en que arranca: ver arriba.
      const suyo = tableros.find((t) => t.beat === b.beat);
      if (suyo) {
        const dur = ADELANTO(b.bloques);
        const at = suyo.at - dur;
        return at < 0 ? null : { at, duration: dur, bloques: b.bloques };
      }
      const dur = reloj.duracionDe(b.beat);
      const tope = ADELANTO(b.bloques) + 3 * FPS;
      // Y si el diseno declaro cuando entra, manda eso: es la misma regla que
      // el tablero —arranca con la palabra— y el panel dice lo mismo antes.
      // **Y un panel no entra mientras un tablero sigue puesto.**
      //
      // `empujaTablero` desconflicta tableros contra tarjetas y nadie hacia lo
      // mismo con los paneles: el de una etapa entraba 0,8 s antes de que el
      // tablero de la anterior se retirase, y los dos se pintaban a la vez. Es
      // la tercera causa de «estan sobrepuestos en todos lados», y como dijo
      // quien compuso reel-02: *«no es colocacion, es que falta el empujon»*.
      //
      // Se empuja con la misma regla que ya existe, aplicada a los tableros que
      // ya estan colocados en vez de a las tarjetas.
      const at = empujaTablero(tableros)(_anclaDeclarada(b, reloj, captions) ?? inicio);
      return dur
        ? { at, duration: Math.min(dur, tope), bloques: b.bloques }
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


/**
 * El frame donde el tablero tiene que entrar, si el diseño lo declaró.
 *
 * `props.anclas` son segundos de la PIEZA MONTADA —lo que se oye—, que es la
 * misma referencia con la que se compuso. Se toma el primero: es cuando se dice
 * lo que el tablero nombra.
 */
function _anclaDeclarada(b, reloj, captions) {
  const a = b?.props?.anclas;
  const s = Array.isArray(a) ? a[0] : a;
  const seg = typeof s === "object" && s !== null ? (s.segundo ?? s.en) : s;
  // **Y si el ancla es TEXTO, se resuelve contra el corte de hoy.**
  //
  // Jaime, al ver que esto era lo unico que no se re-derivaba: *«hay una linea
  // de produccion, ¿por que no se deriva solo?»*.
  //
  // Porque `anclas` era el unico dato del diseno escrito en SEGUNDOS, y los
  // segundos se mueven. Todo lo demas esta expresado contra algo estable —los
  // tableros contra su etapa, los subtitulos contra la transcripcion, los
  // encuadres contra las escenas— y por eso sobrevive a que se corte.
  //
  // Es la regla que el propio Jaime fijo para los cortes: *«las anclas tienen la
  // funcion de establecer los lugares; si el video se edita o se corta, el ancla
  // cambia»*. `revision.ancla` la cumple desde hace semanas; el diseno no.
  //
  // Ahora un `anclas: "por cada 100 dolares"` se busca en los subtitulos y sale
  // donde esa frase suene HOY. Un numero sigue valiendo, y sigue quedandose
  // clavado: por eso lo dice la auditoria de `llega.py`.
  if (typeof seg === "string" && seg.trim() && Number.isNaN(Number(seg))) {
    const q = seg.trim().toLowerCase();
    const cue = (captions ?? []).find((c) =>
      String(c.text ?? "").toLowerCase().includes(q),
    );
    if (cue) {
      const inicio = reloj.anclaDe(b.beat);
      return cue.at >= inicio ? cue.at : inicio;
    }
    return null;
  }
  const n = Number(seg);
  if (!Number.isFinite(n) || n < 0) return null;
  const at = Math.round(n * FPS);
  // No se adelanta a la etapa: un tablero que entra antes de que su beat exista
  // se pinta sobre lo que dice otra cosa.
  const inicio = reloj.anclaDe(b.beat);
  return at >= inicio ? at : null;
}


/**
 * ¿Este trozo se pisa con alguno de los que ya ocupan el cuadro?
 *
 * El contraste es la tercera capa que toma el frame entero y la unica que no
 * pasaba por ningun empujon: en reel-02 se pintaba sobre la cabecera del tablero
 * que venia detras. Vive aqui, con las otras dos reglas de ocupacion, y no en el
 * spec: el spec arma, esto decide quien cede.
 */
export const sePisa = (x, ocupantes = []) =>
  !!x && ocupantes.some((o) => o.at < x.at + x.duration &&
                               o.at + o.duration > x.at);
