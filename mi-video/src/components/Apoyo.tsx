import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fontFamily } from "../brand/fonts";
import { color } from "../brand/paleta";
import { useLienzo } from "../brand/LienzoContexto";
import biblioteca from "../brand/apoyo.json";

/**
 * **Un clip de la biblioteca de apoyo, bajo la voz** (C-673).
 *
 * La voz sigue y la imagen es otra: lo que Jaime enseña mientras habla —Alfred
 * en pantalla, el guion escrito— y que en el CV de YBL se montó a mano en
 * `src/cv/`. Aquí entra como un tablero más, así que lo elige el diseñador con
 * el mismo mando que el resto y lo valida `formas.mjs` contra la biblioteca.
 *
 * Dos formas, y las dos son vídeo en marcha, nunca un cuadro congelado:
 *
 * - `completo` — el clip llena el cuadro con un empuje lento. Era
 *   `PantallaAlfred`.
 * - `panel` — un clip vertical dentro de un cuadro que no lo es, en su columna
 *   y con su etiqueta. Era `Panel`.
 *
 * La insignia —«Demo data»— es **del clip, no del montaje**: la declara
 * `apoyo.json`, porque es una verdad sobre lo que el clip enseña.
 */
type Clip = {
  fichero: string;
  muestra: string;
  orientacion: "vertical" | "horizontal";
  insignia: string | null;
  derechos: string;
};

const CLIPS = (biblioteca as { clips: Record<string, Clip> }).clips;

export type ApoyoProps = {
  clip: string;
  forma?: "completo" | "panel";
  etiqueta?: string;
  desde?: number;
};

/** Cuánto empuja el cuadro en toda la escena: movimiento, no zoom. */
const EMPUJE = 1.06;
const MARGEN_INSIGNIA = 40;

export const Apoyo: React.FC<ApoyoProps> = ({ clip, forma, etiqueta, desde = 0 }) => {
  const lienzo = useLienzo();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const c = CLIPS[clip];
  // `formas.mjs` ya lo para antes de llegar aquí; si llega, que se vea.
  if (!c) throw new Error(`Apoyo: el clip «${clip}» no está en src/brand/apoyo.json`);
  const enPanel = (forma ?? (c.orientacion === "vertical" && lienzo.width > lienzo.height
    ? "panel" : "completo")) === "panel";
  const video = (
    <OffthreadVideo
      src={staticFile(c.fichero)}
      startFrom={desde}
      muted
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
  );
  const escala = interpolate(frame, [0, durationInFrames], [1, EMPUJE], {
    extrapolateRight: "clamp",
  });
  const entra = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const alto = lienzo.height - lienzo.safe.top - lienzo.safe.bottom;

  return (
    <AbsoluteFill style={{ background: enPanel ? color.navy : color.richBlack }}>
      {enPanel ? (
        <>
          <div
            style={{
              position: "absolute",
              right: lienzo.safe.right + 160,
              top: lienzo.safe.top,
              width: Math.round((alto * 9) / 16),
              height: alto,
              overflow: "hidden",
              clipPath: `inset(${(1 - entra) * 50}% 0 ${(1 - entra) * 50}% 0)`,
            }}
          >
            {video}
          </div>
          {etiqueta ? (
            <div
              style={{
                position: "absolute",
                left: lienzo.safe.left,
                top: lienzo.height / 2 - 40,
                width: 560,
                opacity: entra,
                borderTop: `3px solid ${color.gold}`,
                paddingTop: 22,
                fontFamily: fontFamily.data,
                fontSize: 30,
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: color.lightNeutral,
              }}
            >
              {etiqueta}
            </div>
          ) : null}
        </>
      ) : (
        <AbsoluteFill style={{ transform: `scale(${escala})` }}>{video}</AbsoluteFill>
      )}
      {c.insignia ? (
        <div
          style={{
            position: "absolute",
            bottom: Math.max(MARGEN_INSIGNIA, lienzo.safe.bottom),
            right: Math.max(MARGEN_INSIGNIA, lienzo.safe.right),
            background: color.richBlack,
            border: `2px solid ${color.gold}`,
            padding: "10px 18px 11px",
            fontFamily: fontFamily.data,
            fontWeight: 500,
            fontSize: 22,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: color.gold,
          }}
        >
          {c.insignia}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
