import React, { useMemo } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { useLienzo } from "../brand/LienzoContexto";
import { color, ease } from "../brand/tokens";
import { Fondo, Panel, type Recorte } from "./Fondo";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";
import type { Accion } from "./palote/accion";
import { compone } from "./palote/composicion";
import { Cuerpo } from "./palote/Cuerpo";
import { mecanico } from "./palote/Mecanico";
import { millonario } from "./palote/Millonario";
import { musculo } from "./palote/Musculo";

/**
 * **El palote**: un personaje de palotes que actúa la idea; alivio cómico recurrente.
 *
 * Sale igual en vertical y en horizontal: el sitio lo pone el lienzo.
 *
 * Jaime: *«utiliza animación de bolitas y palotes para ejemplificar cosas como
 * code is cheap, o judgment is muscle memory»*, *«el personaje sirve de alivio
 * cómico»* y *«que ese personaje quede como recurso recurrente»*. No explica:
 * **actúa** la frase que se está diciendo, y la frase va escrita a su lado.
 *
 * ## Cuándo pedirlo
 *
 * Cuando el beat es una idea que se entiende mejor **vista hacer** que leída,
 * y la pieza aguanta un respiro de humor sin perder el registro. Una por
 * pieza, dos como mucho: si sale en cada beat deja de ser un respiro. No lleva
 * cifras —una cantidad dibujada afirma igual que una rotulada—: para eso están
 * `Techo` o `comparacion`.
 *
 * ## Lo que sabe hacer (`accion`)
 *
 * - `millonario` — le cae una chistera, se mete la mano al bolsillo y tira
 *   billetes. Lo que de pronto sobra: *code is cheap*. El primer puñado sale
 *   en 1,5 s: cabe en un tablero de 3.
 * - `musculo` — se planta, sube los dos brazos y le sale el bíceps. Lo que se
 *   gana repitiendo: *judgment is muscle memory*. El bíceps revienta en 0,7 s.
 * - `mecanico` — conecta dos tablas con pinzas de batería, como motores, y
 *   salta la chispa. Lo que relaciona dos cosas: *SQL*. Con `tablas`, los
 *   nombres de las dos. La chispa salta hacia los 3 s —cuánto anda lo dice el
 *   cuadro—: pide 5 para verlo entero.
 *
 * Después de la acción **sigue vivo** lo que dure el tablero —tira, saca bola,
 * corre la corriente— y respira siempre: nunca medio segundo quieto.
 *
 * ## El personaje
 *
 * Un trazo grueso de punta redonda, cabeza hueca, codos y rodillas: el
 * registro de las figuras de Alan Becker que trajo Jaime, en `lightNeutral` y
 * no en su naranja. Se mueve de pose a pose con anticipación, se pasa y vuelve,
 * y lo que cuelga llega tarde — *«quiero que veas la fluidez del movimiento»*.
 * Eso es su actuación y es sólo suya: el texto entra como en cualquier tablero,
 * con la curva de salida del sistema y sin rebote.
 * @clase tablero
 */
export type PaloteProps = {
  /** Lo que actúa: millonario, musculo o mecanico. */
  accion: "millonario" | "musculo" | "mecanico";
  /** Las líneas que van a su lado, en Anton versales. Cada entrada es una línea. */
  texto?: string[];
  /** Qué línea va en oro: su texto exacto. Una sola. */
  oro?: string;
  /** Las dos tablas que conecta el mecánico, de izquierda a derecha. */
  tablas?: [string, string];
  /** Suena lo que él hace, en el fotograma en que lo hace. */
  sound?: boolean;
  /** La placa de la pieza, en marcha, detrás. */
  placa?: string;
  recorte?: Recorte;
};

const ACCIONES: Record<PaloteProps["accion"], Accion> = { millonario, musculo, mecanico };

/** Lo que se separa del techo de la franja lo último que se dibuja. */
const AIRE = 28;

/** Una acción que no existe no se adivina: falla el render y dice cuáles hay. */
const sinAccion = (accion: string): never => {
  throw new Error(`Palote: «${accion}» no es una acción. Hay: ${Object.keys(ACCIONES).join(", ")}`);
};

export const Palote: React.FC<PaloteProps> = ({
  accion,
  texto = [],
  oro,
  tablas = ["TABLE A", "TABLE B"],
  sound = true,
  placa,
  recorte = "lleno",
}) => {
  const layout = useLienzo();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const papel = ACCIONES[accion] ?? sinAccion(accion);
  texto.forEach((l) => assertShort(l, "statement", "Palote.texto"));
  tablas.forEach((t) => assertShort(t, "label", "Palote.tablas"));

  /** Dónde va cada cosa lo dice el lienzo: ver `palote/composicion.ts`. */
  const zona = layout.height - layout.franja.reserva;
  const { caja, escena, k, centra, enMedio, cuerpoTexto } = compone(layout, papel, texto, AIRE);
  const suelo = escena.y + escena.h;
  const cx = escena.x + escena.w / 2;

  const [tablaA, tablaB] = tablas;
  const montada = useMemo(
    () =>
      papel.monta({
        ancho: escena.w / k,
        techo: suelo / k,
        dur: durationInFrames,
        tablas: [tablaA, tablaB],
      }),
    [papel, escena.w, k, suelo, durationInFrames, tablaA, tablaB],
  );
  const { cuerpo, detras, delante } = montada.fotograma(frame);
  const enOro = (l: string) => Boolean(oro) && l.trim().toUpperCase() === oro?.trim().toUpperCase();

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.9} deriva={durationInFrames} />
      ) : null}
      {sound
        ? montada.sonidos.map((s) => <MotionSound key={`${s.motion}${s.at}`} motion={s.motion} at={s.at} />)
        : null}
      <ZonaTablero>
        {/* **Sobre la placa, un panel que lo sostiene.** La placa vertical es
            collage claro y él es una línea clara: sin el bloque negro detrás
            no se ve. Es el panel del canon —opaco, girado dos grados, la placa
            asomando por los bordes—; en el horizontal el suelo ya es la
            retícula oscura y no hace falta. */}
        {placa && layout.tablero.suelo === "placa" ? (
          <Panel
            giro={-1.4}
            style={{
              left: layout.safe.left - 30,
              top: layout.safe.top - 40,
              width: layout.width - layout.safe.left - layout.safe.right + 60,
              height: zona - AIRE / 2 - layout.safe.top + 40,
            }}
          >
            {null}
          </Panel>
        ) : null}
        <svg
          width={layout.width}
          height={zona}
          style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
        >
          <g transform={`translate(${cx.toFixed(2)} ${suelo.toFixed(2)}) scale(${k.toFixed(4)})`}>
            {detras}
            <Cuerpo a={cuerpo} tinte={color.lightNeutral} />
            {delante}
          </g>
        </svg>
        <div
          style={{
            position: "absolute",
            left: caja.x,
            top: caja.y,
            width: caja.w,
            height: caja.h,
            display: "flex",
            flexDirection: "column",
            justifyContent: enMedio ? "center" : "flex-start",
            alignItems: centra ? "center" : "flex-start",
            textAlign: centra ? "center" : "left",
          }}
        >
          {texto.map((l, i) => {
            const p = interpolate(frame, [3 + i * 5, 13 + i * 5], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: ease.out,
            });
            return (
              <div
                key={`${i}${l}`}
                style={{
                  fontFamily: fontFamily.bloque,
                  fontSize: cuerpoTexto,
                  lineHeight: 0.96,
                  letterSpacing: "0.005em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  color: enOro(l) ? color.gold : color.lightNeutral,
                  opacity: p,
                  transform: `translateY(${((1 - p) * 26).toFixed(1)}px)`,
                }}
              >
                {l}
              </div>
            );
          })}
        </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};
