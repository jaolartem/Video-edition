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

import { cerrada } from "./biblioteca.mjs";

/**
 * De la prosa de `grafico` a la figura que existe.
 */
//: `FIGURAS` se retiro el 1 de septiembre. Era la tabla de expresiones
//: regulares que deducia la figura de la prosa; lo que dibuja la pieza lo
//: declara el paso de diseno. Una regla nueva quita codigo, no lo anade.

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

/**
 * La figura que se dibuja, **declarada por quien compone y no deducida**.
 *
 * Es la misma regla que ya gobierna el copy dos funciones mas abajo, y que Jaime
 * dio una vez para las dos: *«las escenas y tableros los debe hacer un agente
 * especializado en diseno; eso es editorial, no sale con codigo»*. Se aplico al
 * copy y no aqui, y la mitad que quedo suelta es la que se vio en pantalla.
 *
 * Lo que hacia: sacar una figura de la PROSA de `grafico` con una expresion
 * regular, aunque la etapa declarara otra cosa. En el reel-01 la palabra
 * «desvio» de la descripcion de la etapa 5 dibujo una bifurcacion abstracta
 * sobre el plano — la «Y» flotando en el segundo 42 que Jaime senalo: *«esa Y no
 * es un panel; el panel es figurativo, no abstracto»*. Nadie la habia decidido:
 * la puso una regex leyendo prosa.
 *
 * Ahora se lee de `escena_desc.tablero`, que es donde el paso de diseno escribe
 * lo que decidio, y **se devuelve `null` cuando no hay nada**. Un plano sin
 * figura es una decision legitima; inventarle una no lo es.
 */
//: Las diez que `Pictograma` sabe trazar. Un nombre fuera de esta lista **no
//: deja de dibujarse: dibuja otra cosa**, porque el `switch` tenia un `default`
//: con una flecha y la flecha es lo que salia. Es peor que el caso mudo de
//: `SUENAN` — alli faltaba el fichero y se oia el silencio; aqui la pieza
//: afirma en pantalla algo que nadie compuso (C-168).
export const DIBUJAN = new Set(["persona", "dos-personas", "alto", "ceda", "desvio",
                         "bifurcacion", "escalera", "flecha", "barras",
                         "serie"]);

/**
 * Lo que se declaro y no se puede trazar. Mismo trato que `sonidosMudos`: se
 * acumula y lo imprime `reels-spec.mjs`, que es quien tiene delante el reel y
 * la etapa para poder ir a arreglarlo donde vive.
 */
export const figurasSinDibujo = [];

/**
 * **La biblioteca de figuras puede estar CERRADA.** Jaime, 6-9-2026: *«hasta que
 * no tengamos una biblioteca de figuras decentes no las vamos a utilizar;
 * graficos y palabras, como tablero de clase»*. La pregunta la contesta
 * `scripts/biblioteca.mjs`, que es el unico sitio que la lee.
 */
const CERRADA = cerrada("figuras.json");

/** ¿Es un nombre que `Pictograma` traza, o es prosa que caeria en la flecha? */
export const dibujable = (fig, desc) => {
  if (typeof fig !== "string" || !fig.trim()) return null;
  const f = fig.trim();
  // **Y con la biblioteca cerrada no traza ninguna, ni las que existen.** No se
  // calla: cae por el mismo sitio que una figura inventada, asi que sale como
  // falta declarada con su reel y su etapa. Es la diferencia entre retirar una
  // decision y perderla.
  if (CERRADA) {
    figurasSinDibujo.push({ donde: donde(desc), dice: f.slice(0, 90),
                            cerrada: true });
    return null;
  }
  if (DIBUJAN.has(f)) return f;
  figurasSinDibujo.push({ donde: donde(desc), dice: f.slice(0, 90) });
  return null;
};

export const figuraDe = (desc) => {
  const t = typeof desc === "string" ? null : desc?.tablero;
  if (!t) return null;
  let d = t;
  if (typeof d === "string") {
    try {
      d = JSON.parse(d);
    } catch {
      return null;
    }
  }
  return dibujable(d?.props?.figura ?? d?.figura ?? null, desc);
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

//: Los siete que existen en `public/sfx/`. Un nombre fuera de esta lista no
//: tiene fichero, y `staticFile` **no comprueba que exista**: saldria mudo sin
//: un solo aviso, que es la peor forma de fallar (C-06).
export const SUENAN = new Set(["mark", "draw", "fork", "land", "type", "whoosh",
                        "glitch"]);


/**
 * El sonido de un movimiento: **declarado si se declara, deducido si no**.
 *
 * `desc.sonido` es prosa —«un roce grave y arrastrado cuando el bloque gris se
 * mete debajo de la segunda barra»— y esto la pasaba por una tabla de
 * expresiones regulares. Lo que la tabla no reconoce sale MUDO, y le paso a
 * reel-02 e6 y a reel-05 e8 en la misma corrida: descripciones correctas, bien
 * escritas, que no producen nada.
 *
 * Es la misma averia que tenia la figura y se arregla igual: **quien compone
 * declara el sfx por su nombre** en `tablero.props.sfx`, y la prosa queda para
 * lo que aun no lo declara. La regla de fondo la dio Jaime una vez para las dos:
 * *«eso es editorial, no sale con codigo»*.
 *
 * Lo que NO cambia: no se inventa un sonido. Si no hay declarado y la prosa no
 * casa, se anota en `sonidosMudos` y suena el silencio — porque el sonido sigue
 * al movimiento, y un sfx puesto a dedo es ruido sin movimiento que lo
 * justifique.
 */
export const sonidoDe = (sonido, donde = "", desc = null) => {
  const puesto = desc?.tablero
    ? (() => {
        try {
          const d = typeof desc.tablero === "string"
            ? JSON.parse(desc.tablero)
            : desc.tablero;
          const s = d?.props?.sfx ?? d?.sfx;
          return typeof s === "string" && SUENAN.has(s.trim()) ? s.trim() : null;
        } catch {
          return null;
        }
      })()
    : null;
  if (puesto) return puesto;
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


/**
 * El rotulo del gancho, **declarado por quien compone**. `null` si no lo declara.
 *
 * Misma regla que la figura y que el sfx, y por el mismo motivo: el copy que
 * sale en pantalla es editorial. Vuelve `{lineas, oro}`.
 *
 * **Y `oro` es la otra mitad de la declaracion**, no un extra: el canon dice
 * desde el 6-9-2026 que *«cual lleva el oro no es siempre la ultima: va en la
 * mitad que golpea»*, y no habia por donde decirlo — el render lo clavaba al
 * ultimo renglon. Se nombra por su texto o por su indice, y `null` es «la de
 * siempre». Es declarar sin implementar, que es la averia constante del
 * proyecto, cazada en el sitio donde vive la decision.
 */
export const rotuloDe = (desc) => {
  try {
    const d = typeof desc?.tablero === "string"
      ? JSON.parse(desc.tablero)
      : desc?.tablero;
    // `lineas` es como lo declara quien pone `kind: "Gancho"` (C-422).
    const r = d?.props?.rotulo ?? d?.rotulo
      ?? (d?.props?.lineas ? { lineas: d.props.lineas, oro: d.props.oro } : undefined);
    const suelto = Array.isArray(r) || typeof r === "string";
    const c = suelto ? r : r?.lineas;
    const ls = Array.isArray(c) ? c
      : (typeof c === "string" ? c.split(String.fromCharCode(10)) : []);
    const lineas = ls.map((x) => String(x).trim()).filter(Boolean);
    const o = suelto ? null : r?.oro;
    const i = typeof o === "number" ? o : lineas.indexOf(String(o ?? "").trim());
    return lineas.length ? { lineas, oro: i >= 0 && i < lineas.length ? i : null } : null;
  } catch {
    return null;
  }
};

/**
 * **Lo que se declaro y no llega a producirse, redactado en un solo sitio.**
 *
 * Dos accidentes con la misma forma: una descripcion correcta, bien escrita,
 * que no produce nada. El sonido que ninguna expresion de `SONIDOS` reconoce se
 * monta mudo; la figura que no esta en `DIBUJAN` se montaba **como una flecha**,
 * que es peor —el silencio se nota y una figura equivocada se aprueba (C-168)—.
 *
 * Se redacta aqui y no en `reels-spec.mjs` porque aqui es donde se acumula, y
 * porque estaba escrito alli dos veces: dos redacciones del mismo aviso son dos
 * sitios donde el dia que cambie el formato queda uno mal.
 *
 * No para el lote. Dice **que reel y que etapa**, que es lo que permite ir a
 * declararlo donde vive, en `escena_desc.tablero`.
 */
export const faltasDeclaradas = () => [
  ...figurasSinDibujo.map((f) => f.cerrada
    ? `${f.donde}: declara la figura «${f.dice}» y la biblioteca esta CERRADA ` +
      `desde el 6-9-2026 — «hasta que no tengamos una biblioteca de figuras ` +
      `decentes no las vamos a utilizar; graficos y palabras, como tablero de ` +
      `clase». Lo que dibuja esa etapa tiene que ser un dato —barras, reparto, ` +
      `acumulado, columnas comparadas— o tipografia. Ver src/brand/figuras.json.`
    : `${f.donde}: declara una figura que no se traza — «${f.dice}». No es un ` +
      `nombre del catalogo de \`Pictograma\`, asi que la escena se monta sin figura.`),
  ...sonidosMudos.map((s) =>
    `${s.donde}: describe un sonido que no suena — «${s.dice}». Ninguna ` +
    `expresion de SONIDOS lo reconoce, asi que la capa se monta muda.`),
];
