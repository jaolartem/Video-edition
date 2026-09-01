import React from "react";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe } from "../../brand/medida";
import { color } from "../../brand/tokens";
import type { Columna as Datos } from "./tipos";

/**
 * Caja de las columnas, **por encima de la banda de subtítulos**.
 *
 * Jaime: *«en los tableros también hay cc»*. Y es distinto del panel: bajo un
 * panel la voz dice lo que el panel muestra, así que el subtítulo repetiría;
 * bajo un tablero la voz **sigue diciendo cosas que el tablero no enseña** —es
 * un L-cut— y el 85% mira sin sonido.
 *
 * La banda vive en 960–1160 (`captionBottom` 760 + `captionBand` 200), así que
 * las columnas acaban en 900 y el remate y el pie se van por debajo de ella.
 */
export const COL = { y: 260, alto: 640 } as const;

/**
 * Una de las dos columnas: cabecera, cifra y pie, sobre un bloque plano.
 *
 * **Navy contra oro**, que es como el canon resuelve una comparación: el navy
 * es el estado por defecto y el oro es donde hay que mirar. Nunca semáforo — la
 * distinción se hace con la superficie, no con el color de alarma.
 */
export const Columna: React.FC<{
  datos: Datos;
  /** Borde izquierdo, en píxeles del cuadro. */
  x: number;
  ancho: number;
  /** Si es la columna que el espectador debe mirar. */
  oro: boolean;
  /** Progreso de entrada, 0→1. Lo calcula el horario. */
  progreso: number;
}> = ({ datos, x, ancho, oro, progreso }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: COL.y,
      width: ancho,
      height: COL.alto,
      backgroundColor: oro ? color.gold : color.navy,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 40,
      padding: "0 34px",
      opacity: progreso,
      transform: `translateY(${(1 - progreso) * 26}px)`,
    }}
  >
    <div
      style={{
        fontFamily: fontFamily.bloque,
        fontSize: 46,
        lineHeight: 1.02,
        textAlign: "center",
        textTransform: "uppercase",
        color: oro ? color.richBlack : color.secondaryBlue,
      }}
    >
      {datos.titulo}
    </div>
    <div
      style={{
        fontFamily: fontFamily.bloque,
        // Ajustado a la línea. El avance de la Anton lo declara `brand/medida`,
        // medido sobre render y escrito en un solo sitio: el margen se paga en
        // cuerpo, que es barato, no en texto cortado, que no lo es.
        fontSize: cuerpoQueCabe({
          ancho: ancho - 52,
          largo: datos.cifra.length,
          registro: "anton",
          tope: 128,
        }),
        lineHeight: 0.94,
        whiteSpace: "nowrap",
        textTransform: "uppercase",
        color: oro ? color.richBlack : color.lightNeutral,
      }}
    >
      {datos.cifra}
    </div>
    {datos.pie ? (
      <div
        style={{
          fontFamily: fontFamily.video,
          fontSize: 27,
          fontWeight: 700,
          lineHeight: 1.3,
          textAlign: "center",
          color: oro ? color.richBlack : color.secondaryBlue,
        }}
      >
        {datos.pie}
      </div>
    ) : null}
  </div>
);
