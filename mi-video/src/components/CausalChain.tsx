import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { MotionSound } from "./MotionSound";
import { CaptionBand } from "./CaptionBand";
import { Marco } from "./Canon";
import { Limite } from "./causalChain/Limite";
import { Nodo } from "./causalChain/Nodo";
import { horarioDe } from "./causalChain/horario";
import {
  accentChoice,
  duration,
  ease,
  gap as gaps,
  lineHeight,
  mode as modes,
  size,
  tone as tones,
  tracking,
  weight,
  type ModeTokens,
} from "../brand/tokens";
import type { CausalChainProps } from "./causalChain/tipos";

export type { CausalNode, CausalChainProps } from "./causalChain/tipos";

/**
 * La cadena causal: contexto → creencia → manifestación → consecuencia.
 *
 * El componente **dibuja y ata**. El contrato de cumplimiento vive en
 * `causalChain/tipos` —una cifra sin fuente no compila—, el calendario en
 * `causalChain/horario`, y el eslabón y el límite legal en sus ficheros.
  * @clase tablero
*/
export const CausalChain: React.FC<CausalChainProps> = ({
  nodes,
  mode = "evidence",
  tone = "base",
  accent,
  gap = "normal",
  revealAt,
  title,
  emphasizePayoff = true,
  limitation,
  caption,
  sound = false,
}) => {
  const entra = useEntrada();
  /**
   * Los tokens del modo, con el fondo y el acento sobrescribibles. El modo
   * sigue decidiendo quién habla; el tono y el acento solo varían la superficie
   * para que cincuenta piezas no se vean calcadas.
   */
  const base = modes[mode];
  const t: ModeTokens = {
    ...base,
    ground: tones[mode][tone],
    accent: accent ? accentChoice[accent] : base.accent,
  };
  const gapPx = gaps[gap];

  const horario = React.useMemo(
    () => horarioDe({ nodes, revealAt, emphasizePayoff, limitation }),
    [nodes, revealAt, emphasizePayoff, limitation],
  );
  const { limiteAt } = horario;

  /**
   * El tablero se retira cuando entra el límite legal. No comparten frame: un
   * legal que compite con el argumento no se lee, y con la banda de subtítulos
   * reservada tampoco cabría. Sin límite declarado no hay retirada — antes la
   * había igual y la pieza acababa en negro.
   */
  const limiteEntra = limiteAt === null ? 0 : entra(limiteAt);

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <Marco style={{ opacity: 1 - limiteEntra }}>
        {title ? (
          <div
            style={{
              fontFamily: fontFamily.display,
              fontSize: size.displayL,
              fontWeight: weight.semibold,
              /** Caja mixta y tracking negativo: las versales son de la mono. */
              letterSpacing: tracking.display,
              lineHeight: lineHeight.displayL,
              color: t.text,
              marginBottom: gapPx,
            }}
          >
            {assertShort(title, "title", "CausalChain.title")}
          </div>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column" }}>
          {nodes.map((node, index) => {
            const siguiente = horario.at[index + 1] ?? 0;
            return (
              <Nodo
                key={node.stage}
                node={node}
                tokens={t}
                gapPx={gapPx}
                progress={entra(horario.at[index] ?? 0)}
                conector={entra(
                  siguiente - duration.standard,
                  duration.standard,
                  ease.linear,
                )}
                ultimo={index === nodes.length - 1}
                remate={emphasizePayoff && index === nodes.length - 1}
              />
            );
          })}
        </div>
      </Marco>

      {caption ? <CaptionBand text={caption} tokens={t} /> : null}

      {limitation !== undefined && limiteAt !== null ? (
        <Limite text={limitation} tokens={t} progress={limiteEntra} />
      ) : null}

      {/**
       * El sonido se emite en el mismo frame que el movimiento que lo produce.
       * Cada marcador es un clic; el remate, un golpe. No hay pista de audio
       * aparte porque estos tiempos se derivan de la lectura y del transcript:
       * una pista aparte se desincronizaría al primer ajuste de copy.
       */}
      {sound
        ? nodes.map((node, index) => (
            <MotionSound
              key={node.stage}
              motion={
                emphasizePayoff && index === nodes.length - 1 ? "land" : "mark"
              }
              at={horario.at[index] ?? 0}
            />
          ))
        : null}
    </AbsoluteFill>
  );
};
