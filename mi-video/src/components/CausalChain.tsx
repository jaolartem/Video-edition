import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { MotionSound } from "./MotionSound";
import { CaptionBand } from "./CaptionBand";
import { franja } from "../brand/franja";
import {
  accentChoice,
  beat,
  duration,
  gap as gaps,
  tone as tones,
  ease,
  layout,
  lineHeight,
  mode as modes,
  readingFrames,
  size,
  tracking,
  weight,
  type Accent,
  type Mode,
  type ModeTokens,
  type Tone,
} from "../brand/tokens";

type CausalNodeBase = {
  /** Etapa del framework, p.ej. "Contexto institucional". */
  stage: string;
  /** El enunciado de esa etapa, en español nativo. */
  text: string;
  /**
   * Marca este nodo como el hecho relevante del tablero: sube de cuerpo y toma
   * el color de texto pleno. Es independiente del remate — a veces lo que hay
   * que agrandar está en mitad de la cadena, no al final.
   */
  emphasis?: boolean;
};

/**
 * Cumplimiento por construcción.
 *
 * El playbook exige que toda cifra lleve contexto y fuente fiable. La unión
 * discriminada convierte el incumplimiento en un error de compilación: un nodo
 * con `figure` y sin `source` no compila. No hay forma de olvidar la
 * atribución, que es justo el error que nadie detecta revisando 50 ads.
 */
export type CausalNode =
  | (CausalNodeBase & { figure?: never; source?: never })
  | (CausalNodeBase & { figure: string; source: string });

export type CausalChainProps = {
  /**
   * Los nodos de la cadena. La secuencia rectora del playbook tiene cuatro:
   * contexto institucional → creencia adaptativa → manifestación financiera →
   * consecuencia. Tres a cinco funcionan; más no cabe legible en 9:16.
   */
  nodes: CausalNode[];
  /**
   * Modo del sistemal canon. **Nunca se mezclan dentro de una pieza**: la superficie
   * declara quién habla. `evidence` para EDUCATE, SOCIAL PROOF y SELL —
   * hablan los datos. `guide` para CONNECT — habla Jaime.
   */
  mode?: Mode;
  /** Superficie sobre la que se dibuja. Da variedad entre piezas. */
  tone?: Tone;
  /** Acento del tablero. El oro sigue siendo lo que hay que atender. */
  accent?: Accent;
  /** Aire entre nodos. `loose` para tableros de tres nodos o menos. */
  gap?: keyof typeof gaps;
  /**
   * Frame en que se revela cada nodo, anclado a palabras concretas del
   * transcript. Es lo que se usa en montaje final. Sin esto, el calendario se
   * deriva del tiempo de lectura de cada enunciado.
   */
  revealAt?: number[];
  title?: string;
  /**
   * El último nodo de una cadena causal no es uno más: es la consecuencia. Por
   * defecto recibe trato de remate —pausa antes, bloque de superficie con filo
   * de acento y cuerpo mayor— porque una cadena a ritmo plano informa pero no
   * aprieta. Se desactiva solo si la pieza no cierra en consecuencia.
   */
  emphasizePayoff?: boolean;
  /**
   * El `scope and limitation` que piden los frameworks. Es un slot del
   * componente y no texto opcional del libreto, para que no se caiga en el
   * montaje.
   *
   * Llega con **beat propio al final**, no de adorno permanente al pie. Un
   * límite legal que comparte pantalla con el argumento durante todo el plano
   * no se lee: es ruido. Con beat propio se lee, que es de lo que se trata.
   */
  limitation?: string;
  /**
   * Subtítulo visible en la franja inferior. En producción sale del SRT de
   * CapCut; aquí se pasa a mano para ver la composición real de la pieza.
   */
  caption?: string;
  /**
   * Emite el efecto de sonido de cada movimiento. **Requiere los ficheros de
   * `public/sfx/`**, que aún no existen — por eso está apagado por defecto.
   */
  sound?: boolean;
};

const MARKER = 20;
const MARKER_COLUMN = 56;

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
  const frame = useCurrentFrame();
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

  /**
   * Calendario por defecto derivado del TIEMPO DE LECTURA, no de un stagger
   * fijo. Un enunciado largo necesita más pantalla que uno corto; repartir a
   * intervalos iguales deja unos ilegibles y otros muertos.
   */
  const schedule = React.useMemo(() => {
    const at: number[] = [];
    let cursor = 0;
    nodes.forEach((node, index) => {
      const isPayoff = emphasizePayoff && index === nodes.length - 1;
      if (isPayoff && nodes.length > 1) {
        cursor += beat.hold;
      }
      at.push(revealAt?.[index] ?? cursor);
      cursor = (revealAt?.[index] ?? cursor) + readingFrames(node.text);
      cursor += beat.stagger;
    });
    return { at, limitationAt: cursor + beat.hold };
  }, [nodes, revealAt, emphasizePayoff]);

  const appearFrame = (index: number): number => schedule.at[index] ?? 0;

  /** Entrada de un elemento: llega y se queda. Sin rebote, sin sobrepaso. */
  const nodeProgress = (index: number): number => {
    const at = appearFrame(index);
    return interpolate(frame, [at, at + duration.entry], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });
  };

  /**
   * El conector que baja DESDE el nodo `index` se traza justo antes de que
   * aparezca el siguiente, así la línea guía la mirada hacia donde va a pasar
   * algo en vez de seguirla.
   */
  const connectorProgress = (index: number): number => {
    const next = appearFrame(index + 1);
    return interpolate(frame, [next - duration.standard, next], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.linear,
    });
  };

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <AbsoluteFill
        style={{
          /**
           * El tablero se retira cuando entra el límite legal. No comparten
           * frame: un legal que compite con el argumento no se lee, y con la
           * banda de subtítulos reservada tampoco cabría.
           */
          opacity: interpolate(
            frame,
            [schedule.limitationAt, schedule.limitationAt + duration.entry],
            [1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: ease.out,
            },
          ),
          paddingTop: layout.safe.top,
          /** Se descuenta la banda de subtítulos: también se ven. */
          paddingBottom: franja.reserva,
          paddingLeft: layout.safe.left,
          paddingRight: layout.safe.right,
          display: "flex",
          flexDirection: "column",
        }}
      >
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
            const progress = nodeProgress(index);
            const isLast = index === nodes.length - 1;
            const isPayoff = emphasizePayoff && isLast;

            return (
              <div
                key={node.stage}
                style={{
                  display: "flex",
                  flexDirection: "row",
                  /**
                   * Ninguna fila crece. Repartir el aire sobrante entre los
                   * nodos abre huecos entre ellos y, mientras el tablero se
                   * construye, deja agujeros reservados esperando contenido:
                   * en video eso lee como maqueta rota. La pila se ancla
                   * arriba y el sobrante queda abajo, en un solo bloque.
                   *
                   * `0 0 auto` y no `0`: la abreviatura `flex: 0` fija
                   * `flex-basis: 0%` y la fila colapsaría a altura cero.
                   */
                  flex: "0 0 auto",
                  minHeight: 0,
                }}
              >
                {/* Columna de marcadores: el raíl vertical de la cadena. */}
                <div
                  style={{
                    width: MARKER_COLUMN,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <Marker progress={progress} tokens={t} />
                  {isLast ? null : (
                    <div
                      style={{
                        flex: 1,
                        width: 2,
                        marginTop: 12,
                        backgroundColor: t.hairline,
                        transform: `scaleY(${connectorProgress(index)})`,
                        transformOrigin: "top",
                      }}
                    />
                  )}
                </div>

                <div
                  style={{
                    flex: 1,
                    paddingBottom: isLast ? 0 : gapPx,
                    opacity: progress,
                    transform: `translateY(${(1 - progress) * 12}px)`,
                  }}
                >
                  <div
                    style={{
                      /**
                       * Trato de prioridad del sistema: bloque plano de
                       * superficie con filo de acento a la izquierda. Es el
                       * mismo recurso que marca el hallazgo prioritario en las
                       * tarjetas de evidencia — no se inventa nada.
                       */
                      backgroundColor: isPayoff ? t.surface : undefined,
                      borderLeft: isPayoff ? `3px solid ${t.accent}` : undefined,
                      padding: isPayoff ? "26px 30px 30px" : undefined,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: fontFamily.data,
                        fontSize: size.labelMono,
                        fontWeight: weight.medium,
                        letterSpacing: tracking.labelMono,
                        textTransform: "uppercase",
                        color: t.accent,
                        marginBottom: 14,
                      }}
                    >
                      {assertShort(node.stage, "label", "CausalChain.stage")}
                    </div>

                    <div
                      style={{
                        fontFamily: fontFamily.display,
                        fontSize: isPayoff
                          ? size.payoff
                          : node.emphasis
                            ? size.emphasis
                            : size.nodeText,
                        fontWeight:
                          isPayoff || node.emphasis
                            ? weight.semibold
                            : weight.regular,
                        letterSpacing: tracking.display,
                        lineHeight: lineHeight.displayM,
                        color: t.text,
                      }}
                    >
                      {assertShort(node.text, "statement", "CausalChain.text")}
                    </div>

                    {node.figure === undefined ? null : (
                      <Figure
                        figure={node.figure}
                        source={node.source}
                        tokens={t}
                      />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

      </AbsoluteFill>

      {caption ? <CaptionBand text={caption} tokens={t} /> : null}

      {limitation ? (
        <Limitation
          text={limitation}
          tokens={t}
          progress={interpolate(
            frame,
            [schedule.limitationAt, schedule.limitationAt + duration.entry],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: ease.out,
            },
          )}
        />
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
              at={appearFrame(index)}
            />
          ))
        : null}
    </AbsoluteFill>
  );
};

/**
 * Cuadrado sin radio, bloque plano y filete: el sistema no tiene sombras ni
 * esquinas redondeadas, y el círculo suavizaría lo que debe leerse firme.
 */
const Marker: React.FC<{ progress: number; tokens: ModeTokens }> = ({
  progress,
  tokens,
}) => (
  <div
    style={{
      width: MARKER,
      height: MARKER,
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
        width: MARKER / 2.5,
        height: MARKER / 2.5,
        backgroundColor: tokens.accent,
        opacity: progress,
      }}
    />
  </div>
);

/**
 * Una cifra nunca aparece sin su fuente: el tipo lo garantiza.
 * Va en Playfair y no en mono — el sistema da a las cifras trato editorial.
 */
const Figure: React.FC<{
  figure: string;
  source: string;
  tokens: ModeTokens;
}> = ({ figure, source, tokens }) => (
  <div style={{ marginTop: 24 }}>
    <div
      style={{
        fontFamily: fontFamily.display,
        fontSize: size.displayL,
        fontWeight: weight.semibold,
        letterSpacing: tracking.display,
        color: tokens.accent,
        lineHeight: 1,
      }}
    >
      {figure}
    </div>
    <div
      style={{
        fontFamily: fontFamily.data,
        fontSize: size.source,
        letterSpacing: tracking.labelMono,
        textTransform: "uppercase",
        color: tokens.textSecondary,
        marginTop: 12,
      }}
    >
      {source}
    </div>
  </div>
);

/**
 * El límite legal, en su propio frame.
 *
 * Un `scope and limitation` al pie del tablero no se lee: compite con el
 * argumento y con el subtítulo. Con frame propio se lee, que es exactamente lo
 * que el playbook pide de él — y de paso resuelve que una cadena de cuatro
 * nodos más titular más legal más subtítulo no cabe en 9:16.
 */
const Limitation: React.FC<{
  text: string;
  tokens: ModeTokens;
  progress: number;
}> = ({ text, tokens, progress }) => (
  <AbsoluteFill
    style={{
      paddingTop: layout.safe.top,
      paddingBottom: franja.reserva,
      paddingLeft: layout.safe.left,
      paddingRight: layout.safe.right,
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      opacity: progress,
    }}
  >
    <div
      style={{
        fontFamily: fontFamily.data,
        fontSize: size.labelMono,
        fontWeight: weight.medium,
        letterSpacing: tracking.labelMono,
        textTransform: "uppercase",
        color: tokens.accent,
        marginBottom: 28,
      }}
    >
      Alcance y límite
    </div>
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
  </AbsoluteFill>
);
