import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { dibujaTablero } from "./components/Tablero";
// Sólo los tipos: **quién dibuja cada forma vive en `components/Tablero.tsx`**,
// y aquí se declara nada más el contrato de lo que el spec puede pedir.
import type { CausalChainProps } from "./components/CausalChain";
import type { ComparacionProps } from "./components/Comparacion";
import type { BeliefSwapProps } from "./components/BeliefSwap";
import type { CompuertaProps } from "./components/Compuerta";
import type { AcumulacionProps } from "./components/Acumulacion";
import type { TwoPathsProps } from "./components/TwoPaths";
import { CaptionBand, type Compuesto } from "./components/CaptionBand";
import { CaptionDiscreta } from "./components/CaptionDiscreta";
import { color } from "./brand/tokens";
import { mode as modes, type Mode } from "./brand/tokens";

/**
 * Un tablero programado sobre el vídeo.
 *
 * Mientras está activo **ocupa el frame entero**, no se superpone en una
 * esquina: el tablero ES el plano. Es la decisión que reconcilia el ritmo de
 * corte con la explicación — cada cambio de estado del tablero cuenta como
 * cambio de toma, así que el pulso se mantiene sin abandonar el argumento.
 */
export type BoardCue =
  | { at: number; duration: number; kind: "causal"; props: CausalChainProps }
  | { at: number; duration: number; kind: "twopaths"; props: TwoPathsProps }
  | { at: number; duration: number; kind: "comparacion"; props: ComparacionProps }
  | { at: number; duration: number; kind: "BeliefSwap"; props: BeliefSwapProps }
  | { at: number; duration: number; kind: "Compuerta"; props: CompuertaProps }
  | { at: number; duration: number; kind: "acumulacion"; props: AcumulacionProps }
  /**
   * **Cualquier otra forma que el diseñador declare.**
   *
   * Regla de Jaime: *«hay que conectar al diseñador con el render»*, después de
   * tres ciclos de cambios duros con el mismo vídeo. La causa era ésta: la unión
   * tenía cuatro miembros, el diseño usó veintitrés, y las otras diecinueve
   * caían por el final del ternario **sin dibujar nada y sin decirlo**.
   *
   * Cerrar la lista aquí convertía el catálogo de componentes en el techo del
   * diseño. Ahora la forma declarada entra siempre: si tiene componente propio
   * lo usa, y si no, `TableroDeclarado` dibuja su copy con la jerarquía y la
   * familia que el diseñador puso. Que exista un componente a medida es una
   * mejora, no el requisito para aparecer.
   */
  | { at: number; duration: number; kind: string; props: Record<string, unknown> };

export type CaptionCue = {
  at: number;
  duration: number;
  text: string;
  /** Se oye una cosa y se lee la correcta. Ver `CaptionBand`. */
  corrige?: { dice: string; es: string };
  /** Que la correccion palpite. Ver `Corregida` en `CaptionBand`. */
  palpita?: boolean;
  /** La frase que crece al decirse. Ver `realza` en `CaptionBand`. */
  realza?: string;
  /** Dos renglones con dos fuentes. Ver `Compuesto` en `CaptionBand`. */
  compuesto?: Compuesto;
};

/**
 * Tramo en blanco y negro: **la marca de humanidad**.
 *
 * Jaime, sobre una cifra mal dicha: *«deja el 550 y señala el error, ponme en
 * blanco y negro»*. El desliz no se tapa ni se corrige por encima — se marca, y
 * la marca es la broma. Un desliz reconocido cuesta dos segundos y compra
 * credibilidad; taparlo cuesta el material bueno que lo rodea.
 *
 * Va con el subtítulo corregido, que es la otra mitad: se oye una cosa y se lee
 * la que es. Las dos capas son **una sola marca**, no dos — y la tasa es de una
 * o dos por minuto, así que en estas piezas es una.
 */
export type Desatura = { at: number; duration: number };

/**
 * **El glitch que tapa un corte.**
 *
 * Jaime: *«lo ideal del corte y del cambio de escena es que no se note… se puede
 * poner una transición discreta, algo que no sea un brillo; un efecto glitch por
 * ejemplo, que distorsione la imagen y el sonido como un TV antiguo cuando
 * cambiaba de canal, durante poco tiempo, con el respectivo ruido»*.
 *
 * Funciona porque **no oculta el corte: lo sustituye por otra cosa**. El ojo
 * registra la distorsión, no el salto de encuadre — y como dura tres frames, lo
 * que queda es la sensación de continuidad, no la de efecto.
 *
 * Va **centrado en la costura**, no después: la mitad antes y la mitad después,
 * para que el corte caiga dentro de la distorsión y no en su borde.
 */
export type Glitch = { at: number; duration: number };

/**
 * **El virado del plano.**
 *
 * Jaime: *«que me ponga en sepia… ya tiene más herramientas de diseño, está muy
 * mediocre el diseñador»*. Lo declara quien compone, por etapa, en
 * `escena_desc.camara.virado`, y llega hasta aquí con el filtro **ya resuelto**:
 * el catálogo de virados que el canon admite y su traducción a CSS viven juntos
 * en `scripts/imagen.mjs`, que es la única forma de que las dos mitades no se
 * separen. Aquí no se decide nada, se aplica.
 *
 * No es una capa encima: cambia la propia imagen, así que el subtítulo, el
 * tablero y el rótulo van por delante sin enterarse.
 */
export type Virado = {
  at: number;
  duration: number;
  virado: string;
  css: string;
};

export type AdProps = {
  /**
   * Proxy del vídeo ya cortado, en `public/`. Se trabaja con proxy y no con el
   * bruto: el original es 4K HEVC de varios gigas y decodificarlo por frame para
   * componer encima multiplica el tiempo de render sin aportar nada — la salida
   * es 1080×1920 igualmente.
   */
  video: string;
  /**
   * Volumen del plano. **Existe para poder sacar los efectos solos.**
   *
   * `voz-limpia` sustituye la pista entera por la voz de Adobe (`-map 1:a`), y
   * con ella se iban los sfx, que vivian dentro del render. Con `volumen: 0` la
   * misma composicion se renderiza como pista de SOLO efectos, y esa se mezcla
   * con la voz limpia en vez de tirarla.
   */
  volumen?: number;
  mode?: Mode;
  boards?: BoardCue[];
  /** Donde cae su coronilla. Ver `coronilla` en `CaptionBand`. */
  coronilla?: number;
  /** Lado libre. Ver `lado` en `CaptionBand`. */
  lado?: "izq" | "der";
  captions?: CaptionCue[];
  desatura?: Desatura[];
  glitch?: Glitch[];
  virados?: Virado[];
};

export const Ad: React.FC<AdProps> = ({
  video,
  volumen = 1,
  mode = "evidence",
  boards = [],
  coronilla,
  lado,
  captions = [],
  desatura = [],
  glitch = [],
  virados = [],
}) => {
  const frame = useCurrentFrame();
  const t = modes[mode];

  /**
   * Cuánto glitch hay en este frame, de 0 a 1. Sube y baja dentro del tramo:
   * un valor constante se leería como un filtro puesto, y esto es un tropiezo
   * de la señal.
   */
  const g = glitch.reduce((n, q) => {
    if (frame < q.at || frame >= q.at + q.duration) return n;
    const t = (frame - q.at) / q.duration;
    // Triangular, con el pico justo en la costura.
    return Math.max(n, 1 - Math.abs(t - 0.5) * 2);
  }, 0);

  /** El subtítulo activo. Es capa portante: el argumento funciona sin audio. */
  const caption = captions.find(
    (c) => frame >= c.at && frame < c.at + c.duration,
  );

  /**
   * ¿Hay un tablero puesto en este frame? Decide **qué subtítulo se dibuja**,
   * no sólo cómo de grande. Ver la instrucción T-02 abajo.
   */
  const bajoTablero = boards.some(
    (b) => frame >= b.at && frame < b.at + b.duration,
  );

  /**
   * **El plano se filtra una sola vez, y por eso la cadena se arma aquí.**
   *
   * Estaban como dos objetos derramados dentro del `style`, y el segundo `filter`
   * pisaba al primero: durante un glitch dentro de un tramo en blanco y negro, el
   * blanco y negro desaparecía. Con un virado en juego serían tres y el último
   * ganaría siempre — la avería de este proyecto en su forma más pequeña, una
   * decisión declarada que otra descarta aguas abajo sin decir nada.
   *
   * **Y el blanco y negro gana al virado.** No se suman: `grayscale` seguido de
   * un sepia vuelve a teñir lo que se acababa de vaciar de color. La marca de
   * humanidad es un comentario sobre un desliz y manda sobre el tratamiento de
   * la etapa, que es decoración al lado de eso.
   */
  const bn = desatura.some((d) => frame >= d.at && frame < d.at + d.duration);
  const virado = virados.find(
    (v) => frame >= v.at && frame < v.at + v.duration,
  );
  const filtro = [
    bn ? "grayscale(1) contrast(1.15)" : virado?.css,
    g > 0
      ? `saturate(${(1 + g * 1.8).toFixed(2)}) contrast(${(1 + g * 0.5).toFixed(2)})`
      : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <OffthreadVideo
        src={staticFile(video)}
        volume={volumen}
        style={{
          // Sin transición en el virado ni en el blanco y negro: el cambio de
          // tratamiento tiene que notarse. Un fundido lo convertiría en un
          // efecto, y aquí es un comentario sobre lo que se está diciendo.
          ...(filtro ? { filter: filtro } : {}),
          ...(g > 0
            ? {
                // Desplazamiento horizontal y salto de color: la señal que se
                // rompe un instante. La escala evita que asome el borde negro.
                transform: `translateX(${(g * 26).toFixed(2)}px) scale(${(1 + g * 0.04).toFixed(4)})`,
              }
            : {}),
        }}
      />

      {boards.map((cue, i) => (
        <Sequence
          key={`${cue.at}-${i}`}
          from={cue.at}
          durationInFrames={cue.duration}
        >
          {/* Cada estructura tiene su tablero. Un mismo componente en cuatro
              frameworks distintos hace que los cuatro se vean iguales, y
              entonces el tablero deja de significar nada. Quién dibuja cada
              forma lo dice `dibujaTablero`,
              en `components/Tablero.tsx`. */}
          {dibujaTablero(cue, mode)}
        </Sequence>
      ))}

      {/* Bandas de ruido: lo que hace que se lea como señal y no como zoom. */}
      {g > 0 ? (
        <AbsoluteFill style={{ pointerEvents: "none", opacity: g * 0.55 }}>
          {[0.18, 0.42, 0.71].map((y, i) => (
            <div
              key={y}
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: `${(y + g * 0.05 * (i % 2 ? 1 : -1)) * 100}%`,
                height: `${2 + i}%`,
                backgroundColor: i === 1 ? color.gold : color.lightNeutral,
                mixBlendMode: "overlay",
                transform: `translateX(${(g * (i % 2 ? -40 : 34)).toFixed(1)}px)`,
              }}
            />
          ))}
        </AbsoluteFill>
      ) : null}

      {/**
       * **Bajo un tablero el subtitulo cambia de forma Y de sitio.**
       *
       * Instrucción de Jaime (T-02): *«durante los tableros el subtítulo pasa a
       * estilo tradicional discreto: cuerpo pequeño, sin caja ni contorno,
       * apoyado en el borde inferior de la zona segura —no del cuadro—»*.
       *
       * `CaptionDiscreta` llevaba escrito desde entonces y **no lo dibujaba
       * nadie**: aquí sólo se le bajaba el cuerpo a la banda portante. Y el
       * cuerpo no era el problema — la banda sube sobre la coronilla cuando hay
       * hueco, así que en reel-04 el subtítulo se pintaba **encima del bloque de
       * oro del tablero**, a 400 px de altura, texto sobre texto. Bajarle el
       * cuerpo no arregla que esté en el sitio de otro.
       *
       * Con un tablero puesto no hay cara que acompañar, así que el sitio bueno
       * es el que no roba composición: el suelo de la franja. El subtítulo no se
       * calla —*«en los tableros también hay cc»*— pero deja de ser la capa que
       * manda.
       */}
      {caption ? (
        bajoTablero ? (
          <CaptionDiscreta
            text={caption.text}
            tokens={t}
            corrige={caption.corrige}
            desde={caption.at}
          />
        ) : (
          <CaptionBand
            text={caption.text}
            tokens={t}
            coronilla={coronilla}
            lado={lado}
            corrige={caption.corrige}
            palpita={caption.palpita}
            realza={caption.realza}
            compuesto={caption.compuesto}
            desde={caption.at}
          />
        )
      ) : null}
    </AbsoluteFill>
  );
};
