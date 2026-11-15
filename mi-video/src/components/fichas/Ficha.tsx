import React from "react";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe } from "../../brand/medida";
import { color, size, tracking } from "../../brand/tokens";
import type { Linea } from "../declarado/lineas";

/**
 * **Una ficha: un bloque plano con su rótulo y su frase.**
 *
 * Es la unidad del canon que más se repite en las 26 láminas y la que no
 * existía en código: bloque de color liso, el oficio o el número arriba en
 * cuerpo pequeño, el hecho debajo en versales condensadas. Sin sombra, sin
 * esquina redondeada y sin degradado — lo que separa una ficha de la siguiente
 * es un filete, y lo pone quien las apila.
 *
 * **Entra en diagonal desde el borde**, no aparece. Es lo que pidió el encargo
 * de reel-05 e2 —*«dos fichas rectangulares que entran en diagonal desde el
 * borde derecho y se apilan junto a él»*— y es transformar, que es la familia de
 * animación más barata y la que menos se nota: sostiene el ritmo sin llamar la
 * atención sobre sí misma.
 */
export const Ficha: React.FC<{
  linea: Linea;
  /** Su número en la lista, si la forma va numerada. Base 1. */
  indice?: number;
  alto: number;
  ancho: number;
  /** Progreso de entrada, 0→1. Lo reparte el horario de la forma. */
  progreso: number;
  /** Alterna la superficie de las fichas que no son la de oro. */
  alterna?: boolean;
  /**
   * **El filete de lectura, 0→1** (C-701): una raya que recorre el pie de la
   * ficha mientras es la que se está diciendo, hasta que entra la siguiente —y
   * la última, hasta que la lámina acaba—. Es lo que hace que una lista nunca
   * se quede clavada entre entrada y entrada: emisión midió 4,3 s quietos en
   * reel-23 e5 con las cuatro filas ya dentro. Lo reparte quien apila.
   */
  lectura?: number;
}> = ({ linea, indice, alto, ancho, progreso, alterna = false, lectura = 0 }) => {
  const tinta = linea.oro ? color.richBlack : color.lightNeutral;
  const menor = linea.oro ? color.richBlack : color.secondaryBlue;
  // El cuerpo cede antes que el texto: el avance de la Anton lo declara
  // `brand/medida`, medido sobre render y escrito en un solo sitio.
  // El relleno cede con la ficha: 48 px a cada lado dentro de una condición de
  // 314 px de ancho se come un tercio del hueco y baja el cuerpo a 23 px, por
  // debajo del mínimo práctico. En una ficha ancha 48 es el aire que pide.
  const relleno = Math.min(48, Math.round(ancho * 0.06));
  const cuerpo = cuerpoQueCabe({
    ancho: ancho - relleno * 2,
    largo: linea.texto.length,
    registro: "anton",
    tope: Math.min(96, Math.round(alto * (linea.etiqueta || indice ? 0.46 : 0.6))),
  });

  return (
    <div
      style={{
        position: "relative",
        width: ancho,
        height: alto,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 10,
        padding: `0 ${relleno}px`,
        boxSizing: "border-box",
        backgroundColor: linea.oro
          ? color.gold
          : alterna
            ? color.navyHi
            : color.navy,
        opacity: progreso,
        // Diagonal desde el borde derecho: se desplaza y sube a la vez, así que
        // el recorrido es una diagonal y no dos movimientos rectos seguidos.
        transform: `translate(${((1 - progreso) * 300).toFixed(1)}px, ${
          ((1 - progreso) * -54).toFixed(1)
        }px)`,
      }}
    >
      {indice || linea.etiqueta ? (
        <div
          style={{
            fontFamily: fontFamily.data,
            fontSize: size.labelMono,
            letterSpacing: tracking.labelMono,
            textTransform: "uppercase",
            color: menor,
            whiteSpace: "nowrap",
            overflow: "hidden",
          }}
        >
          {indice ? String(indice).padStart(2, "0") : null}
          {indice && linea.etiqueta ? "  ·  " : null}
          {linea.etiqueta}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: fontFamily.bloque,
          fontSize: cuerpo,
          lineHeight: 0.98,
          letterSpacing: "0.004em",
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          color: tinta,
        }}
      >
        {linea.texto}
      </div>
      {lectura > 0 && lectura < 1 ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            bottom: 0,
            height: 4,
            width: `${(lectura * 100).toFixed(2)}%`,
            backgroundColor: linea.oro ? color.richBlack : color.gold,
          }}
        />
      ) : null}
    </div>
  );
};

/**
 * El filete que separa dos fichas. **Nunca una sombra ni un hueco**: el canon
 * separa bloques planos con una raya de un píxel, y el hueco deja ver el fondo,
 * que es otra cosa distinta.
 */
export const FileteFicha: React.FC<{ vertical?: boolean; largo: number }> = ({
  vertical = false,
  largo,
}) => (
  <div
    style={{
      width: vertical ? 2 : largo,
      height: vertical ? largo : 2,
      backgroundColor: color.secondaryBlue,
      opacity: 0.55,
      flexShrink: 0,
    }}
  />
);
