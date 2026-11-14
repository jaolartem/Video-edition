import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { color, readingFrames } from "../brand/tokens";
import { Cinta, Fondo, type Recorte } from "./Fondo";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";
import { useLienzo } from "../brand/LienzoContexto";
import type { Lienzo } from "../brand/lienzo";

/**
 * **Un universo, y lo que cabe dentro de él.** La contención dicha con
 * geometría, no con un porcentaje escrito.
 *
 * El encargo de reel-02 e6 lo describe entero: *«el rectángulo del universo se
 * dibuja entero; dentro encaja el bloque del 2,5% en azul pizarra; dentro de
 * ése, la astilla de oro del 0,1%. Cada uno encaja más estrecho que el
 * anterior»*.
 *
 * Y por eso no es una `Comparacion` ni una `Acumulacion`: las dos ponen
 * magnitudes **una al lado de la otra**, y lo que esta etapa dice es que la
 * pequeña está **dentro** de la grande. La proporción se ve sin leer ninguna
 * cifra —que es para lo que sirve un tablero— y las cifras confirman lo que el
 * ojo ya entendió.
 *
 * ## El oro es la astilla, y sólo ella
 *
 * Las tres capas se dibujan con la paleta oscura —contorno, azul pizarra, oro—
 * y el oro se reserva a la de dentro porque es donde el argumento aterriza.
 * Poner las tres en oro sería lo mismo que no poner ninguna.
 * @clase tablero
 */
export type AnidadoProps = {
  /** Titular del tablero. Va en cinta, arriba. */
  titulo?: string;
  /** El universo: el rectángulo entero. Su rótulo va dentro, arriba. */
  base?: string;
  /** Lo que encaja dentro del universo. */
  capa_media?: string;
  /** La astilla: lo que encaja dentro de la anterior. Es el oro. */
  capa_dentro?: string;
  /** Qué acota la lectura de las cifras. Banda propia, al pie. */
  condicion?: string;
  /** De dónde salen. Va con la condición. */
  source?: string;
  placa?: string;
  recorte?: Recorte;
  sound?: boolean;
};

/**
 * Caja del universo, dentro de la zona que el tablero puede ocupar.
 *
 * Acaba en 760 y no más abajo porque debajo va la banda de fuente y condición,
 * y esa banda **crece con lo que le echen**: la del reel-02 lleva la cita del
 * PBO más el alcance del dato y mide ~230 px, así que se apoya en el techo de
 * la franja y sube hasta el 818. Con la caja hasta el 860 se pisaban.
 */
const cajaEn = (layout: Lienzo) => {
  // El ancho es el útil de su lienzo: 950 en vertical, que estaba escrito a
  // mano dos veces (C-670).
  const CAJA = { x: layout.safe.left, y: 240, w: layout.util, h: 520 } as const;

  /** Cada capa encaja más estrecha que la anterior: izquierda, arriba, ancho, alto. */
  const CAPAS = [
    { x: 0, y: 0, w: CAJA.w, h: 520 },
    { x: 62, y: 143, w: 782, h: 317 },
    { x: 148, y: 274, w: 610, h: 159 },
  ] as const;
  return { CAJA, CAPAS };
};

export const Anidado: React.FC<AnidadoProps> = ({
  titulo,
  base,
  capa_media,
  capa_dentro,
  placa,
  recorte = "lleno",
  sound = false,
}) => {
  const layout = useLienzo();
  const { CAJA, CAPAS } = cajaEn(layout);
  const entra = useEntrada();
  const textos = [base, capa_media, capa_dentro];

  // El horario: el universo primero, y cada capa cuando la anterior se pudo
  // leer. Ver el encargo — el orden de encaje ES el argumento.
  const entradas: number[] = [];
  let t = 0;
  for (const x of textos) {
    entradas.push(t);
    t += Math.max(18, readingFrames(x ?? ""));
  }

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.8} deriva={t + 90} />
      ) : null}
      {sound ? (
        <>
          <MotionSound motion="draw" at={entradas[0]} />
          <MotionSound motion="mark" at={entradas[1]} />
          <MotionSound motion="land" at={entradas[2]} />
        </>
      ) : null}

      <ZonaTablero>
        {titulo ? (
          <div
            style={{
              position: "absolute",
              top: 110,
              left: layout.safe.left,
              right: layout.safe.right,
              display: "flex",
              justifyContent: "flex-start",
              opacity: entra(0),
              fontFamily: fontFamily.bloque,
            }}
          >
            <Cinta tinte={color.lightNeutral} giro={-1.6} cuerpo={48}>
              {titulo}
            </Cinta>
          </div>
        ) : null}

        <div
          style={{
            position: "absolute",
            left: CAJA.x,
            top: CAJA.y,
            width: CAJA.w,
            height: CAJA.h,
          }}
        >
          {CAPAS.map((c, i) => {
            const texto = textos[i];
            if (!texto) return null;
            const p = entra(entradas[i]);
            const dentro = i === CAPAS.length - 1;
            return (
              <div
                key={texto}
                style={{
                  position: "absolute",
                  left: c.x,
                  top: c.y,
                  width: c.w,
                  height: c.h,
                  boxSizing: "border-box",
                  // El universo es contorno —no es una masa, es el límite de la
                  // cuenta—; lo que encaja dentro sí es bloque plano.
                  border: i ? "none" : `3px solid ${color.secondaryBlue}`,
                  backgroundColor: i
                    ? dentro
                      ? color.gold
                      : color.navy
                    : "transparent",
                  display: "flex",
                  // **El rótulo de una capa que contiene a otra va ARRIBA.**
                  // Centrado, el texto del 2,5% quedaba justo detrás de la
                  // astilla de oro que encaja dentro: en el frame se leía «EL»
                  // y un trozo. Sólo la de dentro se centra, porque no contiene
                  // nada.
                  alignItems: dentro ? "center" : "flex-start",
                  padding: dentro ? "0 40px" : i ? "22px 40px" : "24px 30px",
                  // Encaja: entra estrechándose desde su borde izquierdo, que es
                  // el gesto de meterse dentro y no el de aparecer encima.
                  opacity: p,
                  transform: `scaleX(${(0.86 + p * 0.14).toFixed(3)})`,
                  transformOrigin: "left center",
                }}
              >
                <div
                  style={{
                    fontFamily: fontFamily.bloque,
                    fontSize: cuerpoQueCabe({
                      ancho: c.w - 90,
                      largo: texto.length,
                      registro: "anton",
                      tope: dentro ? 84 : i ? 72 : 44,
                    }),
                    lineHeight: 0.98,
                    letterSpacing: "0.004em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                    color: dentro
                      ? color.richBlack
                      : i
                        ? color.lightNeutral
                        : color.secondaryBlue,
                  }}
                >
                  {texto}
                </div>
              </div>
            );
          })}
        </div>

        {/* **El pie ya no lo dibuja cada forma.** Va fuera de la zona segura,
            en una línea, y lo monta `dibujaTablero` para las 24 láminas del
            lote. Ver `PieTablero.tsx`. */}
      </ZonaTablero>
    </AbsoluteFill>
  );
};
