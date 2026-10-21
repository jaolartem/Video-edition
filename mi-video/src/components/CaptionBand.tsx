import React from "react";
import { fontFamily } from "../brand/fonts";
import { Compuesta, DESDE_EL_LADO } from "./captionBand/Compuesta";
import { Corregida } from "./captionBand/Corregida";
import { Plana } from "./captionBand/Plana";
import { cabeElCcArriba, cc, type Trato } from "../brand/cc";
import { franja } from "../brand/franja";
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
  * @clase sistema
*/
export const CaptionBand: React.FC<{
  text: string;
  tokens: ModeTokens;
  /**
   * Dónde cae su coronilla, en fracción del cuadro. Con esto el subtítulo se
   * coloca **en el hueco de encima de su cabeza** en vez de junto a la barbilla.
   *
   * Jaime: *«hay mucho espacio arriba de mi cabeza en esas tomas para poner cc
   * y letreros»*, *«sí, aprovechemos el espacio de la toma, que para eso es;
   * además es una toma muy bonita»*.
   *
   * Medido en las siete piezas: la coronilla cae en 0,317–0,320 y la zona segura
   * de Meta empieza en 0,14 — **340–345 px sin usar**, el 18% del cuadro. Abajo,
   * en cambio, la banda se toca con su mentón.
   *
   * Y no contradice el porqué de la posición anterior —*«los subtítulos van
   * pegados a la barbilla»*, para que el ojo no viaje—: encima de la cabeza
   * está igual de cerca de la cara, y además no tapa la toma.
   */
  coronilla?: number;
  /**
   * El lado libre del cuadro, donde vive el panel. Sólo importa cuando el
   * subtítulo sube: arriba **comparten franja** y hay que repartirla.
   *
   * Sin esto el cc a todo lo ancho se comió el panel «EMPRESARIO / EN ONTARIO /
   * AÑO TRAS AÑO» de reel-06: dos capas de texto en la misma esquina, las dos
   * ilegibles. Abajo no pasaba porque el panel vive arriba.
   */
  lado?: "izq" | "der";
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
  /**
   * **Abajo y punto: aquí manda otra capa.**
   *
   * Jaime, 6-9-2026, sobre el gancho: *«puedes mantener el subtítulo los
   * primeros 5 segundos, con el cc abajo de mí»*. Mientras el rótulo del gancho
   * está en cuadro, el hueco de encima de su cabeza **no está libre** —es
   * justamente donde vive el rótulo—, así que subir ahí es lo contrario de lo
   * que la subida venía a hacer. Medido en reel-06: con 544 px de hueco el cc se
   * subía y tapaba «NADA HA» de «NADA HA PASADO».
   *
   * Se apoya en el suelo de la franja, que es la geometría que ya estaba
   * declarada en `franja.json` y que ningún tablero invade.
   *
   * Lo decide el montaje —`reels/portada.mjs :: bajarEnElGancho`— y no este
   * componente: aquí no se sabe qué más hay en cuadro.
   */
  abajo?: boolean;
  /**
   * **Cómo se resuelve su fondo**, que hasta hoy no se resolvía: era el cuadro
   * negro en los 90 segundos de las siete piezas.
   *
   * Jaime, 6-9-2026: *«los CC están feos; pueden ser a negativo solamente para
   * variar el cuadro negro, es decir, unos CC que se compongan mejor respecto a
   * la composición»*, *«hay varios que quedarían bien sin el cuadro, otras a las
   * que le queda bien y otras a las que le quedaría mejor negativo»*.
   *
   * No se elige aquí: lo mide `scripts/dominio/trasfondo.py` sobre la banda que
   * este componente ocupa en esa escena y lo decide `scripts/reels/cc.mjs`.
   * Los tres tratamientos y lo que comparten viven en `src/brand/cc.ts`.
   */
  trato?: Trato;
  /**
   * **A qué lado va el texto, si el diseñador lo pidió para la etapa** (C-633).
   * Jaime, reel-20: *«prefiero que todas las letras queden al lado derecho»*,
   * para equilibrar el plano que se cerró para sacar el clóset. A la derecha,
   * en la mitad libre y alineado a ese borde. Sin él, el de siempre.
   */
  alinea?: "izq" | "der";
}> = ({ text, tokens, corrige, palpita, realza, compuesto, desde = 0,
        coronilla, lado, abajo, alinea, trato = cc.porDefecto }) => (
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
      /**
       * Encima de la cabeza **sólo si de verdad cabe**; si no, junto a la
       * barbilla, que es donde Jaime lo pidió en su día.
       *
       * El hueco no es igual en las siete: medido sobre los cortes, va de −7 px
       * (reel-05, donde su cabeza entra POR ENCIMA de la zona segura) a 565 px
       * (reel-06, sentado y reclinado). Sólo R4 y R6 tienen sitio para dos
       * renglones; en las otras cinco subir el subtítulo lo metería sobre su
       * frente.
       *
       * La primera versión lo subía en las siete porque el dato de la coronilla
       * era falso —predicho desde el ancla de movimiento, que devolvía siempre
       * 0,32— y con él todas parecían tener 340 px libres. Ahora se mide.
       */
      // `abajo` gana siempre: es la única que sabe que arriba hay otra capa.
      // Si cabe o no lo dice `cabeElCcArriba`, con los números de `cc.json`:
      // estaban aquí sueltos —un 260 y un 24— y hacían falta en tres sitios más,
      // el que mide el fondo de esa banda, el que decide el tratamiento y éste.
      ...(!abajo && cabeElCcArriba(coronilla)
        ? {
            top: cc.cabeza.desde,
            // Arriba se comparte con el panel: el cc se queda con su mitad.
            ...(lado === "der"
              ? { right: layout.width * 0.44 }
              : { left: layout.width * 0.44 }),
            // Acaba un pelo antes de la coronilla, para no morderla. Sin
            // `Math.max`: aquí ya se sabe que hay 260 px o más, y un suelo
            // artificial era lo que la metía sobre su cara cuando no cabía.
            maxHeight:
              (coronilla ?? 0) * layout.height -
              cc.cabeza.desde -
              cc.cabeza.margen,
            justifyContent: "flex-end" as const,
          }
        : // Bajo el gancho se apoya en el suelo de la franja —672 px, el borde
          // inferior de la zona segura— y no en la barbilla: ahí es donde el
          // rótulo tiene garantizado no llegar. Ver `abajo`.
          { bottom: abajo ? franja.desdeAbajo : layout.captionBottom }),
      minHeight: layout.captionBand,
      display: "flex",
      flexDirection: "column",
      // El borde de abajo es el que no se mueve; lo que crece, crece hacia
      // arriba. Ver la cabecera del componente.
      justifyContent: "flex-end",
      alignItems: alinea === "der" ? "flex-end" : "flex-start",
      ...(alinea === "der"
        ? { left: layout.width * DESDE_EL_LADO, textAlign: "right" as const }
        : {}),
      fontFamily: fontFamily.body,
      // **Sobre un tablero esta banda ya no se dibuja.** Bajaba a 0,68 del
      // cuerpo y se quedaba donde estaba —incluso encima de la coronilla, o sea
      // encima del propio tablero—. Ahora ese caso lo lleva `CaptionDiscreta`,
      // que es lo que la instruccion T-02 pedia y llevaba escrito sin usarse.
      fontSize: videoText.caption,
      fontWeight: 800,
      lineHeight: 1.2,
      letterSpacing: videoText.tracking,
      color: tokens.text,
    }}
  >
    {compuesto ? (
      <Compuesta c={compuesto} desde={desde} alinea={alinea} />
    ) : (
      <Plana desde={desde} trato={trato}>
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
