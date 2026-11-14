import franjaJson from "./franja.json";

/**
 * **La franja del subtítulo, y quién cede ante quién.**
 *
 * Instrucción de Jaime (T-02), después de ver en R-04 un tablero de texto
 * cruzándose con los subtítulos quemados: *«durante los tableros el subtítulo
 * pasa a estilo tradicional discreto: cuerpo pequeño, sin caja ni contorno,
 * apoyado en el **borde inferior de la zona segura** —no del cuadro—. El
 * tablero es la capa de información y el subtítulo sólo acompaña. Por
 * implicación: **ningún tablero baja hasta esa franja**, que queda reservada al
 * subtítulo»*.
 *
 * Son dos reglas y una sola geometría, y por eso viven juntas aquí:
 *
 * - el subtítulo **se apoya** en el suelo de la franja mientras hay tablero,
 * - el tablero **no llega** al techo de la franja, nunca.
 *
 * ## De dónde sale el número, que no se inventó
 *
 * `franja.json` lo declara una vez y esto sólo lo traduce a píxeles. La
 * derivación es la de `tokens.ts`: Meta reserva el **35% inferior** de la pieza
 * (672 px sobre 1920), así que el borde inferior de la zona segura cae en el
 * **65%** de la altura; y la banda de subtítulos son **200 px**, el 10,4166%.
 * La franja va del **54,58% al 65%**.
 *
 * Y el motivo de que el suelo sea el de la zona segura y no el del cuadro lo
 * dio Jaime con la cuenta: en Reels y Stories la interfaz de la plataforma
 * ocupa el ~20% inferior —nombre de cuenta, caption, botones— así que el texto
 * que cae por debajo de la zona segura desaparece bajo la interfaz. Y como la
 * mayoría mira sin audio, ahí no se pierde un adorno: se pierde el argumento.
 */
/** Lo que la franja necesita saber de su lienzo. Ver `lienzo.ts`. */
type Medidas = {
  readonly height: number;
  readonly safe: { readonly bottom: number };
  readonly captionBand: number;
};

/**
 * **La franja de un lienzo** (C-670). Se deriva como dice `_derivacion` de
 * `franja.json` —el suelo es el borde inferior de la zona segura y el alto, la
 * banda—, así que cada lienzo tiene la suya sin declararla otra vez. Sobre el
 * vertical da exactamente el 0,65 y el 200/1920 de `franja.json`, y
 * `scripts/franja.mjs` para la línea si dejan de casar.
 *
 * Se pide al lienzo: `useLienzo().franja`.
 */
export const franjaDe = (layout: Medidas) => {
  const SUELO = 1 - layout.safe.bottom / layout.height;
  const ALTO = layout.captionBand / layout.height;
  return {
    /** Suelo, en fracción de altura: 0,65. El borde inferior de la zona segura. */
    suelo: SUELO,
    /** Techo, en fracción de altura: 0,5458333. Ningún tablero baja de aquí. */
    techo: SUELO - ALTO,
    /** Alto, en fracción de altura: 0,1041666 (200 px sobre 1920). */
    alto: ALTO,
    /** Distancia del suelo de la franja al borde inferior del cuadro: 672 px. */
    desdeAbajo: Math.round((1 - SUELO) * layout.height),
    /**
     * **Lo que un tablero deja libre por abajo: 872 px.**
     *
     * Es la zona segura inferior más la banda. Coincide con lo que
     * `CausalChain` y `TwoPaths` ya reservaban escribiendo
     * `layout.safe.bottom + layout.captionBand` en cada uno — que era el mismo
     * número escrito cuatro veces, y por eso `Comparacion` y `Acumulacion`
     * pudieron ignorarlo sin que nadie se enterara.
     */
    reserva: Math.round((1 - SUELO + ALTO) * layout.height),
    /** El techo, en píxeles desde arriba: 1048. */
    techoPx: Math.round((SUELO - ALTO) * layout.height),
    /**
     * **El suelo, en píxeles desde arriba: 1248.** Es donde empieza lo que va
     * FUERA de la zona segura, y ahí vive el pie de fuente.
     *
     * Instrucción de Jaime (6-9-2026): *«por fuera de la zona segura; no me
     * interesa que lo lean, sólo que sepan que existe»* — pegado por debajo de
     * esta línea y **no al fondo del cuadro**, porque la interfaz de Meta se come
     * el 35% inferior y ahí abajo la fuente no queda fuera de la zona segura:
     * queda tapada, y entonces no cumple ni el único trabajo que se le pide.
     *
     * Estaba escrito a mano como `1262` en `PanelDentro` y en `acumulacion/Cierre`
     * —dos copias del mismo número derivado—, que es exactamente cómo empezaron
     * las cuatro copias de `layout.safe.bottom + layout.captionBand`.
     */
    sueloPx: Math.round(SUELO * layout.height),
    /** Cuerpo del subtítulo discreto. Ver `franja.json`. */
    cuerpo: franjaJson.cuerpo,
  } as const;
};

export type Franja = ReturnType<typeof franjaDe>;

/**
 * La franja dicha en porcentaje, para quien la tiene que respetar sin dibujar:
 * el prompt del que compone, el informe y los documentos.
 */
export const franjaEnPorcentaje = (franja: Franja): string =>
  `del ${(franja.techo * 100).toFixed(1)}% al ${(franja.suelo * 100).toFixed(1)}%` +
  ` de la altura`;
