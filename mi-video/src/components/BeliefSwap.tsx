import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { Marco } from "./Canon";
import { Fondo, Cinta } from "./Fondo";
import { Remate } from "./Remate";
import type { Recorte } from "./Fondo";
import { fontFamily } from "./../brand/fonts";
import { assertShort } from "../brand/copy";
import { color, duration, ease, layout, readingFrames } from "../brand/tokens";
import { ZonaTablero } from "./ZonaTablero";

/**
 * La creencia se tacha y la verdad entra en oro. **Dos cintas, nada más.**
 * @clase tablero
 */
export type BeliefSwapProps = {
  /** Lo que el espectador cree. Entra primero y se tacha. */
  creencia: string;
  /** Lo que pasa de verdad. Entra en oro, después de la tacha. */
  verdad: string;
  /** Placa de `public/fondos/`. Sin ella el tablero va sobre negro liso. */
  /**
   * Como se recorta la placa. A cuadro completo va `lleno`.
   *
   * Estaba escrito a fuego aqui, y con eso la diagonal dejaba ver el VIDEO por
   * debajo — y lo que se ve depende de donde cayera el encuadre: en la sesion de
   * noche, las rodillas. Jaime: *«se ve feo ese tablero; mejor dejar el tablero
   * sin video»*.
   *
   * A `cubre: pleno` lo pone `armarTableros` en `lleno`: alli la placa ES el
   * plano. El valor de aqui es el respaldo para los que acompanan.
   */
  recorte?: Recorte;
  placa?: string;
  /** Lo que se dice al pie: fuente o condición. */
  condicion?: string;
  duracion?: number;
};

/**
 * **La lámina 01_Loss_Aversion/slide-04, en movimiento.**
 *
 * Jaime, al elegir qué construir: *«que utilicen los fondos que ya existen,
 * para generar texto encima de ellos, como lo muestran los ejemplos de
 * carruseles; no es reinventar la rueda, es seguir la identidad gráfica»*.
 *
 * Y la lámina ya lo tiene resuelto: dos cintas giradas apiladas abajo, la de
 * arriba clara y la de abajo en oro, con Anton en negro dentro — «NO FUE MALA
 * SUERTE» / «FUE IMPUESTO EVITABLE». Aquí no se inventa una forma: se anima esa.
 *
 * ## Lo que aporta el vídeo sobre la lámina
 *
 * El carrusel enseña las dos a la vez y el lector decide en qué orden leerlas.
 * El vídeo no: **entran en orden y la tacha ocurre delante**. Primero la
 * creencia, el tiempo justo de leerla, luego el filete que la cruza, y sólo
 * cuando ya está tachada entra la verdad. Es la misma composición contada como
 * una secuencia, que es lo que un reel puede hacer y un carrusel no.
 *
 * **La tacha se traza, no aparece.** Un tachado que ya está puesto cuando la
 * frase entra no tacha nada: se lee como una frase con una raya. Cruzando de
 * izquierda a derecha en diez frames, el espectador ve *cómo* se cae.
 *
 * ## Por qué no lleva más
 *
 * Lo pidieron tres piezas y las tres declararon lo mismo: `creencia`, `verdad`,
 * `tachado`, `oro`. Una idea por tablero — si hacen falta dos, son dos.
 */
export const BeliefSwap: React.FC<BeliefSwapProps> = ({
  creencia,
  verdad,
  placa,
  recorte = "cuna",
  duracion,
}) => {
  const frame = useCurrentFrame();
  assertShort(creencia, "statement", "BeliefSwap.creencia");
  assertShort(verdad, "statement", "BeliefSwap.verdad");

  /**
   * El horario, repartido sobre lo que dura la escena que el tablero reemplaza.
   *
   * Con tiempos fijos el tablero se monta en tres segundos y se queda quieto el
   * resto, que es lo que hace que un tablero se sienta relleno. La creencia
   * necesita leerse **entera** antes de que la tache algo: si la tacha llega
   * antes, el espectador no llega a creerla y la corrección no corrige nada.
   */
  const total = duracion ?? readingFrames(creencia) + readingFrames(verdad) + 60;
  const leeCreencia = readingFrames(creencia);
  const tCreencia = 0;
  const tTacha = tCreencia + leeCreencia;
  const tVerdad = tTacha + duration.standard;

  const entra = (at: number) =>
    interpolate(frame, [at, at + duration.entry], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });
  /** La tacha cruza. Lineal a propósito: un filete que frena parece dudar. */
  const tacha = interpolate(frame, [tTacha, tTacha + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease.linear,
  });

  const pCreencia = entra(tCreencia);
  const pVerdad = entra(tVerdad);

  return (
    <Marco style={{ justifyContent: "flex-end" }}>
      {/**
       * La placa **recortada**, no a sangre: en el canon la fotografía entra
       * como fragmento de lados rectos y el resto es plano de color. A sangre
       * deja de ser collage y pasa a ser papel pintado.
       */}
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.85} deriva={total} />
      ) : null}

      {/* **Dentro de la zona del tablero**, para que su recorte tenga sitio:
          con `sujeto` declarado la línea no lo montaba (reel-08 e2, C-438). */}
      <ZonaTablero>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: `0 ${layout.safe.left}px`,
          }}
        >
          <div style={{ position: "relative", marginBottom: 26 }}>
            <div
              style={{
                opacity: pCreencia,
                transform: `translateY(${((1 - pCreencia) * 22).toFixed(1)}px)`,
              }}
            >
              <Cinta tinte={color.lightNeutral} giro={-2.4} cuerpo={62}>
                <span style={{ fontFamily: fontFamily.bloque }}>{creencia}</span>
              </Cinta>
            </div>
            {/**
             * El filete que la cruza. Va **encima de la cinta y no dentro del
             * texto**: un `line-through` tipográfico se escala con la fuente y se
             * pierde a tamaño de móvil; una barra de 8 px se ve siempre.
             */}
            <div
              style={{
                position: "absolute",
                top: "48%",
                left: 0,
                height: 8,
                width: `${(tacha * 100).toFixed(1)}%`,
                background: color.richBlack,
                transform: "rotate(-2.4deg)",
                transformOrigin: "left center",
              }}
            />
          </div>

          <div
            style={{
              opacity: pVerdad,
              transform: `translateY(${((1 - pVerdad) * 22).toFixed(1)}px)`,
            }}
          >
            {/* **`acento` porque aquí no hay otro oro.** Dos bloques planos y la
                conclusión: si ésta va en claro, el tablero se queda sin sitio por
                donde entrar. La regla es un acento, no ninguno. Ver `Remate.tsx`. */}
            <Remate acento giro={1.9} cuerpo={68}>
              <span style={{ fontFamily: fontFamily.bloque }}>{verdad}</span>
            </Remate>
          </div>
        </div>
      </ZonaTablero>

      {/* **La condición ya no se rotula dentro.** Va al pie, fuera de la zona
          segura y en una línea: la monta `dibujaTablero`. Ver
          `PieTablero.tsx`. */}
    </Marco>
  );
};
