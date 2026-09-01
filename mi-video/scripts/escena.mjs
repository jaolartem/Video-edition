/**
 * Lo que la escena **declaró**, traducido a lo que existe.
 *
 * Salió de `caminos.mjs`, que hacía dos cosas: decidir por qué camino va un
 * segmento y, antes de eso, leer la prosa que escribió quien compone. Son dos
 * responsabilidades y sólo una es de los caminos — la prueba es que este
 * vocabulario lo necesita también `describir.mjs`, que no monta nada: valida la
 * descripción en el momento de recibirla. Mientras vivió dentro de los caminos,
 * `describir.mjs` llevaba **su propia copia** de la regla del gancho
 * tipográfico: dos expresiones regulares con el mismo texto y ningún sitio
 * donde arreglarlas a la vez.
 *
 * ## La regla que gobierna todo este fichero
 *
 * **Se detecta, no se interpreta.** La skill lo dice: el `grafico` es el
 * encargo y no hay que reinterpretarlo. Así que esto es un vocabulario corto y
 * literal; cuando no reconoce nada **no inventa** — devuelve `null` y quien
 * llama registra la falta. Un pictograma inventado es un pictograma que nadie
 * puede discutir.
 *
 * El otro lado de la misma regla: tampoco se calla. Un sonido descrito que no
 * suena se apunta en `sonidosMudos` con su sitio, porque una descripción bien
 * escrita que no produce nada es peor que una que falla.
 */

/**
 * De la prosa de `grafico` a la figura que existe.
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
 *
 * **Y es la MISMA regla que exige `describir.mjs`** al recibir la descripción.
 * Estaba escrita dos veces, una en cada fichero: si alguien afinaba el
 * vocabulario en uno, el otro seguía admitiendo lo que el primero ya rechazaba.
 */
const ES_TIPO = /versales|el tipo es|la frase entera|solo texto|nada mas/i;

export const esTipografico = (grafico) => Boolean(grafico && ES_TIPO.test(grafico));

export const figuraDe = (grafico) => {
  if (!grafico) return null;
  for (const [re, fig] of FIGURAS) if (re.test(grafico)) return fig;
  return null;
};

/**
 * El copy que el gancho tipográfico pone en pantalla, **declarado, no deducido**.
 *
 * Regla de Jaime, y corrige lo que yo estaba haciendo: *«las escenas y tableros
 * las debe hacer un agente especializado en diseño; eso es editorial, no sale
 * con código»*. La primera versión de esto sacaba la palabra de la prosa de
 * `grafico` con una expresión regular — o sea código decidiendo qué dice el
 * plano que compite contra el pulgar. Eso es exactamente lo que no le toca.
 *
 * Lo que sí le toca es **leer lo que el diseño declaró** y negarse a inventar
 * cuando no hay nada. El copy vive en `escena_desc.tablero`, que es el mismo
 * sitio del que salen los tableros desde C-142: dato, no prosa, escrito por
 * quien compone y leído por quien monta.
 *
 * Qué arregla, y es el sitio más caro de la pieza: el bloque no traía texto
 * propio y `Reel.tsx` le pasaba `lineas[0]`, la primera línea del rótulo. El
 * segundo gancho visual **repetía el primero** — en reel-04 el rótulo decía
 * «NO ES POR / SER INMIGRANTE» y el bloque, encima y a la vez, «NO ES POR».
 */
export const copyDeclarado = (desc) => {
  const t = desc?.tablero;
  if (!t) return null;
  let d = t;
  if (typeof d === "string") {
    try {
      d = JSON.parse(d);
    } catch {
      return null;
    }
  }
  const txt = d?.props?.texto ?? d?.props?.titulo ?? d?.texto ?? null;
  return typeof txt === "string" && txt.trim() ? txt.trim().slice(0, 26) : null;
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

/** El sitio de una escena, para que una falta se pueda ir a mirar.
 *
 * Estaba escrito tres veces —una por cada camino que pide sonido— y las tres
 * veces igual. Tres copias de una expresión son tres sitios donde el día que
 * cambie el formato quedan dos mal.
 */
export const donde = (desc) =>
  `${desc?.video_slug ?? "?"} e${desc?.etapa_orden ?? "?"}`;

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
export const desaturaDe = (color) =>
  color === "apagar" ? 0.55 : color === "avivar" ? 1.15 : 1;
