import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { MotionSound } from "./MotionSound";
import { Cinta, Fondo } from "./Fondo";
import { color, duration, ease, layout } from "../brand/tokens";

/**
 * La cortinilla: lo que media un corte duro entre dos beats.
 *
 * Jaime, sobre el segundo 33 del reel 1: *«el corte es demasiado duro, muy
 * brusco; eso debe estar mediado o por un gráfico o por algo que lo suavice, se
 * nota muy fuerte»*. Y tenía razón por una causa medible: ahí el montaje salta
 * **83 segundos** de material de origen y cambia de encuadre a la vez. Dos
 * cambios simultáneos sin nada que los cubra.
 *
 * ## Por qué una cortinilla y no un fundido
 *
 * Un fundido suaviza el corte y no dice nada. Ésta hace tres cosas a la vez:
 *
 * 1. **Tapa la costura.** Es la forma clásica de esconder un corte: cortar a
 *    otra cosa. Aquí esa otra cosa además pertenece a la pieza.
 * 2. **Mantiene el frame presente.** Lleva el nombre de la etapa que empieza,
 *    que es lo que Jaime pidió desde el principio — *«el frame debe estar
 *    presente siempre»*.
 * 3. **Marca el pulso.** Cada etapa entra anunciada, así que la estructura se
 *    oye y se ve.
 *
 * ## Corta a propósito
 *
 * 0,7 s. Lo suficiente para leer dos palabras en versales y no más: con seis
 * costuras en una pieza de 75 s, alargarlas convertiría el anuncio en una
 * sucesión de rótulos. La placa se reconoce, no se contempla.
 *
 * El audio **no se interrumpe** — la voz sigue corriendo por debajo, así que es
 * un L-cut y la costura tampoco se oye.
 */
export type CortinillaProps = {
  /** Placa de `public/fondos/`, sin extensión. La que dice lo que dice el beat. */
  placa: string;
  /** El nombre de la etapa que empieza. Va en la cinta. */
  etapa: string;
  /** Posición en el argumento: `[4, 8]` imprime «04—08». */
  beat: [number, number];
  framework: string;
  sound?: boolean;
};

export const Cortinilla: React.FC<CortinillaProps> = ({
  placa,
  etapa,
  beat,
  framework,
  sound = false,
}) => {
  const frame = useCurrentFrame();
  assertShort(etapa, "label", "Cortinilla.etapa");

  /**
   * Entra y sale rápido, pero **no con un fundido simétrico**: entra de golpe
   * —es un corte, y taparlo con otro corte es lo que lo hace invisible— y sale
   * desvaneciendo, que es lo que devuelve el plano sin un segundo salto.
   */
  const dentro = interpolate(frame, [0, 2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fuera = interpolate(frame, [15, 21], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const p = Math.min(dentro, fuera);

  const entraCinta = interpolate(frame, [1, 1 + duration.entry], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease.out,
  });

  return (
    <AbsoluteFill style={{ opacity: p }}>
      {sound ? <MotionSound motion="whoosh" at={0} /> : null}
      <Fondo placa={placa} />

      {/* La cabecera, igual que en los tableros: el frame no desaparece
          porque la pieza cambie de plano. */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 92,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingLeft: layout.safe.left,
          paddingRight: layout.safe.right,
          backgroundColor: color.richBlack,
          fontFamily: fontFamily.video,
          fontSize: 22,
          whiteSpace: "nowrap",
          fontWeight: 800,
          letterSpacing: "0.06em",
          color: color.lightNeutral,
          textTransform: "uppercase",
        }}
      >
        <span>
          El código del empresario{" "}
          <span style={{ color: color.secondaryBlue }}>/ {framework}</span>
        </span>
        <span>
          {String(beat[0]).padStart(2, "0")}—{String(beat[1]).padStart(2, "0")}
        </span>
      </div>

      {/* La cinta con la etapa. Entra deslizando desde el lado, que es el
          movimiento que justifica el barrido. */}
      <div
        style={{
          position: "absolute",
          top: layout.height * 0.42,
          left: layout.safe.left,
          right: layout.safe.right,
          display: "flex",
          fontFamily: fontFamily.bloque,
          opacity: entraCinta,
          transform: `translateX(${(1 - entraCinta) * -180}px)`,
        }}
      >
        <Cinta tinte={color.gold} giro={-2.4} cuerpo={64}>
          {etapa}
        </Cinta>
      </div>
    </AbsoluteFill>
  );
};

/** Duración de la cortinilla en frames. 0,7 s: se reconoce, no se contempla. */
export const DURACION = 21;
