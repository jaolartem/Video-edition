import React from "react";
import {
  AbsoluteFill,
  Easing,
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
 * Tres formas, y las tres son vídeo en marcha, nunca un cuadro congelado:
 *
 * - `completo` — el clip llena el cuadro con un empuje lento. Era
 *   `PantallaAlfred`.
 * - `panel` — un clip vertical dentro de un cuadro que no lo es, en su columna
 *   y con su etiqueta. Era `Panel`.
 * - `amplia` — el clip arranca **dentro del monitor que se ve en el plano** y
 *   crece hasta llenar el cuadro, con la cámara debajo mientras tanto (C-696).
 *   Jaime, 15-11-2026, sobre la apertura de reel-23: *«cuando mirara al
 *   computador, la pantalla se compartiera, como que se ampliara»*. Dónde está
 *   el monitor lo pone el spec (`scripts/reels/monitor.mjs`) desde lo que la
 *   cinta declara, no el diseñador.
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

export type Monitor = { x: number; y: number; w: number; h: number };

export type ApoyoProps = {
  clip: string;
  forma?: "completo" | "panel" | "amplia";
  etiqueta?: string;
  desde?: number;
  /** Sólo con `amplia`: el monitor en píxeles del cuadro. Lo pone el spec. */
  monitor?: Monitor;
  /** Sólo con `amplia`: fotogramas quieto en el monitor antes de crecer. */
  espera?: number;
  /** Sólo con `amplia`: fotogramas que tarda en llenar el cuadro. */
  crece?: number;
};

/** Cuánto empuja el cuadro en toda la escena: movimiento, no zoom. */
const EMPUJE = 1.06;
const MARGEN_INSIGNIA = 40;
const ESPERA = 12;
const CRECE = 20;

/**
 * El cuadro del clip en este fotograma: del monitor al lienzo entero. La
 * entrada es la propia ampliación, así que no lleva otra.
 */
const cuadroQueCrece = (frame: number, m: Monitor, espera: number, crece: number,
                        ancho: number, alto: number) => {
  const p = interpolate(frame, [espera, espera + crece], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  return {
    p,
    left: m.x * (1 - p),
    top: m.y * (1 - p),
    width: m.w + (ancho - m.w) * p,
    height: m.h + (alto - m.h) * p,
  };
};

export const Apoyo: React.FC<ApoyoProps> = ({
  clip, forma, etiqueta, desde = 0, monitor, espera = ESPERA, crece = CRECE,
}) => {
  const lienzo = useLienzo();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const c = CLIPS[clip];
  // `formas.mjs` ya lo para antes de llegar aquí; si llega, que se vea.
  if (!c) throw new Error(`Apoyo: el clip «${clip}» no está en src/brand/apoyo.json`);
  if (forma === "amplia" && !monitor)
    throw new Error(`Apoyo «amplia» sin monitor: el spec no supo dónde está en «${clip}»`);
  const enPanel = (forma ?? (c.orientacion === "vertical" && lienzo.width > lienzo.height
    ? "panel" : "completo")) === "panel";
  const amplia = forma === "amplia" && monitor
    ? cuadroQueCrece(frame, monitor, espera, crece, lienzo.width, lienzo.height)
    : null;
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

  if (amplia) {
    // La cámara sigue debajo hasta que el clip la tapa: el fondo entra con la
    // ampliación. Después, el mismo empuje lento que `completo`.
    return (
      <AbsoluteFill style={{ background: `rgba(0,0,0,${amplia.p})` }}>
        <div
          style={{
            position: "absolute",
            left: amplia.left,
            top: amplia.top,
            width: amplia.width,
            height: amplia.height,
            overflow: "hidden",
            transform: amplia.p >= 1 ? `scale(${escala})` : undefined,
          }}
        >
          {video}
        </div>
        {c.insignia ? (
          <div style={{ position: "absolute", inset: 0, opacity: amplia.p }}>
            <Insignia texto={c.insignia} lienzo={lienzo} />
          </div>
        ) : null}
      </AbsoluteFill>
    );
  }

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
      {c.insignia ? <Insignia texto={c.insignia} lienzo={lienzo} /> : null}
    </AbsoluteFill>
  );
};

/** «Demo data» en la esquina: es del clip, y sale igual en las tres formas. */
const Insignia: React.FC<{ texto: string; lienzo: ReturnType<typeof useLienzo> }> = ({
  texto, lienzo,
}) => (
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
    {texto}
  </div>
);
