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
import { esTipografico } from "./escena.mjs";

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
        `«tablero» falta y la etapa declara componente «${d.componente}»:` +
        ` sin él, el tablero se queda con lo que ya hubiera y la descripción` +
        ` no llega a la pantalla`);
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
        `«tablero» falta y el gráfico de esta etapa es tipográfico: di qué dice` +
        ` en \`tablero.props.texto\`. Si no, el render no tiene copy y la capa` +
        ` no entra — o peor, repite el rótulo`);
    }
  }
  return d;
}
