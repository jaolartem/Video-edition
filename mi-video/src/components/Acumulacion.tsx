import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { MotionSound } from "./MotionSound";
import { Cinta, Fondo, Panel } from "./Fondo";
import { ZonaTablero } from "./ZonaTablero";
import {
  color,
  duration,
  ease,
  layout,
  readingFrames,
  size,
  tracking,
} from "../brand/tokens";

/**
 * Una magnitud que se acumula, y la línea que no había que cruzar.
 *
 * Es el tablero de tres beats del lote, y los tres dicen literalmente esto:
 *
 * - R5 · *«dejó la plata dentro de la corporación mientras esperaba los meses
 *   lentos»* — la barra crece por debajo de la línea. Aún no pasa nada.
 * - R5 · *«cuando esa plata quieta cruzó cierto umbral, el gobierno empezó a
 *   cobrarle más sobre cada dólar nuevo»* — la barra cruza, y lo que asoma por
 *   encima se pone en oro. **$14,000.**
 * - R6 · *«en diez años eso es entre $250.000 y $300.000»* — la misma barra sin
 *   umbral: sólo acumulación sobre un horizonte declarado.
 *
 * Jaime: *«cada animación funciona como un tablero que muestra gráficamente lo
 * que se dice en el audio»*. Por eso la geometría no ilustra el tema, dice la
 * frase: hay una cantidad que sube, hay una raya, y el momento en que la
 * cantidad pasa la raya es el momento en que la voz lo dice.
 *
 * ## El canon
 *
 * La referencia son **los carruseles de Jaime**, y mandan sobre el canon — palabras
 * suyas: *«esto es más canon que el el canon; el el canon de hecho sirvió como inspiración,
 * pero esto es mucho más cercano a lo que quiero»*. De ahí sale la anatomía, y
 * lo que cambia respecto de la web es sustantivo:
 *
 * - **Condensada pesada en versales para TODO lo grande**, cifras incluidas. En
 *   los doce ejemplos no aparece la serif ni una vez. Playfair se queda en la
 *   web, que se lee con calma y sin compresión encima.
 * - **Fotomontaje debajo**, no fondo plano. Ver `Fondo`.
 * - **Panel opaco y girado** sosteniendo el contenido, y **cintas** cruzándolo.
 * - **El oro es superficie**, no sólo tinta: paneles y bandas enteras en oro.
 *
 * **Cumplimiento por construcción:** `resultado` exige cifra y fuente juntas
 * —el tipo no admite una sin la otra— y `horizonte` y `condicion` son
 * obligatorias. Una cifra acumulada sin horizonte no significa nada, y sin
 * condición se lee como promesa de resultado, que el playbook prohíbe.
 */
export type Tramo = {
  /** Qué es este tramo. Versales condensadas, al lado de su bloque. */
  etiqueta: string;
  /** Cuánto ocupa, en fracción de la altura total del gráfico (0–1). */
  alto: number;
};

export type AcumulacionProps = {
  title: string;
  /** Qué se acumula. Va en la cinta de arriba, con el horizonte. */
  concepto: string;
  /**
   * El horizonte sobre el que se acumula. **Obligatorio**: «$300.000» no dice
   * nada hasta que se sabe si son diez años o un trimestre.
   */
  horizonte: string;
  /** Los tramos, de abajo arriba. Entran de uno en uno. */
  tramos: Tramo[];
  /**
   * La raya. Opcional — no toda acumulación tiene umbral: la de diez años del
   * R6 sólo crece.
   */
  umbral?: { etiqueta: string; en: number };
  /** Lo que la acumulación produce. Cifra Y fuente, o ninguna de las dos. */
  resultado?: { figure: string; source: string };
  /** Qué cambiaría el cálculo. **Obligatorio.** */
  condicion: string;
  /**
   * Placa de fondo, si el tablero la lleva. **El collage asoma por los bordes y
   * el panel opaco sostiene las cifras** — que es como lo hace el canon: una
   * tabla sobre un fotomontaje no se lee, pero una tabla flotando en negro deja
   * medio cuadro muerto. Jaime: *«más color y movimiento»*.
   */
  placa?: string;
  /** Requiere los ficheros de `public/sfx/`. */
  sound?: boolean;
};

/**
 * Caja del panel sobre el que se apoya todo, **dentro de la zona del tablero**.
 *
 * Iba de 300 a 1390 y la banda de condición al 1452: los dos por debajo del
 * 65% de altura, o sea bajo la interfaz de la plataforma. Nadie los veía. Con
 * T-02 el tablero acaba en el techo de la franja del subtítulo (1048), así que
 * el panel se recoge y la banda se cuelga de ese techo.
 *
 * Lo que se paga es escala, no contenido: el eje y la cifra de remate bajan de
 * tamaño y el tablero dice exactamente lo mismo — en el sitio donde se ve.
 */
const PANEL = { x: 46, y: 270, w: 988, h: 610 } as const;
/** Caja del gráfico, en coordenadas del panel. */
const EJE = { x: 60, y: 170, alto: 250 } as const;
const BARRA = 330;

export const Acumulacion: React.FC<AcumulacionProps> = ({
  title,
  concepto,
  horizonte,
  tramos,
  umbral,
  resultado,
  condicion,
  placa,
  sound = false,
}) => {
  const frame = useCurrentFrame();

  assertShort(title, "title", "Acumulacion.title");
  assertShort(concepto, "label", "Acumulacion.concepto");
  assertShort(horizonte, "label", "Acumulacion.horizonte");
  assertShort(condicion, "legal", "Acumulacion.condicion");
  if (resultado) {
    assertShort(resultado.figure, "outcome", "Acumulacion.resultado.figure");
  }

  /**
   * Cuándo entra cada cosa, en cadena por tiempo de lectura.
   *
   * El componente lleva su propio horario, así que **la duración del hueco tiene
   * que salir de aquí, no de un número redondo puesto desde fuera**: con 5,5 s
   * el `TwoPaths` mostraba sólo la cabecera y parecía roto cuando estaba a medio
   * construir. `duracionDe` lo publica para que el spec lo pregunte.
   */
  const raya = duration.entry * 2;
  const entradas: number[] = [];
  let reloj = raya + duration.entry;
  for (const tr of tramos) {
    entradas.push(reloj);
    reloj += Math.max(duration.entry + 4, readingFrames(tr.etiqueta));
  }
  const finTramos = reloj;

  const p = (desde: number, dura = duration.entry) =>
    interpolate(frame, [desde, desde + dura], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });

  const bases: number[] = [];
  let suma = 0;
  for (const tr of tramos) {
    bases.push(suma);
    suma += tr.alto;
  }

  const aPx = (f: number) => Math.min(1, Math.max(0, f)) * EJE.alto;
  const suelo = EJE.y + EJE.alto;
  const yUmbral = umbral ? suelo - aPx(umbral.en) : null;
  const cruce = umbral
    ? tramos.findIndex((tr, i) => bases[i] + tr.alto > umbral.en)
    : -1;

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? <Fondo placa={placa} recorte="columna" fuerza={1} deriva={finTramos + 60} /> : null}
      {/**
       * **Tablero de datos: fondo PLANO.** No lleva fotomontaje.
       *
       * El canon tiene dos familias y se alternan. La cargada —punto de fuga,
       * geometría rota, elemento conceptual— acompaña el golpe. La tranquila
       * —negro o navy liso, geometría plana, grilla respetada— es donde hay
       * cifras que leer, y ésta es de ésas: una tabla sobre un fotomontaje es
       * una tabla que no se lee.
       *
       * Y la regla que las une: **lo que está torcido está torcido con
       * intención**. Aquí lo único torcido son las cintas. El panel va a
       * escuadra porque sostiene números.
       */}

      {sound ? (
        <>
          <MotionSound motion="draw" at={raya} />
          {entradas.map((f, i) => (
            <MotionSound key={tramos[i].etiqueta} motion="mark" at={f} />
          ))}
          {resultado ? <MotionSound motion="land" at={finTramos + 6} /> : null}
          {umbral && cruce >= 0 && !resultado ? (
            <MotionSound motion="land" at={entradas[cruce]} />
          ) : null}
        </>
      ) : null}

      {/**
       * **Sin cabecera.** Llevaba `EL CÓDIGO DEL EMPRESARIO / INFORMATION GAP`
       * y el contador `03—08`, y Jaime lo señaló: *«tiene un título en la parte
       * superior que no debe ir ahí»*.
       *
       * Dos motivos, y los dos son de traducción de medio:
       *
       * - **El nombre de la estructura es vocabulario del playbook.** «Information
       *   Gap» no significa nada para un dueño de negocio, igual que «revelación»
       *   no significaba nada en la cortinilla.
       * - **El contador es una prestación de carrusel.** Orienta cuando deslizas
       *   seis láminas; en vídeo no hay nada que contar y sólo ocupa la franja
       *   donde debería empezar el contenido.
       *
       * Que el frame esté presente no es imprimir su nombre: es que la pieza
       * respete su secuencia. Eso lo garantiza el montaje, no un rótulo.
       */}

      {/* Todo lo que hay que LEER va dentro de la zona del tablero: del borde
          de arriba al techo de la franja del subtítulo. El fondo se queda
          fuera, que ocupa el cuadro entero. Ver `ZonaTablero`. */}
      <ZonaTablero>
      {/* Cinta de encabezado: las condiciones de la comparación. Va arriba y en
          claro, como en el canon — es el marco del dato, no el dato. */}
      <div
        style={{
          position: "absolute",
          top: 152,
          left: layout.safe.left,
          right: layout.safe.right,
          display: "flex",
          justifyContent: "center",
          opacity: p(0),
          fontFamily: fontFamily.bloque,
        }}
      >
        <Cinta tinte={color.lightNeutral} giro={-1.6} cuerpo={44}>
          {concepto} · {horizonte}
        </Cinta>
      </div>

      <Panel
        giro={0}
        style={{
          left: PANEL.x,
          top: PANEL.y,
          width: PANEL.w,
          height: PANEL.h,
        }}
      >
        {/* Cuerpo ajustado a la linea, y `nowrap`.
            El titulo se partia en «LA PLATA QUE SE QUEDO / QUIETA», con la
            segunda linea huerfana. **Donde respira una frase lo decide quien la
            escribe**, no el ancho que sobra — y el render es determinista, asi
            que no hay layout al que preguntar: se estima. Anton gasta ~0,47 em
            por caracter en versales, medido sobre render. */}
        <div
          style={{
            position: "absolute",
            top: 44,
            left: 56,
            right: 56,
            fontFamily: fontFamily.bloque,
            fontSize: Math.min(96, (PANEL.w - 112) / (title.length * 0.47)),
            lineHeight: 0.94,
            letterSpacing: "0.004em",
            whiteSpace: "nowrap",
            textTransform: "uppercase",
            color: color.lightNeutral,
            opacity: p(0),
          }}
        >
          {title}
        </div>

        {/* La barra: cada tramo se parte en lo que queda debajo de la raya y lo
            que asoma por encima. Ese corte ES el argumento. */}
        {tramos.map((tr, i) => {
          const crece = p(entradas[i]);
          const base = bases[i];
          const tope = base + tr.alto;
          const corte = umbral ? Math.min(Math.max(umbral.en, base), tope) : tope;
          const partes = [
            { desde: base, hasta: corte, oro: false },
            { desde: corte, hasta: tope, oro: true },
          ].filter((q) => q.hasta > q.desde);
          return (
            <React.Fragment key={tr.etiqueta}>
              {partes.map((q) => (
                <div
                  key={q.oro ? "oro" : "base"}
                  style={{
                    position: "absolute",
                    left: EJE.x,
                    width: BARRA,
                    top: suelo - aPx(q.hasta),
                    height: aPx(q.hasta) - aPx(q.desde),
                    backgroundColor: q.oro
                      ? color.gold
                      : i % 2
                        ? color.navyHi
                        : color.navy,
                    transformOrigin: "bottom",
                    transform: `scaleY(${crece})`,
                  }}
                />
              ))}
              {/* Etiqueta centrada en su bloque y en UNA línea. Sin `nowrap`
                  «Cruza el umbral» salía en tres renglones dentro de una
                  columna estrecha y se leía como tres etiquetas distintas:
                  dónde respira una frase lo decide quien la escribe, no el
                  ancho que sobra. */}
              <div
                style={{
                  position: "absolute",
                  left: EJE.x + BARRA + 34,
                  top: suelo - aPx((base + tope) / 2) - 22,
                  whiteSpace: "nowrap",
                  fontFamily: fontFamily.bloque,
                  fontSize: 40,
                  letterSpacing: "0.01em",
                  textTransform: "uppercase",
                  color: q0Color(i, umbral, base, tope),
                  opacity: crece,
                }}
              >
                {assertShort(tr.etiqueta, "label", "Acumulacion.tramo")}
              </div>
            </React.Fragment>
          );
        })}

        {/* La raya. Se traza ANTES de que la barra llegue: primero se ve el
            límite, después se ve cruzarlo. Al revés no hay drama, hay un dato. */}
        {umbral && yUmbral !== null ? (
          <>
            <div
              style={{
                position: "absolute",
                left: EJE.x - 34,
                top: yUmbral,
                width: (PANEL.w - EJE.x - 20) * p(raya),
                height: 4,
                backgroundColor: color.gold,
              }}
            />
            {/* Al final de la raya, no al principio: al principio cae debajo
                de la barra y desaparece justo cuando la barra la cruza, que es
                el unico momento en que hace falta leerla. */}
            <div
              style={{
                position: "absolute",
                right: 56,
                top: yUmbral - 52,
                fontFamily: fontFamily.bloque,
                fontSize: 34,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: color.gold,
                opacity: p(raya),
              }}
            >
              {assertShort(umbral.etiqueta, "label", "Acumulacion.umbral")}
            </div>
          </>
        ) : null}

        {resultado ? (
          <div
            style={{
              position: "absolute",
              left: EJE.x - 34,
              right: 56,
              top: suelo + 48,
              opacity: p(finTramos + 6),
            }}
          >
            <div
              style={{
                fontFamily: fontFamily.bloque,
                // 96 y no 132: la cifra de remate cabe dentro de la zona del
                // tablero. Ver `PANEL`.
                fontSize: 96,
                lineHeight: 0.9,
                letterSpacing: "0.002em",
                textTransform: "uppercase",
                color: color.gold,
                whiteSpace: "nowrap",
                transform: `translateY(${(1 - p(finTramos + 6)) * 22}px)`,
              }}
            >
              {resultado.figure}
            </div>
            <div
              style={{
                marginTop: 14,
                fontFamily: fontFamily.data,
                fontSize: size.source,
                letterSpacing: tracking.labelMono,
                color: color.secondaryBlue,
                textTransform: "uppercase",
              }}
            >
              {resultado.source}
            </div>
          </div>
        ) : null}
      </Panel>

      {/* Banda inferior: la condición. Lleva banda propia y no vive de adorno
          al pie — un límite que comparte pantalla con el argumento no se lee.
          Colgada del TECHO de la franja: crece hacia arriba y no puede bajar. */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: color.lightNeutral,
          transform: "rotate(0.9deg)",
          padding: "16px 64px",
          fontFamily: fontFamily.video,
          fontSize: 24,
          fontWeight: 700,
          lineHeight: 1.26,
          color: color.richBlack,
          opacity: p(finTramos + 14),
        }}
      >
        {condicion}
      </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};

/**
 * Color de la etiqueta de un tramo: oro si el tramo asoma por encima de la
 * raya, azul secundario si no. **El oro marca lo que hay que mirar**, así que
 * la etiqueta se pone de acuerdo con su bloque en vez de ir toda del mismo
 * color y dejar que el espectador empareje a mano.
 */
const q0Color = (
  _i: number,
  umbral: { en: number } | undefined,
  base: number,
  tope: number,
): string =>
  umbral && tope > umbral.en && base < tope ? color.gold : color.secondaryBlue;

/**
 * Cuánto dura el tablero completo, en frames.
 *
 * **Un componente con horario propio necesita su tiempo.** El spec pregunta en
 * vez de poner un número redondo: con 5,5 s el `TwoPaths` mostraba sólo la
 * cabecera y el pie, y en el render parecía un tablero vacío cuando lo que
 * estaba era a medio construir.
 */
export const duracionDe = (props: AcumulacionProps): number => {
  let reloj = duration.entry * 3;
  for (const tr of props.tramos) {
    reloj += Math.max(duration.entry + 4, readingFrames(tr.etiqueta));
  }
  return reloj + readingFrames(props.condicion) + 20;
};
