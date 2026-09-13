import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { color, layout, readingFrames, size, tracking } from "../brand/tokens";
import { Cinta, Fondo, type Recorte } from "./Fondo";
import { Remate } from "./Remate";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";
import { FileteFicha } from "./fichas/Ficha";

/**
 * **Dos cosas que el espectador cree separadas y son una sola.**
 *
 * El encargo de reel-04 e3 la dibuja entera: *«dos rectángulos iguales en azul
 * pizarra separados por un filete de un píxel: EL NEGOCIO a la izquierda,
 * USTED a la derecha. Al oírse "son la misma cosa" el filete desaparece y los
 * dos se juntan en un solo bloque, que pasa a oro»*.
 *
 * ## Por qué el filete es el componente
 *
 * Porque **lo que se quita es el argumento**. Un tablero que enseñara el bloque
 * fusionado desde el principio diría lo mismo con letras y no explicaría nada:
 * el espectador tiene que ver primero los dos separados —que es como lo tiene
 * en la cabeza— y luego ver desaparecer la raya. La animación no es adorno
 * aquí; es la frase.
 *
 * Después caen dentro del bloque las cosas que quedan expuestas, una a una y
 * cada una cuando se la nombra, y al final el veredicto con una pausa delante.
 * @clase tablero
 */
export type FusionProps = {
  /** Titular del tablero. Cinta, arriba. */
  title?: string;
  /** El bloque de la izquierda antes de la fusión. */
  izquierda: string;
  /** El de la derecha. */
  derecha: string;
  /** Lo que los dos resultan ser. Es el oro. */
  fusion: string;
  /** Rótulo del grupo que queda a la vista. */
  expuesto?: string;
  /** Lo que queda expuesto, en el orden en que se nombra. */
  expone?: string[];
  /** El remate, con pausa delante. */
  veredicto?: string;
  fuente?: string;
  source?: string;
  condicion?: string;
  placa?: string;
  recorte?: Recorte;
  sound?: boolean;
  /** Frames desde el arranque en que se dice cada campo anclado. Lo pone el motor. */
  tiempos?: Record<string, number | (number | undefined)[] | undefined>;
};

const ANCHO = layout.width - layout.safe.left * 2;
/** Caja del bloque que se fusiona. */
const BLOQUE = { y: 200, h: 270 } as const;
/** Caja de las etiquetas expuestas: dos columnas, dos filas. */
const ETIQUETA = { y: 540, alto: 86 } as const;

export const Fusion: React.FC<FusionProps> = ({
  title,
  izquierda,
  derecha,
  fusion,
  expuesto,
  expone = [],
  veredicto,
  placa,
  recorte = "lleno",
  sound = false,
  tiempos,
}) => {
  const entra = useEntrada();

  // El horario. La fusión espera a que las dos mitades se hayan podido leer:
  // si llega antes, el espectador no llegó a verlas separadas y no se fusiona
  // nada.
  const tDos = 0;
  // **Y si el diseño lo ancló, cuando él lo dice** (C-442): el reloj fijo
  // metía las fichas 6 a 15 s antes de que se nombraran (reel-11 e3).
  const t = tiempos ?? {};
  const uno = (v: unknown) => (typeof v === "number" ? v : undefined);
  const tFusion = uno(t.fusion) ?? Math.max(24, readingFrames(`${izquierda} ${derecha}`));
  const tsExpone = expone.map(
    (_e, i) => (Array.isArray(t.expone) ? uno(t.expone[i]) : undefined)
      ?? tFusion + 20 + i * Math.max(14, Math.round(0.6 * 30)),
  );
  const tVeredicto = uno(t.veredicto)
    ?? (tsExpone[tsExpone.length - 1] ?? tFusion) + 34;
  const pFusion = entra(tFusion);

  const mitad = (texto: string, lado: "izq" | "der") => {
    const p = entra(tDos);
    return (
      <div
        style={{
          flex: 1,
          height: BLOQUE.h,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          // El azul pizarra se va al oro en el momento de la fusión: no es un
          // fundido de color, es el bloque que cambia de identidad.
          backgroundColor: pFusion > 0.5 ? color.gold : color.navy,
          opacity: p,
          transform: `translateX(${
            ((1 - p) * (lado === "izq" ? -40 : 40)).toFixed(1)
          }px)`,
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.bloque,
            fontSize: 56,
            lineHeight: 1,
            textTransform: "uppercase",
            letterSpacing: "0.004em",
            whiteSpace: "nowrap",
            // Al fusionarse, el rótulo de cada mitad cede el sitio al de la
            // fusión: dos nombres dentro de un bloque que ya es uno se leen
            // como dos bloques otra vez.
            opacity: 1 - pFusion,
            color: color.lightNeutral,
          }}
        >
          {texto}
        </div>
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.75} deriva={tVeredicto + 90} />
      ) : null}
      {sound ? (
        <>
          <MotionSound motion="land" at={tFusion} />
          {tsExpone.map((f, i) => (
            <MotionSound key={expone[i]} motion="mark" at={f} />
          ))}
          {veredicto ? <MotionSound motion="land" at={tVeredicto} /> : null}
        </>
      ) : null}

      <ZonaTablero>
        {title ? (
          <div
            style={{
              position: "absolute",
              top: 100,
              left: layout.safe.left,
              opacity: entra(0),
              fontFamily: fontFamily.bloque,
            }}
          >
            <Cinta tinte={color.lightNeutral} giro={-1.5} cuerpo={46}>
              {title}
            </Cinta>
          </div>
        ) : null}

        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            top: BLOQUE.y,
            width: ANCHO,
            height: BLOQUE.h,
            display: "flex",
          }}
        >
          {mitad(izquierda, "izq")}
          {/* El filete que separa. Desaparece, y con él la separación: es el
              único movimiento que este tablero necesita para decir su frase. */}
          <div style={{ opacity: 1 - pFusion, display: "flex" }}>
            <FileteFicha vertical largo={BLOQUE.h} />
          </div>
          {mitad(derecha, "der")}
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: pFusion,
              // **Y el bloque fundido es UNO: se pinta entero.** Sin fondo, la
              // rendija del filete (1-2 px) dejaba ver la placa y partía LA
              // MISMA COSA entre la M y la A (reel-11 e3, C-449).
              backgroundColor: color.gold,
              pointerEvents: "none",
            }}
          >
            <div
              style={{
                fontFamily: fontFamily.bloque,
                fontSize: cuerpoQueCabe({
                  ancho: ANCHO - 120,
                  largo: fusion.length,
                  registro: "anton",
                  tope: 116,
                }),
                lineHeight: 1,
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                color: color.richBlack,
              }}
            >
              {fusion}
            </div>
          </div>
        </div>

        {expuesto ? (
          <div
            style={{
              position: "absolute",
              left: layout.safe.left,
              top: ETIQUETA.y - 46,
              // Sobre la placa el azul pizarra a 26 px desaparece: se leía como
              // una mancha. La etiqueta va sobre su propio bloque plano, que es
              // como el canon sostiene la letra pequeña encima de un collage.
              backgroundColor: color.navy,
              padding: "6px 14px",
              fontFamily: fontFamily.data,
              fontSize: size.labelMono,
              letterSpacing: tracking.labelMono,
              textTransform: "uppercase",
              color: color.lightNeutral,
              opacity: pFusion,
            }}
          >
            {expuesto}
          </div>
        ) : null}

        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            top: ETIQUETA.y,
            width: ANCHO,
            display: "flex",
            flexWrap: "wrap",
            gap: 4,
          }}
        >
          {expone.map((e, i) => {
            const p = entra(tsExpone[i]);
            return (
              <div
                key={e}
                style={{
                  width: (ANCHO - 4) / 2,
                  height: ETIQUETA.alto,
                  display: "flex",
                  alignItems: "center",
                  padding: "0 26px",
                  boxSizing: "border-box",
                  backgroundColor: color.navy,
                  fontFamily: fontFamily.bloque,
                  fontSize: 40,
                  letterSpacing: "0.01em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  color: color.lightNeutral,
                  opacity: p,
                  transform: `translateY(${((1 - p) * -22).toFixed(1)}px)`,
                }}
              >
                {e}
              </div>
            );
          })}
        </div>

        {veredicto ? (
          <div
            style={{
              position: "absolute",
              left: layout.safe.left,
              // 720 y no 760: la banda de fuente y condición se apoya en el
              // techo de la franja y sube lo que ocupe su texto — la de reel-04
              // son ~200 px, o sea desde el 848. Con la cinta en 760 se pisaban
              // por seis píxeles, que en el frame se ve como un solape.
              top: 720,
              opacity: entra(tVeredicto),
              fontFamily: fontFamily.bloque,
            }}
          >
            {/* **Un acento por tablero, y aquí es el bloque que se funde.**
                Lo que este tablero demuestra es que cuatro cosas distintas
                acaban siendo una sola, y eso lo dice el bloque al pasar a oro.
                Con el veredicto también en oro son dos masas gritando a la vez.
                Ver `Remate.tsx`. */}
            <Remate giro={1.7} cuerpo={62}>{veredicto}</Remate>
          </div>
        ) : null}

        {/* **El pie ya no lo dibuja cada forma.** Va fuera de la zona segura,
            en una línea, y lo monta `dibujaTablero` para las 24 láminas del
            lote. Ver `PieTablero.tsx`. */}

      </ZonaTablero>
    </AbsoluteFill>
  );
};
