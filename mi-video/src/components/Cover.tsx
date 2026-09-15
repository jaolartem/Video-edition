import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
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
  videoText,
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
    * @clase tablero
*/
  hook: string;
  /** Etiqueta de serie, en versales. */
  kicker?: string;
  /**
   * Segunda línea, **debajo del título y centrada con él**.
   *
   * Jaime, 14-9-2026, viendo la portada de R13 sacada como fotograma: *«el cc
   * puede servir de subtítulo más centrado y así no sea un CC, lo mismo el
   * título»*. Es la diferencia entre una portada y una captura: un subtítulo
   * quemado cuenta lo que se está diciendo en ese instante —media frase— y
   * esto dice de qué va la pieza.
   *
   * Sale del libreto, no se inventa: es la línea que sigue al título.
   */
  subtitulo?: string;
  /**
   * El plano detrás, si la portada va sobre imagen. Ruta dentro de `public/`.
   *
   * Sin él, la portada es la lámina plana de siempre. Con él, el fotograma
   * manda y el texto se centra encima — que es el estilo que aprobó mirando
   * el gancho montado.
   */
  fotograma?: string;
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
  subtitulo,
  fotograma,
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

  /**
   * **Sobre imagen, la portada se centra; sin imagen, se queda como estaba.**
   *
   * No son dos componentes: es la misma portada con o sin plano detrás. Un
   * segundo fichero «CoverConFoto» seria la averia de siempre — dos sitios que
   * dicen como se ve una portada y que se separan en cuanto uno se toca.
   */
  if (fotograma) {
    return (
      <AbsoluteFill style={{ backgroundColor: t.ground }}>
        <Img
          src={staticFile(fotograma)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
        {/**
         * Velo de contacto, no decoración: el texto cae sobre imagen real de
         * luminancia variable. Misma razón que la sombra del rótulo en
         * `HookTitle`, y por eso sube desde abajo, que es donde va el texto.
         */}
        <AbsoluteFill
          style={{
            background:
              `linear-gradient(to top, ${t.ground} 8%, ${t.ground}e6 42%,`
              + ` ${t.ground}00 74%)`,
          }}
        />
        <AbsoluteFill
          style={{
            paddingLeft: layout.safe.left,
            paddingRight: layout.safe.right,
            /**
             * **La portada no reserva banda de subtítulos.** `layout.safe.bottom`
             * son 672 px porque bajo esa línea va el CC del vídeo, y aquí no hay
             * CC: usarlo subía el bloque hasta media altura y el título le
             * cruzaba la barbilla. Se usa el inset de arriba, que es el mismo
             * respiro declarado, en simétrico.
             */
            paddingBottom: layout.safe.top,
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <div
            style={{
              height: 4,
              width: 180,
              backgroundColor: t.accent,
              transform: `scaleX(${rule})`,
              marginBottom: 34,
            }}
          />
          <div
            style={{
              fontFamily: fontFamily.video,
              fontSize: videoText.title,
              fontWeight: videoText.weight,
              letterSpacing: videoText.tracking,
              lineHeight: 1.02,
              textTransform: "uppercase",
              color: t.accent,
              textShadow: "0 2px 18px rgba(0,0,0,0.55)",
              opacity: enter(duration.standard),
            }}
          >
            {assertShort(hook, "title", "Cover.hook")}
          </div>
          {subtitulo ? (
            <div
              style={{
                marginTop: 28,
                maxWidth: "88%",
                fontFamily: fontFamily.video,
                /** `videoText.caption`: «subtítulo, nunca por debajo de esto». */
                fontSize: videoText.caption,
                fontWeight: weight.medium,
                letterSpacing: videoText.tracking,
                lineHeight: 1.22,
                color: t.text,
                textShadow: "0 2px 14px rgba(0,0,0,0.6)",
                opacity: enter(duration.standard * 2),
              }}
            >
              {assertShort(subtitulo, "statement", "Cover.subtitulo")}
            </div>
          ) : null}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

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
