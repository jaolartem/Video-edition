/**
 * **El lienzo**: qué mide el cuadro, qué franjas no se tocan y cuánto aire hay
 * entre las cosas.
 *
 * Es geometría de superficie y no tiene nada que ver con el color ni con el
 * ritmo. Vivía dentro de `tokens` junto a la paleta, la escala tipográfica y
 * las duraciones, y ahí un cambio de zona segura se leía como un cambio de
 * marca.
 *
 * ## Y es de la pieza, no del sistema (C-670)
 *
 * Era una constante —1080×1920— porque todas las piezas eran verticales. El CV
 * de YBL es horizontal y entra por la misma línea, así que el lienzo pasa a ser
 * **una propiedad de la pieza**: `formato` en `frames.json`, y sin declararlo,
 * `vertical`. Los números viven en [`lienzos.json`](./lienzos.json), que leen
 * también los scripts; aquí sólo se les da forma.
 *
 * Quien dibuja lo pide con `useLienzo()` (ver [`LienzoContexto`](./LienzoContexto.tsx));
 * `layout` sigue siendo el vertical, para quien no está dentro de una pieza.
 */
import lienzosJson from "./lienzos.json";
import { franjaDe, type Franja } from "./franja";

/** Los lienzos declarados en `lienzos.json`. */
export type Formato = "vertical" | "horizontal";

type Margenes = {
  readonly top: number;
  readonly bottom: number;
  readonly left: number;
  readonly right: number;
};

type Datos = {
  width: number;
  height: number;
  safe: Margenes;
  captionBand: number;
  captionBottom: number;
  safeBottomExtremo: number;
  interfaz: number;
  columna: { x: number; ancho: number };
};

export class Lienzo {
  readonly width: number;
  readonly height: number;
  /**
   * Las plataformas verticales superponen su interfaz. El margen inferior es
   * mucho mayor porque ahí viven el copy, el usuario y los botones de
   * Reels/TikTok: cualquier texto que caiga dentro queda tapado.
   *
   * Zonas seguras de Instagram Reels — **fuente oficial de Meta**.
   *
   * Meta indica dejar libres de texto, logos y elementos clave: **14% arriba,
   * 35% abajo y 6% a cada lado**. Sobre 1080x1920 son 269 / 672 / 65.
   *
   * Se llego aqui despues de un rodeo que conviene no repetir: los blogs de
   * terceros daban cifras contradictorias —de 108 a 270 arriba, de 280 a 672
   * abajo— y varios afirmaban margenes ASIMETRICOS por los botones de accion.
   * La guia oficial dice **simetricos**. Cuando hay fuente canonica, no se
   * promedian opiniones.
   *
   * Meta publica ademas una plantilla verificadora de zona segura (ppt/psd/key)
   * si hace falta comprobar una pieza concreta.
   *
   * En horizontal no hay interfaz encima: es el aire de una pantalla.
   */
  readonly safe: Margenes;
  /**
   * Franja de subtitulos, **dentro** de la zona segura.
   *
   * Los subtitulos son elemento clave —el playbook exige que el argumento
   * funcione sin audio— asi que van por encima del 35% inferior que Meta
   * reserva, no dentro. Ocupan los ultimos 200 px de la zona segura.
   */
  readonly captionBand: number;
  /**
   * Distancia de la banda de subtitulos al borde inferior.
   *
   * **760, no 420: los subtitulos van pegados a la barbilla, nunca abajo.**
   * Peticion de Jaime. Con 420 la banda caia en el 68-78% de altura —lejos de
   * la cara, en la zona donde la vista ya no esta— y el ojo tenia que viajar
   * entre el rostro y el texto en cada frase.
   *
   * Con 760 la banda ocupa el 50-60%: justo debajo de la barbilla en los planos
   * medios, donde la mirada ya esta puesta. Sigue muy por encima de la interfaz
   * de la plataforma, que ocupa los 400 px inferiores.
   *
   * Esto **desplazo el rotulo**, que vivia en esa franja: ahora va debajo (ver
   * `BigTitle`). El subtitulo es la capa permanente y se queda con el mejor
   * sitio; el rotulo es un golpe de dos segundos y cede.
   */
  readonly captionBottom: number;
  /** Margen inferior extremo que citan algunas fuentes (35%). Solo para
   *  comprobar si un elemento critico sobrevive al peor caso. */
  readonly safeBottomExtremo: number;
  /**
   * Lo que la interfaz de la plataforma tapa de verdad abajo: 412 px en
   * vertical, más estrecho que la zona segura. En horizontal no hay interfaz,
   * así que es el margen. Ver `_interfaz` en `lienzos.json`.
   */
  readonly interfaz: number;
  /** La columna libre cuando el sujeto está dentro del tablero. Ver `panel/sitio.ts`. */
  readonly columna: { readonly x: number; readonly ancho: number };
  /** La franja del subtítulo de este lienzo, derivada de él: ver `franja.ts`. */
  readonly franja: Franja;

  constructor(
    readonly formato: Formato,
    d: Datos,
  ) {
    const { safe } = d;
    if (!(d.width > 0 && d.height > 0))
      throw new Error(`lienzo ${formato}: ${d.width}x${d.height} no es un cuadro`);
    if (safe.left + safe.right >= d.width || safe.top + safe.bottom >= d.height)
      throw new Error(`lienzo ${formato}: la zona segura no deja cuadro`);
    if (d.interfaz < 0 || d.interfaz > safe.bottom)
      throw new Error(`lienzo ${formato}: la interfaz no cae dentro de la zona segura`);
    if (d.columna.x + d.columna.ancho > d.width)
      throw new Error(`lienzo ${formato}: la columna se sale del cuadro`);
    this.width = d.width;
    this.height = d.height;
    this.safe = safe;
    this.captionBand = d.captionBand;
    this.captionBottom = d.captionBottom;
    this.safeBottomExtremo = d.safeBottomExtremo;
    this.interfaz = d.interfaz;
    this.columna = d.columna;
    this.franja = franjaDe(this);
  }

  /** El ancho entre los dos márgenes laterales. */
  get util(): number {
    return this.width - this.safe.left - this.safe.right;
  }

  /** Altura útil real de un tablero, ya descontada la banda de subtítulos. */
  get boardHeight(): number {
    return this.height - this.safe.top - this.safe.bottom - this.captionBand;
  }
}

const LIENZOS: Record<Formato, Lienzo> = {
  vertical: new Lienzo("vertical", lienzosJson.vertical),
  horizontal: new Lienzo("horizontal", lienzosJson.horizontal),
};

/**
 * El lienzo de un formato. Sin formato, el vertical: es lo que una pieza que
 * no lo declara ha sido siempre. Uno que no existe no se adivina.
 */
export const lienzoDe = (formato?: string | null): Lienzo => {
  const l = LIENZOS[(formato ?? "vertical") as Formato];
  if (!l) throw new Error(`formato «${formato}»: no está en lienzos.json`);
  return l;
};

/** El lienzo vertical: el de quien dibuja fuera de una pieza. */
export const layout = LIENZOS.vertical;

/** Altura útil real de un tablero vertical. */
export const boardHeight = layout.boardHeight;

/** Escala de espaciado sobre base 4, duplicada para la superficie de video. */
export const space = [8, 16, 24, 40, 64, 104, 168] as const;

/** Separación vertical entre nodos de un tablero. */
export const gap = {
  tight: 40,
  normal: 64,
  loose: 88,
} as const;
