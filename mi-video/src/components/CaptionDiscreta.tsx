import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, videoText, type ModeTokens } from "../brand/tokens";
import { useLienzo } from "../brand/LienzoContexto";

/**
 * **El subtítulo mientras manda el tablero.**
 *
 * Instrucción de Jaime (T-02): *«durante los tableros el subtítulo pasa a
 * estilo tradicional discreto: cuerpo pequeño, sin caja ni contorno, apoyado en
 * el borde inferior de la zona segura —no del cuadro—. El tablero es la capa de
 * información y el subtítulo sólo acompaña»*.
 *
 * Origen: en R-04 un tablero de texto se cruzaba con los subtítulos quemados —
 * texto sobre texto, ilegibles los dos. Y no era casualidad: la banda portante
 * vive en el 50–60% de altura y el tablero dibujaba hasta el 54,58%, así que se
 * pisaban por diseño.
 *
 * ## Qué cambia y por qué, punto por punto
 *
 * - **Se apoya en el suelo de la franja** (`franja.desdeAbajo`, 672 px) en vez
 *   de en la barbilla. Pegado a la barbilla es la regla cuando hay una cara en
 *   cuadro; con un tablero no hay cara, y el sitio bueno es el que no roba
 *   composición.
 * - **El contraste va en la letra, no en el cuadro.** Aquí no había ni caja ni
 *   contorno, con el argumento de que *«sobre un tablero el fondo lo pone el
 *   tablero»*, y es falso justo donde escribe: la franja empieza en el 54,58%,
 *   que es donde el tablero **deja** de dibujar, así que detrás de esta letra
 *   está la placa — y las placas del canon tienen discos de hueso. Blanco sobre
 *   hueso no se lee.
 *
 *   Se resolvió una vez apagando 872 px del cuadro, y Jaime lo devolvió
 *   (C-253): *«era más fácil poner las letras en oro que tapar la mitad»*. Así
 *   que el contraste lo lleva la línea: **oro sobre el negro del canon**, en un
 *   bloque plano que mide lo que mide el texto. `boxDecorationBreak: clone` lo
 *   recorta renglón a renglón, así que no es un rectángulo alrededor del
 *   párrafo: es la cinta del canon a tamaño de letra.
 * - **Cuerpo pequeño**, 55 px. Es el mínimo práctico medido, no un número
 *   suelto: por debajo el subtítulo se pierde a distancia de brazo. Pequeño
 *   frente a los 62 de la capa portante, y legible.
 * - **Sin realce, sin forma compuesta y sin palpitar.** Son tratamientos de
 *   énfasis, y aquí el énfasis lo lleva el tablero. Dos capas subrayando lo
 *   mismo en el mismo segundo no es énfasis, es ruido.
 *
 * Lo que **no** cambia: el subtítulo no se calla. El playbook exige que el
 * argumento funcione sin audio, bajo un tablero la voz sigue diciendo cosas que
 * el tablero no enseña —es un L-cut— y el 85% mira sin sonido.
 */
export const CaptionDiscreta: React.FC<{
  text: string;
  tokens: ModeTokens;
  /**
   * La corrección que se burla sigue valiendo —se oye una cosa y se lee la que
   * es, porque el dato tiene fuente— pero **sin agrandar la palabra**: crecer
   * al 145% es justo lo que esta forma renuncia a hacer.
   */
  corrige?: { dice: string; es: string };
  /** Frame en que empieza este subtítulo, para animar dentro de él. */
  desde?: number;
}> = ({ text, tokens, corrige, desde = 0 }) => {
  const layout = useLienzo();
  const franja = layout.franja;
  const frame = useCurrentFrame();
  const p = interpolate(frame, [desde, desde + 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const partes = corrige
    ? text.split(new RegExp(`(${corrige.dice})`, "i"))
    : [text];
  return (
    <div
      style={{
        position: "absolute",
        left: layout.safe.left,
        right: layout.safe.right,
        // El borde inferior de la ZONA SEGURA, no el del cuadro. Ver `franja`.
        bottom: franja.desdeAbajo,
        minHeight: layout.captionBand,
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-end",
        alignItems: "flex-start",
        fontFamily: fontFamily.body,
        fontSize: franja.cuerpo,
        // **Peso 900.** Sobre vídeo el peso pesa más que el cuerpo, y esta capa
        // no puede crecer: es la que acompaña. Lo que se paga en cuerpo se cobra
        // aquí.
        fontWeight: 900,
        lineHeight: 1.28,
        letterSpacing: videoText.tracking,
        opacity: p,
      }}
    >
      {/* El envoltorio de bloque hace falta para que el `<span>` de dentro siga
          siendo INLINE: como hijo directo del flex se blockifica, y entonces
          `clone` pinta un solo rectángulo del ancho de la columna en vez de
          recortarse renglón a renglón. */}
      <div style={{ maxWidth: "100%" }}>
      <span
        style={{
          backgroundColor: color.richBlack,
          color: color.gold,
          // Renglón a renglón: sin esto el bloque sale como un rectángulo que
          // abraza el párrafo entero, incluido el hueco de la última línea.
          boxDecorationBreak: "clone",
          WebkitBoxDecorationBreak: "clone",
          padding: "0.06em 0.28em",
        }}
      >
        {partes.map((t, i) =>
          corrige && t.toLowerCase() === corrige.dice.toLowerCase() ? (
            <span key={i} style={{ color: tokens.accent }}>
              {corrige.es}
            </span>
          ) : (
            <React.Fragment key={i}>{t}</React.Fragment>
          ),
        )}
      </span>
      </div>
    </div>
  );
};
