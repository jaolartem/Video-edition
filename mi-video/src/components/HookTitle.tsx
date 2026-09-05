import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import {
  duration,
  ease,
  layout,
  mode as modes,
  videoText,
  type Mode,
} from "../brand/tokens";

/**
 * Rótulo sobre el vídeo, para sostener la atención en el gancho.
 * @clase capa
 */
export type TitleCue = {
  /** Frame en que entra. Anclado a la palabra que subraya. */
  at: number;
  /** Cuántos frames se sostiene. Mínimo el tiempo de lectura. */
  duration: number;
  text: string;
  /** Marca el remate: cuerpo mayor y acento. Uno por pieza como mucho. */
  remate?: boolean;
};

/**
 * Rótulo sobre el vídeo, para sostener la atención.
 *
 * No es decoración ni subtítulo: **subraya la palabra que carga el argumento**.
 * Por eso entra anclado a esa palabra y no a un tiempo redondo, y por eso no se
 * apilan dos a la vez — dos rótulos compitiendo no retienen el doble, reparten
 * la mitad.
 *
 * Vive por encima de la banda de subtítulos y por debajo del rostro: el sujeto
 * es la cara, y un rótulo que la tapa deja de ser ayuda.
 */
export const HookTitle: React.FC<{
  cues: TitleCue[];
  mode?: Mode;
}> = ({ cues, mode = "evidence" }) => {
  const frame = useCurrentFrame();
  const t = modes[mode];

  const activo = cues.find(
    (c) => frame >= c.at && frame < c.at + c.duration,
  );
  if (!activo) {
    return null;
  }

  const p = interpolate(
    frame,
    [activo.at, activo.at + duration.entry],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease.out },
  );
  /** Salida al final, para que no desaparezca de golpe. */
  const salida = interpolate(
    frame,
    [activo.at + activo.duration - duration.standard, activo.at + activo.duration],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease.linear },
  );
  const o = Math.min(p, salida);

  /** El filete se traza; el texto llega detrás. El orden guía la mirada. */
  const rule = interpolate(
    frame,
    [activo.at, activo.at + duration.standard * 2],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease.linear },
  );

  return (
    <AbsoluteFill
      style={{
        paddingLeft: layout.safe.left,
        paddingRight: layout.safe.right,
        /** Por encima de la banda de subtítulos, nunca sobre la cara. */
        paddingBottom: layout.safe.bottom + layout.captionBand,
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-end",
        opacity: o,
      }}
    >
      <div
        style={{
          height: activo.remate ? 4 : 3,
          backgroundColor: t.accent,
          transform: `scaleX(${rule})`,
          transformOrigin: "left",
          marginBottom: 22,
        }}
      />
      <div
        style={{
          /** Montserrat pesada: es texto sobre video. Ver `fontFamily.video`. */
          fontFamily: fontFamily.video,
          fontSize: activo.remate ? videoText.titleBig : videoText.title,
          fontWeight: videoText.weight,
          letterSpacing: videoText.tracking,
          lineHeight: 1.05,
          color: activo.remate ? t.accent : t.text,
          transform: `translateY(${(1 - p) * 14}px)`,
          /**
           * Sombra de contacto, no decorativa: el rótulo cae sobre imagen real
           * de luminancia variable y sin ella se pierde contra una pared clara.
           * El sistema prohíbe la sombra como recurso de profundidad —tarjetas
           * flotantes—, no como garantía de legibilidad sobre vídeo.
           */
          textShadow: "0 2px 18px rgba(0,0,0,0.55)",
        }}
      >
        {assertShort(activo.text, "title", "HookTitle.text")}
      </div>
    </AbsoluteFill>
  );
};
