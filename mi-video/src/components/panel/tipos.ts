import type { Casilla } from "../Casillas";
import type { Porcion } from "../Reparto";
import type { Volumen } from "../Volumen";
import type { Motion } from "../../brand/sfx";

/**
 * **Lo que un panel lateral declara.**
 *
 * Sale de [`SidePanel`](../SidePanel.tsx) por el mismo reparto que ya tienen
 * `causalChain`, `comparacion`, `twoPaths`, `acumulacion` y `ctaCard`: **lo que
 * se declara y lo que se dibuja son dos cosas**. El día que el panel dejó de ser
 * una pila de rótulos —la lámina de casillas y el reparto entraron el mismo
 * día— el fichero pasó de 272 a 380 líneas de código, y de las 108 nuevas más de
 * la mitad eran esto: el contrato, no el dibujo.
 *
 * Se parte por responsabilidad y no por líneas, que es la regla: aquí está qué
 * puede pedir quien compone, allí cómo se pinta.
 * @clase capa
 */
export type SidePanelProps = {
  /** Líneas del panel, de arriba abajo. Cortas: es un ancla, no un párrafo. */
  bloques: { texto: string; fuerte?: boolean; placa?: string }[];
  /**
   * **El lado de los BLOQUES**, que es el de la pieza y lleva ahí desde el
   * principio. Un bloque de texto cabe en cualquier margen, así que aquí no hace
   * falta la medida — y meterla costó una vuelta: al mandar también el texto al
   * lado medido, los dos paneles de reel-06 se fueron al margen donde estaba el
   * subtítulo y quedaron **encima de la línea**, «EMPRESARIO / EN ONTARIO / AÑO
   * TRAS AÑO» tachando «quizás hoy, quizás hace un mes». La medida es del
   * volumen, que es el que pide 30% del ancho; el texto no la necesitaba.
   */
  lado: "izq" | "der";
  /**
   * **El lado del VOLUMEN**, medido sobre la escena en la que cae el panel. Si
   * no viene, se cae al de los bloques.
   */
  ladoVolumen?: "izq" | "der";
  /**
   * **La animación del panel; sin ella el panel es sólo texto.**
   *
   * Instrucción de lote de Jaime (5-9-2026): *«las animaciones de bolitas y
   * palitos y ultra sencillas se acaban, quitan más de lo que dan; ahora sólo
   * animaciones complejas que muestren luz o movimiento, ojalá con animación 3D,
   * y que estén en consonancia con la idea del tablero o del panel»*. Los tres
   * paneles de reel-01 eran tres rótulos quietos y un pictograma de trazo — o
   * sea, justo lo que se acaba.
   *
   * Va aquí y no en una capa aparte porque **es del panel**: los bloques dicen
   * el ancla y el volumen dice lo que el ancla significa. **Retirado desde el
   * 6-9-2026**: la biblioteca está cerrada y declararlo es lo que ahora para la
   * pieza (`scripts/reels/paneles.mjs`).
   */
  volumen?: Volumen;
  /**
   * **La lámina del panel con la biblioteca de figuras cerrada.**
   *
   * Jaime, 6-9-2026: *«hasta que no tengamos una biblioteca de figuras decentes
   * no las vamos a utilizar. Gráficos y palabras, como tablero de clase»*.
   * Cerradas `figuras.json` y `volumenes.json`, un panel se quedó sin nada que
   * dibujar y los cuatro de reel-04 salieron como bloques negros de texto en una
   * esquina — tres formas declaradas distintas con el mismo aspecto, porque
   * `cubre: panel` tira el `kind`.
   *
   * Esto es lo que lo sustituye y es el otro medio de la instrucción: geometría
   * plana a escuadra y tipografía. Ver [`Casillas`](../Casillas.tsx).
   */
  casillas?: Casilla[];
  /**
   * **La otra lámina de la biblioteca cerrada: el dato.**
   *
   * Misma instrucción y la otra mitad de su literal — *«gráficos y palabras»*:
   * `Casillas` pone las palabras a escuadra y esto pone el gráfico de datos, que
   * es lo que la instrucción del 6-9-2026 deja entrar en primer lugar («barras,
   * repartos, acumulados, columnas comparadas»). La figura la traza
   * [`Reparto`](../Reparto.tsx), la misma que dibuja el reparto del tablero que
   * Jaime aprobó (`docs/ejemplos/composicion/01-panel-con-el-dentro.png`); aquí
   * sólo se le da sitio en el hueco del plano, que es lo que faltaba para que un
   * panel pudiera llevar un dato en vez de decirlo con letras.
   *
   * Va **después de los bloques**, al revés que `Casillas`, y no es capricho: un
   * reparto se argumenta DESDE su premisa —«de cada $100» y entonces la barra—,
   * mientras que una serie de casillas se resume DESPUÉS, en su pie. El orden de
   * lectura lo manda lo que cada lámina afirma.
   */
  reparto?: {
    /** El todo del que se reparte. Suele ser 100. */
    total: number;
    /** Las partes. **Una sola** lleva `foco`: el oro señala una. */
    porciones: Porcion[];
    /** Qué se antepone a cada cifra: «$», «%», o nada. */
    signo?: string;
    /** De qué caso es la barra. El pie de la fuente lo pone el panel. */
    etiqueta?: string;
  };
  /** `columna` apila; `fila` pone la serie de lado. Ver `Casillas`. */
  eje?: "columna" | "fila";
  /** El movimiento con el que entra cada casilla, declarado en su tablero. */
  sfx?: Motion | null;
  /**
   * **Cuánto sitio deja su cuerpo de ese lado**, en fracción del ancho, medido
   * por `scripts/dominio/hueco.py` sobre la escena en la que cae el panel. El
   * volumen lo usa para saber cuánto de él cabe; lo que sobra sangra por el
   * borde.
   */
  hueco?: number;
  /**
   * **De dónde salen las cifras, y es obligatorio si el panel enseña alguna.**
   *
   * Instrucción de Jaime (6-9-2026): el pie va *«por fuera de la zona segura»*,
   * en una línea, en mono, y **en afirmativo** — «basado en X datos bajo X
   * condiciones», nunca «sólo cuadra si…». Y *«pequeña no es descuidada»*: la
   * cifra y el tramo exactos, no un «según la fuente».
   *
   * Quien obliga es `scripts/reels/paneles.mjs`: un panel con un dígito y sin
   * pie no se monta. Aquí sólo se dibuja.
   */
  fuente?: string;
  /**
   * Frames entre la entrada de un bloque y el siguiente. Por defecto, `LEE`:
   * el tiempo que cuesta leer el anterior.
   */
  escalon?: number;
  /** Frames que tarda un bloque en entrar. */
  paso?: number;
};
