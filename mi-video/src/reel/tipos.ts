import type { BoardCue, CaptionCue } from "../Ad";
import type { Capa } from "../components/Capas";
import type { ContrasteProps } from "../components/Contraste";
import type { CortinillaProps } from "../components/Cortinilla";
import type { TarjetaProps } from "../components/Tarjeta";

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
  /** Tramos en blanco y negro. Ver `Desatura` en `Ad`. */
  desatura: { at: number; duration: number }[];
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
  paneles: { at: number; duration: number; bloques: { texto: string; fuerte?: boolean }[] }[];
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
