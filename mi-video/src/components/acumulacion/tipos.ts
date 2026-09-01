export type Tramo = {
  /** Qué es este tramo. Versales condensadas, al lado de su bloque. */
  etiqueta: string;
  /** Cuánto ocupa, en fracción de la altura total del gráfico (0–1). */
  alto: number;
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
