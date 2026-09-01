/**
 * **El contrato de cumplimiento de la comparación de dos columnas.**
 *
 * Vive aparte del dibujo porque lo que el playbook exige de una cifra en
 * pantalla no es una decisión de composición: `fuente` es obligatoria —si el
 * tablero enseña cifras, lleva de dónde salen— y `condicion` también, porque
 * sin ella la comparación se lee como promesa de resultado y el playbook
 * prohíbe garantizar resultados individuales. Declarado como tipo, un
 * incumplimiento deja de ser una revisión pendiente y pasa a ser un fallo de
 * compilación.
 */

export type Columna = {
  /** Cabecera de la columna. Versales condensadas. */
  titulo: string;
  /** La cifra o el estado. Es el remate de la columna. */
  cifra: string;
  /** Una línea de detalle, si hace falta. */
  pie?: string;
};

export type ComparacionProps = {
  /** Cinta superior: la condición común. «Misma facturación», «De cada $100». */
  premisa: string;
  /** La columna del estado por defecto. Va en navy: no es donde hay que mirar. */
  izquierda: Columna;
  /** La columna que importa. Va en oro. */
  derecha: Columna;
  /** Cinta inferior: la diferencia, o la pregunta que deja. */
  remate?: string;
  /** De dónde salen las cifras. **Obligatoria.** */
  fuente: string;
  /** Qué cambiaría la comparación. **Obligatoria.** */
  condicion: string;
  /**
   * Placa de fondo, si el tablero la lleva. **El collage asoma por los bordes y
   * el panel opaco sostiene las cifras** — que es como lo hace el canon: una
   * tabla sobre un fotomontaje no se lee, pero una tabla flotando en negro deja
   * medio cuadro muerto. Jaime: *«más color y movimiento»*.
   */
  placa?: string;
  /**
   * Cuánto dura la escena que este tablero **reemplaza**, en frames.
   *
   * Jaime: *«el tablero reemplaza la escena, y el tablero es un instrumento
   * pedagógico»*; y *«se tiene que presentar poco a poco y durar toda la
   * escena»*. Así que el horario no es fijo: se **reparte** sobre el tiempo
   * disponible.
   *
   * Con un horario fijo el tablero se montaba en 10 s y se quedaba quieto el
   * resto — que es justo lo que hace que un tablero se sienta relleno. Repartido,
   * cada elemento entra cuando el anterior ya se pudo leer Y hay algo entrando
   * hasta el final.
   */
  duracion?: number;
  /** Requiere los ficheros de `public/sfx/`. */
  sound?: boolean;
};
