/**
 * **El lienzo**: qué mide el cuadro, qué franjas no se tocan y cuánto aire hay
 * entre las cosas.
 *
 * Es geometría de superficie y no tiene nada que ver con el color ni con el
 * ritmo. Vivía dentro de `tokens` junto a la paleta, la escala tipográfica y
 * las duraciones, y ahí un cambio de zona segura se leía como un cambio de
 * marca.
 */

export const layout = {
  width: 1080,
  height: 1920,
  /**
   * Las plataformas verticales superponen su interfaz. El margen inferior es
   * mucho mayor porque ahí viven el copy, el usuario y los botones de
   * Reels/TikTok: cualquier texto que caiga dentro queda tapado.
   */
  /**
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
   */
  safe: { top: 269, bottom: 672, left: 65, right: 65 },
  /**
   * Franja de subtitulos, **dentro** de la zona segura.
   *
   * Los subtitulos son elemento clave —el playbook exige que el argumento
   * funcione sin audio— asi que van por encima del 35% inferior que Meta
   * reserva, no dentro. Ocupan los ultimos 200 px de la zona segura.
   */
  captionBand: 200,
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
  captionBottom: 760,
  /** Margen inferior extremo que citan algunas fuentes (35%). Solo para
   *  comprobar si un elemento critico sobrevive al peor caso. */
  safeBottomExtremo: 672,
} as const;

/** Altura útil real de un tablero, ya descontada la banda de subtítulos. */
export const boardHeight =
  layout.height - layout.safe.top - layout.safe.bottom - layout.captionBand;

/** Escala de espaciado sobre base 4, duplicada para la superficie de video. */
export const space = [8, 16, 24, 40, 64, 104, 168] as const;

/** Separación vertical entre nodos de un tablero. */
export const gap = {
  tight: 40,
  normal: 64,
  loose: 88,
} as const;
