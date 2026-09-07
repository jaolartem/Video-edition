import React from "react";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe, masLarga } from "../../brand/medida";
import { color } from "../../brand/tokens";
import { CAJA, COLUMNA, MARCA } from "./caja";

/**
 * **Los tres bloques con los que se dibuja el recuento**: la cabecera de una
 * columna, la condición que la califica y la marca.
 *
 * Viven aparte de `Recuento.tsx` por el mismo reparto que `caja` y `horario`:
 * allí se arma la lámina y se decide qué entra cuándo; aquí sólo se pinta. Es
 * el reparto que ya tiene `acumulacion/Barra.tsx`.
 */

/** La cabecera de una columna: caja negra que se acaba donde se acaba la palabra. */
export const Cabecera: React.FC<{ texto: string; x: number; p: number }> = ({
  texto,
  x,
  p,
}) => (
  <div style={{ position: "absolute", left: x, top: CAJA.cabeceras, opacity: p }}>
    {/* El negro que abraza su texto, no media lámina apagada: es la masa del
        canon. */}
    <div
      style={{
        display: "inline-block",
        backgroundColor: color.richBlack,
        padding: "10px 18px",
      }}
    >
      <div
        style={{
          fontFamily: fontFamily.bloque,
          fontSize: cuerpoQueCabe({
            ancho: COLUMNA - 40,
            largo: texto.length,
            registro: "anton",
            tope: 58,
          }),
          lineHeight: 1,
          letterSpacing: "0.006em",
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          color: color.lightNeutral,
        }}
      >
        {texto}
      </div>
    </div>
  </div>
);

/**
 * **La condición de una columna: para quién está hecho lo que hay ahí.**
 *
 * Misma caja negra que la cabecera y cuerpo menor —tope 46 contra 58—, porque
 * califica lo que tiene encima en vez de encabezarlo. El tinte lo hereda de las
 * marcas que califica: el oro no se reparte.
 */
export const Condicion: React.FC<{
  lineas: string[];
  x: number;
  y: number;
  p: number;
  tinte: string;
}> = ({ lineas, x, y, p, tinte }) => (
  <div style={{ position: "absolute", left: x, top: y, opacity: p }}>
    <div
      style={{
        display: "inline-block",
        backgroundColor: color.richBlack,
        padding: "12px 18px",
        fontFamily: fontFamily.bloque,
        fontSize: cuerpoQueCabe({
          ancho: COLUMNA - 36,
          largo: masLarga(lineas),
          registro: "anton",
          tope: 46,
        }),
        lineHeight: 1.08,
        letterSpacing: "0.006em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        color: tinte,
      }}
    >
      {lineas.map((l) => (
        <div key={l}>{l}</div>
      ))}
    </div>
  </div>
);

/** Una marca. Se traza desde su base: no aparece, crece. */
export const Trazo: React.FC<{
  x: number;
  y: number;
  p: number;
  oro?: boolean;
}> = ({ x, y, p, oro = false }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: MARCA.ancho,
      height: MARCA.alto,
      backgroundColor: oro ? color.gold : color.secondaryBlue,
      opacity: p,
      transform: `scaleY(${(0.18 + p * 0.82).toFixed(3)})`,
      transformOrigin: "bottom",
    }}
  />
);
