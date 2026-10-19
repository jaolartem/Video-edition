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
import fs from "node:fs";
import { FPS } from "./reloj.mjs";
import { anclaDeclarada, cuandoSeDice, tiemposDe, ventanaDeclarada } from "./anclas.mjs";
import { empujaTablero } from "./ocupacion.mjs";
import { ADELANTO, SOLAPE, duracionTablero } from "./lectura.mjs";
import { placaDe, precioVigente, sujetoDe } from "./material.mjs";
import { HAY_CIFRA } from "./paneles.mjs";
import { tratoDelSujeto } from "../imagen.mjs";

/**
 * **La escalera de precios se DERIVA; en un tablero no se escribe.**
 *
 * Instrucción de lote de Jaime (#64, 4-9-2026): *«el precio en pantalla está mal
 * y vencido»* — el escalón sale de `precioVigente()`, no de un literal. El CTA ya
 * lo cumplía (`reels/copy.mjs`), y el tablero que enseña los peldaños uno debajo
 * de otro no tenía por dónde: escribir «$30» y «$40» a mano en
 * `escena_desc.tablero` es la misma avería un piso más abajo, y ahí sin fecha de
 * caducidad a la vista.
 *
 * Quien compone declara `escalera: true` y aquí se sustituye por `escalones`, ya
 * redactados en `scripts/dominio/precio.py :: vigente`. Redactarlos aquí sería la
 * segunda redacción del mismo peldaño, que es como se separan dos rótulos.
 *
 * Se pregunta **una vez por corrida**: cada llamada lanza un subproceso Python.
 */
const ESCALERA = precioVigente();

/**
 * Sustituye `escalera: true` por los peldaños de hoy.
 *
 * Si ya no hay escalón vigente la clave **se retira y se dice**: dejarla puesta
 * rotularía «true» en versales, que es el accidente del «430» de
 * `TableroDeclarado` por la misma puerta. Y una tarifa cerrada en pantalla es
 * peor que ninguna.
 */
const conEscalera = (props, donde, faltas) => {
  if (props?.escalera !== true) return props;
  const { escalera: _pide, ...resto } = props;
  if (!ESCALERA?.escalones?.length) {
    faltas.push(
      `${donde}: el tablero pide la escalera de precios y ya no hay escalón ` +
      `vigente en la tabla \`precio\`. Sale sin ella — una tarifa cerrada en ` +
      `pantalla es peor que ninguna.`,
    );
    return resto;
  }
  return { ...resto, escalones: ESCALERA.escalones };
};


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
export function armarTableros(
  bs, { slug, reloj, duracion, empuja, captions, desc = {}, faltas = [] },
) {
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
      const vent = ventanaDeclarada(b, reloj, captions);
      const at = empuja(vent?.at ?? anclaDeclarada(b, reloj, captions)
        ?? reloj.anclaDe(b.beat));
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
      let dur = Math.min(suyo + SOLAPE, fin - at,
        vent?.fin > at ? vent.fin - at : Infinity);
      // **Y la pieza no acaba tapada por un tablero que ya dijo lo suyo** (C-478).
      // Techo de reel-13 e6 anclaba la cifra y el alcance a la voz, pero duraba
      // la etapa entera y llegaba al último fotograma: él no volvía a verse en
      // «…porque no tenía la información completa». Si llega al final y tiene
      // anclas, se retira tres segundos después de la última. Un tablero que no
      // llega al final no cambia: ahí lo retira la etapa siguiente.
      const tq = tiemposDe(b.props?.anclas, at, captions);
      const ultimo = tq ? Math.max(0, ...Object.values(tq).flat().filter(Number.isFinite)) : 0;
      if (ultimo && at + dur >= fin - SOLAPE && ultimo + 3 * FPS < dur) dur = ultimo + 3 * FPS;
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
        // La placa de la pieza: **los fondos son para usarse**. El collage
        // asoma alrededor y los bloques opacos sostienen las cifras, que es
        // como lo hace el canon. Los ficheros de `public/sfx/` ya existen, así
        // que el sonido de los movimientos se enciende: niveles bajos, la voz
        // manda.
        // **Y la que ELIGE el diseñador gana.** Esto ponia `placaDe()`
        // DESPUES de sus props, asi que una placa declarada no llegaba nunca:
        // el mismo dia que las catorce placas empezaron a viajar en el pedido
        // —para que se pudiera elegir— el codigo seguia imponiendo la asignada.
        // Declarar sin poder aplicar es no declarar.
        //
        // `placaDe` se queda de respaldo y **es de la pieza, no del beat**:
        // Jaime, *«es un FONDO de tablero por reel»*. Que gane la declarada no
        // abre la puerta a dos suelos en una misma pieza — eso lo para
        // `reels/fondo.mjs`, que compara lo que acaba en pantalla.
        // `conEscalera` va en el spread de entrada, no después: lo que sustituye
        // es una declaración de quien compone, así que tiene que llegar antes de
        // que nadie lea los props — y lo que el motor añade abajo sigue mandando
        // sobre ella, como hasta ahora.
        props: { ...conEscalera(b.props, `${slug} e${b.beat}`, faltas),
                 sound: true,
                 // Las casillas de un tablero también se resuelven cuando se
                 // dicen: sólo los paneles lo hacían, y reel-04 e5 salía sin tachar.
                 ...(Array.isArray(b.props?.casillas)
                   ? { casillas: cuandoSeDice(b.props.casillas, at, captions) } : {}),
                 // Y cada campo anclado, cuando se dice (C-442).
                 ...(tiemposDe(b.props?.anclas, at, captions)
                   ? { tiempos: tiemposDe(b.props.anclas, at, captions) } : {}),
                 placa: b.props?.placa ?? placaDe(slug),
                 // **Sobre collage su recorte es pegatina, no cuadro.** Jaime,
                 // 11-9: el cuadro es de los tableros formales. Desde C-436
                 // todo tablero de estas piezas lleva placa, y el cuadro se
                 // devolvía en cada visto (reel-10 e3, reel-13 e5; C-453).
                 ...(b.props?.sujeto_forma === "cuadro" && (b.props?.placa ?? placaDe(slug))
                   ? { sujeto_forma: "pegatina" } : {}),
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
                 // **Él dentro del tablero: el fichero y el tratamiento los pone
                 // el spec, no quien compone.**
                 //
                 // El diseño declara UNA cosa —`sujeto`, o sea de qué lado va—
                 // y de ahí sale todo lo demás: el recorte lo produce
                 // `dominio/sujeto.py` con su nombre de convención, y el
                 // tratamiento sale de `escena_desc.color`, que es el arco
                 // emocional. *«En color o en sepia, depende del arco»* — así
                 // que pedirlo dos veces sería dejar que se contradigan.
                 ...(b.props?.sujeto
                   ? { sujeto_src: sujetoDe(slug, b.beat) ?? undefined,
                       // **Y sale del instante que hay debajo del tablero, con
                       // su voz** (C-493). El recorte cubre la etapa entera y
                       // empezaba en su frame 0, desfasado de la voz (C-451).
                       // `sujeto_desde` lo sacaba de otro momento o lo congelaba
                       // (C-459, C-485), y Jaime, 14-9: *«la cara es un activo
                       // solo cuando habla y expresa, nunca puede ser un
                       // estiquer»* — *«pásalos todos a video hablando»*.
                       sujeto_trim: Math.max(0, Math.round(at - reloj.anclaDe(b.beat))),
                       sujeto_css: tratoDelSujeto(desc?.[b.beat]?.color,
                                                  b.props?.sujeto_color).css }
                   : {}),
                 duracion: dur },
      };
    })
    .filter((b) => {
      // **Un tablero que lo pide y no tiene recorte se dice.** Sin esto sale
      // igual, sin él dentro y sin avisar: exactamente la avería de la casa —
      // una decisión declarada que se descarta aguas abajo en silencio.
      if (b.props.sujeto && !b.props.sujeto_src) {
        faltas.push(
          `${slug}: el tablero del beat ${b.beat} lleva a Jaime dentro y no hay` +
            ` recorte en public/recorte/${slug}-e${b.beat}.webm — falta la` +
            ` pasada de scripts/dominio/sujeto.py sobre este corte.`,
        );
      }
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
//
// `volumen` es de la misma clase que `figura`: el nombre de una animación del
// catálogo de `src/brand/volumenes.json`, escrito para `SidePanel` y no para la
// pantalla. Sin esta línea el panel rotularía «compuerta» en versales.
// `eje` es de la misma clase que `entrada` y `zona`: la descripcion de un
// movimiento, escrita para quien compone. Sin esta linea el panel de reel-02 e10
// rotulaba en pantalla los 112 caracteres de «una sola linea horizontal: su
// marca muy adelantada, la de usted en el arranque, y la linea sigue fuera de
// cuadro». Es el mismo accidente que «ceda» y que el «430», por la misma puerta.
//
// **Y lo que va al PIE no es un bloque del panel**, que es la misma clase por la
// puerta contraria: `condicion` es texto de cumplimiento —hasta 190 caracteres—
// escrito para la línea de debajo, no para una cinta de 24. Mientras el panel
// tuvo tres rótulos delante nunca llegó al `slice(0, 3)`; en cuanto una lámina
// se lleva los rótulos —el reparto de reel-02 e1 deja uno— `condicion` sube al
// segundo puesto y **tumba el render**, porque `assertShort(…, "panel")` son 24.
//
// La lista de lo que va al pie ya existe y la escribe `reels/cifras.json`: es la
// misma con la que `cifrasDe` decide qué NO cuenta como cifra rotulada. Se lee
// de ahí y no se copia — dos listas de lo mismo divergen a la primera.
const CIFRAS = JSON.parse(
  fs.readFileSync(new URL("./cifras.json", import.meta.url), "utf8"),
);
const AL_PIE = CIFRAS.al_pie;

const NO_TEXTO = new Set(["familia", "zona", "cubre", "oro", "sound", "fondo",
                          "filete", "source", "paso", "entrada", "eje",
                          "figura", "sfx", "camara", "volumen",
                          "recorte", "fuerza", "deriva", "placa",
                          // **Y `anclas` es un puntero al transcript, no copy.**
                          // Desde que un panel puede arrancar con la palabra, su
                          // ancla puede ser TEXTO —«de cada 100 dólares»— y
                          // entonces cae en la derivación de rótulos y sale en
                          // versales sobre el plano. Los tres paneles que ya la
                          // declaraban la traían en segundos y por eso no se
                          // veía: un número no pasa el `typeof v === "string"`.
                          "anclas",
                          ...AL_PIE,
                          // **Y la lista común de lo que no es copy** (C-464):
                          // `lado: "arriba"` salía como bloque «ARRIBA» en el
                          // panel de reel-11 e2 porque esta copia no lo tenía.
                          ...CIFRAS.no_es_texto]);

/**
 * **Un prop cuyo valor es el NOMBRE de otro prop es un puntero, no copy.**
 *
 * `NO_TEXTO` es una lista de nombres y va a la zaga: ya se le escaparon `figura`
 * («ceda» rotulado en versales), `duracion` (el «430» de `TableroDeclarado`),
 * `eje` (112 caracteres de descripción de movimiento) y `volumen`. La quinta fue
 * `tachado: "creencia"`, y el panel de reel-02 e5 salió rotulando **CREENCIA**
 * como tercer bloque: el nombre interno de un campo, en pantalla, delante del
 * espectador.
 *
 * Añadir el nombre número cinco a la lista arregla ese caso y espera al sexto.
 * Esto arregla la clase: si el valor de un prop coincide con la clave de otro
 * prop del mismo tablero, ese prop está señalando a un hermano — quien compone
 * lo escribe para el motor, y el motor no lo rotula.
 */
const ES_PUNTERO = (props) => {
  const claves = new Set(Object.keys(props ?? {}));
  return ([, v]) => typeof v === "string" && claves.has(v.trim());
};

/**
 * **Los bloques de texto que dibuja un panel.** Una sola regla para el montaje
 * (`armarPaneles`) y para la puerta del diseño (`scripts/dibujable.mjs`), que
 * comprueba cada uno contra el tope `panel` de `src/brand/copy.ts` al llegar la
 * respuesta (C-572): reel-18 murió en el render por un bloque de 25 caracteres.
 */
export const bloquesDePanel = (props) => {
  if (Array.isArray(props?.bloques)) return props.bloques;
  if (Array.isArray(props?.casillas)) return [];
  const puntero = ES_PUNTERO(props);
  // **Una linea, un bloque.** El disenador escribe los renglones con un salto
  // de linea dentro de un mismo texto, y el tope de 24 es del bloque entero:
  // «A MI TAMBIEN / ME DA MIEDO.» son dos renglones de 12 y morian como un
  // bloque de 25 (C-572).
  return Object.entries(props ?? {})
    .filter(([k, v]) => !NO_TEXTO.has(k) && typeof v === "string" && v.trim())
    .filter((e) => !puntero(e))
    .flatMap(([, v]) => v.split(/\r?\n/).map((x) => x.trim()).filter(Boolean))
    .slice(0, LINEAS_PANEL)
    .map((texto) => ({ texto }));
};

/** Cuantos renglones caben en un panel: los de una firma, nombre mas titulo. */
export const LINEAS_PANEL = 4;

// El tope de un bloque de panel, leido de donde lo declara el componente
// (`src/brand/copy.ts`), no copiado aqui (C-572).
const TOPE_PANEL = Number((fs.readFileSync("src/brand/copy.ts", "utf8")
  .match(/panel:\s*(\d+)/) || [])[1] || 24);

/**
 * **Los bloques de panel que pasan del tope**, que es lo que `SidePanel` mide
 * con `assertShort` y tumba el render. Lo preguntan la puerta del diseño
 * (`dibujable.mjs`) y la de antes del render (`base.tablerosDe` → `rompe`):
 * con sólo la primera, un diseño aceptado antes de C-572 llegaba al render y
 * moria en el fotograma 150 —reel-20 y reel-22, cinco veces cada una— (C-581).
 */
export const panelLargo = (props) => (props?.cubre === "panel" ? bloquesDePanel(props) : [])
  .filter((b) => String(b?.texto ?? "").length > TOPE_PANEL)
  .map((b) => `panel: «${b.texto}» tiene ${String(b.texto).length} caracteres y el`
    + ` maximo es ${TOPE_PANEL}; partelo en otro bloque o acortalo`);

export function armarPaneles(bs, reloj, tableros, captions) {
  return bs
    .map((b) => {
      // **La lámina del panel, cuando el diseño la declara.**
      //
      // Con `figuras.json` y `volumenes.json` cerradas —*«gráficos y palabras,
      // como tablero de clase»*— un panel se quedó sin nada que dibujar: los
      // cuatro de reel-04 salieron como bloques negros apilados en una esquina,
      // tres formas declaradas distintas con el mismo aspecto, porque
      // `repartirPorCubre` manda el `panel` por aquí y aquí se tira el `kind`.
      //
      // `casillas` va APARTE de `bloques` porque no son lo mismo: la tira de
      // días con la fecha sellada lleva además sus tres renglones debajo. Ver
      // `src/components/Casillas.tsx`.
      const casillas = Array.isArray(b.props?.casillas) ? b.props.casillas : null;
      // **La otra lámina de la misma instrucción: el gráfico de datos.** Cerrada
      // la biblioteca, lo que entra son *«barras, repartos, acumulados, columnas
      // comparadas — y palabras»*; `casillas` pone las palabras a escuadra y esto
      // pone el dato. Es un objeto, así que nunca cae en la derivación de
      // rótulos: lo que iba a pasar sin esta línea es que no llegara a ningún
      // sitio y el panel volviera a decir con letras lo que la barra hace ver.
      const reparto = b.props?.reparto?.porciones?.length
        ? b.props.reparto
        : null;
      const bloques = bloquesDePanel(b.props);
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
      // **Y la animación del panel viaja con él.** `cubre` viaja también: no es
      // cromo aquí, es lo que distingue un panel —que ilustra, y por eso tiene
      // que moverse— de una banda de pie, que es un rótulo. Lo lee la puerta.
      return { beat: b.beat, bloques,
               casillas: casillas ?? undefined,
               reparto: reparto ?? undefined,
               eje: b.props?.eje ?? undefined,
               // **Y el ancla del panel, que estaba declarada y no llegaba.**
               // `_anclaDeclarada` lee `b.props.anclas`, y en la segunda vuelta
               // este objeto ya no tiene `props`: un panel no podía arrancar con
               // la palabra por mucho que lo declarase.
               anclas: b.props?.anclas ?? undefined,
               // El movimiento con el que entra cada casilla lo declara quien
               // compone, igual que el del tablero: `Casillas` lo emite en el
               // frame en que la casilla se mueve.
               sfx: b.props?.sfx ?? undefined,
               volumen: b.props?.volumen ?? undefined,
               // **El pie de cumplimiento viaja con el panel.** `source` estaba
               // en `NO_TEXTO` —bien, no es copy de pantalla— y ahi se quedaba:
               // el panel de reel-02 e1 enseñaba «SE VA $54» y «LE QUEDA $46»
               // con la fuente declarada en su tablero y ningun sitio por donde
               // llegar al render. Declarar sin poder aplicar es la averia de
               // la casa; quien lo exige ahora es `paneles.mjs`.
               //
               // **Y viaja solo si hay cifra que respaldar.** `source` sirve
               // para dos cosas distintas: el pie que va en pantalla y la nota
               // del que compone diciendo por que NO hay cifra —«sin cifra: no
               // rotula ninguna cantidad…»—. La segunda esta escrita para quien
               // compone, no para el espectador, y pasarla como pie es el mismo
               // accidente que el «ceda» de `figura` y el «430» de `duracion`:
               // un valor de un consumidor tratado como si fuera texto. Lo que
               // convierte un `source` en pie es que el panel ensene un digito.
               // **Y un reparto SIEMPRE enseña cifras**: las rotula la propia
               // barra, así que el pie es obligatorio aunque los rótulos que
               // queden al lado no lleven un dígito. Sin esta mitad, mover el
               // «$54 / $46» de los bloques a la barra se llevaba por delante la
               // atribución — la cifra en pantalla y su fuente en la base.
               fuente: bloques.some((x) => HAY_CIFRA.test(x.texto)) || reparto
                 ? b.props?.source ?? undefined
                 : undefined,
               cubre: String(b.props?.cubre ?? "panel") };
    })
    // **Un panel existe si tiene algo que poner en pantalla**, y desde que la
    // lámina es una vía propia eso ya no son sólo los rótulos: un panel de sólo
    // casillas —cinco síntomas que se tachan— se caía aquí sin decir nada.
    .filter((b) => b.bloques.length || b.casillas?.length)
    .map((b) => {
      const inicio = reloj.anclaDe(b.beat);
      // **Lo que hay que leer son las dos vías juntas.** `ADELANTO` reparte
      // 0,75 s por bloque más medio segundo, y contando sólo los rótulos un
      // panel de cinco casillas se quedaba con medio segundo para construirse.
      // Las porciones del reparto cuentan igual: cada una entra con su cifra y
      // su rótulo, y son lo que hay que leer. Contando sólo el bloque que las
      // acompaña, el panel de reel-02 e1 se retiraba 1,3 s después de acabar de
      // construirse.
      // Y cuentan las que se LEEN: las casillas anónimas de una tira de días no
      // dicen, cuentan, y sumarlas pediría siete tiempos de lectura por siete
      // cuadrados iguales.
      const leible = [...b.bloques, ...(b.casillas ?? []),
                      ...(b.reparto?.porciones ?? [])]
        .filter((x) => x.texto || x.dato || x.rotulo);
      // Se busca **por etapa**, no por el frame en que arranca: ver arriba.
      const suyo = tableros.find((t) => t.beat === b.beat);
      if (suyo) {
        const dur = ADELANTO(leible);
        const at = suyo.at - dur;
        return at < 0 ? null : { ...b, at, duration: dur,
                                 casillas: cuandoSeDice(b.casillas, at, captions) };
      }
      const dur = reloj.duracionDe(b.beat);
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
      const at = empujaTablero(tableros)(anclaDeclarada(b, reloj, captions) ?? inicio);
      const casillas = cuandoSeDice(b.casillas, at, captions);
      /**
       * **Una lámina anclada a la voz dura hasta la última que se dice.**
       *
       * «Lo que se tarda en leer más tres segundos» es el tope correcto para una
       * pila de rótulos: dice lo suyo y devuelve el cuadro. Una lámina cuyas
       * casillas se tachan cuando se dicen no puede irse antes de la última — en
       * reel-04 e5 las cinco se resuelven a lo largo de 10 s de voz y el panel se
       * retiraba a los 7,3, así que el sello del remate no llegaba a salir.
       *
       * Dos segundos después de la última: lo que cuesta leer lo que acaba de
       * quedar en pantalla. Y por eso la etapa deja de ser el techo: quien manda
       * es el transcript, que es contra lo que se ancló.
       */
      const ultima = Math.max(0, ...(casillas ?? []).map((c) => c.en ?? 0));
      const pide = Math.max(ADELANTO(leible) + 3 * FPS,
                            ultima ? ultima + 2 * FPS : 0);
      return dur
        ? { ...b, at, casillas,
            duration: ultima ? pide : Math.min(dur, pide) }
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


