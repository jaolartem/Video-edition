import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { CausalChain, type CausalChainProps } from "./components/CausalChain";
import { Comparacion, type ComparacionProps } from "./components/Comparacion";
import { Acumulacion, type AcumulacionProps } from "./components/Acumulacion";
import { TwoPaths, type TwoPathsProps } from "./components/TwoPaths";
import { TableroDeclarado } from "./components/TableroDeclarado";
import { CaptionBand, type Compuesto } from "./components/CaptionBand";
import { color } from "./brand/tokens";
import { mode as modes, type Mode } from "./brand/tokens";

/**
 * Un tablero programado sobre el vídeo.
 *
 * Mientras está activo **ocupa el frame entero**, no se superpone en una
 * esquina: el tablero ES el plano. Es la decisión que reconcilia el ritmo de
 * corte con la explicación — cada cambio de estado del tablero cuenta como
 * cambio de toma, así que el pulso se mantiene sin abandonar el argumento.
 */
export type BoardCue =
  | { at: number; duration: number; kind: "causal"; props: CausalChainProps }
  | { at: number; duration: number; kind: "twopaths"; props: TwoPathsProps }
  | { at: number; duration: number; kind: "comparacion"; props: ComparacionProps }
  | { at: number; duration: number; kind: "acumulacion"; props: AcumulacionProps }
  /**
   * **Cualquier otra forma que el diseñador declare.**
   *
   * Regla de Jaime: *«hay que conectar al diseñador con el render»*, después de
   * tres ciclos de cambios duros con el mismo vídeo. La causa era ésta: la unión
   * tenía cuatro miembros, el diseño usó veintitrés, y las otras diecinueve
   * caían por el final del ternario **sin dibujar nada y sin decirlo**.
   *
   * Cerrar la lista aquí convertía el catálogo de componentes en el techo del
   * diseño. Ahora la forma declarada entra siempre: si tiene componente propio
   * lo usa, y si no, `TableroDeclarado` dibuja su copy con la jerarquía y la
   * familia que el diseñador puso. Que exista un componente a medida es una
   * mejora, no el requisito para aparecer.
   */
  | { at: number; duration: number; kind: string; props: Record<string, unknown> };

export type CaptionCue = {
  at: number;
  duration: number;
  text: string;
  /** Se oye una cosa y se lee la correcta. Ver `CaptionBand`. */
  corrige?: { dice: string; es: string };
  /** Que la correccion palpite. Ver `Corregida` en `CaptionBand`. */
  palpita?: boolean;
  /** La frase que crece al decirse. Ver `realza` en `CaptionBand`. */
  realza?: string;
  /** Dos renglones con dos fuentes. Ver `Compuesto` en `CaptionBand`. */
  compuesto?: Compuesto;
};

/**
 * Tramo en blanco y negro: **la marca de humanidad**.
 *
 * Jaime, sobre una cifra mal dicha: *«deja el 550 y señala el error, ponme en
 * blanco y negro»*. El desliz no se tapa ni se corrige por encima — se marca, y
 * la marca es la broma. Un desliz reconocido cuesta dos segundos y compra
 * credibilidad; taparlo cuesta el material bueno que lo rodea.
 *
 * Va con el subtítulo corregido, que es la otra mitad: se oye una cosa y se lee
 * la que es. Las dos capas son **una sola marca**, no dos — y la tasa es de una
 * o dos por minuto, así que en estas piezas es una.
 */
export type Desatura = { at: number; duration: number };

/**
 * **El glitch que tapa un corte.**
 *
 * Jaime: *«lo ideal del corte y del cambio de escena es que no se note… se puede
 * poner una transición discreta, algo que no sea un brillo; un efecto glitch por
 * ejemplo, que distorsione la imagen y el sonido como un TV antiguo cuando
 * cambiaba de canal, durante poco tiempo, con el respectivo ruido»*.
 *
 * Funciona porque **no oculta el corte: lo sustituye por otra cosa**. El ojo
 * registra la distorsión, no el salto de encuadre — y como dura tres frames, lo
 * que queda es la sensación de continuidad, no la de efecto.
 *
 * Va **centrado en la costura**, no después: la mitad antes y la mitad después,
 * para que el corte caiga dentro de la distorsión y no en su borde.
 */
export type Glitch = { at: number; duration: number };

export type AdProps = {
  /**
   * Proxy del vídeo ya cortado, en `public/`. Se trabaja con proxy y no con el
   * bruto: el original es 4K HEVC de varios gigas y decodificarlo por frame para
   * componer encima multiplica el tiempo de render sin aportar nada — la salida
   * es 1080×1920 igualmente.
   */
  video: string;
  mode?: Mode;
  boards?: BoardCue[];
  captions?: CaptionCue[];
  desatura?: Desatura[];
  glitch?: Glitch[];
};

export const Ad: React.FC<AdProps> = ({
  video,
  mode = "evidence",
  boards = [],
  captions = [],
  desatura = [],
  glitch = [],
}) => {
  const frame = useCurrentFrame();
  const t = modes[mode];

  /**
   * Cuánto glitch hay en este frame, de 0 a 1. Sube y baja dentro del tramo:
   * un valor constante se leería como un filtro puesto, y esto es un tropiezo
   * de la señal.
   */
  const g = glitch.reduce((n, q) => {
    if (frame < q.at || frame >= q.at + q.duration) return n;
    const t = (frame - q.at) / q.duration;
    // Triangular, con el pico justo en la costura.
    return Math.max(n, 1 - Math.abs(t - 0.5) * 2);
  }, 0);

  /** El subtítulo activo. Es capa portante: el argumento funciona sin audio. */
  const caption = captions.find(
    (c) => frame >= c.at && frame < c.at + c.duration,
  );

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <OffthreadVideo
        src={staticFile(video)}
        style={{
          ...(desatura.some((d) => frame >= d.at && frame < d.at + d.duration)
            ? // Sin transición: el corte a blanco y negro tiene que notarse.
              // Un fundido lo convertiría en un efecto y aquí es un comentario.
              { filter: "grayscale(1) contrast(1.15)" }
            : {}),
          ...(g > 0
            ? {
                // Desplazamiento horizontal y salto de color: la señal que se
                // rompe un instante. La escala evita que asome el borde negro.
                transform: `translateX(${(g * 26).toFixed(2)}px) scale(${(1 + g * 0.04).toFixed(4)})`,
                filter: `saturate(${(1 + g * 1.8).toFixed(2)}) contrast(${(1 + g * 0.5).toFixed(2)})`,
              }
            : {}),
        }}
      />

      {boards.map((cue, i) => (
        <Sequence
          key={`${cue.at}-${i}`}
          from={cue.at}
          durationInFrames={cue.duration}
        >
          {/* Cada estructura tiene su tablero. Un mismo componente en cuatro
              frameworks distintos hace que los cuatro se vean iguales, y
              entonces el tablero deja de significar nada. */}
          {cue.kind === "causal" ? (
            <CausalChain {...(cue.props as CausalChainProps)} mode={mode} />
          ) : cue.kind === "comparacion" ? (
            <Comparacion {...(cue.props as ComparacionProps)} />
          ) : cue.kind === "acumulacion" ? (
            <Acumulacion {...(cue.props as AcumulacionProps)} />
          ) : cue.kind === "twopaths" ? (
            <TwoPaths {...(cue.props as TwoPathsProps)} mode={mode} />
          ) : (
            /* **Y lo demás también se dibuja.** Aquí caían diecinueve formas
               declaradas por el diseñador y no salía nada — ni en pantalla ni
               en el log. `TwoPaths` era el `else`, así que una forma que no
               fuera ninguna de las tres primeras se intentaba dibujar como dos
               trayectorias y reventaba o salía vacía. */
            <TableroDeclarado
              kind={cue.kind}
              props={cue.props as Record<string, unknown>}
            />
          )}
        </Sequence>
      ))}

      {/* Bandas de ruido: lo que hace que se lea como señal y no como zoom. */}
      {g > 0 ? (
        <AbsoluteFill style={{ pointerEvents: "none", opacity: g * 0.55 }}>
          {[0.18, 0.42, 0.71].map((y, i) => (
            <div
              key={y}
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: `${(y + g * 0.05 * (i % 2 ? 1 : -1)) * 100}%`,
                height: `${2 + i}%`,
                backgroundColor: i === 1 ? color.gold : color.lightNeutral,
                mixBlendMode: "overlay",
                transform: `translateX(${(g * (i % 2 ? -40 : 34)).toFixed(1)}px)`,
              }}
            />
          ))}
        </AbsoluteFill>
      ) : null}

      {caption ? (
        <CaptionBand
          text={caption.text}
          tokens={t}
          corrige={caption.corrige}
          palpita={caption.palpita}
          realza={caption.realza}
          compuesto={caption.compuesto}
          desde={caption.at}
        />
      ) : null}
    </AbsoluteFill>
  );
};
