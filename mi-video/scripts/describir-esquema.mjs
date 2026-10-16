/**
 * **El esquema de la descripción: qué tiene que traer, y qué se rechaza.**
 *
 * Es la tercera de las cuatro condiciones que el proyecto pone a un paso de IA:
 * *«la salida es un esquema fijo, validado al recibirla; lo que no encaja se
 * rechaza, no se arregla a mano»*. Vivía dentro de `describir.mjs`, mezclado
 * con el pedido y con el bucle del lote, y por eso pudo tener **su propia copia
 * de dos listas cerradas** que ya existían en otro sitio:
 *
 * - `trato` repetía los cinco caminos de `caminos.mjs`. Un camino nuevo allí
 *   quedaba fuera de esta validación; uno borrado se seguía admitiendo aquí.
 * - `componente` repetía las seis formas de `KIND_DE`, que es la tabla que dice
 *   qué dibuja cada una. Podían separarse: un componente admitido sin `kind`
 *   declarado caía en un `?? "comparacion"` puesto por si acaso.
 *
 * Ahora las dos listas **se derivan** de donde ya estaban escritas. Una lista
 * escrita dos veces son dos listas, y cuando divergen las dos parecen correctas.
 */
import { NOMBRES } from "./caminos.mjs";
import { PALABRAS_TIPO, esTipografico } from "./escena.mjs";
import { canonico, revisarTablero } from "./formas.mjs";

/**
 * Qué forma dibuja cada componente. Es también **la lista de componentes que
 * existen**: si una forma no dice qué dibuja, no se puede admitir.
 */
const KIND_DE = {
  TwoPaths: "comparacion",
  ComparisonTable: "comparacion",
  CausalChain: "causal",
  BeliefSwap: "comparacion",
  ThenNow: "comparacion",
  EvidenceCard: "acumulacion",
};

/**
 * Las dos exigencias que no son una lista. Viven aquí, en una sola frase cada
 * una, porque las leen dos sitios: el error que rechaza y el contrato que se le
 * manda a quien contesta. Escritas dos veces serían dos reglas.
 */
const REGLAS = [
  "Si `componente` no es «ninguno», `tablero` tiene que ser un objeto con"
  + " `props`: sin él el tablero se queda con lo que ya hubiera y la"
  + " descripción no llega a la pantalla.",
  "Si el `grafico` es tipográfico —lo es si dice "
  + PALABRAS_TIPO.map((p) => `«${p}»`).join(", ")
  + ", aunque `componente` sea «ninguno»—, el copy va en `tablero.props.texto`"
  + " (o `props.titulo`, o `tablero.texto`) y no puede estar vacío: sin él el"
  + " render no tiene copy y la capa no entra — o peor, repite el rótulo.",
];

/** Las claves que la descripción tiene que traer, y sus valores admitidos. */
export const CAMPOS = {
  etapa_orden: null,
  que_pasa: null,
  trato: NOMBRES,
  trato_porque: null,
  prioridad: ["entrega", "limpieza"],
  integridad: null,
  remedio: ["recuperar", "tablero", "cortar", "ninguno"],
  emocion: null,
  componente: [...Object.keys(KIND_DE), "ninguno"],
  grafico: null,
  color: ["avivar", "apagar", "dejar"],
  sonido: null,
  plano: ["en cuadro", "cerrado", "fuera"],
};

/**
 * **Y lo que se exige se le dice a quien contesta, derivado de aquí.**
 *
 * Jaime, 7-9-2026, eligiendo entre las dos salidas posibles: *«que el contrato
 * declare lo que el esquema exige, que es lo que lo hace innecesario: hoy el
 * que contesta se entera del requisito por el rechazo»*.
 *
 * Se paga en vueltas enteras del servicio. `componente: null` —cuando la lista
 * dice `ninguno`— tumbó la respuesta de reel-01 el 7 de septiembre y la de
 * reel-03 el 8, las dos después de que el oficio hiciera el trabajo entero.
 *
 * Va DERIVADO y no escrito a mano por el mismo motivo que las dos listas de
 * arriba: copiarlo al prompt sería una tercera copia, y cuando divergiera las
 * dos parecerían correctas. Cambiar `CAMPOS` cambia lo que se pide.
 */
export const exigencias = () => [
  "\n\n---\n\n## Lo que el esquema rechaza al recibir esto",
  "",
  "No es consejo: es la validación que corre al consumir tu respuesta, y una",
  "sola etapa que no encaje devuelve la respuesta entera sin aplicar.",
  "",
  "Valores admitidos, y no hay otros:",
  "",
  ...Object.entries(CAMPOS).filter(([, v]) => v)
    .map(([k, v]) => `- \`${k}\`: ${v.join(", ")}`),
  "",
  "Y dos reglas que no son de lista:",
  "",
  `- ${REGLAS[0]}`,
  `- ${REGLAS[1]}`,
  "",
  "`null` sólo vale donde el prompt lo declara —`integridad`, `grafico`,",
  "`sonido`, `corrige`, `tablero`—. Donde hay lista, «no hace falta» se dice con",
  "el valor que la lista trae para eso (`ninguno`, `dejar`), no con `null`.",
  "",
].join("\n");

/** El esquema se comprueba aquí: lo que no encaja se rechaza. */
export function valida(d) {
  for (const [k, admitidos] of Object.entries(CAMPOS)) {
    if (!(k in d)) throw new Error(`falta «${k}»`);
    if (admitidos && !admitidos.includes(d[k])) {
      throw new Error(`«${k}» = ${JSON.stringify(d[k])} no es de la lista`);
    }
  }
  /**
   * **Un componente sin `tablero` es una etapa que no va a cambiar nunca.**
   *
   * El contenido del tablero vivía en un literal por pieza y la descripción no
   * lo tocaba: cuatro entregas idénticas, y Jaime contándolas una a una. Ahora
   * el campo existe (`escena_desc.tablero`) y lo lee el render — pero si este
   * paso no lo escribe, la etapa se queda con lo que hubiera, que es
   * exactamente el mismo agujero por dentro.
   *
   * Así que se exige donde tiene sentido exigirlo: si la etapa declara un
   * componente, tiene que traer su contenido.
   */
  if (d.componente && d.componente !== "ninguno") {
    const t = d.tablero;
    if (!t || typeof t !== "object" || !t.props) {
      throw new Error(
        `«tablero» falta y la etapa declara componente «${d.componente}». `
        + REGLAS[0]);
    }
    // Sin `?? "comparacion"`: la lista de componentes admitidos SON las claves
    // de `KIND_DE`, asi que aqui ya no hay hueco que rellenar. El valor por
    // defecto solo podia taparle un fallo a la lista, que es lo que hacia.
    if (!t.kind) t.kind = KIND_DE[d.componente];
  }
  /**
   * **Y la composición TIPOGRÁFICA es un tablero, aunque no lleve componente.**
   *
   * El gancho de reel-04 pide tipo —su `grafico` dice «una sola palabra, y es
   * la que se oye: INMIGRANTE en Anton versales»— y `componente` es `ninguno`,
   * así que la exigencia de arriba no le tocaba y la etapa salía sin copy. El
   * render entonces rellenaba el bloque con `lineas[0]`, la primera línea del
   * rótulo, y el segundo gancho visual **repetía el primero** encima de él, en
   * el único segundo que compite contra el pulgar.
   *
   * No se arregla deduciendo la palabra de la prosa: eso sería código decidiendo
   * el copy. Se arregla exigiéndolo aquí, que es donde el diseño entrega.
   *
   * **Y la regla de qué es tipográfico se le pregunta a la escena.** Estaba
   * escrita dos veces —aquí y en `caminos.mjs`— con el mismo texto: el paso que
   * lo exige y el que lo monta podían dejar de entender lo mismo por «versales».
   */
  if (esTipografico(d.grafico ?? "")) {
    const t = d.tablero;
    const txt = t?.props?.texto ?? t?.props?.titulo ?? t?.texto;
    if (typeof txt !== "string" || !txt.trim()) {
      throw new Error(
        "«tablero» falta y el gráfico de esta etapa es tipográfico. "
        + REGLAS[1]);
    }
  }
  /**
   * **Y lo que el montaje no puede dibujar se rechaza aquí** (C-547), con la
   * misma vara. reel-19 e1 llegó como «Cover» con `linea1`/`linea2` —«Cover» se
   * declara con `hook`—, pasó cuatro pasos y se atascó en `montado`, donde ya no
   * hay a quién preguntarle. Rechazado al llegar, se le vuelve a pedir con el
   * error delante.
   */
  const t = d.tablero;
  if (t && typeof t === "object" && t.kind && t.props) {
    const faltas = revisarTablero(canonico(t.kind), t.props);
    if (faltas.length) {
      throw new Error(`«tablero» no se puede dibujar: ${faltas.join("; ")}`);
    }
  }
  return d;
}
