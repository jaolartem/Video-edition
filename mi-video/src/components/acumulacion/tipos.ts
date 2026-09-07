import type { Recorte } from "../Fondo";
export type Tramo = {
  /** Qué es este tramo. Versales condensadas, al lado de su bloque. */
  etiqueta: string;
  /** Cuánto ocupa, en fracción de la altura total del gráfico (0–1). */
  alto: number;
  /**
   * **Cuánto es, en la unidad de la raya. Obligatorio cuando hay `umbral`.**
   *
   * `alto` es un número libre: nada lo ata a nada, y con `umbral` eso deja de
   * ser inocente. Una raya rotulada «$50,000 AL AÑO» convierte la columna en
   * una escala en dólares, así que cada `alto` afirma cuánto puso ese tramo y
   * el cruce afirma en cuál se pasó. Son mediciones, y **una cantidad dibujada
   * afirma igual que una cifra rotulada** — es la regla que `Recuento.cuantos`
   * ya aplica a las marcas.
   *
   * Declarado, se rotula debajo de la etiqueta y entra en `sinRespaldo`, que
   * pide su fila en `dato`. Sin declarar y con raya, el render muere: cuatro
   * fracciones inventadas que suman 1 dibujan un cruce que ninguna fuente
   * sostiene (tiquet #217, reel-05 e6).
   */
  valor?: string;
};

/**
 * **Cumplimiento por construcción.**
 *
 * `resultado` exige cifra y fuente juntas —el tipo no admite una sin la otra— y
 * `horizonte` y `condicion` son obligatorias. Una cifra acumulada sin horizonte
 * no significa nada, y sin condición se lee como promesa de resultado, que el
 * playbook prohíbe.
 */
export type AcumulacionProps = {
  /**
   * El hueco de la placa, puesto donde esta su cara. Ver `ventana` en `Fondo`.
   *
   * El recorte va escrito a fuego en el componente, y con eso lo que se ve por
   * el hueco depende de donde cayera el encuadre: en la sesion de noche, las
   * rodillas. Jaime: *«mis pies son la parte mas quieta y la que menos comunica
   * intencionalmente»*, *«por ahora que salga mi cara en los huecos»*.
   *
   * Declarada, manda sobre `recorte`. Sin declarar, todo sigue igual.
   */
  recorte?: Recorte;
  title: string;
  /** Qué se acumula. Va en la cinta de arriba, con el horizonte. */
  concepto: string;
  /**
   * El horizonte sobre el que se acumula. **Obligatorio**: «$300.000» no dice
   * nada hasta que se sabe si son diez años o un trimestre.
   */
  horizonte: string;
  /** Los tramos, de abajo arriba. Entran de uno en uno. */
  tramos: Tramo[];
  /**
   * La raya. Opcional — no toda acumulación tiene umbral: la de diez años del
   * R6 sólo crece.
   */
  umbral?: { etiqueta: string; en: number };
  /** Lo que la acumulación produce. Cifra Y fuente, o ninguna de las dos. */
  resultado?: { figure: string; source: string };
  /**
   * **De qué datos sale lo que se dibuja, cuando no hay `resultado`.**
   *
   * `pieDe` escribe el respaldo de un `acumulacion` en `resultado.source`, así
   * que una acumulación sin resultado —la de R3, la de R5— se quedaba sin sitio
   * donde ponerlo: el diseño declaraba `fuente` en el spec, el componente lo
   * destructuraba por nombre sin `rest` y **el valor se evaporaba sin error**.
   * Es la avería de la casa —declarar sin poder aplicar— y se cerraba dando el
   * prop, no discutiendo el pie.
   */
  fuente?: string;
  /** Qué cambiaría el cálculo. **Obligatorio.** */
  condicion: string;
  /**
   * Placa de fondo, si el tablero la lleva. **El collage asoma por los bordes y
   * el panel opaco sostiene las cifras** — que es como lo hace el canon: una
   * tabla sobre un fotomontaje no se lee, pero una tabla flotando en negro deja
   * medio cuadro muerto. Jaime: *«más color y movimiento»*.
   */
  placa?: string;
  /** Requiere los ficheros de `public/sfx/`. */
  sound?: boolean;
};
