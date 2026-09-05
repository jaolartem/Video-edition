import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { MotionSound } from "./MotionSound";
import { Cinta, Fondo } from "./Fondo";
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
 * Dos columnas, mismas condiciones de partida, resultados distintos.
 *
 * Es el tablero de la **familia tranquila**: fondo plano, geometría a escuadra,
 * y lo único torcido son las cintas. Va donde hay cifras que leer — una tabla
 * sobre un fotomontaje es una tabla que no se lee.
 *
 * Sirve a tres beats del lote, y los tres son la misma forma:
 *
 * - R2 · *«en inglés va a encontrar seminarios del CRA; en español, solo hay
 *   uno»* — la asimetría ES el argumento.
 * - R1 · *«$180.000 de utilidad: sin estructura paga $30.000 más»*.
 * - R3 · *«hasta 53,53% marginal; con la mezcla correcta, 32%»* — y aquí no es
 *   opcional: en Polarizing Thesis **la demostración carga el argumento**, la
 *   actitud sola no.
 *
 * ## Por qué no es `TwoPaths`
 *
 * `TwoPaths` es el componente de **una** estructura del playbook — Two Paths /
 * Default Loss, que en este lote sólo ejecuta el reel 2 — y recorre dos
 * trayectorias paso a paso con horizonte y condición obligatorios. Esto es otra
 * cosa: una comparación de dos estados como **evidencia** dentro de otra
 * estructura. Usar `TwoPaths` en los cuatro reels hacía que cuatro frameworks
 * distintos se vieran idénticos, y entonces el componente deja de significar
 * nada.
 *
 * ## Cumplimiento por construcción
 *
 * `fuente` es obligatoria: si el tablero enseña cifras, lleva de dónde salen.
 * `condicion` también — sin ella la comparación se lee como promesa de
 * resultado, y el playbook prohíbe garantizar resultados individuales.
 */
export type Columna = {
  /** Cabecera de la columna. Versales condensadas. */
  titulo: string;
  /** La cifra o el estado. Es el remate de la columna. */
  cifra: string;
  /** Una línea de detalle, si hace falta. */
  pie?: string;
};

export type ComparacionProps = {
  /** Cinta superior: la condición común. «Misma facturación», «De cada $100». */
  premisa: string;
  /** La columna del estado por defecto. Va en navy: no es donde hay que mirar. */
  izquierda: Columna;
  /** La columna que importa. Va en oro. */
  derecha: Columna;
  /** Cinta inferior: la diferencia, o la pregunta que deja. */
  remate?: string;
  /** De dónde salen las cifras. **Obligatoria.** */
  fuente: string;
  /** Qué cambiaría la comparación. **Obligatoria.** */
  condicion: string;
  /**
   * Placa de fondo, si el tablero la lleva. **El collage asoma por los bordes y
   * el panel opaco sostiene las cifras** — que es como lo hace el canon: una
   * tabla sobre un fotomontaje no se lee, pero una tabla flotando en negro deja
   * medio cuadro muerto. Jaime: *«más color y movimiento»*.
   */
  placa?: string;
  /**
   * Cuánto dura la escena que este tablero **reemplaza**, en frames.
   *
   * Jaime: *«el tablero reemplaza la escena, y el tablero es un instrumento
   * pedagógico»*; y *«se tiene que presentar poco a poco y durar toda la
   * escena»*. Así que el horario no es fijo: se **reparte** sobre el tiempo
   * disponible.
   *
   * Con un horario fijo el tablero se montaba en 10 s y se quedaba quieto el
   * resto — que es justo lo que hace que un tablero se sienta relleno. Repartido,
   * cada elemento entra cuando el anterior ya se pudo leer Y hay algo entrando
   * hasta el final.
   */
  duracion?: number;
  /** Requiere los ficheros de `public/sfx/`. */
  sound?: boolean;
};

// **Aire.** Jaime: *«dales aire y espacio a los tableros, que se sientan útiles
// y no un comodity para cambiar escenas»*. Las columnas ocupaban 500-1200 y el
// resto era negro apretado arriba y vacío abajo; ahora respiran de verdad y el
// pie legal tiene su banda.
/**
 * Caja de las columnas, **dentro de la zona del tablero**.
 *
 * Jaime: *«en los tableros también hay cc»*. Y es distinto del panel: bajo un
 * panel la voz dice lo que el panel muestra, así que el subtítulo repetiría;
 * bajo un tablero la voz **sigue diciendo cosas que el tablero no enseña** —es
 * un L-cut— y el 85% mira sin sonido.
 *
 * **Esto bajaba a 900 y mandaba el remate al 1390 y el pie al 1570**, o sea
 * fuera de la zona segura: por debajo del 65% vive la interfaz de la
 * plataforma, así que ese remate y ese pie no los veía nadie. La regla nueva de
 * Jaime (T-02) los recoge: ningún tablero baja hasta la franja del subtítulo,
 * y por tanto tampoco más abajo. Las columnas pierden 140 px de alto —el
 * contenido cabía de sobra en 500— y el pie se cuelga del techo de la franja.
 */
const COL = { y: 260, alto: 500 } as const;
/** El remate, justo debajo de las columnas y dentro de la zona. */
const REMATE_Y = COL.y + COL.alto + 20;

export const Comparacion: React.FC<ComparacionProps> = ({
  premisa,
  izquierda,
  derecha,
  remate,
  fuente,
  condicion,
  placa,
  duracion,
  sound = false,
}) => {
  const frame = useCurrentFrame();

  assertShort(premisa, "title", "Comparacion.premisa");
  assertShort(condicion, "legal", "Comparacion.condicion");
  for (const [k, c] of [["izquierda", izquierda], ["derecha", derecha]] as const) {
    assertShort(c.titulo, "label", `Comparacion.${k}.titulo`);
    assertShort(c.cifra, "outcome", `Comparacion.${k}.cifra`);
    if (c.pie) assertShort(c.pie, "statement", `Comparacion.${k}.pie`);
  }
  if (remate) assertShort(remate, "title", "Comparacion.remate");

  const p = (desde: number, dura = duration.entry) =>
    interpolate(frame, [desde, desde + dura], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });

  /**
   * Las columnas entran **de una en una**, no a la vez. Ver las dos juntas es
   * un dato; verlas aparecer una tras otra es una comparación — el espectador
   * tiene tiempo de leer la primera antes de que llegue la que la desmiente.
   */
  /**
   * **El horario se reparte sobre la escena.** Las proporciones salen de lo que
   * cada cosa tiene que dejar leer: la premisa abre, la primera columna se
   * asienta, la segunda la desmiente, y el remate llega cuando las dos ya se
   * compararon.
   *
   * Sin `duracion` cae al horario mínimo por tiempo de lectura, que es lo que
   * hace falta para una vista suelta.
   */
  const minimo =
    duration.entry * 2 +
    Math.max(20, readingFrames(izquierda.cifra)) +
    Math.max(20, readingFrames(derecha.cifra));
  const total = Math.max(duracion ?? 0, minimo + 40);
  const entraIzq = Math.round(total * 0.14);
  const entraDer = Math.round(total * 0.38);
  const finColumnas = Math.round(total * 0.62);
  /**
   * **El pie legal tiene beat propio, y por eso releva al remate.**
   *
   * Es la regla del canon —*«el texto legal lleva beat propio, no vive de
   * adorno permanente al pie»*— más lo que impone T-02: el tablero acaba en el
   * techo de la franja, así que abajo hay un solo hueco y no dos. El remate
   * ocupa ese hueco desde que las columnas se comparan; cuando llega la
   * condición, se va. Nunca se pisan porque nunca coinciden.
   */
  const entraPie = Math.round(total * 0.78);

  const util = layout.width - layout.safe.left * 2;
  const ancho = (util - 34) / 2;

  const columna = (c: Columna, x: number, oro: boolean, desde: number) => {
    const q = p(desde);
    return (
      <div
        style={{
          position: "absolute",
          left: x,
          top: COL.y,
          width: ancho,
          height: COL.alto,
          backgroundColor: oro ? color.gold : color.navy,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 40,
          padding: "0 34px",
          opacity: q,
          transform: `translateY(${(1 - q) * 26}px)`,
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.bloque,
            fontSize: 46,
            lineHeight: 1.02,
            textAlign: "center",
            textTransform: "uppercase",
            color: oro ? color.richBlack : color.secondaryBlue,
          }}
        >
          {c.titulo}
        </div>
        <div
          style={{
            fontFamily: fontFamily.bloque,
            // Ajustado a la línea: Anton gasta ~0,47 em por carácter en
            // versales, medido sobre render. El margen se paga en cuerpo, que
            // es barato, no en texto cortado, que no lo es.
            fontSize: Math.min(128, (ancho - 52) / (c.cifra.length * 0.47)),
            lineHeight: 0.94,
            whiteSpace: "nowrap",
            textTransform: "uppercase",
            color: oro ? color.richBlack : color.lightNeutral,
          }}
        >
          {c.cifra}
        </div>
        {c.pie ? (
          <div
            style={{
              fontFamily: fontFamily.video,
              fontSize: 27,
              fontWeight: 700,
              lineHeight: 1.3,
              textAlign: "center",
              color: oro ? color.richBlack : color.secondaryBlue,
            }}
          >
            {c.pie}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? <Fondo placa={placa} recorte="esquina" fuerza={1} deriva={finColumnas + 60} /> : null}
      {sound ? (
        <>
          <MotionSound motion="mark" at={entraIzq} />
          <MotionSound motion="mark" at={entraDer} />
          {remate ? <MotionSound motion="land" at={finColumnas + 6} /> : null}
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
      {/* Cinta de premisa: la condición común. Sin ella la comparación no es
          honesta — el playbook exige que el punto de partida sea el mismo. */}
      <div
        style={{
          position: "absolute",
          top: 120,
          left: layout.safe.left,
          right: layout.safe.right,
          display: "flex",
          justifyContent: "center",
          opacity: p(0),
          fontFamily: fontFamily.bloque,
        }}
      >
        <Cinta tinte={color.lightNeutral} giro={-1.5} cuerpo={44}>
          {premisa}
        </Cinta>
      </div>

      {columna(izquierda, layout.safe.left, false, entraIzq)}
      {columna(derecha, layout.safe.left + ancho + 34, true, entraDer)}

      {remate ? (
        <div
          style={{
            position: "absolute",
            top: REMATE_Y,
            left: layout.safe.left,
            right: layout.safe.right,
            display: "flex",
            justifyContent: "center",
            opacity: p(finColumnas + 6) * (1 - p(entraPie, 8)),
            fontFamily: fontFamily.bloque,
          }}
        >
          <Cinta tinte={color.gold} giro={1.8} cuerpo={50}>
            {remate}
          </Cinta>
        </div>
      ) : null}

      {/**
       * **Fuente y condición en la misma banda clara.**
       *
       * La fuente iba suelta sobre el fondo y caía justo encima de la trama de
       * la placa: ilegible. En el canon el pie va sobre plano —«FUENTE: CRA
       * 2026»— y por eso aquí comparte la banda con la condición: las dos son
       * letra pequeña que tiene que poder leerse, y ninguna compite con el dato.
       */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          // Colgado del TECHO de la franja: crece hacia arriba y no puede
          // bajar. Estaba en `top` y por eso acababa a 1570, bajo la interfaz.
          bottom: 0,
          backgroundColor: color.lightNeutral,
          transform: "rotate(0.8deg)",
          padding: "16px 64px 18px",
          opacity: p(entraPie),
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.data,
            fontSize: size.source,
            letterSpacing: tracking.labelMono,
            textTransform: "uppercase",
            color: color.navy,
            marginBottom: 12,
          }}
        >
          {fuente}
        </div>
        <div
          style={{
            fontFamily: fontFamily.video,
            fontSize: 24,
            fontWeight: 700,
            lineHeight: 1.26,
            color: color.richBlack,
          }}
        >
          {condicion}
        </div>
      </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};

/** Cuánto dura el tablero completo, en frames. El spec pregunta, no supone. */
export const duracionDe = (props: ComparacionProps): number =>
  duration.entry * 2 +
  Math.max(20, readingFrames(props.izquierda.cifra)) +
  Math.max(20, readingFrames(props.derecha.cifra)) +
  readingFrames(props.condicion) +
  24;
