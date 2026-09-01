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
 * ## Dónde vive cada mitad
 *
 * Este fichero decidía el camino **y** leía la prosa de la escena **y** montaba
 * el gancho, tres cosas de tamaños muy distintos en 503 líneas. Ahora:
 *
 *     scripts/escena.mjs   la prosa de la escena -> lo que existe (figura,
 *                          efecto, copy, desaturación). Lo comparte `describir`
 *     scripts/capa.mjs     el reloj de una capa: frames, reparto y sonido
 *     scripts/gancho.mjs   la portada, que es la que es diferente
 *     scripts/caminos.mjs  los cinco caminos, el despacho y lo de pieza entera
 *
 * La superficie pública no se movió: lo que `reels-spec.mjs` importaba de aquí
 * se sigue importando de aquí.
 */
import { FPS, sonar } from "./capa.mjs";
import { desaturaDe, donde, figuraDe, rotuloDe, sonidoDe } from "./escena.mjs";
import { portada } from "./gancho.mjs";

export { GANCHO_S, GANCHO_CLAVE_S } from "./gancho.mjs";
export { copyDeclarado, esTipografico, figuraDe, rotuloDe, sonidoDe, sonidosMudos }
  from "./escena.mjs";

export const CAMINOS = {
  portada,

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
      const motion = sonidoDe(desc?.sonido, donde(desc), desc);
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
      const { at, duration, det } = ctx;
      // **Sin figura.** Jaime: *«en todos los planos sobra si no tiene un
      // proposito»*, y aqui no lo tiene por definicion: el camino cercano
      // existe porque **la cara es el argumento**. Metia una figura cada vez
      // que la descripcion mencionaba una palabra dibujable, que es precisamente
      // poner un grafico porque se puede y no porque haga falta.
      //
      // Si una etapa necesita figura, el paso de descripcion la manda a
      // `metafora`. Eso es una decision, no una coincidencia de vocabulario.
      //
      // Por eso este camino no mira `desc` ni `lado`: no le hacen falta, y
      // pedirlos era una invitacion a volver a usarlos.
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
      const fig = figuraDe(desc) ?? det.figura ?? null;
      const motion = sonidoDe(desc?.sonido, donde(desc), desc);
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

/**
 * Los cinco, por si alguien quiere recorrerlos sin conocer los nombres.
 *
 * **Y es la lista cerrada de `trato`**, no una copia de ella: `describir.mjs`
 * validaba la respuesta contra su propio array de cinco cadenas, así que un
 * camino nuevo aquí quedaba fuera de la validación y un camino borrado seguía
 * siendo admitido. Una lista escrita dos veces es dos listas.
 */
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
  return { capas, faltas: c.exige(capas, ctx) };
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
