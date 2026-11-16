import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, tracking } from "../brand/tokens";
import { useLienzo } from "../brand/LienzoContexto";
import { Fondo, type Recorte } from "./Fondo";

/**
 * Tarjeta neo-constructivista: **el plano cuando la toma no sirve**.
 *
 * Nace de dos cosas que dijo Jaime. Una, la regla: *«a cada estructura le
 * escogemos el mejor, y si no entra bien hacemos un gráfico, así sea sólo
 * palabras»* — un beat del libreto no se cae por falta de toma, se dibuja. Dos,
 * la referencia: sus carruseles, que son constructivismo con piel nativa
 * digital.
 *
 * De la referencia sale la anatomía, y cada parte hace un trabajo:
 *
 * - **Cabecera** con la marca, el framework del playbook y el contador de beat.
 *   Es lo que mantiene el frame presente aunque cambie el plano — Jaime:
 *   *«el frame debe estar presente siempre»*.
 * - **Bloques inclinados** que entran apilándose, cada uno por su lado. La
 *   diagonal es la que sugiere movimiento; el constructivismo evita la simetría
 *   por eso mismo.
 * - **Remate** grande en condensada pesada. El texto ES la composición: quita
 *   las palabras y no queda nada.
 * - **Pie** corto, en oro, que aterriza la idea.
 *
 * Los bloques entran **de uno en uno**, no todos a la vez: apilarse delante del
 * espectador es lo que convierte una lista en un argumento.
  * @clase tablero
*/
export type TarjetaProps = {
  /** Nombre del framework del playbook. Va en la cabecera. */
  framework: string;
  /** Posición en el argumento: `[3, 8]` imprime «03—08». */
  beat: [number, number];
  /** Bloques inclinados, de arriba abajo. Cortos: son etiquetas, no frases. */
  bloques: { texto: string; tono?: "azul" | "claro" | "oro" }[];
  /** El remate, en líneas. Cada entrada es una línea y no se parte. */
  remate: string[];
  /** Pie corto en oro. Opcional. */
  pie?: string;
  /** Frames entre la entrada de un bloque y el siguiente. */
  escalon?: number;
  /**
   * Emite el sonido de cada movimiento. **El sonido sigue al movimiento**: si el
   * bloque se pega, suena el pegado, y en el mismo frame en que se pega — no
   * desde una pista aparte, que se desincroniza al primer reajuste de tiempos.
   *
   * Los nombres de fichero los fija `src/brand/sfx.ts`. Aqui decian
   * «pegatina.wav» y «golpe.wav», que es como los generaba el script, y el
   * resto del sistema pedia «mark.wav» y «land.wav»: el efecto fallaba en
   * silencio porque `staticFile` no avisa de un fichero que no esta.
   */
  sonido?: boolean;
  /**
   * **La placa de la pieza, en marcha, detrás** (C-709). Al despachar la
   * Tarjeta a este componente (C-706) salió sobre negro liso y emisión midió 15
   * congelados en reel-23 bajo e6, e14 y e19: los bloques entran y luego nada
   * cambia. La placa la pone el spec, como a toda forma; aquí sólo se pinta.
   */
  placa?: string;
  recorte?: Recorte;
};

const TONO = {
  azul: { fondo: color.secondaryBlue, texto: color.richBlack },
  claro: { fondo: color.lightNeutral, texto: color.richBlack },
  oro: { fondo: color.gold, texto: color.richBlack },
} as const;

/** Inclinaciones fijas por posición: variadas, pero iguales en cada render. */
const GIRO = [-2.4, 1.8, -1.4, 2.6, -2.0];
/** Sangrías que rompen la alineación: la simetría es lo que se evita. */
const SANGRIA = [0, 0.14, 0.05, 0.18, 0.02];

export const Tarjeta: React.FC<TarjetaProps> = ({
  framework,
  beat,
  bloques,
  remate,
  pie,
  escalon = 8,
  sonido = true,
  placa,
  recorte = "lleno",
}) => {
  const layout = useLienzo();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const dos = (n: number) => String(n).padStart(2, "0");

  const entra = (desde: number, dura = 9) =>
    interpolate(frame, [desde, desde + dura], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });

  const util = layout.width - layout.safe.left * 2;
  const { alinea, cuerpo: escala, serie } = layout.tablero;
  const centra = alinea === "center";
  /**
   * **Y lo que entra, cabe** (C-716). Centrado y a cuerpo de horizontal, cuatro
   * bloques y el remate pasaban del alto útil y el primero salía por arriba
   * (reel-23 e14). Se estima el alto a cuerpo 1 y se encoge lo justo.
   */
  const alto = layout.height - layout.safe.top - layout.franja.reserva;
  const masLarga = Math.max(...remate.map((l) => l.length), 1);
  const altoA1 =
    bloques.length * (58 * 1.4 + 26) +
    (remate.length ? 40 + remate.length * Math.min(150, util / (masLarga * 0.47)) * 0.94 : 0) +
    (pie ? 70 : 0);
  const cuerpo = centra ? Math.min(escala, alto / Math.max(1, altoA1)) : escala;
  /**
   * Cuerpo del remate ajustado a la línea más larga.
   *
   * Anton es condensada: gasta ~0,47 em por carácter en versales, bastante
   * menos que la Montserrat 900 (0,70). Medido sobre render — estimar el ancho
   * de un texto sin medirlo tiene un error irreducible, y el margen se paga en
   * cuerpo, que es barato, no en texto cortado.
   */
  const cuerpoRemate = Math.min(150 * cuerpo, util / (masLarga * 0.47));

  const finBloques = bloques.length * escalon;
  /** Nivel bajo a propósito: la voz de Jaime es el audio principal. */
  const NIVEL = 0.5;

  /**
   * **Y centrado, el grupo visible es el que se centra** (C-716). El remate
   * entra al final —en reel-23 e14 al 85% de la lámina— y ocupaba su sitio
   * desde el principio: los bloques se quedaban arriba casi toda la lámina.
   * Empiezan en el centro y suben lo que el remate necesita cuando entra.
   */
  const pRemate = entra(finBloques + 6, 14);
  const altoRemate = remate.length
    ? 40 * cuerpo + remate.length * cuerpoRemate * 0.94
    : 0;
  const envuelve = (hijos: React.ReactNode) =>
    centra ? (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          transform: `translateY(${(((1 - pRemate) * altoRemate) / 2).toFixed(1)}px)`,
        }}
      >
        {hijos}
      </div>
    ) : (
      hijos
    );

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.9} deriva={durationInFrames} />
      ) : null}
      {sonido ? (
        <>
          {bloques.map((b, i) => (
            <Sequence key={b.texto} from={i * escalon} durationInFrames={12}>
              <Audio src={staticFile("sfx/mark.wav")} volume={NIVEL} />
            </Sequence>
          ))}
          <Sequence from={finBloques + 6} durationInFrames={16}>
            <Audio src={staticFile("sfx/land.wav")} volume={NIVEL} />
          </Sequence>
        </>
      ) : null}
      {/* Cabecera: el frame de la serie. Sin serie, no hay cabecera (C-716). */}
      {serie ? (
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 96,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 20,
          paddingLeft: layout.safe.left,
          paddingRight: layout.safe.right,
          borderBottom: `1px solid ${color.navyHi}`,
          fontFamily: fontFamily.video,
          // 20, no 26: en 9:16 el ancho util son 950 px y con 26 la marca mas
          // el framework se partian en dos lineas. Una cabecera de dos lineas
          // deja de leerse como cabecera.
          fontSize: 20,
          whiteSpace: "nowrap",
          fontWeight: 800,
          letterSpacing: tracking.labelMono,
          color: color.lightNeutral,
          textTransform: "uppercase",
        }}
      >
        <span>
          {serie}{" "}
          <span style={{ color: color.secondaryBlue }}>/ {framework}</span>
        </span>
        <span>
          {dos(beat[0])}—{dos(beat[1])}
        </span>
      </div>
      ) : null}

      <div
        style={{
          position: "absolute",
          top: centra ? layout.safe.top : 190,
          left: layout.safe.left,
          right: layout.safe.right,
          bottom: centra ? layout.franja.reserva : 300,
          display: "flex",
          flexDirection: "column",
          justifyContent: centra ? "center" : undefined,
          textAlign: centra ? "center" : undefined,
        }}
      >
        {envuelve(bloques.map((b, i) => {
          const p = entra(i * escalon);
          if (p <= 0) return null;
          const t = TONO[b.tono ?? (["claro", "azul", "oro"] as const)[i % 3]];
          return (
            <div
              key={b.texto}
              style={{
                alignSelf: alinea,
                marginLeft: centra ? 0 : `${(SANGRIA[i % SANGRIA.length] ?? 0) * 100}%`,
                marginBottom: 26 * cuerpo,
                padding: "0.16em 0.5em",
                backgroundColor: t.fondo,
                color: t.texto,
                fontFamily: fontFamily.bloque,
                fontSize: 58 * cuerpo,
                letterSpacing: "0.02em",
                lineHeight: 1.08,
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                transform: `translateX(${(1 - p) * -420}px) rotate(${
                  GIRO[i % GIRO.length]
                }deg)`,
                opacity: p,
              }}
            >
              {b.texto}
            </div>
          );
        }))}

        <div style={centra ? { height: 40 * cuerpo } : { flex: 1 }} />

        {remate.map((l, i) => {
          const p = entra(finBloques + 6 + i * 4);
          return (
            <div
              key={l}
              style={{
                fontFamily: fontFamily.bloque,
                fontSize: cuerpoRemate,
                lineHeight: 0.94,
                letterSpacing: "0.005em",
                color: color.lightNeutral,
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                opacity: p,
                transform: `translateY(${(1 - p) * 26}px)`,
              }}
            >
              {l}
            </div>
          );
        })}

        {pie ? (
          <div
            style={{
              marginTop: 30,
              fontFamily: fontFamily.video,
              fontSize: 30,
              fontWeight: 800,
              letterSpacing: "0.08em",
              lineHeight: 1.25,
              color: color.gold,
              textTransform: "uppercase",
              opacity: entra(finBloques + 6 + remate.length * 4 + 4),
            }}
          >
            {pie}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
