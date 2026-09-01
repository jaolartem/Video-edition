import type { Accent, Mode, Tone, gap } from "../../brand/tokens";

type CausalNodeBase = {
  /** Etapa del framework, p.ej. "Contexto institucional". */
  stage: string;
  /** El enunciado de esa etapa, en español nativo. */
  text: string;
  /**
   * Marca este nodo como el hecho relevante del tablero: sube de cuerpo y toma
   * el color de texto pleno. Es independiente del remate — a veces lo que hay
   * que agrandar está en mitad de la cadena, no al final.
   */
  emphasis?: boolean;
};

/**
 * Cumplimiento por construcción.
 *
 * El playbook exige que toda cifra lleve contexto y fuente fiable. La unión
 * discriminada convierte el incumplimiento en un error de compilación: un nodo
 * con `figure` y sin `source` no compila. No hay forma de olvidar la
 * atribución, que es justo el error que nadie detecta revisando 50 ads.
 */
export type CausalNode =
  | (CausalNodeBase & { figure?: never; source?: never })
  | (CausalNodeBase & { figure: string; source: string });

export type CausalChainProps = {
  /**
   * Los nodos de la cadena. La secuencia rectora del playbook tiene cuatro:
   * contexto institucional → creencia adaptativa → manifestación financiera →
   * consecuencia. Tres a cinco funcionan; más no cabe legible en 9:16.
   */
  nodes: CausalNode[];
  /**
   * Modo del sistema del canon. **Nunca se mezclan dentro de una pieza**: la
   * superficie declara quién habla. `evidence` para EDUCATE, SOCIAL PROOF y
   * SELL — hablan los datos. `guide` para CONNECT — habla Jaime.
   */
  mode?: Mode;
  /** Superficie sobre la que se dibuja. Da variedad entre piezas. */
  tone?: Tone;
  /** Acento del tablero. El oro sigue siendo lo que hay que atender. */
  accent?: Accent;
  /** Aire entre nodos. `loose` para tableros de tres nodos o menos. */
  gap?: keyof typeof gap;
  /**
   * Frame en que se revela cada nodo, anclado a palabras concretas del
   * transcript. Es lo que se usa en montaje final. Sin esto, el calendario se
   * deriva del tiempo de lectura de cada enunciado.
   */
  revealAt?: number[];
  title?: string;
  /**
   * El último nodo de una cadena causal no es uno más: es la consecuencia. Por
   * defecto recibe trato de remate —pausa antes, bloque de superficie con filo
   * de acento y cuerpo mayor— porque una cadena a ritmo plano informa pero no
   * aprieta. Se desactiva solo si la pieza no cierra en consecuencia.
   */
  emphasizePayoff?: boolean;
  /**
   * El `scope and limitation` que piden los frameworks. Es un slot del
   * componente y no texto opcional del libreto, para que no se caiga en el
   * montaje.
   *
   * Llega con **beat propio al final**, no de adorno permanente al pie. Un
   * límite legal que comparte pantalla con el argumento durante todo el plano
   * no se lee: es ruido. Con beat propio se lee, que es de lo que se trata.
   */
  limitation?: string;
  /**
   * Subtítulo visible en la franja inferior. En producción sale del SRT de
   * CapCut; aquí se pasa a mano para ver la composición real de la pieza.
   */
  caption?: string;
  /**
   * Emite el efecto de sonido de cada movimiento. **Requiere los ficheros de
   * `public/sfx/`**, que aún no existen — por eso está apagado por defecto.
   */
  sound?: boolean;
};
