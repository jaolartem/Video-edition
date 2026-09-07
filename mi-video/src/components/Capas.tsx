import React from "react";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { color, videoText } from "../brand/tokens";
import { fontFamily } from "../brand/fonts";
import { Pictograma, type Figura } from "./Pictograma";
import { MotionSound } from "./MotionSound";
import type { Motion } from "../brand/sfx";

/**
 * Las capas que decide `scripts/caminos.mjs`, puestas en pantalla.
 *
 * Este fichero **no decide nada**. Recibe una lista de capas ya resueltas —con
 * su frame, su duración y sus props— y las dibuja. La decisión de qué lleva cada
 * segmento vive en un solo sitio, que es lo que Jaime pidió: *«el renderizado
 * también debe ser por código, cada camino con sus propias indicaciones»*.
 *
 * La separación importa porque antes no existía: los tableros y los paneles
 * salían de dos literales escritos a mano por pieza, así que cada reel tenía sus
 * propias reglas y ninguna se podía comprobar.
  * @clase capa
*/

export type Capa = {
  tipo:
    | "punch"
    | "rotulo"
    | "titular"
    | "figura"
    | "remate"
    | "bloque"
    | "subtitulo"
    | "sonido";
  at: number;
  duration?: number;
  camino: string;
  beat: number;
  props: Record<string, unknown>;
};

/**
 * El plano se mueve dentro de sí mismo.
 *
 * Jaime, sobre el gancho: *«dentro de la toma mucho movimiento»*. Un plano fijo
 * con cosas encima sigue siendo un plano fijo, y a velocidad de scroll eso se
 * lee como una foto con texto.
 *
 * Se hace escalando **el contenedor del vídeo**, no el vídeo: así las capas de
 * encima —figura, rótulo, subtítulo— no se mueven con él y el movimiento se
 * percibe como cámara, que es de donde tiene que parecer que viene. Y la rampa
 * es lineal-suave y sin rebote: `Easing.back` está prohibido en este proyecto
 * porque convierte a un asesor financiero en un anuncio de refrescos.
 *
 * **Y la curva la pide el camino.** Por defecto entra y sale suave, que es lo
 * que quiere un empuje dentro de una escena. El gancho pide `lineal` por un
 * motivo medido: con `inOut` el encuadre **arranca parado** —a los 15 frames
 * todavía no se ha movido—, y eso es medio segundo quieto justo donde el pulgar
 * decide. Lineal es un travelling: no acelera, no frena y **no para**.
 */
export const PunchIn: React.FC<{
  capas: Capa[];
  children: React.ReactNode;
}> = ({ capas, children }) => {
  const frame = useCurrentFrame();
  const activa = capas.find(
    (c) => frame >= c.at && frame < c.at + (c.duration ?? 0),
  );
  const escala = activa
    ? interpolate(
        frame,
        [activa.at, activa.at + (activa.duration ?? 1)],
        [
          Number(activa.props.desde ?? 1),
          Number(activa.props.hasta ?? 1),
        ],
        {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing:
            activa.props.curva === "lineal"
              ? Easing.linear
              : Easing.inOut(Easing.quad),
        },
      )
    : 1;
  return (
    <AbsoluteFill style={{ transform: `scale(${escala.toFixed(4)})` }}>
      {children}
    </AbsoluteFill>
  );
};

/** Dónde cae la capa: el lado libre del cuadro, el contrario al sujeto. */
const sitio = (lado: unknown): React.CSSProperties =>
  lado === "izq" ? { left: 96 } : { right: 96 };

/**
 * La figura de la escena, entrando desde fuera del cuadro.
 *
 * Entra deslizando desde el borde y **no aparece con un fundido**: una entrada
 * es un movimiento, y un movimiento es lo que engancha. Los 18 frames de
 * entrada son 0,6 s — el tiempo que la figura necesita para leerse antes de que
 * llegue la siguiente capa.
 */
const CapaFigura: React.FC<{ props: Record<string, unknown> }> = ({ props }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const fuera = props.lado === "izq" ? -280 : 280;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          // **Debajo de la cara.** Jaime: *«en todos los planos sobra si no
          // tiene un proposito o si no esta debajo de mi cara»*. Estuvo a 470
          // (junto a la cabeza), a 560 (sobre la barba) y a 250 (arriba, en la
          // pared) — y ninguna es debajo de la cara. La franja util es la que
          // va del menton a la banda de subtitulos.
          top: 790,
          ...sitio(props.lado),
          width: 460,
          transform: `translateX(${((1 - p) * fuera).toFixed(1)}px)`,
          opacity: p,
        }}
      >
        <Pictograma
          figura={props.figura as Figura}
          oro={Boolean(props.oro)}
          dura={22}
          alto={190}
        />
      </div>
    </AbsoluteFill>
  );
};

/**
 * El remate: el filete que cruza y se queda.
 *
 * Es el gancho visual que **entra y sale**, no el que se instala. Cruza el
 * cuadro en 10 frames, se sostiene y se retira por donde vino. Un filete de un
 * píxel no se ve a velocidad de scroll, así que aquí son 14 px de plano de
 * color: el canon separa bloques con filete fino, pero un elemento que tiene
 * que **verse cruzar** es otra cosa.
 */
const CapaRemate: React.FC<{ props: Record<string, unknown>; dura: number }> = ({
  props,
  dura,
}) => {
  const frame = useCurrentFrame();
  const entra = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const sale = interpolate(frame, [dura - 10, dura], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const p = Math.min(entra, sale);
  const tinte = props.tinte === "navy" ? color.navyHi : color.gold;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          // **Dónde cruza el filete lo decide quien compone.**
          //
          // Estaba clavado en 900 y el gancho de reel-05 declara una escalera
          // que ocupa 834-948: el filete la partía por la mitad. No es un fallo
          // de la escalera ni del filete — es una coordenada fija en el sitio
          // donde otro elemento se coloca por composición.
          //
          // 900 se queda como valor por defecto: las piezas que no lo declaran
          // salen igual que hasta ahora.
          top: typeof props.y === "number" ? props.y : 900,
          left: 0,
          height: 14,
          width: `${(p * 100).toFixed(1)}%`,
          background: tinte,
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * El bloque de tipo: el gancho cuando la escena dice que **el tipo es la
 * composición**.
 *
 * Entra por corte —aparece de golpe, sin fundido— porque eso es romper el
 * patrón: todo lo demás desliza y esto no. Anton en versales sobre plano de
 * color, que es la voz del canon para lo grande.
 */
const CapaBloque: React.FC<{ props: Record<string, unknown>; texto: string }> = ({
  props,
  texto,
}) => {
  const frame = useCurrentFrame();
  // Por corte: dos frames de nada y entra entero. Sin rampa.
  if (frame < 2) return null;
  const tinte = props.tinte === "navy" ? color.navyHi : color.gold;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: 620,
          ...sitio(props.lado),
          maxWidth: 620,
          background: tinte,
          color: color.richBlack,
          padding: "10px 22px",
          fontFamily: fontFamily.bloque,
          fontSize: videoText.title,
          lineHeight: 1.02,
          letterSpacing: videoText.tracking,
          textTransform: "uppercase",
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

/**
 * Todas las capas de una pieza.
 *
 * El sonido va **en el frame del movimiento** y se emite desde aquí porque aquí
 * es donde se conoce ese frame: una pista aparte se desincroniza en el primer
 * ajuste de copy.
 */
export const Capas: React.FC<{
  capas: Capa[];
  /**
   * Si la pieza lleva los efectos de sonido de cada movimiento.
   *
   * **La versión sin aprobar va muda de extras.** Jaime: *«los vídeos para
   * aprobación van sin música y sin audio adicional, no los necesitamos, y será
   * más fácil con el audio final y definitivo, menos retrabajo»*. Para juzgar si
   * el mensaje llega, el sonido de acompañamiento estorba más que ayuda — y
   * ponerlo sobre un corte que aún puede cambiar es pagarlo dos veces.
   */
  sonido?: boolean;
}> = ({ capas, sonido }) => (
  <>
    {capas.map((c, i) => {
      const key = `${c.tipo}-${c.at}-${i}`;
      if (c.tipo === "sonido")
        return sonido ? (
          <MotionSound key={key} motion={c.props.motion as Motion} at={c.at} />
        ) : null;
      // El punch lo aplica `PunchIn` alrededor del video, no aquí.
      // El rótulo y el subtítulo los llevan `BigTitle` y `CaptionBand`, que ya
      // existen: el camino les fija el frame de entrada, no los duplica.
      //
      // Y el `titular` del gancho lo dibuja `Gancho.tsx` **dentro de `Ad`**, no
      // aquí: tiene que quedar entre el plano y el recorte del sujeto para que
      // le pase por detrás de la cabeza, y esta pila va por encima de los dos.
      if (
        c.tipo === "punch" ||
        c.tipo === "rotulo" ||
        c.tipo === "titular" ||
        c.tipo === "subtitulo"
      )
        return null;
      const dura = c.duration ?? 1;
      return (
        <Sequence key={key} from={c.at} durationInFrames={dura}>
          {c.tipo === "figura" ? (
            <CapaFigura props={c.props} />
          ) : c.tipo === "remate" ? (
            <CapaRemate props={c.props} dura={dura} />
          ) : c.tipo === "bloque" ? (
            // **El texto viene en la capa, declarado por la escena.** Aquí
            // llegaba `kicker`, que era `lineas[0]` — la primera línea del
            // rótulo—, así que el bloque repetía el rótulo palabra por palabra
            // encima de él. El camino ya no emite la capa sin copy declarado,
            // de modo que si llega es porque alguien lo escribió.
            <CapaBloque props={c.props} texto={String(c.props.texto ?? "")} />
          ) : null}
        </Sequence>
      );
    })}
  </>
);
