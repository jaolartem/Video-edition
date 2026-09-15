import type { BoardCue, CaptionCue } from "../Ad";
import type { Capa } from "../components/Capas";
import type { Casilla } from "../components/Casillas";
import type { Motion } from "../brand/sfx";
import type { Porcion } from "../components/Reparto";
import type { Recorte } from "../components/Detras";
import type { ContrasteProps } from "../components/Contraste";
import type { CortinillaProps } from "../components/Cortinilla";
import type { TarjetaProps } from "../components/Tarjeta";
import type { Volumen } from "../components/Volumen";

/**
 * **Lo que una pieza declara**, aparte de cómo se dibuja.
 *
 * El spec es el contrato entre `reels-spec.mjs` —que decide— y `Reel.tsx` —que
 * pinta—. Vivía dentro del componente, así que añadir una capa nueva obligaba a
 * abrir el fichero del dibujo y viceversa; y lo que se declara aquí no es una
 * decisión de composición: es lo que la línea de montaje acordó.
 *
 * Un reel completo es vídeo montado + subtítulos + rótulo de gancho + CTA.
 * El vídeo ya viene cortado y con los encuadres aplicados (`plan-reel.mjs` →
 * `punch-ins.py` → `render-hook.mjs`). Lo de aquí es sólo lo que se superpone, y
 * las capas portantes son:
 *
 * - **Subtítulos**: el playbook exige que el argumento funcione sin audio.
 * - **Rótulo**: entra por un lado **en la palabra que subraya** y sale por el
 *   otro. Antes se quedaba quieto desde el frame 0 diciendo lo que la voz diría
 *   cinco segundos después: para cuando llegaba la frase, el remate ya estaba
 *   gastado.
 * - **Tableros**: durante una explicación el tablero ES el plano; Jaime
 *   desaparece del cuadro y la voz sigue por debajo (un L-cut, así la costura no
 *   se oye).
 * - **CTA**: uno y sólo uno, y sólo en SELL. Los demás pilares llevan cero, así
 *   que el CTA vive en el spec y no en el componente: una pieza sin CTA
 *   simplemente no lo trae.
 */
export type ReelSpec = {
  id: string;
  video: string;
  /** Volumen del plano. `0` renderiza la pieza como pista de solo efectos. */
  volumen?: number;
  /**
   * Las capas que decidio el camino de cada segmento. Ver `scripts/caminos.mjs`
   * y `components/Capas.tsx`: aqui solo se dibujan.
   */
  caminos: Capa[];
  /**
   * Si la pieza lleva efectos de sonido.
   *
   * **La version sin aprobar va muda de extras.** Jaime: *«los videos para
   * aprobacion van sin musica y sin audio adicional»*. Lo decide el spec
   * mirando si la version esta aprobada, no una bandera que haya que recordar.
   */
  sonido?: boolean;
  duracion: number;
  lineas: string[];
  /** Frame en que ENTRA el rótulo: el de la palabra que subraya. */
  entra: number;
  /** Frames que se sostiene dentro del cuadro antes de salir. */
  sostiene: number;
  /**
   * La portada de la pieza, si la declara. La pinta `Cover` sobre su propio
   * fotograma; no se saca del render, que traeria el rotulo y el CC quemados.
   */
  portada?: {
    titulo: string;
    subtitulo?: string;
    fotograma: string;
    por_que?: string;
  } | null;
  cta: {
    at: number;
    dur: number;
    promesa: string;
    fecha: string;
    duracion?: number;
    corrige?: { dice: string; es: string };
    /** Las dos cuentas enfrentadas. Ver `cuenta` en `CtaCard`. */
    cuenta?: { cuesta: string; vale: string; nota?: string };
    placa?: string;
    /** Opcional: no se declara porque sube pronto. Ver `CtaCard`. */
    precio?: string;
  } | null;
  captions: CaptionCue[];
  /**
   * Tableros: el plano de las explicaciones.
   *
   * Petición explícita de Jaime — «animaciones en las partes que se expliquen
   * cosas, así yo no me vea». Y resuelve lo otro que señaló, que los cambios de
   * escena se ven raros: un punch-in cada tres segundos desde una cámara fija es
   * un jump cut, y los jump cuts son visibles por diseño. Se tapan cortando a
   * otra cosa. Aquí esa otra cosa además explica.
   */
  boards: BoardCue[];
  /**
   * Donde cae su cara en el cuadro, en fracciones. Lo mide `punch-ins.py` y lo
   * trae `reels-spec`. Con esto el subtitulo se coloca **encima de su cabeza**,
   * que es el 18% del cuadro que estaba sin usar.
   */
  cara?: { coronilla: number; menton: number } | null;
  /** Tramos en blanco y negro. Ver `Desatura` en `Ad`. */
  desatura: { at: number; duration: number }[];
  /**
   * Tramos virados —sepia, navy, duro—, con su filtro ya resuelto.
   *
   * Los pide el diseñador por etapa en `escena_desc.camara.virado` y el horario
   * sale del plan, no del EDL (`scripts/reels/imagen.mjs`). Vacío es lo normal:
   * una pieza que nadie ha virado sale como se grabó.
   */
  virados: { at: number; duration: number; virado: string; css: string }[];
  /**
   * Etapas donde un ELEMENTO le pasa por detrás. Ver `Recorte` en `Ad`.
   *
   * Jaime: *«y ojalá jueguen con mi cara… que se escondan detrás»*. Se pide en
   * `escena_desc.camara.detras` y el recorte del sujeto lo produce
   * `scripts/dominio/sujeto.py` sobre el corte de hoy. Vacío es lo normal: la
   * pasada de MediaPipe cuesta, así que sólo corre donde se pidió.
   *
   * Y el `titular` es uno de ellos: **el rótulo del gancho detrás de su
   * cabeza**. Cuando está, `BigTitle` no se dibuja — decir el mismo rótulo dos
   * veces sería devolverlo al tercio de abajo, que es la lámina que esto vino a
   * quitar. Lo emite el camino `portada` y lo comprueba `reels/portada.mjs`.
   */
  recortes?: Recorte[];
  /**
   * Costuras cruzadas por la transición animada. Ver `Filete`.
   *
   * Jaime: *«que haga una animación en esa transición»*. Es la tercera vía —el
   * glitch distorsiona la imagen, la cortinilla interrumpía con una placa y
   * quedó retirada— y sólo sale donde alguien la pide.
   */
  filetes: { at: number; duration: number; grosor: number; segundo: number }[];
  /**
   * Costuras tapadas con distorsión. Ver `Glitch` en `Ad`.
   *
   * Jaime: *«lo ideal del corte y del cambio de escena es que no se note»*. El
   * glitch no oculta el corte — lo **sustituye**: el ojo registra la
   * distorsión, no el salto de encuadre.
   */
  glitch: { at: number; duration: number }[];
  /**
   * Cortinillas: lo que media cada costura entre beats.
   *
   * Jaime, del segundo 33: *«el corte es demasiado duro, muy brusco; eso debe
   * estar mediado o por un gráfico o por algo que lo suavice»*. Ahí el montaje
   * salta 83 s de material y cambia de encuadre a la vez, sin nada que lo cubra.
   */
  cortinillas: { at: number; duration: number; props: CortinillaProps }[];
  /**
   * Frames donde cambia el encuadre.
   *
   * Ya **no** llevan barra: se probó en todos y quedó peor que el salto. La
   * barra queda reservada a la entrada de una tarjeta, que es cuando el
   * movimiento trae algo. Se conservan porque el rótulo los usa para decidir
   * dónde cede.
   */
  cortes: number[];
  /** Lado libre del cuadro, derivado de dónde está el sujeto. */
  lado: "izq" | "der";
  /**
   * Paneles que se construyen en el hueco del plano, **sin cortar**.
   *
   * Idea de Jaime: en vez de cortar, irse al plano más lejano y animar en el
   * espacio disponible. El cambio deja de verse porque no hay corte — cambia lo
   * que ocupa el cuadro.
   */
  paneles: {
    at: number;
    duration: number;
    bloques: { texto: string; fuerte?: boolean; placa?: string }[];
    /**
     * La animación del panel, del catálogo de `src/brand/volumenes.json`. Un
     * panel sin ella es sólo texto, y eso lo para `scripts/reels/puerta.mjs`.
     */
    volumen?: Volumen;
    /**
     * **La lámina de datos y palabras del panel.** Es lo que dibuja un panel
     * desde que la biblioteca de figuras está cerrada —*«gráficos y palabras,
     * como tablero de clase»*—: casillas iguales de las que una se sella y las
     * demás se tachan o se quedan. Ver `components/Casillas`.
     */
    casillas?: Casilla[];
    /**
     * **La otra mitad de esa instrucción: el gráfico de datos.** Un reparto de
     * un total en porciones, con el oro en la que importa. Ver
     * `components/Reparto`, que es la misma figura del tablero aprobado.
     */
    reparto?: {
      total: number;
      porciones: Porcion[];
      signo?: string;
      etiqueta?: string;
    };
    /** Si la serie se apila o va de lado. Ver `Casillas`. */
    eje?: "columna" | "fila";
    /** El movimiento con el que entra cada casilla: `escena_desc.tablero.sfx`. */
    sfx?: Motion | null;
    /**
     * **A qué lado deja sitio su cuerpo en ESA escena**, medido con la silueta
     * por `scripts/dominio/hueco.py`. Manda sobre el `lado` de la pieza, que
     * sale del recorte de la primera escena y con la cámara fija da casi
     * siempre el mismo — así doce de trece volúmenes cayeron sobre su cara.
     */
    lado?: "izq" | "der";
    /** Cuánto ancho libre deja de ese lado, en fracción del cuadro. */
    hueco?: number;
    /** El pie de cumplimiento. Obligatorio si el panel enseña una cifra. */
    fuente?: string;
  }[];
  /**
   * Tarjetas: los beats del libreto que no tienen plano utilizable.
   *
   * *«A cada estructura le escogemos el mejor, y si no entra bien hacemos un
   * gráfico, así sea sólo palabras.»* Un beat no se cae por falta de toma: se
   * dibuja, con el audio bueno por debajo si lo hay.
   */
  tarjetas: { at: number; duration: number; props: TarjetaProps }[];
  /**
   * Las dos cifras de la comparacion, encima del plano. Ver `Contraste`.
   *
   * No roba el plano como un tablero: Jaime sigue en cuadro contando quien es
   * cada uno mientras los dos numeros se quedan arriba.
   */
  contraste?: { at: number; duration: number; props: ContrasteProps } | null;
};
