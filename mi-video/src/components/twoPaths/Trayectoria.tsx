import React from "react";
import { assertShort } from "../../brand/copy";
import type { Entrada } from "../../brand/horario";
import { fontFamily } from "../../brand/fonts";
import {
  lineHeight,
  size,
  tracking,
  weight,
  type ModeTokens,
} from "../../brand/tokens";
import { Cifra, Etiqueta, Fuente } from "../Canon";
import type { ComparedPath } from "./tipos";

/**
 * Una de las dos columnas: etiqueta, pasos y remate, con el raíl al costado.
 *
 * El raíl **crece conforme se recorren los pasos**: es el camino siendo andado,
 * no un borde decorativo. Por eso su progreso llega de fuera y en lineal — lo
 * calcula el horario, que es quien sabe dónde empieza y acaba la trayectoria.
 */
export const Trayectoria: React.FC<{
  path: ComparedPath;
  tokens: ModeTokens;
  ink: string;
  /** Frame de entrada de cada paso. Uno por paso, en orden. */
  stepAt: number[];
  railProgress: number;
  outcomeProgress: number;
  entra: Entrada;
  emphasized?: boolean;
}> = ({
  path,
  tokens,
  ink,
  stepAt,
  railProgress,
  outcomeProgress,
  entra,
  emphasized = false,
}) => (
  <div
    style={{
      flex: 1,
      minWidth: 0,
      position: "relative",
      backgroundColor: tokens.ground,
      padding: "26px 26px 26px 29px",
      display: "flex",
      flexDirection: "column",
    }}
  >
    {/* El raíl: el camino recorrido hasta ahora. */}
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        bottom: 0,
        width: emphasized ? 3 : 2,
        backgroundColor: ink,
        transform: `scaleY(${railProgress})`,
        transformOrigin: "top",
      }}
    />

    <div style={{ opacity: entra(stepAt[0] ?? 0) }}>
      <Etiqueta tinta={ink}>
        {assertShort(path.label, "label", "TwoPaths.label")}
      </Etiqueta>
    </div>

    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        marginTop: 20,
        flex: 1,
      }}
    >
      {path.steps.map((step, index) => {
        const progress = entra(stepAt[index] ?? 0);
        return (
          <div
            key={step}
            style={{
              fontFamily: fontFamily.body,
              fontSize: size.step,
              lineHeight: 1.45,
              color: tokens.textSecondary,
              opacity: progress,
              transform: `translateY(${(1 - progress) * 10}px)`,
            }}
          >
            {assertShort(step, "statement", "TwoPaths.step")}
          </div>
        );
      })}
    </div>

    <div
      style={{
        marginTop: 22,
        paddingTop: 18,
        borderTop: `1px solid ${tokens.hairline}`,
        opacity: outcomeProgress,
      }}
    >
      <div
        style={{
          fontFamily: fontFamily.display,
          fontSize: size.body,
          fontWeight: emphasized ? weight.semibold : weight.regular,
          letterSpacing: tracking.display,
          lineHeight: lineHeight.displayM,
          color: tokens.text,
          /**
           * Reserva de dos líneas para que los filetes de resultado queden a la
           * misma altura en ambas columnas. Sin esto los bloques se anclan
           * abajo, el resultado de dos líneas sube su filete y el de una lo
           * baja: el ojo deja de comparar como con como, que es lo único que
           * este tablero tiene que hacer.
           */
          minHeight: size.body * lineHeight.displayM * 2,
        }}
      >
        {assertShort(path.outcome, "outcome", "TwoPaths.outcome")}
      </div>

      {path.figure === undefined ? null : (
        <>
          <Cifra tinta={ink} style={{ marginTop: 14 }}>
            {path.figure}
          </Cifra>
          <Fuente tinta={tokens.textSecondary} style={{ marginTop: 10 }}>
            {path.source}
          </Fuente>
        </>
      )}
    </div>
  </div>
);
