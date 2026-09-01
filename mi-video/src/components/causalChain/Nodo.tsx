import React from "react";
import { assertShort } from "../../brand/copy";
import { fontFamily } from "../../brand/fonts";
import {
  lineHeight,
  size,
  tracking,
  weight,
  type ModeTokens,
} from "../../brand/tokens";
import { Cifra, Etiqueta, Fuente } from "../Canon";
import type { CausalNode } from "./tipos";

const MARCA = 20;
const COLUMNA = 56;

/**
 * Cuadrado sin radio, bloque plano y filete: el sistema no tiene sombras ni
 * esquinas redondeadas, y el círculo suavizaría lo que debe leerse firme.
 */
const Marca: React.FC<{ progress: number; tokens: ModeTokens }> = ({
  progress,
  tokens,
}) => (
  <div
    style={{
      width: MARCA,
      height: MARCA,
      border: `2px solid ${tokens.accent}`,
      transform: `scale(${progress})`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}
  >
    <div
      style={{
        width: MARCA / 2.5,
        height: MARCA / 2.5,
        backgroundColor: tokens.accent,
        opacity: progress,
      }}
    />
  </div>
);

/**
 * Un eslabón de la cadena: marcador, conector y enunciado.
 *
 * El **conector baja desde este nodo y se traza justo antes de que aparezca el
 * siguiente**, así la línea guía la mirada hacia donde va a pasar algo en vez de
 * seguirla. Por eso su progreso llega de fuera: lo sabe el horario, no el nodo.
 */
export const Nodo: React.FC<{
  node: CausalNode;
  tokens: ModeTokens;
  /** Aire hasta el nodo siguiente. */
  gapPx: number;
  progress: number;
  conector: number;
  ultimo: boolean;
  /** Trato de remate: bloque de superficie con filo de acento y cuerpo mayor. */
  remate: boolean;
}> = ({ node, tokens, gapPx, progress, conector, ultimo, remate }) => (
  <div
    style={{
      display: "flex",
      flexDirection: "row",
      /**
       * Ninguna fila crece. Repartir el aire sobrante entre los nodos abre
       * huecos entre ellos y, mientras el tablero se construye, deja agujeros
       * reservados esperando contenido: en video eso lee como maqueta rota. La
       * pila se ancla arriba y el sobrante queda abajo, en un solo bloque.
       *
       * `0 0 auto` y no `0`: la abreviatura `flex: 0` fija `flex-basis: 0%` y
       * la fila colapsaría a altura cero.
       */
      flex: "0 0 auto",
      minHeight: 0,
    }}
  >
    {/* Columna de marcadores: el raíl vertical de la cadena. */}
    <div
      style={{
        width: COLUMNA,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        flexShrink: 0,
      }}
    >
      <Marca progress={progress} tokens={tokens} />
      {ultimo ? null : (
        <div
          style={{
            flex: 1,
            width: 2,
            marginTop: 12,
            backgroundColor: tokens.hairline,
            transform: `scaleY(${conector})`,
            transformOrigin: "top",
          }}
        />
      )}
    </div>

    <div
      style={{
        flex: 1,
        paddingBottom: ultimo ? 0 : gapPx,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 12}px)`,
      }}
    >
      <div
        style={{
          /**
           * Trato de prioridad del sistema: bloque plano de superficie con filo
           * de acento a la izquierda. Es el mismo recurso que marca el hallazgo
           * prioritario en las tarjetas de evidencia — no se inventa nada.
           */
          backgroundColor: remate ? tokens.surface : undefined,
          borderLeft: remate ? `3px solid ${tokens.accent}` : undefined,
          padding: remate ? "26px 30px 30px" : undefined,
        }}
      >
        <Etiqueta tinta={tokens.accent} style={{ marginBottom: 14 }}>
          {assertShort(node.stage, "label", "CausalChain.stage")}
        </Etiqueta>

        <div
          style={{
            fontFamily: fontFamily.display,
            fontSize: remate
              ? size.payoff
              : node.emphasis
                ? size.emphasis
                : size.nodeText,
            fontWeight:
              remate || node.emphasis ? weight.semibold : weight.regular,
            letterSpacing: tracking.display,
            lineHeight: lineHeight.displayM,
            color: tokens.text,
          }}
        >
          {assertShort(node.text, "statement", "CausalChain.text")}
        </div>

        {node.figure === undefined ? null : (
          <div style={{ marginTop: 24 }}>
            <Cifra tinta={tokens.accent}>{node.figure}</Cifra>
            <Fuente tinta={tokens.textSecondary} style={{ marginTop: 12 }}>
              {node.source}
            </Fuente>
          </div>
        )}
      </div>
    </div>
  </div>
);
