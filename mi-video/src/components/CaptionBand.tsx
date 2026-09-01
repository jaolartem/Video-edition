import React from "react";
import { fontFamily } from "../brand/fonts";
import { Compuesta } from "./captionBand/Compuesta";
import { Corregida } from "./captionBand/Corregida";
import { Plana } from "./captionBand/Plana";
import { layout, videoText, type ModeTokens } from "../brand/tokens";
import type { Compuesto } from "./captionBand/Compuesta";

export type { Compuesto } from "./captionBand/Compuesta";

/**
 * La franja de subtítulos, encima de la interfaz de la plataforma.
 *
 * **No es decoración.** El playbook exige que el argumento funcione sin audio, y
 * esa carga la lleva esta capa: el tablero pone el ancla corta y el subtítulo
 * recoge lo que se dice. Por eso el tablero tiene prohibido invadir esta zona.
 *
 * En producción el texto sale del SRT de CapCut vía `parseSrt()`. Aquí se pasa
 * a mano solo para ver la composición real de la pieza.
 *
 * **Cuerpo de vídeo, no de página.** Estaba en `size.body` (38 px), que es la
 * medida de la web y de los tableros — se leen con calma. A velocidad de scroll
 * y sobre imagen comprimida hace falta el cuerpo de vídeo (62) y peso, que es lo
 * que dice el aprendizaje 11: el peso pesa más que el cuerpo.
 *
 * Y va con **contorno, no con sombra**: el sistema prohíbe la sombra por nombre,
 * y un contorno sólido aguanta igual sobre pared clara que sobre camisa azul.
 * El contorno es la forma plana; la compuesta cambia a bloque, que es el
 * recurso del canon.
 *
 * ## Se ancla por abajo
 *
 * Antes centraba en una banda de altura fija, así que una cue de dos renglones
 * se salía por arriba y por abajo a partes iguales. Ahora el **borde inferior
 * es el que no se mueve** y el bloque crece hacia arriba: el ojo tiene un
 * punto fijo al que volver, y lo que crece lo hace hacia la barbilla y no
 * hacia la interfaz de la plataforma.
 *
 * ## Aquí sólo se elige la forma
 *
 * Las tres formas viven aparte, cada una con su regla: la
 * [plana](./captionBand/Plana.tsx), la
 * [compuesta](./captionBand/Compuesta.tsx) —que es la única que mide texto— y
 * la [corregida](./captionBand/Corregida.tsx), que sirve igual a la corrección
 * y a la idea fuerza.
 */
export const CaptionBand: React.FC<{
  text: string;
  tokens: ModeTokens;
  /**
   * La correccion que se burla: se oye una cosa y se lee otra.
   *
   * Regla de Jaime — *«no pones lo mismo que yo digo sino lo que esta bien y lo
   * amplias, de manera que la contradiccion se note y sea una especie de
   * burla»*. En el reel 2 atribuye la estadistica al «ministerio de comercio»
   * cuando es el de **Finanzas**: se oye *comercio*, se lee **FINANZAS** en
   * grande y en oro.
   *
   * Es distinto de hinchar la palabra equivocada, que fue el primer intento:
   * agrandar el error solo lo subraya. Poner la palabra correcta en su sitio
   * **arma la contradiccion**, y la broma la remata el espectador.
   *
   * Broma de subordinado, deadpan: el montaje no comenta nada, solo cambia la
   * palabra y sigue.
   *
   * Tasa maxima: una o dos por minuto. Ver «Que se note que hay alguien
   * detras» en CLAUDE.md — por encima de eso deja de ser una persona y pasa a
   * ser un montaje de fallos.
   */
  corrige?: { dice: string; es: string };
  /** Que la correccion palpite: tres golpes duros y se queda. */
  palpita?: boolean;
  /**
   * **La idea fuerza**: la frase del beat que crece y se pone en oro cuando se
   * dice. No sustituye nada —eso es `corrige`— sólo subraya.
   *
   * Es el tercer tratamiento del reparto. Jaime: *«animaciones para conceptos
   * complejos e ideas fuerza para lo demás, sin dejar de lado los subtítulos»*.
   * Va donde el beat **afirma, provoca o promete**: ahí la fuerza está en la
   * voz y el texto sólo tiene que marcar dónde cae el golpe.
   *
   * Frente a un tablero es más barato y más rápido —no roba el plano— y frente
   * a nada, sostiene la atención en el tramo en que sólo hay una cara hablando.
   */
  realza?: string;
  /** Dos renglones, dos fuentes. Ver `Compuesto`. Lo deriva `reels-spec.mjs`. */
  compuesto?: Compuesto;
  /** Frame en que empieza este subtitulo, para poder animar dentro de el. */
  desde?: number;
}> = ({ text, tokens, corrige, palpita, realza, compuesto, desde = 0 }) => (
  <div
    style={{
      position: "absolute",
      left: layout.safe.left,
      right: layout.safe.right,
      /**
       * 760 px desde abajo: **los subtitulos van pegados a la barbilla**.
       *
       * Peticion de Jaime. Con 420 la banda caia en el 68-78% de altura —lejos
       * de la cara, donde la vista ya no esta— y el ojo tenia que viajar entre
       * el rostro y el texto en cada frase.
       *
       * Sigue muy por encima de la interfaz de la plataforma, que ocupa los
       * 400 px inferiores.
       */
      bottom: layout.captionBottom,
      minHeight: layout.captionBand,
      display: "flex",
      flexDirection: "column",
      // El borde de abajo es el que no se mueve; lo que crece, crece hacia
      // arriba. Ver la cabecera del componente.
      justifyContent: "flex-end",
      alignItems: "flex-start",
      fontFamily: fontFamily.body,
      fontSize: videoText.caption,
      fontWeight: 800,
      lineHeight: 1.2,
      letterSpacing: videoText.tracking,
      color: tokens.text,
    }}
  >
    {compuesto ? (
      <Compuesta c={compuesto} desde={desde} />
    ) : (
      <Plana desde={desde}>
        {corrige ? (
          <Corregida texto={text} corrige={corrige} desde={desde} palpita={palpita} />
        ) : realza ? (
          <Corregida
            texto={text}
            corrige={{ dice: realza, es: realza }}
            factor={1.22}
            desde={desde}
          />
        ) : (
          text
        )}
      </Plana>
    )}
  </div>
);
