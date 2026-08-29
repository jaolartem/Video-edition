import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import {
  duration,
  ease,
  layout,
  lineHeight,
  mode as modes,
  size,
  tracking,
  weight,
  accentChoice,
  tone as tones,
  type Accent,
  type Mode,
  type Tone,
} from "../brand/tokens";

export type CoverProps = {
  /**
   * El gancho del reel. Es la primera línea hablada, no un título inventado:
   * la portada y la voz tienen que decir lo mismo o el espectador siente el
   * cambiazo en el primer segundo.
   */
  hook: string;
  /** Etiqueta de serie, en versales. */
  kicker?: string;
  mode?: Mode;
  tone?: Tone;
  accent?: Accent;
};

/**
 * Portada del reel.
 *
 * Tiene que funcionar en dos sitios a la vez: como **primer fotograma en
 * movimiento** y como **miniatura estática** en la parrilla del perfil. Por eso
 * el estado final es legible por sí solo y la animación solo lo construye — si
 * hiciera falta ver el movimiento para entenderla, fallaría como miniatura, que
 * es donde se decide si alguien entra.
 *
 * Sin logo, por decisión de Jaime. La identidad la carga la tipografía.
 */
export const Cover: React.FC<CoverProps> = ({
  hook,
  kicker,
  mode = "evidence",
  tone = "base",
  accent,
}) => {
  const frame = useCurrentFrame();
  const base = modes[mode];
  const t = {
    ...base,
    ground: tones[mode][tone],
    accent: accent ? accentChoice[accent] : base.accent,
  };

  const enter = (at: number) =>
    interpolate(frame, [at, at + duration.entry], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });

  /** El filete se traza; el texto llega detrás. El orden guía la mirada. */
  const rule = interpolate(frame, [0, duration.standard * 2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease.linear,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <AbsoluteFill
        style={{
          paddingTop: layout.safe.top,
          paddingBottom: layout.safe.bottom,
          paddingLeft: layout.safe.left,
          paddingRight: layout.safe.right,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            height: 3,
            backgroundColor: t.accent,
            transform: `scaleX(${rule})`,
            transformOrigin: "left",
            marginBottom: 44,
          }}
        />

        {kicker ? (
          <div
            style={{
              fontFamily: fontFamily.data,
              fontSize: size.labelMono,
              fontWeight: weight.medium,
              letterSpacing: tracking.labelMono,
              textTransform: "uppercase",
              color: t.accent,
              marginBottom: 32,
              opacity: enter(duration.standard),
            }}
          >
            {assertShort(kicker, "label", "Cover.kicker")}
          </div>
        ) : null}

        <div
          style={{
            fontFamily: fontFamily.display,
            fontSize: size.displayXl,
            fontWeight: weight.semibold,
            /** Caja mixta y tracking negativo: las versales son de la mono. */
            letterSpacing: tracking.display,
            lineHeight: lineHeight.displayXl,
            color: t.text,
            opacity: enter(duration.standard * 2),
            transform: `translateY(${(1 - enter(duration.standard * 2)) * 16}px)`,
          }}
        >
          {assertShort(hook, "title", "Cover.hook")}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
