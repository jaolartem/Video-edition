import type { CSSProperties } from "react";
import ccJson from "./cc.json";
import { color, layout } from "./tokens";

/**
 * **El fondo del subtítulo: los tres tratamientos, y qué comparten.**
 *
 * Jaime, 6-9-2026, viendo las siete con el cc puesto: *«los CC están feos;
 * pueden ser a negativo solamente para variar el cuadro negro, es decir, unos CC
 * que se compongan mejor respecto a la composición»*, *«hay varios que quedarían
 * bien sin el cuadro, otras a las que le queda bien y otras a las que le quedaría
 * mejor negativo»*, y el límite: *«no te cierres a un solo sistema, pero debe ser
 * coherente con el resto del video»*.
 *
 * El cuadro negro no desaparece: deja de ser el **único**. Era el mismo parche en
 * los 90 segundos de las siete — la zona de pantalla que más tiempo está ocupada,
 * resuelta sin componer.
 *
 * ## Lo que NO cambia entre los tres, que es lo que los hace la misma mano
 *
 * El sitio, la familia, el cuerpo, el peso, el interletrado, la alineación y la
 * entrada. Cambia **cómo se resuelve el suelo de la letra** y nada más. Por eso
 * los tres pueden convivir en una pieza sin que se lea como tres piezas cosidas:
 * la coherencia manda sobre la variedad, y variar por variar rompe más de lo que
 * arregla.
 *
 * - `caja` — el bloque de `richBlack` de siempre. Fondo cargado o que cambia
 *   dentro de la misma línea: ahí la caja es lo único que garantiza que se lea.
 * - `limpio` — sin caja, con el contorno de `richBlack` que ya llevaba debajo.
 *   Fondo oscuro y quieto: la caja sólo tapaba imagen sin comprar contraste.
 * - `negativo` — `mix-blend-mode: difference`. **No elige color: lo calcula**
 *   contra lo de debajo en cada fotograma, así que el contraste está garantizado
 *   sobre un fondo claro o que se mueve. Jaime, mirando referencias: *«algunas
 *   letras quedan como negativo del fondo, eso es muy interesante porque los
 *   fondos son dinámicos»*.
 *
 * **Y la fusión necesita compartir contexto de apilamiento con el vídeo.** El
 * `<span>` blanco se compone contra lo que hay pintado debajo dentro del mismo
 * grupo: el plano, lo que le pasa por detrás y las bandas del glitch. Meter una
 * capa aislada entre medias —`opacity`, `filter` o `isolation` en un ancestro que
 * no contenga el vídeo— lo apaga **sin dar error**: el texto sale blanco y nadie
 * se entera. Por eso se comprueba mirando el render, no razonando (C-268).
 *
 * Cuál toca no se opina: lo mide `scripts/dominio/trasfondo.py` y lo decide
 * `scripts/reels/cc.mjs`. Los números viven en `cc.json` y en ningún otro sitio.
 */
export type Trato = "caja" | "limpio" | "negativo";

const J = ccJson;

export const cc = {
  /** Los tratamientos declarados. No es un menú cerrado: ver `cc.json`. */
  tratos: Object.keys(J.tratos) as Trato[],
  /** Con qué se dibuja una cue que nadie midió: la caja, que siempre se lee. */
  porDefecto: J.por_defecto as Trato,
  /** Suelo del cc pegado a la barbilla, en fracción de altura: 0,604. */
  sueloBarbilla: J.suelo_barbilla,
  cabeza: J.cabeza,
} as const;

/**
 * **Si el cc cabe en el hueco de encima de su cabeza.**
 *
 * Estaba escrito a pelo dentro de `CaptionBand` —un `260` y un `24` sueltos— y
 * hacía falta en tres sitios más: quien mide la banda del fondo, quien decide el
 * tratamiento y quien lo dibuja. Los números viven ahora en `cc.json`.
 *
 * Medido en las siete: sólo reel-06 (coronilla 0,436) tiene sitio; en las otras
 * seis el cc se queda junto a la barbilla, que es donde Jaime lo pidió.
 */
export const cabeElCcArriba = (coronilla?: number): boolean =>
  !!coronilla &&
  coronilla * layout.height - cc.cabeza.desde - cc.cabeza.margen >=
    cc.cabeza.minimo;

/**
 * Lo único que cambia entre los tres: cómo se resuelve el suelo de la letra.
 *
 * El contorno se queda en `caja` y en `limpio` porque hace su trabajo en los
 * bordes de las letras sobre pared clara o camisa azul. En `negativo` se retira:
 * un contorno de `richBlack` bajo `difference` es casi la identidad —resta
 * nada— así que sería un contorno declarado que no dibuja.
 */
export const pintaDelCc = (trato: Trato): CSSProperties => {
  if (trato === "negativo") {
    return {
      color: "#ffffff",
      mixBlendMode: "difference",
      /**
       * **Sin caja y sin contorno, y el contorno se probó.**
       *
       * Uno de `richBlack` aquí es la identidad —restar nada— así que no dibuja
       * borde ninguno. Y uno blanco se probó en el render: engorda la mancha que
       * se invierte, o sea la misma letra más gorda, y el resultado quedó peor —
       * más masa y el mismo contraste. La letra se queda con su trazo.
       */
      padding: "0.06em 0.22em",
    } as CSSProperties;
  }
  return {
    ...(trato === "caja" ? { backgroundColor: color.richBlack } : {}),
    padding: "0.06em 0.22em",
    boxDecorationBreak: "clone",
    WebkitBoxDecorationBreak: "clone",
    WebkitTextStroke: `4px ${color.richBlack}`,
    paintOrder: "stroke fill",
  } as CSSProperties;
};
