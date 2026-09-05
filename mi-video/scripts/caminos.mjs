/**
 * Los caminos de renderizado, y qué exige cada uno.
 *
 * Regla de Jaime, y es el motivo de que este fichero exista: *«creo que el
 * renderizado también debe ser por código, tres caminos y cada camino con sus
 * propias indicaciones; hay muchas decisiones sueltas que simplemente no se
 * están cumpliendo»*. Y acto seguido: *«dije tres pero son más, y
 * definitivamente el gancho es uno de ellos porque es diferente»*.
 *
 * ## Qué estaba suelto
 *
 * `trato.py` decidía el tratamiento de cada segmento y lo escribía en el EDL —
 * y **nadie lo leía**. El render sacaba sus tableros y sus paneles de
 * `TABLEROS[slug]` y `PANELES[slug]`, dos literales escritos a mano por pieza:
 * exactamente el `if (slug === …)` que el proyecto prohíbe. Así que la portada
 * salía como un plano cualquiera con subtítulo, y la queja era inevitable:
 * *«la escena inicial le faltaban ilustraciones y movimientos»*.
 *
 * ## Cómo se cumple aquí lo que antes se declaraba
 *
 * Cada camino trae dos cosas y las dos son código:
 *
 * - `capas(ctx)` — **qué pone en pantalla**, derivado de la descripción de la
 *   escena (`escena_desc`) y del segmento (`detalle` del EDL). No hay literal
 *   por pieza: si dos reels tienen la misma descripción, sale lo mismo.
 * - `exige(capas, ctx)` — **qué tiene que cumplirse**, devuelto como lista de
 *   faltas. `guardas.mjs` las lee y **para el lote**. Una indicación que sólo
 *   está escrita en un documento es una indicación que se incumple; una que
 *   devuelve una falta es una que no se puede incumplir sin enterarse.
 *
 * ## El gancho es distinto, y por eso va primero
 *
 * Los otros cuatro caminos acompañan lo que Jaime dice. El gancho **compite
 * contra el pulgar**: no tiene que explicar, tiene que impedir que el vídeo se
 * vaya. Por eso es el único que apila capas sobre la cara, el único con más de
 * una entrada por segundo y el único donde el subtítulo va en su forma grande.
 */

import { faltasDeCobertura } from "./lectura.mjs";

const FPS = 30;

/** El gancho son 5 s y el primero es el que decide. Igual que en `trato.py`. */
export const GANCHO_S = 5.0;
export const GANCHO_CLAVE_S = 1.0;

/**
 * La primera entrada, antes de esto. En frames.
 *
 * Doce frames son 0,4 s: lo que tarda el pulgar en decidir es ~1,3 s, así que
 * si la primera cosa que se mueve llega en el segundo 1, ya llegó tarde. El
 * plano puede estar quieto; la pantalla no.
 */
const PRIMERA_ENTRADA = 12;

/** Entradas mínimas dentro del gancho. Menos de esto no es maximalismo. */
const ENTRADAS_MIN = 3;

/**
 * De la prosa de `grafico` a la figura que existe.
 *
 * **Se detecta, no se interpreta.** La skill lo dice: el `grafico` es el
 * encargo y no hay que reinterpretarlo. Así que esto es un vocabulario corto y
 * literal; cuando no reconoce nada **no inventa una figura**, devuelve `null` y
 * el camino registra la falta. Un pictograma inventado es un pictograma que
 * nadie puede discutir.
 */
const FIGURAS = [
  // Dos cantidades enfrentadas. Es lo que mas piden las descripciones —«una
  // barra llena y, debajo, la de lo que queda a un tercio»— y es geometria
  // plana: rectangulos y un hueco. Va la primera porque «barra» tambien casa
  // con verbos de movimiento y no queremos que la gane «flecha».
  [/barra|dos cantidad|facturaci.n.*queda|lo que queda/i, "barras"],
  // Tres marcas en fila, tachadas una tras otra. Lo piden tres escenas del
  // lote con esas mismas palabras.
  [/tres .*(en fila|una tras otra|tachad)|en fila|una tras otra/i, "serie"],
  [/bifurcaci|dos camino|se divide|dos trayectoria|dos ruta/i, "bifurcacion"],
  [/escalera|peldan|peldañ|escalon|escalón/i, "escalera"],
  [/prohibi|alto\b|no se puede|puerta.*cerrad|cerrad[ao].*puerta/i, "alto"],
  [/ceda|advertenc|riesgo/i, "ceda"],
  [/desv[ií]o|rodeo|atajo/i, "desvio"],
  [/dos persona|socio|empleado|equipo/i, "dos-personas"],
  [/persona|dueñ|duen|empresari|sujeto/i, "persona"],
  [/flecha|sube|crece|asciende|cae\b|baja\b/i, "flecha"],
];

/**
 * Hay escenas cuyo grafico **es la tipografia**: *«la pregunta en versales sobre
 * negro; nada mas»*, *«la frase entera en versales; el tipo es la composicion»*.
 *
 * Eso no es una figura que falte: es una figura que la escena no quiere. Forzar
 * un pictograma ahi seria justo lo que la skill prohibe —reinterpretar el
 * encargo— asi que el gancho usa un bloque de tipo como segundo gancho visual y
 * el resultado cumple sin inventarse nada.
 */
const ES_TIPO = /versales|el tipo es|la frase entera|solo texto|nada mas/i;

export const esTipografico = (grafico) => Boolean(grafico && ES_TIPO.test(grafico));

export const figuraDe = (grafico) => {
  if (!grafico) return null;
  for (const [re, fig] of FIGURAS) if (re.test(grafico)) return fig;
  return null;
};

/**
 * De la prosa de `sonido` al efecto que existe en `src/brand/sfx.ts`.
 *
 * Mismo criterio: la descripción dice *«el golpe seco cuando la segunda barra
 * se detiene antes»* y eso es `land`, no un whoosh elegido a gusto. Si no
 * reconoce el movimiento devuelve `null`, y entonces la capa **no suena** — que
 * es la regla del proyecto: prohibido el sonido sin movimiento que lo
 * justifique, y también al revés, prohibido inventarle un sonido a un
 * movimiento que la escena no describió.
 */
const SONIDOS = [
  [/golpe|seco|se detiene|aterriza|remate|impacto/i, "land"],
  [/traz|dibuj|línea|linea|se escribe a mano/i, "draw"],
  [/tecle|letra a letra|se escribe/i, "type"],
  [/separa|bifurca|se abre|dos caminos/i, "fork"],
  [/marca|sella|pegatina|subray/i, "mark"],
  [/barrid|cruza|pasa de lado|entra de golpe/i, "whoosh"],
  [/distorsi|glitch|corte sucio/i, "glitch"],
];

/**
 * Lo que se describió y no sonó. Se acumula y lo lee `reels-spec.mjs`, que es
 * quien puede decirlo con el reel y la etapa delante.
 */
export const sonidosMudos = [];

export const sonidoDe = (sonido, donde = "") => {
  if (!sonido) return null;
  for (const [re, m] of SONIDOS) if (re.test(sonido)) return m;
  /**
   * **Un sonido descrito que no suena tiene que decirlo.**
   *
   * Esto devolvía `null` en silencio, y el propio contrato lo llevaba escrito
   * como deuda: *«texto libre: lo que `sonidoDe` no reconozca cae en silencio.
   * O es lista cerrada, o `sonidoDe` avisa»*. Se pagó al oír el reel-01
   * montado — Jaime: *«el tablero sin sonido»*, y después *«el sonido del
   * tablero deben ser las acciones animadas del tablero»*.
   *
   * Quien compone escribe frases como «zumbido corto ascendente mientras la
   * barra sube, un golpe metálico seco al cruzar el umbral». Si ninguna
   * expresión de `SONIDOS` la reconoce, la capa se monta muda **y nadie se
   * entera**: la descripción existe, está bien escrita, y no produce nada.
   *
   * No se inventa un sonido —eso rompería la regla de que el sonido sigue al
   * movimiento— pero tampoco se calla: se anota con su sitio.
   */
  sonidosMudos.push({ donde, dice: String(sonido).slice(0, 90) });
  return null;
};

/** `color` de la escena: `avivar`, `apagar` o `dejar`. Nunca por gusto. */
const desaturaDe = (color) =>
  color === "apagar" ? 0.55 : color === "avivar" ? 1.15 : 1;

/**
 * Reparte n entradas dentro de una ventana, empezando pronto y espaciándolas.
 *
 * No es decorativo que empiece en `PRIMERA_ENTRADA`: el gancho se pierde en el
 * primer segundo, así que la primera cosa que se mueve no puede esperar a que
 * la anterior termine. A partir de ahí, aire igual entre entradas.
 */
const reparte = (n, desde, hasta) => {
  const paso = (hasta - desde) / Math.max(1, n);
  return Array.from({ length: n }, (_, i) => Math.round(desde + paso * i));
};

const sonar = (motion, at) =>
  motion ? [{ tipo: "sonido", at, props: { motion } }] : [];

export const CAMINOS = {
  /**
   * **portada — el gancho.** Los primeros 5 s, *«de los que el primero es
   * clave»*.
   *
   * Indicaciones, y todas se comprueban abajo: cara y máxima expresividad, mucho
   * movimiento dentro de la toma, ganchos visuales múltiples, sonidos que
   * acompañan al título y a los subtítulos animados. *«Maximalismo coherente:
   * romper el patrón y generar curiosidad.»*
   *
   * Coherente es la palabra que hace el trabajo: apila, pero apila con la
   * paleta, la tipografía y las prohibiciones del canon. Nada de rebote ni
   * confeti — el maximalismo aquí es **densidad de entradas**, no blandura.
   */
  portada: {
    nombre: "gancho",
    manda: "toma",
    porque:
      "compite contra el pulgar, no explica: la única que apila sobre la cara",
    capas(ctx) {
      const { at, duration, desc, det, lado } = ctx;
      // **El gancho dura 5 s, no lo que dure el segmento.** Si la toma que abre
      // dura 2 s, las capas siguen sobre la escena siguiente hasta cerrar los 5:
      // el gancho es una ventana de la pieza, no una propiedad del corte.
      const fin = at + Math.round(GANCHO_S * FPS);
      void duration;
      const clave = at + Math.round(GANCHO_CLAVE_S * FPS);
      const tipo = esTipografico(desc?.grafico);
      const fig = tipo ? null : figuraDe(desc?.grafico);
      const motion = sonidoDe(desc?.sonido, `${desc?.video_slug ?? "?"} e${desc?.etapa_orden ?? "?"}`);
      const out = [];

      // 1 · El plano se mueve dentro de sí mismo. No es un plano fijo con cosas
      //     encima: la toma empuja. Va primero porque no necesita entrada.
      out.push({
        tipo: "punch",
        at,
        duration: fin - at,
        props: { desde: 1.0, hasta: 1.08 },
      });

      // 2 · El rótulo entra con movimiento —por bloques desde el lado libre—,
      //     no con un fundido. Un fundido no rompe ningún patrón.
      const tR = at + PRIMERA_ENTRADA;
      out.push({
        tipo: "rotulo",
        at: tR,
        duration: fin - tR,
        props: { lado, entrada: "bloque" },
      });
      out.push(...sonar("whoosh", tR));

      // 3 · La figura de la escena, entrando desde fuera del cuadro. Sólo si la
      //     descripción la nombra: el catálogo de `FIGURAS` no adivina.
      if (fig) {
        const [t1, t2] = reparte(2, clave, fin - Math.round(0.6 * FPS));
        out.push({
          tipo: "figura",
          at: t1,
          duration: fin - t1,
          props: { figura: fig, oro: true, lado, dura: fin - t1 },
        });
        out.push(...sonar("draw", t1));
        // 4 · Y el elemento geométrico que entra y sale — el segundo gancho
        //     visual, con el sonido que la escena describió para él.
        out.push({
          tipo: "remate",
          at: t2,
          duration: fin - t2,
          props: { lado, tinte: "gold" },
        });
        out.push(...sonar(motion ?? "land", t2));
      }

      // 3bis · El gancho tipografico. Mismo trabajo que la figura —segundo y
      //     tercer gancho visual dentro de los 5 s— pero con el material que la
      //     escena pidio: tipo, en versales, entrando por bloques.
      if (tipo) {
        const [t1, t2] = reparte(2, clave, fin - Math.round(0.6 * FPS));
        out.push({
          tipo: "bloque",
          at: t1,
          duration: fin - t1,
          props: { lado, tinte: "gold", entrada: "corte" },
        });
        out.push(...sonar("mark", t1));
        out.push({
          tipo: "remate",
          at: t2,
          duration: fin - t2,
          props: { lado, tinte: "navy" },
        });
        out.push(...sonar(motion ?? "land", t2));
      }

      // 5 · El subtítulo, en su forma grande. En el gancho el subtítulo no
      //     acompaña: es una de las capas que enganchan.
      out.push({
        tipo: "subtitulo",
        at,
        duration: fin - at,
        props: { forma: "grande", suena: "type" },
      });

      return out.map((c) => ({ ...c, camino: "portada", beat: det.beat }));
    },
    exige(capas, ctx) {
      const faltas = [];
      const entradas = capas.filter(
        (c) => c.tipo !== "sonido" && c.tipo !== "punch",
      );
      if (entradas.length < ENTRADAS_MIN)
        faltas.push(
          `el gancho lleva ${entradas.length} entradas y necesita ${ENTRADAS_MIN}:` +
            " «ganchos visuales múltiples»",
        );
      const primera = Math.min(...entradas.map((c) => c.at - ctx.at));
      if (!(primera <= PRIMERA_ENTRADA))
        faltas.push(
          `la primera entrada llega en el frame ${primera} y el primer segundo` +
            " es el que decide",
        );
      if (!capas.some((c) => c.tipo === "punch"))
        faltas.push("el gancho no se mueve dentro de la toma");
      if (
        !capas.some((c) => c.tipo === "subtitulo" && c.props.forma === "grande")
      )
        faltas.push("el subtítulo del gancho no va en su forma grande");
      // Cada movimiento suena. Se comprueba que no haya entrada muda salvo el
      // subtítulo, que trae su sonido dentro.
      for (const c of entradas) {
        if (c.tipo === "subtitulo") continue;
        if (
          !capas.some((s) => s.tipo === "sonido" && Math.abs(s.at - c.at) <= 2)
        )
          faltas.push(`la capa «${c.tipo}» del gancho entra sin sonido`);
      }
      if (!figuraDe(ctx.desc?.grafico) && !esTipografico(ctx.desc?.grafico))
        faltas.push(
          "la escena del gancho no describe ni figura dibujable ni composición" +
            ` de tipo: «${ctx.desc?.grafico ?? "sin descripción"}»`,
        );
      return faltas;
    },
  },

  /**
   * **tablero — el gráfico es el plano.** *«Los tableros son ideales para ideas
   * complejas»*, y el copy sale de la propia lectura: por ser exacta dice lo que
   * el libreto quería, palabra por palabra.
   */
  tablero: {
    nombre: "tablero",
    manda: "grafico",
    porque: "la idea es compleja y el espectador no puede rebobinar",
    capas(ctx) {
      const { at, duration, desc, det } = ctx;
      const motion = sonidoDe(desc?.sonido, `${desc?.video_slug ?? "?"} e${desc?.etapa_orden ?? "?"}`);
      return [
        {
          tipo: "tablero",
          at,
          duration,
          camino: "tablero",
          beat: det.beat,
          props: {
            componente: desc?.componente ?? null,
            grafico: desc?.grafico ?? null,
            texto: det.texto ?? "",
            desatura: desaturaDe(desc?.color),
            sound: true,
          },
        },
        ...sonar(motion, at).map((s) => ({
          ...s,
          camino: "tablero",
          beat: det.beat,
        })),
      ];
    },
    exige(capas, ctx) {
      const faltas = [];
      const t = capas.find((c) => c.tipo === "tablero");
      if (!t?.props.componente)
        faltas.push(
          `el tablero del beat ${ctx.det.beat} no dice qué componente lo dibuja`,
        );
      if (!t?.props.texto)
        faltas.push(
          `el tablero del beat ${ctx.det.beat} no trae su propio copy, y el` +
            " tablero es el plano",
        );
      return faltas;
    },
  },

  /**
   * **cercano — leído pero bien entregado.** *«Excepto si el delivery emocional
   * es especialmente bueno, en cuyo caso buscamos planos cercanos enfatizando la
   * emoción en la cara y animaciones que expliquen la idea.»*
   *
   * Aquí la cara es el argumento, así que la animación **no la tapa**: vive en
   * el hueco libre y punto.
   */
  cercano: {
    nombre: "cercano",
    manda: "toma",
    porque: "la cara es el argumento; la animación acompaña y no tapa",
    capas(ctx) {
      const { at, duration, desc, det, lado } = ctx;
      // **Sin figura.** Jaime: *«en todos los planos sobra si no tiene un
      // proposito»*, y aqui no lo tiene por definicion: el camino cercano
      // existe porque **la cara es el argumento**. Metia una figura cada vez
      // que la descripcion mencionaba una palabra dibujable, que es precisamente
      // poner un grafico porque se puede y no porque haga falta.
      //
      // Si una etapa necesita figura, el paso de descripcion la manda a
      // `metafora`. Eso es una decision, no una coincidencia de vocabulario.
      void desc;
      const out = [
        {
          tipo: "punch",
          at,
          duration,
          props: { desde: 1.06, hasta: 1.12 },
        },
      ];
      return out.map((c) => ({ ...c, camino: "cercano", beat: det.beat }));
    },
    exige(capas, ctx) {
      const faltas = [];
      if (capas.some((c) => c.tipo === "tablero"))
        faltas.push(
          `el beat ${ctx.det.beat} es cercano y le entró un tablero encima`,
        );
      if (!capas.some((c) => c.tipo === "punch"))
        faltas.push(
          `el beat ${ctx.det.beat} es cercano y no cierra sobre la cara`,
        );
      return faltas;
    },
  },

  /**
   * **metafora — Jaime en cuadro y la figura acompaña.** *«Cuando hablamos del
   * dentista, una ilustración de un odontólogo puede ser útil; o los símbolos de
   * prohibido; o un camino que se divide en dos cuando decimos usted no va a X.»*
   *
   * No sustituyen el plano: lo acompañan. Por eso la figura va al lado libre y
   * no hay punch que compita con ella.
   */
  metafora: {
    nombre: "metáfora",
    manda: "toma",
    porque: "la figura acompaña el plano, no lo sustituye",
    capas(ctx) {
      const { at, duration, desc, det, lado } = ctx;
      const fig = figuraDe(desc?.grafico) ?? det.figura ?? null;
      const motion = sonidoDe(desc?.sonido, `${desc?.video_slug ?? "?"} e${desc?.etapa_orden ?? "?"}`);
      const t = at + Math.round(0.5 * FPS);
      const out = [];
      if (fig) {
        out.push({
          tipo: "figura",
          at: t,
          duration: duration - Math.round(0.5 * FPS),
          props: { figura: fig, oro: false, lado, dura: duration },
        });
        out.push(...sonar(motion ?? "draw", t));
      }
      return out.map((c) => ({ ...c, camino: "metafora", beat: det.beat }));
    },
    exige(capas, ctx) {
      // Una metáfora sin figura es una diapositiva con otro nombre. No para el
      // lote —la cinta manda— pero se dice, que es lo que no pasaba antes.
      return capas.some((c) => c.tipo === "figura")
        ? []
        : [
            `el beat ${ctx.det.beat} va por metáfora y no hay figura que dibujar:` +
              ` «${ctx.desc?.grafico ?? "sin descripción"}»`,
          ];
    },
  },

  /**
   * **diapositiva — lo demás.** El subtítulo animado entra por un lado y sale
   * por otro. Es el camino de reposo: sin él todo sería gancho y nada
   * destacaría.
   */
  diapositiva: {
    nombre: "diapositiva",
    manda: "toma",
    porque: "el camino de reposo: sin reposo el gancho no destaca",
    capas(ctx) {
      const { at, duration, det, lado } = ctx;
      return [
        {
          tipo: "subtitulo",
          at,
          duration,
          camino: "diapositiva",
          beat: det.beat,
          props: { forma: "lateral", lado, suena: null },
        },
      ];
    },
    exige() {
      return [];
    },
  },
};

/** Los cinco, por si alguien quiere recorrerlos sin conocer los nombres. */
export const NOMBRES = Object.keys(CAMINOS);

/**
 * Las capas de un segmento, y sus faltas. **Un `trato` desconocido es una
 * falta, no un silencio**: si `trato.py` inventa un sexto camino, aquí se ve.
 */
export const construir = (ctx) => {
  const c = CAMINOS[ctx.det.trato];
  if (!c)
    return {
      capas: [],
      faltas: [
        `el beat ${ctx.det.beat} pide el camino «${ctx.det.trato}», que no existe`,
      ],
    };
  const capas = c.capas(ctx);
  /**
   * **La cobertura de los tramos leídos es transversal a los cinco caminos**, y
   * por eso se comprueba aquí y no dentro de cada uno. Instrucción T-01: si en
   * el audio se está leyendo, ese tramo va cubierto con tablero. Ver
   * `lectura.mjs`, que es donde vive el criterio.
   */
  return {
    capas,
    faltas: [...c.exige(capas, ctx), ...faltasDeCobertura(ctx.det.trato, ctx.det)],
  };
};

/**
 * Lo que se comprueba sobre la pieza entera y no cabe en un segmento.
 *
 * **El gancho es uno.** Jaime: *«definitivamente el gancho es uno de ellos
 * porque es diferente»* — y diferente en singular. Dos portadas en una pieza no
 * son dos ganchos: son un gancho y una escena que se cree gancho, compitiendo
 * por la atención en los primeros segundos. Salía en reel-04 y reel-05 y no lo
 * veía nadie.
 */
export const revisarPieza = (capas) => {
  const faltas = [];
  const ganchos = new Set(
    capas.filter((c) => c.camino === "portada").map((c) => c.beat),
  );
  if (ganchos.size > 1)
    faltas.push(
      `la pieza lleva ${ganchos.size} ganchos (beats ${[...ganchos].join(", ")})` +
        " y el gancho es uno",
    );
  return faltas;
};
