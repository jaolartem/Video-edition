import React from "react";
import { AbsoluteFill } from "remotion";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { Reloj, useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { color, duration, ease, layout, readingFrames, videoText }
  from "../brand/tokens";
import { Cinta, Fondo, type Recorte } from "./Fondo";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";

/**
 * **Una sola cifra, y sobre qué se aplica.** El tablero de la tasa que sólo
 * muerde por arriba.
 *
 * ## Por qué existe, con el número delante
 *
 * Lo que había en reel-03 e3 era una `acumulacion` de dos tramos —0,78 y 0,22—
 * y esas dos fracciones **no las medía nada**: el dato de la etapa es una tasa
 * marginal y un umbral en dólares, no un reparto de un total. Dibujarlas
 * afirmaba una proporción que ninguna fuente sostiene, que es una cifra
 * rotulada con otra forma. En pantalla salían **dos rectángulos vacíos** con la
 * raya del umbral encima del bloque de oro, cuatro cosas en oro a la vez y la
 * cifra que el tablero demuestra reducida a la etiqueta de la raya (tiquet
 * #215).
 *
 * El encargo de la etapa pedía otra cosa, y con estas palabras: *«la cifra sola
 * y enorme en condensada pesada, lo único en oro de todo el cuadro… pegado a
 * ella, en azul pizarra y a un cuerpo mucho menor, el alcance que la voz se
 * dejó… la segunda columna no se dibuja»*.
 *
 * ## Y por eso es tipografía y no un gráfico
 *
 * Jaime, 6-9-2026: *«gráficos y palabras, como tablero de clase»* — y de las dos
 * mitades ésta es la de las palabras, porque **lo que se dibuja es lo que se
 * mide**. Una tasa marginal no tiene forma: tiene un número, una condición que
 * lo produce y un tramo donde vale. Las tres cosas son texto, y las tres están
 * aquí.
 *
 * ## Las tres capas, y el orden es el argumento
 *
 * 1. **La condición que produce el número**, arriba, en cinta clara con el
 *    texto en negro. Es el marco del dato, no el dato.
 * 2. **La cifra**, sola, sobre el único negro de la lámina —*«el negro sólo
 *    bajo lo que hay que leer»*— y en el único oro del cuadro.
 * 3. **El alcance**, pegado a ella y separado por un filete de un píxel, en
 *    azul pizarra y a un cuerpo mucho menor. Se escribe letra a letra: sin esta
 *    línea el bloque se lee como lo que se paga sobre todo lo que se gana, que
 *    es justo lo que la voz se dejó.
 *
 * El pie de fuente no se dibuja aquí: lo monta `dibujaTablero` para las 24
 * láminas. Ver [`PieTablero`](./PieTablero.tsx).
 * @clase tablero
 */
export type TechoProps = {
  /** La condición que produce el número. Arriba, en cinta clara. */
  titulo: string;
  /** La cifra. Sola, enorme y **el único oro del cuadro**. */
  cifra: string;
  /**
   * Sobre qué se aplica. Es obligatoria y no es adorno: una tasa marginal sin
   * su tramo se lee como la que se paga sobre todo, y eso es cumplimiento.
   */
  alcance: string;
  /** La placa de la pieza. La pone el spec; va a sangre, detrás de todo. */
  placa?: string;
  recorte?: Recorte;
  /** Lo que dura el tablero, en frames. Sólo para la deriva del fondo. */
  duracion?: number;
  sound?: boolean;
  /**
   * Frames, desde el arranque del tablero, en que se dice cada campo. Los pone
   * el spec a partir de `anclas` (`tiemposDe`); con `cifra` anclada, la cifra
   * entra con su palabra y el alcance detrás (C-473).
   */
  tiempos?: Record<string, number | (number | undefined)[] | undefined>;
};

/** La cinta del marco, dentro de la zona segura de arriba. */
const CINTA = { y: layout.safe.top, cuerpo: 46 } as const;

/**
 * El bloque de la cifra. **Sangra por la izquierda**, como la premisa de la
 * lámina aprobada: un negro que entra desde el borde ancla la composición sin
 * dibujar una caja alrededor de todo.
 *
 * Va centrado entre la cinta y el techo de la franja del subtítulo, que es lo
 * que `ZonaTablero` deja libre.
 */
const BLOQUE = { y: 556, ancho: 1000, relleno: 46, aire: 22 } as const;

/** Cuerpo máximo de la cifra: el de gran formato. Cede si no cabe. */
const TOPE_CIFRA = videoText.behind;

/** Cuerpo máximo del alcance. «Mucho menor» que la cifra, dice el encargo. */
const TOPE_ALCANCE = 44;

/**
 * **Dónde cae cada capa dentro del beat**, en fracción de lo que dura.
 *
 * No es decoración de ritmo: es la regla que Jaime dio para los tableros —*«el
 * tablero inicia con lo que se dice, y lo que se dice queda repartido por el
 * tablero, siempre»*—. Con sólo el tiempo de lectura encadenado, las tres capas
 * de esta lámina caben en 4,6 s y un beat de 10 s se queda **5,4 s quieto**, que
 * es el tablero estático que el canon prohíbe por nombre.
 */
const REPARTO = { cifra: 0.34, alcance: 0.5 } as const;

/**
 * Cuándo entra cada cosa: **por tiempo de lectura, y repartido por el beat**.
 *
 * La cifra no entra hasta que la condición que la produce se ha podido leer, y
 * el alcance no se escribe hasta que la cifra aterrizó — 0,75 s por bloque más
 * medio segundo, que es el suelo del canon y el orden en que la voz lo dice. Si
 * el beat da más tiempo del que el suelo pide, se reparte por él en vez de
 * acumularse al principio.
 *
 * Y el tecleo **acaba antes que el tablero**: en un beat corto, lo que cede es
 * la velocidad de escritura, no la última palabra del alcance.
 */
const horarioDe = (
  titulo: string,
  cifra: string,
  alcance: string,
  duracion: number,
) => {
  const reloj = new Reloj(0);
  const cinta = reloj.ahora;
  reloj.lee(titulo, duration.entry);
  const golpe = Math.max(reloj.ahora, Math.round(duracion * REPARTO.cifra));
  reloj.en(golpe).lee(cifra, duration.entry + 6);
  const tecleo = Math.max(reloj.ahora, Math.round(duracion * REPARTO.alcance));
  const teclea = Math.min(
    readingFrames(alcance),
    Math.max(duration.entry, duracion - tecleo - duration.entry),
  );
  return { cinta, golpe, tecleo, teclea };
};

export const Techo: React.FC<TechoProps> = ({
  titulo,
  cifra,
  alcance,
  placa,
  recorte = "lleno",
  duracion = 240,
  sound = false,
  tiempos,
}) => {
  const entra = useEntrada();

  assertShort(titulo, "label", "Techo.titulo");
  assertShort(cifra, "outcome", "Techo.cifra");
  assertShort(alcance, "statement", "Techo.alcance");

  // **Si el diseño ancló la cifra a su palabra, entra con ella** (C-473). Por
  // reparto caía al 34 % del tablero: en reel-13 e6, 5 s después de que él
  // dijera «entre 250 mil y 300 mil». Sin ancla, el reparto de siempre.
  const base = horarioDe(titulo, cifra, alcance, duracion);
  const primero = (v: unknown) => (typeof v === "number" ? v
    : Array.isArray(v) ? v.find((x) => typeof x === "number") : undefined);
  const golpe = Math.max(duration.entry, primero(tiempos?.cifra) ?? base.golpe);
  const tecleo = Math.max(golpe + duration.entry,
    primero(tiempos?.alcance) ?? (tiempos?.cifra != null ? golpe + duration.entry : base.tecleo));
  const t = {
    ...base, golpe, tecleo,
    teclea: Math.min(readingFrames(alcance),
      Math.max(duration.entry, duracion - tecleo - duration.entry)),
  };
  // La cinta se pega de golpe: entra en seis frames y se queda. La escala baja
  // de 1,02 a 1 —monótona, sin rebote— que es lo que hace que se lea como una
  // pegatina y no como un fundido.
  const pega = entra(t.cinta, duration.max);
  const abre = entra(t.golpe, duration.entry);
  const aterriza = entra(t.golpe + 4, duration.entry);
  // El tecleo va lineal: una máquina de escribir no acelera ni frena.
  const escribe = entra(t.tecleo, t.teclea, ease.linear);

  const util = BLOQUE.ancho - BLOQUE.relleno * 2;
  const cuerpoCifra = cuerpoQueCabe({
    ancho: util,
    largo: cifra.length,
    registro: "anton",
    tope: TOPE_CIFRA,
  });
  const cuerpoAlcance = cuerpoQueCabe({
    ancho: util,
    largo: alcance.length,
    registro: "anton",
    pista: 0.04,
    tope: TOPE_ALCANCE,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {/* La placa, a sangre y detrás de todo: es el suelo de la pieza entera y
          no compite con nadie. Por eso se queda fuera de `ZonaTablero`. */}
      {placa ? (
        <Fondo placa={placa} recorte={recorte} deriva={duracion + 60} />
      ) : null}

      {sound ? (
        <>
          <MotionSound motion="mark" at={t.cinta} />
          <MotionSound motion="land" at={t.golpe} />
          <MotionSound motion="type" at={t.tecleo} />
        </>
      ) : null}

      <ZonaTablero>
        {/* El marco del dato: la condición bajo la que existe el número. Va
            arriba, en claro y con el texto en negro, que es como el canon pone
            una cinta — nunca al revés. */}
        <div
          style={{
            position: "absolute",
            top: CINTA.y,
            left: layout.safe.left,
            opacity: pega,
            transform: `scale(${(1.02 - 0.02 * pega).toFixed(4)})`,
            transformOrigin: "left top",
            fontFamily: fontFamily.bloque,
          }}
        >
          <Cinta tinte={color.lightNeutral} giro={-1.6} cuerpo={CINTA.cuerpo}>
            {titulo}
          </Cinta>
        </div>

        <div
          style={{
            position: "absolute",
            left: 0,
            top: BLOQUE.y,
            width: BLOQUE.ancho,
            padding: `${BLOQUE.aire * 2}px ${BLOQUE.relleno}px`,
            boxSizing: "border-box",
          }}
        >
          {/* El negro se abre desde el borde y **el texto no se estira con
              él**: puesto como fondo del mismo div, el `scaleX` deformaría la
              Anton hasta que el bloque acabara de abrirse. */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: color.richBlack,
              transformOrigin: "left",
              transform: `scaleX(${abre})`,
            }}
          />
          <div
            style={{
              position: "relative",
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoCifra,
              lineHeight: 0.94,
              letterSpacing: "-0.01em",
              whiteSpace: "nowrap",
              textTransform: "uppercase",
              color: color.gold,
              opacity: aterriza,
              transform: `translateY(${((1 - aterriza) * 22).toFixed(1)}px)`,
            }}
          >
            {cifra}
          </div>
          {/* El filete de un píxel, que es como el canon separa dos bloques
              planos: nunca una sombra y nunca un hueco. */}
          <div
            style={{
              position: "relative",
              height: 1,
              margin: `${BLOQUE.aire}px 0`,
              backgroundColor: color.secondaryBlue,
              transformOrigin: "left",
              transform: `scaleX(${aterriza})`,
            }}
          />
          {/* El alcance, escrito letra a letra. El renglón entero se reserva
              con una copia oculta: sin ella el bloque negro crecería mientras
              se teclea, y lo que se mueve sería la caja y no el texto. */}
          <div
            style={{
              position: "relative",
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoAlcance,
              lineHeight: 1.1,
              letterSpacing: "0.04em",
              whiteSpace: "nowrap",
              textTransform: "uppercase",
              color: color.secondaryBlue,
            }}
          >
            <span style={{ visibility: "hidden" }}>{alcance}</span>
            <span style={{ position: "absolute", left: 0, top: 0 }}>
              {alcance.slice(0, Math.round(escribe * alcance.length))}
            </span>
          </div>
        </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};
