import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { layout, size, tracking, weight } from "../brand/tokens";

/**
 * Las piezas de **registro tipográfico** del canon, escritas una vez.
 *
 * `Fondo.tsx` tiene las piezas de superficie —placa, panel, cinta—; éstas son
 * las de tipo, y estaban copiadas dentro de cada tablero: la etiqueta en mono y
 * versales aparecía seis veces con las mismas cinco declaraciones, y el pie de
 * fuente nueve. Copiar una regla del canon dentro de un componente es cómo se
 * pierde: la siguiente pieza la copia otra vez, con una diferencia.
 *
 * Ninguna decide nada — el color lo pone quien la usa, porque el tinte depende
 * del modo, del tono y de si el bloque es el que hay que mirar. Lo que fijan es
 * la familia, el cuerpo y el interletrado, que son del sistema y no de la pieza.
  * @clase sistema
*/

/**
 * El marco de un tablero: la zona segura de Reels, **con la banda de subtítulos
 * descontada**.
 *
 * El tablero tiene prohibido invadir esa banda. No es una preferencia de
 * composición: el playbook exige que el argumento funcione sin audio, y esa
 * carga la lleva el subtítulo. Si el tablero se le echa encima, la pieza deja de
 * cumplir para el 85% que mira en silencio.
 */
export const Marco: React.FC<{
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ style, children }) => (
  <AbsoluteFill
    style={{
      paddingTop: layout.safe.top,
      paddingBottom: layout.safe.bottom + layout.captionBand,
      paddingLeft: layout.safe.left,
      paddingRight: layout.safe.right,
      display: "flex",
      flexDirection: "column",
      ...style,
    }}
  >
    {children}
  </AbsoluteFill>
);

/**
 * Etiqueta en versales con interletrado amplio: el registro mono del sistema.
 *
 * Las versales con tracking abierto son de la etiqueta, **nunca del titular** —
 * el display va en caja mixta y con tracking negativo. Confundir los dos
 * registros es lo que hace que una pieza parezca de otra familia.
 */
export const Etiqueta: React.FC<{
  tinta: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ tinta, style, children }) => (
  <div
    style={{
      fontFamily: fontFamily.data,
      fontSize: size.labelMono,
      fontWeight: weight.medium,
      letterSpacing: tracking.labelMono,
      textTransform: "uppercase",
      color: tinta,
      ...style,
    }}
  >
    {children}
  </div>
);

/**
 * Una cifra grande y aislada. Va en Playfair y no en mono: el sistema le da
 * trato editorial, que es reverencia y no dato tabular.
 */
export const Cifra: React.FC<{
  tinta: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ tinta, style, children }) => (
  <div
    style={{
      fontFamily: fontFamily.display,
      fontSize: size.displayL,
      fontWeight: weight.semibold,
      letterSpacing: tracking.display,
      lineHeight: 1,
      color: tinta,
      ...style,
    }}
  >
    {children}
  </div>
);

/**
 * El pie de dato: la fuente, el horizonte, la fecha.
 *
 * **Una cifra no aparece sin él.** Los tipos de cada tablero ya lo garantizan
 * —`figure` y `source` van juntos o no van— y esto es cómo se ve: letra
 * pequeña, mono, en el color secundario, para que acompañe sin competir.
 */
export const Fuente: React.FC<{
  tinta: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ tinta, style, children }) => (
  <div
    style={{
      fontFamily: fontFamily.data,
      fontSize: size.source,
      letterSpacing: tracking.labelMono,
      textTransform: "uppercase",
      color: tinta,
      ...style,
    }}
  >
    {children}
  </div>
);
