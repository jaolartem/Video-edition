import React from "react";
import { assertShort } from "../../brand/copy";
import { fontFamily } from "../../brand/fonts";
import { lineHeight, size, type ModeTokens } from "../../brand/tokens";
import { Etiqueta, Marco } from "../Canon";

/**
 * El límite legal, en su propio frame.
 *
 * Un `scope and limitation` al pie del tablero no se lee: compite con el
 * argumento y con el subtítulo. Con frame propio se lee, que es exactamente lo
 * que el playbook pide de él — y de paso resuelve que una cadena de cuatro
 * nodos más titular más legal más subtítulo no cabe en 9:16.
 */
export const Limite: React.FC<{
  text: string;
  tokens: ModeTokens;
  progress: number;
}> = ({ text, tokens, progress }) => (
  <Marco style={{ justifyContent: "center", opacity: progress }}>
    <Etiqueta tinta={tokens.accent} style={{ marginBottom: 28 }}>
      Alcance y límite
    </Etiqueta>
    <div
      style={{
        fontFamily: fontFamily.body,
        fontSize: size.body,
        lineHeight: lineHeight.body,
        color: tokens.text,
      }}
    >
      {assertShort(text, "legal", "CausalChain.limitation")}
    </div>
  </Marco>
);
