import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { color, ease, readingFrames } from "../brand/tokens";
import { Fondo, type Recorte } from "./Fondo";
import { Remate } from "./Remate";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";
import { Corredor } from "./desvio/Corredor";
import { useLienzo } from "../brand/LienzoContexto";
import type { Franja } from "../brand/franja";

/**
 * **La vía de siempre choca; la otra rodea el bloque y sale.**
 *
 * Es la única forma del lote que dice *«hay un camino y alguien encuentra
 * otro»* sin repartir en dos desde el principio, que es lo que hace `TwoPaths`.
 * Aquí las dos vías **son la misma hasta el choque**: la segunda se despega de
 * la primera, y ese despegue es el argumento entero.
 *
 * El encargo de reel-07 e2 lo escribe movimiento a movimiento: *«una banda
 * gruesa en azul pizarra entra desde la izquierda y corre hasta chocar contra
 * un bloque negro que la para en seco; la señal de desvío en oro cae encima del
 * choque; de la banda parada se despega una segunda banda que rodea el bloque
 * por arriba y sale del cuadro por delante de la primera; la cinta de remate se
 * sella al final»*.
 *
 * ## Cuatro movimientos, uno cada cuatro segundos
 *
 * El propio encargo lo fija —*«nada se queda quieto más de eso»*— y por eso el
 * horario se **reparte sobre la duración de la etapa** en vez de correr con
 * tiempos fijos: con tiempos fijos el tablero se monta en tres segundos y se
 * queda quieto los trece restantes, que es exactamente lo que hace que un
 * tablero se sienta relleno.
 *
 * Y la señal en oro es lo único vivo del cuadro: el desvío es lo que hay que
 * mirar, así que las dos bandas van en la paleta oscura.
 * @clase tablero
 */
export type DesvioProps = {
  /** La vía de siempre. Va sobre la banda que choca. */
  premisa: string;
  /** La que se despega y rodea. Va sobre la segunda banda. */
  desvio: string;
  /** El remate, sellado al final en cinta de oro. */
  remate?: string;
  fuente?: string;
  source?: string;
  condicion?: string;
  placa?: string;
  recorte?: Recorte;
  /** Cuánto dura la etapa que este tablero reemplaza, en frames. */
  duracion?: number;
  sound?: boolean;
};

/**
 * La geometría del choque, dentro de lo que el tablero puede ocupar.
 *
 * **Y ocupa lo que puede, no el tercio de arriba.** Jaime, sobre R-07 e2: *«15,9
 * s con el 75% del cuadro en negro vacío»*. Estaba medido y era cierto: el
 * choque acababa en 520, el remate en 730, y de ahí al techo de la franja —1048—
 * no había nada, con el subtítulo flotando en el medio. Los números vivían
 * escritos a mano y ninguno miraba cuánto sitio hay.
 */
/** Medida sobre el techo de la franja de su lienzo (C-670). */
const geometria = (franja: Franja) => {
  const ZONA = franja.techoPx;
  const VIA = { y: Math.round(ZONA * 0.4), alto: 132 } as const;
  const BLOQUE = { x: 790, y: VIA.y - 48, w: 230, h: 228 } as const;
  /** La banda que rodea: sube por aquí y sale por arriba. */
  const RODEO = { x: 636, y: Math.round(ZONA * 0.14), alto: 112 } as const;
  /**
   * **El corredor de fuga: adónde va la que se desvía.**
   *
   * Es lo que llena la mitad de abajo, y no es relleno — es el canon: *«punto de
   * fuga, geometría rota, líneas»*, y el elemento conceptual dice lo que dice el
   * beat. Aquí el beat es *hay otra manera y alguien la encuentra*, así que las
   * líneas se abren desde el bloque que paró a la primera vía hacia un punto que
   * está fuera, y la luz recorre la que sale.
   *
   * Sustituye a lo que el canon acaba de retirar —*«las animaciones de bolitas y
   * palitos se acaban, quitan más de lo que dan»*—: no es una viñeta que aparece,
   * es profundidad que se abre mientras la banda escapa.
   */
  const FUGA = { x: 300, y: ZONA - 40 } as const;
  return { ZONA, VIA, BLOQUE, RODEO, FUGA };
};
/** Impar, para que haya una central: es la que sale. */
const LINEAS_FUGA = 9;

export const Desvio: React.FC<DesvioProps> = ({
  premisa,
  desvio,
  remate,
  placa,
  recorte = "lleno",
  duracion,
  sound = false,
}) => {
  const layout = useLienzo();
  const { ZONA, VIA, BLOQUE, RODEO, FUGA } = geometria(layout.franja);
  const frame = useCurrentFrame();
  const entra = useEntrada();

  const total = Math.max(
    duracion ?? 0,
    readingFrames(premisa) + readingFrames(desvio) + 90,
  );
  const tChoque = Math.round(total * 0.14);
  const tSenal = Math.round(total * 0.22);
  const tRodeo = Math.round(total * 0.3);
  const tRemate = Math.round(total * 0.6);

  /** El avance de una banda. Lineal: un trazo que frena parece dudar. */
  const traza = (desde: number, hasta: number) =>
    interpolate(frame, [desde, hasta], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.linear,
    });

  const corre = traza(0, tChoque);
  const sube = traza(tRodeo, tRodeo + 14);
  const sale = traza(tRodeo + 14, Math.round(total * 0.46));
  /** El corredor se abre detrás de la banda que sale, no antes. */
  const abre = traza(tRodeo + 14, Math.round(total * 0.58));
  /**
   * **La luz que recorre la salida.** Recorre la banda de arriba abajo una vez
   * por cada tercio de lo que queda, con borde duro: es un plano de luz
   * constructivista, no un degradado. Se apaga cuando entra el remate para no
   * competir con lo que hay que leer.
   */
  const barrido = interpolate(
    frame,
    [tRodeo + 20, tRemate],
    [-0.35, 1.35],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease.linear },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.7} deriva={total} />
      ) : null}
      {sound ? (
        <>
          <MotionSound motion="whoosh" at={0} />
          <MotionSound motion="land" at={tChoque} />
          <MotionSound motion="mark" at={tSenal} />
          <MotionSound motion="draw" at={tRodeo} />
          {remate ? <MotionSound motion="land" at={tRemate} /> : null}
        </>
      ) : null}

      <ZonaTablero>
        {/* La vía de siempre: corre desde el borde izquierdo y se para en seco
            contra el bloque. No se desvanece — se PARA, que es lo que dice. */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: VIA.y,
            height: VIA.alto,
            width: BLOQUE.x * corre,
            backgroundColor: color.navy,
            display: "flex",
            alignItems: "center",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              paddingLeft: layout.safe.left,
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoQueCabe({
                ancho: BLOQUE.x - layout.safe.left - 40,
                largo: premisa.length,
                registro: "anton",
                tope: 66,
              }),
              lineHeight: 1,
              letterSpacing: "0.004em",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              color: color.lightNeutral,
              opacity: entra(Math.round(tChoque * 0.4)),
            }}
          >
            {premisa}
          </div>
        </div>

        {/* El bloque que la para. Negro con filete: es un límite, no una masa. */}
        <div
          style={{
            position: "absolute",
            left: BLOQUE.x,
            top: BLOQUE.y,
            width: BLOQUE.w,
            height: BLOQUE.h,
            backgroundColor: color.richBlack,
            border: `3px solid ${color.secondaryBlue}`,
            boxSizing: "border-box",
            opacity: entra(0),
          }}
        />

        {/* La señal de desvío: un cuadrado a 45°, que es el único ángulo que el
            canon admite fuera de la escuadra. Cae sobre el choque. */}
        <div
          style={{
            position: "absolute",
            left: BLOQUE.x - 62,
            top: VIA.y - 18,
            width: 118,
            height: 118,
            backgroundColor: color.gold,
            transform: `rotate(45deg) scale(${entra(tSenal).toFixed(3)})`,
            opacity: entra(tSenal),
          }}
        />

        {/* La banda que se despega: sube por delante del bloque y sale por
            arriba, cruzando el cuadro entero. */}
        <div
          style={{
            position: "absolute",
            left: RODEO.x,
            top: RODEO.y + RODEO.alto,
            width: RODEO.alto,
            height: (VIA.y - RODEO.y - RODEO.alto) * sube,
            backgroundColor: color.navyHi,
            transformOrigin: "bottom",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: RODEO.x,
            top: RODEO.y,
            height: RODEO.alto,
            width: (layout.width - RODEO.x) * sale,
            backgroundColor: color.navyHi,
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-start",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              paddingLeft: 32,
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoQueCabe({
                ancho: layout.width - RODEO.x - 60,
                largo: desvio.length,
                registro: "anton",
                tope: 58,
              }),
              lineHeight: 1,
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              color: color.lightNeutral,
              opacity: sale,
            }}
          >
            {desvio}
          </div>
          {/* La luz que recorre la salida: plano de borde duro, no degradado. */}
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: `${barrido * 100}%`,
              width: 120,
              backgroundColor: color.gold,
              opacity: 0.34,
              transform: "skewX(-18deg)",
            }}
          />
        </div>

        <Corredor
          desdeY={VIA.y + VIA.alto}
          fuga={FUGA}
          lineas={LINEAS_FUGA}
          abre={abre}
        />

        {remate ? (
          <div
            style={{
              position: "absolute",
              left: layout.safe.left,
              top: Math.round(ZONA * 0.78),
              opacity: entra(tRemate),
              fontFamily: fontFamily.bloque,
            }}
          >
            {/* **Un acento por tablero, y aquí es la señal de desvío.** El
                cuadrado a 45° marca dónde se bifurca el camino, que es lo que
                el tablero demuestra; el remate lo dice con palabras y va en
                claro. Ver `Remate.tsx`. */}
            <Remate giro={-1.9} cuerpo={68}>{remate}</Remate>
          </div>
        ) : null}

        {/* **El pie ya no lo dibuja cada forma.** Va fuera de la zona segura,
            en una línea, y lo monta `dibujaTablero` para las 24 láminas del
            lote. Ver `PieTablero.tsx`. */}
      </ZonaTablero>
    </AbsoluteFill>
  );
};
