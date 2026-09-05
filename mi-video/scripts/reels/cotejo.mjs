/**
 * **El cotejo: lo que se decidió, contra lo que se pintó.**
 *
 * Jaime, dos noches seguidas: *«los tickets que mandé no están resueltos, otra
 * vez se está renderizando lo que no está actualizado»*. Y la pista está en que
 * la causa fue distinta cada vez —una respuesta contestada tarde, un pedido
 * regenerado, un `split` que no casa—: el fallo no es ninguno de esos bugs, es
 * que **nadie comprobaba que lo corregido llegara al frame**.
 *
 * Este fichero es esa comprobación, y es una sola: por cada decisión escrita en
 * `escena_desc`, ¿aparece en el spec? Tiene exactamente la forma de la guarda
 * que ya existe en `reels-spec.mjs` —«el diseñador declaró N tableros y sólo M
 * llegan al render»—, que es la única que ha cazado esta familia de averías.
 * Comparar las dos cifras es lo único que la caza: mientras cada lado informe
 * de lo suyo, los dos parecen correctos.
 *
 * **Y no avisa: para la pieza.** Lo lee `puerta.mjs` y llama a `para()`, así que
 * una corrección que no llega a la pantalla deja la pieza fuera del render en
 * vez de salir al mundo sin ella. `REELS_VER=1` la sigue enseñando con los
 * motivos escritos, que es la puerta que Jaime se reservó.
 */

/** Comparar texto de pantalla es comparar en minúsculas y sin bordes. */
const baja = (t) => String(t ?? "").trim().toLowerCase();

/**
 * Los metacaracteres que `Corregida.tsx` mete **crudos** en un `new RegExp`.
 *
 * `texto.split(new RegExp(`(${palabra})`, "i"))` con una `palabra` que venga de
 * la base sin filtro: un `(`, un `+` o un `$` casan donde no deben o tumban el
 * render entero. El arreglo bueno es escapar allí; mientras eso viva en
 * `src/components/`, aquí no se deja salir un valor que lo rompa.
 */
const META = /[\\^$.*+?()[\]{}|]/;

/**
 * **Por qué esta corrección no se puede pintar**, o `null` si sí se puede.
 *
 * Una sola definición, dos lectores: `corregirLoDicho` la usa para no colocar lo
 * que no se lee, y `cotejar` para decir por qué la pieza no sale. Escrita dos
 * veces serían dos reglas con el mismo nombre, que es la avería que este
 * proyecto ya pagó cuatro veces con `limpio`/`norm`.
 */
export function noSePintaBien(dice, es) {
  const d = String(dice ?? "").trim();
  const e = String(es ?? "").trim();
  if (!d || !e) return "viene vacía por un lado";
  if (META.test(d))
    return `«${d}» lleva un metacarácter y \`Corregida.tsx\` lo mete crudo en un`
      + ` \`new RegExp\`: o casa donde no debe, o tumba el render`;
  /**
   * **Ampliar no es corregir.** `corrige_dice='obligaba a'` con
   * `corrige_es='obligaba a pagar'`: el `split` parte por «obligaba a» y el
   * `map` pega «obligaba a pagar» ENTERO, sin quitar el « pagar» que ya venía
   * detrás en el texto. Medido en reel-06 e6: «le obligaba a pagar pagar, pero
   * que usted», en oro y palpitando, 65 frames — 2,2 s de vídeo.
   *
   * No se puede arreglar recortando por código: qué palabra sobra es editorial.
   * Se devuelve a quien escribe el copy.
   */
  if (baja(e).includes(baja(d)))
    return `«${e}» CONTIENE «${d}»: eso no sustituye, amplía — y en pantalla sale`
      + ` la palabra repetida. Reescribe \`corrige_es\` para que sustituya`;
  return null;
}

/**
 * **Las correcciones de la base, una por una, contra los subtítulos del spec.**
 *
 * Tres cosas, y cada una tiene su vídeo detrás:
 *
 * 1. La corrección **no se puede pintar** — ampliación o metacarácter.
 * 2. La corrección **no llega a ningún frame**: `corrige_dice` no cabe entero en
 *    ninguna línea de CC. Medido en reel-02 e1, `'56 y se queda con 44'` contra
 *    un caption que dice «queda con 44.».
 * 3. La corrección llega **con otro valor**: el literal de `ads/frames.json`
 *    ganó por orden de llamada. Medido en reel-02 e6, donde la base dice
 *    «Ministro de Finanzas de Canadá» y el frame 1826 pintaba «FINANZAS».
 */
function correcciones(pieza, filas) {
  const motivos = [];
  const cues = pieza.captions.filter((c) => c.corrige);
  for (const f of filas) {
    if (!f.corrige_dice) continue;
    const mal = noSePintaBien(f.corrige_dice, f.corrige_es);
    if (mal) {
      motivos.push(`e${f.etapa_orden}: la corrección ${mal}.`);
      continue;
    }
    const cue = cues.find((c) => baja(c.corrige.dice) === baja(f.corrige_dice));
    if (!cue) {
      motivos.push(
        `e${f.etapa_orden}: la base corrige «${f.corrige_dice}» -> ` +
        `«${f.corrige_es}» y no llega a NINGÚN frame — esa frase no cabe entera ` +
        `en ninguna línea de CC. Escribe en \`corrige_dice\` las palabras que sí ` +
        `caben en una, que es donde se pinta.`,
      );
      continue;
    }
    if (String(cue.corrige.es) !== String(f.corrige_es)) {
      motivos.push(
        `e${f.etapa_orden}: el frame ${cue.at} pinta «${cue.corrige.es}» y la ` +
        `base dice «${f.corrige_es}». Manda la base: quita esa fila \`senala\` de ` +
        `\`ads/frames.json\`, que es un literal escrito a mano.`,
      );
    }
  }
  /**
   * **Y toda cue con corrección tiene que casar con su propio texto.**
   *
   * `Corregida.tsx` hace `texto.split(...)` y sustituye la parte que sea igual a
   * `dice`: si `dice` no está literal en el texto, `partes` sale de un solo
   * elemento, el `map` no sustituye nada y **el subtítulo sale sin corregir sin
   * dar una sola falta**. Es la comprobación que no existía en ningún sitio —ni
   * `puerta.mjs`, ni `guardas.mjs`, ni `verificar.py` miraban `corrige`—.
   */
  for (const c of cues) {
    if (!baja(c.text).includes(baja(c.corrige.dice))) {
      motivos.push(
        `el frame ${c.at} lleva corrección «${c.corrige.dice}» y su texto es ` +
        `«${c.text}»: el \`split\` de \`Corregida.tsx\` no la encuentra, así que ` +
        `el subtítulo sale SIN corregir y no lo denuncia nadie.`,
      );
    }
  }
  return motivos;
}

/**
 * **El `trato` congelado en el EDL contra el que decidió el diseñador.**
 *
 * El render no lee `escena_desc.trato`: lee una copia congelada en
 * `ads/<slug>/edl-sell.json`, y `caminos.mjs` despacha por ella. Medido en
 * reel-07: la base dice `tablero`/`cercano`/`metafora` en cinco etapas y el EDL
 * —escrito una hora antes— dice `diapositiva` en las cinco. Resultado: cero
 * tableros, cero paneles y siete subtítulos laterales, sin que nada lo dijera.
 *
 * **Y no se arregla leyendo el campo vivo y dejando el resto congelado.** En el
 * mismo `detalle` viajan `texto`, `figura`, `densidad` y `cobertura`, que son
 * medidas de ESE corte: coger el `trato` nuevo con el `texto` viejo hace una
 * quimera que además parece correcta. Si el EDL es viejo, la pieza es vieja —
 * se vuelve a cortar.
 *
 * `portada` y `cta` no cuentan: los decide el reloj, no el diseñador
 * (`trato.decidir` los devuelve antes de mirar lo decidido).
 */
function tratos(pieza, filas, slug) {
  const motivos = [];
  const porBeat = new Map(filas.map((f) => [Number(f.etapa_orden), f]));
  const dichos = new Set();
  for (const d of pieza.edl?.detalle ?? []) {
    const f = porBeat.get(Number(d.beat));
    if (!f?.trato || !d.trato || dichos.has(d.beat)) continue;
    if (d.trato === f.trato || d.trato === "portada" || d.trato === "cta") continue;
    dichos.add(d.beat);
    motivos.push(
      `e${d.beat}: el EDL congeló el trato «${d.trato}» y el diseñador decidió ` +
      `«${f.trato}». El render despacha por la copia del EDL, así que esa ` +
      `decisión no toca un solo frame: vuelve a cortar con ` +
      `\`python scripts/seleccionar.py ${Number(slug.slice(-2))}\`.`,
    );
  }
  return motivos;
}

/**
 * Los motivos por los que esta pieza **no está actualizada**. Vacío es que lo
 * decidido y lo pintado dicen lo mismo.
 */
export const cotejar = (pieza, filas, slug) => [
  ...correcciones(pieza, filas),
  ...tratos(pieza, filas, slug),
];

/**
 * **Lo que el diseñador declara y ninguna línea de React dibuja.**
 *
 * `escena_desc.componente` y `escena_desc.color` viajaban hasta el spec y morían
 * ahí: `Capas.tsx` no despacha el tipo «tablero», así que las 15 capas que lo
 * llevaban entraban en un `<Sequence>` con hijo `null`. El tablero que se ve
 * sale por otro sitio —`escena_desc.tablero.kind` -> `boards`—, y por eso las
 * dos declaraciones podían discrepar en 16 de 20 filas sin que nada fallara.
 *
 * Manda `tablero.kind`, que es el que dibuja; `componente` decide el `kind` sólo
 * cuando el diseño no lo declara (`describir-esquema.mjs`). Y `color` se queda
 * dicho y sin dibujante: se cuenta aquí, en una línea por pieza, en vez de
 * prometer un efecto que ningún frame tiene.
 */
export const sinDibujante = (filas) => {
  const n = filas.filter((f) => f.color && f.color !== "dejar").length;
  return n
    ? `${n} etapa(s) declaran \`color\` y ninguna línea lo pinta: hace falta que` +
      ` \`Capas.tsx\` despache la saturación del tablero (C-169).`
    : null;
};
