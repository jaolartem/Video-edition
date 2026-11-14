import React from "react";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe } from "../../brand/medida";
import { color } from "../../brand/tokens";
import { useLienzo } from "../../brand/LienzoContexto";
import type { Lienzo } from "../../brand/lienzo";

/** Ancho de cada cuenta en su lienzo. Dos columnas, un filete de 24 px entre ellas. */
export const anchoEn = (layout: Lienzo): number =>
  (layout.width - layout.safe.left - layout.safe.right - 24) / 2;

/**
 * Una cuenta: etiqueta arriba, cifra grande, condición debajo.
 *
 * `oro` marca cuál es la que el espectador debe mirar. En el canon la
 * distinción entre lo que se atiende y lo que no se hace **con oro contra
 * navy**, nunca con semáforo — no hay rojo en el sistema.
 *
 * Vivía declarada **dentro del cuerpo de `CtaCard`**, así que se redefinía en
 * cada render y se llevaba `ancho` por cierre en vez de por prop: la geometría
 * de una columna dependía de dónde estuviera escrita.
 */
export const Cuenta: React.FC<{
  etiqueta: string;
  cifra: string;
  pie?: string;
  tachado?: string;
  oro?: boolean;
  /** Progreso de entrada, 0→1. Lo calcula el horario. */
  progreso: number;
}> = ({ etiqueta, cifra, pie, tachado, oro, progreso }) => {
  const ANCHO = anchoEn(useLienzo());
  return (
    <div
      style={{
        width: ANCHO,
        minHeight: 420,
        backgroundColor: oro ? color.gold : color.navy,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 22,
        padding: "34px 26px",
        opacity: progreso,
        transform: `translateY(${((1 - progreso) * 26).toFixed(1)}px)`,
      }}
    >
      <div
        style={{
          fontFamily: fontFamily.bloque,
          fontSize: 42,
          lineHeight: 1.02,
          textAlign: "center",
          textTransform: "uppercase",
          color: oro ? color.richBlack : color.secondaryBlue,
        }}
      >
        {etiqueta}
      </div>
      {tachado ? (
        <div
          style={{
            fontFamily: fontFamily.bloque,
            fontSize: 44,
            textDecoration: "line-through",
            textTransform: "uppercase",
            color: oro ? color.richBlack : color.secondaryBlue,
            opacity: 0.75,
          }}
        >
          {tachado}
        </div>
      ) : null}
      <div
        style={{
          fontFamily: fontFamily.bloque,
          // El avance de la Anton lo declara `brand/medida`, medido sobre render.
          // El margen se paga en cuerpo, que es barato.
          fontSize: cuerpoQueCabe({
            ancho: ANCHO - 52,
            largo: cifra.length,
            registro: "anton",
            tope: 156,
          }),
          lineHeight: 0.94,
          whiteSpace: "nowrap",
          textTransform: "uppercase",
          color: oro ? color.richBlack : color.lightNeutral,
        }}
      >
        {cifra}
      </div>
      {pie ? (
        <div
          style={{
            fontFamily: fontFamily.video,
            fontSize: 28,
            fontWeight: 800,
            lineHeight: 1.2,
            textAlign: "center",
            textTransform: "uppercase",
            letterSpacing: "0.02em",
            color: oro ? color.richBlack : color.secondaryBlue,
          }}
        >
          {pie}
        </div>
      ) : null}
    </div>
  );
};
