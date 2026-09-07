import React from "react";
import { fontFamily } from "../../brand/fonts";
import { color, tracking } from "../../brand/tokens";

/**
 * **El cuerpo del pie: por debajo del cuerpo de dato, y en la misma familia.**
 *
 * `size.source` (22) es el cuerpo de una fuente **sobre plano**, donde no
 * compite con nada. Dentro de un tablero compite con la cifra, así que baja: la
 * fuente a 20 y la condición a 18, que es lo que hace falta para que 25
 * palabras —el tope de `enPantalla`— quepan en dos líneas de mono a lo ancho
 * del cuadro en vez de en el párrafo que salía antes.
 */
const PIE = { fuente: 20, condicion: 18 };

/**
 * **Lo que cierra el panel con él dentro**, apilado desde abajo.
 *
 * Vive aparte de [`PanelDentro`](../PanelDentro.tsx) por la misma razón que
 * `comparacion/Columna`: son dos trabajos. Allí se decide qué capa va sobre
 * cuál; aquí, cómo se apila lo que remata.
 *
 * **Y se apila, no se coloca.** El remate estaba en `top: 790` y la pila crecía
 * hacia arriba según lo larga que fuera la condición, así que quién tapaba a
 * quién dependía del texto: en el primer fotograma del render el bloque de la
 * pregunta se comió la etiqueta `CON ESTRUCTURA` y media línea del remate, sin
 * error y sin log. Apilados desde abajo el solape deja de ser posible — es la
 * misma corrección que T-02 hizo con la franja: sustituir un número escrito a
 * mano por una relación que no se puede incumplir.
 */

/** El bloque negro que sostiene un texto. El negro ya no es el fondo. */
export const Bloque: React.FC<{
  ancho: number;
  /** 0 a 1: el bloque se abre desde su borde izquierdo. */
  abre: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ ancho, abre, style, children }) => (
  <div style={{ position: "relative", width: ancho, ...style }}>
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundColor: color.richBlack,
        transformOrigin: "left",
        transform: `scaleX(${abre})`,
      }}
    />
    <div style={{ position: "relative", padding: "26px 34px", opacity: abre }}>
      {children}
    </div>
  </div>
);

export const Cierre: React.FC<{
  /** La conclusión de los repartos, en oro y en una línea. */
  remate?: string;
  /**
   * La pregunta que se la devuelve al espectador.
   *
   * Va **abajo y en su propio bloque**: es otro movimiento —del dato a él— y por
   * eso no comparte bloque con el remate, que todavía habla de las cifras.
   */
  pregunta?: string;
  /** De dónde salen las cifras. Cumplimiento, no adorno. */
  fuente: string;
  /** Bajo qué supuestos son ciertas. */
  condicion?: string;
  /** Dónde empieza la columna de contenido, para alinear el remate con ella. */
  x: number;
  ancho: number;
  /** El horario de cada uno, ya resuelto por quien lo hospeda. */
  entra: { remate: number; pregunta: number; pie: number };
}> = ({ remate, pregunta, fuente, condicion, x, ancho, entra }) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      right: 0,
      bottom: 0,
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-start",
    }}
  >
    {/**
     * **El remate lleva su propio negro, y no el de la masa de las cifras.**
     *
     * Se apoyaba en la masa que `PanelDentro` pone bajo la columna, y esa masa
     * tiene un alto fijo mientras que esto se apila **desde abajo**: cuando el
     * pie ocupa dos líneas en vez de cuatro, el remate baja y se sale de la
     * masa. Visto con `sujeto: derecha`, el oro cayó sobre el collage claro y
     * dejó de leerse — el mismo fallo que la masa de las cifras vino a
     * arreglar, un piso más abajo.
     *
     * Con su bloque, quien lo sostiene viaja con él: la relación es «este texto
     * se apoya en este negro» y no «este negro llega hasta aquí».
     */}
    {remate ? (
      <Bloque
        ancho={ancho + 68}
        abre={entra.remate}
        style={{ marginLeft: x - 34, marginBottom: 22 }}
      >
        <div
          style={{
            width: ancho,
            textAlign: "center",
            fontFamily: fontFamily.bloque,
            fontSize: 32,
            letterSpacing: tracking.display,
            textTransform: "uppercase",
            color: color.gold,
          }}
        >
          {remate}
        </div>
      </Bloque>
    ) : null}
    {/**
     * **La pregunta y el pie se tocan: son un solo pie de página.**
     *
     * Con 18 px entre los dos, esos 18 px eran un ventanuco por el que asomaba
     * un trozo de sus antebrazos y del collage, y una figura cortada en dos
     * sitios deja de ser una figura. En la lámina aprobada un bloque negro
     * cruza entero por delante de él —lo corta a la altura de las rodillas— y
     * eso se lee; cortarlo dos veces con una rendija en medio, no.
     */}
    {pregunta ? (
      <Bloque ancho={760} abre={entra.pregunta}>
        <div
          style={{
            fontFamily: fontFamily.bloque,
            fontSize: 44,
            letterSpacing: "0.01em",
            textTransform: "uppercase",
            color: color.gold,
          }}
        >
          {pregunta}
        </div>
      </Bloque>
    ) : null}
    {/**
     * **El pie es letra pequeña sobre el mismo negro, no una tarjeta clara.**
     *
     * Iba en una banda de `lightNeutral` con la condición en Montserrat 700 a
     * 22 px, y en el fotograma de reel-02 e2 eso no era un pie: era **un
     * párrafo blanco cruzando la pieza**, la masa más clara del cuadro puesta
     * en lo que menos hay que mirar, y partiendo su figura en dos. El canon lo
     * dice al revés —el pie es *«una línea pequeña al pie»*, en `JetBrains
     * Mono`, sobre el mismo negro— y la jerarquía del tablero también: el
     * blanco y el oro son de la cifra.
     *
     * Sobre negro se lee igual, porque la banda es opaca y el collage no se le
     * transparenta. Las dos líneas comparten la familia de dato y se separan
     * por color: de dónde sale la cifra, y bajo qué supuesto es cierta.
     */}
    <div
      style={{
        alignSelf: "stretch",
        backgroundColor: color.richBlack,
        padding: "14px 56px 18px",
        opacity: entra.pie,
      }}
    >
      <div
        style={{
          fontFamily: fontFamily.data,
          fontSize: PIE.fuente,
          letterSpacing: tracking.labelMono,
          textTransform: "uppercase",
          lineHeight: 1.3,
          color: color.secondaryBlue,
        }}
      >
        {fuente}
      </div>
      {condicion ? (
        <div
          style={{
            fontFamily: fontFamily.data,
            fontSize: PIE.condicion,
            lineHeight: 1.34,
            color: color.lightNeutral,
            opacity: 0.66,
            marginTop: 6,
          }}
        >
          {condicion}
        </div>
      ) : null}
    </div>
  </div>
);
