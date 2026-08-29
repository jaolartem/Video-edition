import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { layout, videoText, color, type ModeTokens } from "../brand/tokens";

/**
 * El subtítulo compuesto: **dos renglones, dos fuentes, dos superficies.**
 *
 * Petición de Jaime: *«el cc también puede ser grande, o compuesto —una frase
 * luego otra abajo— con dos fuentes y con más colores. De esa manera los
 * animamos»*.
 *
 * Es el canon aplicado a la capa portante. Los ejemplos no tienen texto
 * flotante con contorno: tienen **bloques planos de color con el tipo dentro**,
 * y lo grande va en condensada pesada y versales. Así que el renglón de arriba
 * lleva el contexto en Montserrat sobre negro, y el de abajo **el golpe** en
 * Anton versales sobre color.
 *
 * - `arriba` — lo que sitúa. Caja mixta, cuerpo de subtítulo.
 * - `abajo` — lo que remata. Versales, cuerpo derivado de su largo.
 * - `tinte` — **oro sólo cuando hay una cifra o una fecha**, que es lo que el
 *   espectador debe mirar. El resto va en navy. El oro decorativo está
 *   prohibido por nombre, y un remate en oro cada tres segundos lo sería.
 */
export type Compuesto = {
  arriba: string;
  abajo: string;
  tinte: "gold" | "navy";
};

/**
 * La franja de subtítulos, encima de la interfaz de la plataforma.
 *
 * **No es decoración.** El playbook exige que el argumento funcione sin audio, y
 * esa carga la lleva esta capa: el tablero pone el ancla corta y el subtítulo
 * recoge lo que se dice. Por eso el tablero tiene prohibido invadir esta zona.
 *
 * En producción el texto sale del SRT de CapCut vía `parseSrt()`. Aquí se pasa
 * a mano solo para ver la composición real de la pieza.
 *
 * **Cuerpo de vídeo, no de página.** Estaba en `size.body` (38 px), que es la
 * medida de la web y de los tableros — se leen con calma. A velocidad de scroll
 * y sobre imagen comprimida hace falta el cuerpo de vídeo (62) y peso, que es lo
 * que dice el aprendizaje 11: el peso pesa más que el cuerpo.
 *
 * Y va con **contorno, no con sombra**: el sistema prohíbe la sombra por nombre,
 * y un contorno sólido aguanta igual sobre pared clara que sobre camisa azul.
 * El contorno es la forma plana; la compuesta cambia a bloque, que es el
 * recurso del canon.
 *
 * ## Se ancla por abajo
 *
 * Antes centraba en una banda de altura fija, así que una cue de dos renglones
 * se salía por arriba y por abajo a partes iguales. Ahora el **borde inferior
 * es el que no se mueve** y el bloque crece hacia arriba: el ojo tiene un
 * punto fijo al que volver, y lo que crece lo hace hacia la barbilla y no
 * hacia la interfaz de la plataforma.
 */
export const CaptionBand: React.FC<{
  text: string;
  tokens: ModeTokens;
  /**
   * La correccion que se burla: se oye una cosa y se lee otra.
   *
   * Regla de Jaime — *«no pones lo mismo que yo digo sino lo que esta bien y lo
   * amplias, de manera que la contradiccion se note y sea una especie de
   * burla»*. En el reel 2 atribuye la estadistica al «ministerio de comercio»
   * cuando es el de **Finanzas**: se oye *comercio*, se lee **FINANZAS** en
   * grande y en oro.
   *
   * Es distinto de hinchar la palabra equivocada, que fue el primer intento:
   * agrandar el error solo lo subraya. Poner la palabra correcta en su sitio
   * **arma la contradiccion**, y la broma la remata el espectador.
   *
   * Broma de subordinado, deadpan: el montaje no comenta nada, solo cambia la
   * palabra y sigue.
   *
   * Tasa maxima: una o dos por minuto. Ver «Que se note que hay alguien
   * detras» en CLAUDE.md — por encima de eso deja de ser una persona y pasa a
   * ser un montaje de fallos.
   */
  corrige?: { dice: string; es: string };
  /** Que la correccion palpite: tres golpes duros y se queda. */
  palpita?: boolean;
  /**
   * **La idea fuerza**: la frase del beat que crece y se pone en oro cuando se
   * dice. No sustituye nada —eso es `corrige`— sólo subraya.
   *
   * Es el tercer tratamiento del reparto. Jaime: *«animaciones para conceptos
   * complejos e ideas fuerza para lo demás, sin dejar de lado los subtítulos»*.
   * Va donde el beat **afirma, provoca o promete**: ahí la fuerza está en la
   * voz y el texto sólo tiene que marcar dónde cae el golpe.
   *
   * Frente a un tablero es más barato y más rápido —no roba el plano— y frente
   * a nada, sostiene la atención en el tramo en que sólo hay una cara hablando.
   */
  realza?: string;
  /** Dos renglones, dos fuentes. Ver `Compuesto`. Lo deriva `reels-spec.mjs`. */
  compuesto?: Compuesto;
  /** Frame en que empieza este subtitulo, para poder animar dentro de el. */
  desde?: number;
}> = ({ text, tokens, corrige, palpita, realza, compuesto, desde = 0 }) => (
  <div
    style={{
      position: "absolute",
      left: layout.safe.left,
      right: layout.safe.right,
      /**
       * 760 px desde abajo: **los subtitulos van pegados a la barbilla**.
       *
       * Peticion de Jaime. Con 420 la banda caia en el 68-78% de altura —lejos
       * de la cara, donde la vista ya no esta— y el ojo tenia que viajar entre
       * el rostro y el texto en cada frase.
       *
       * Sigue muy por encima de la interfaz de la plataforma, que ocupa los
       * 400 px inferiores.
       */
      bottom: layout.captionBottom,
      minHeight: layout.captionBand,
      display: "flex",
      flexDirection: "column",
      // El borde de abajo es el que no se mueve; lo que crece, crece hacia
      // arriba. Ver la cabecera del componente.
      justifyContent: "flex-end",
      alignItems: "flex-start",
      fontFamily: fontFamily.body,
      fontSize: videoText.caption,
      fontWeight: 800,
      lineHeight: 1.2,
      letterSpacing: videoText.tracking,
      color: tokens.text,
    }}
  >
    {compuesto ? (
      <Compuesta c={compuesto} desde={desde} />
    ) : (
      <Plana desde={desde}>
        {corrige ? (
          <Corregida texto={text} corrige={corrige} desde={desde} palpita={palpita} />
        ) : realza ? (
          <Corregida
            texto={text}
            corrige={{ dice: realza, es: realza }}
            factor={1.22}
            desde={desde}
          />
        ) : (
          text
        )}
      </Plana>
    )}
  </div>
);

/**
 * La forma plana, **con entrada**.
 *
 * Jaime cuenta los subtitulos animados entre los tratamientos validos: *«si no
 * hay tablero hay animaciones detras mio o los subtitulos animados; las dos son
 * validas»*. Sin entrada, la banda cambia de texto por sustitucion y el ojo lo
 * lee como un fallo de sincronia; con cuatro frames de subida, cada frase
 * **llega**.
 *
 * Cuatro frames, no doce: es la capa permanente y aparece cuarenta veces por
 * pieza. Lo que se puede permitir un rotulo que sale dos veces, esta no.
 * Y sin rebote — prohibido por nombre.
 */
const Plana: React.FC<{ desde: number; children: React.ReactNode }> = ({
  desde,
  children,
}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [desde, desde + 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    <span
      style={{
        /**
         * **Bloque, no contorno flotante.** El contorno aguantaba sobre el
         * plano, pero sobre un tablero el subtitulo era lo unico sin fondo:
         * flotaba encima de la composicion y se leia como pegado de otra
         * pieza. El canon no tiene texto flotante en ninguna lamina — tiene
         * bloques planos con el tipo dentro, que es lo que ya hace la forma
         * compuesta.
         *
         * El contorno se queda debajo del bloque: sobre pared clara o camisa
         * azul sigue haciendo su trabajo en los bordes de las letras.
         */
        backgroundColor: color.richBlack,
        padding: "0.06em 0.22em",
        boxDecorationBreak: "clone",
        WebkitBoxDecorationBreak: "clone",
        WebkitTextStroke: `4px ${color.richBlack}`,
        paintOrder: "stroke fill",
        opacity: p,
        transform: `translateY(${((1 - p) * 14).toFixed(1)}px)`,
      }}
    >
      {children}
    </span>
  );
};

/** Ancho util de la banda, ya descontadas las zonas seguras. */
const ANCHO = layout.width - layout.safe.left - layout.safe.right;
/** El tracking, en em, para poder sumarlo al avance. */
const PISTA = Number.parseFloat(videoText.tracking);

/**
 * Avance medio de la Anton en versales. Es condensada de verdad, asi que ocupa
 * mucho menos que la Montserrat 900 (0,70 em) del rotulo.
 *
 * **El interletrado y el relleno cuentan, y esa es la parte que se olvida.** El
 * aprendizaje 40 lo dice con estas palabras y `SidePanel` ya lo aplica; aqui
 * faltaba. El ancho real de un bloque no es `cuerpo * n * avance`: es
 *
 *     cuerpo * (n * (avance + tracking) + relleno)
 *
 * Con el relleno horizontal del bloque (0,32 em) y el tracking (0,01 em),
 * despejar el cuerpo sin esos dos terminos daba **siempre** un bloque mas ancho
 * que la banda: medido sobre el lote, ocho de trece se salian entre 39 y 58 px,
 * y con `nowrap` no envuelven — se salen y punto.
 *
 * El margen se paga en cuerpo, que es barato, no en texto cortado, que no lo
 * es. Y el numero final **se comprueba sobre un still**, no se razona.
 */
const AVANCE_ANTON = 0.46;
/** Relleno horizontal del bloque, en em. Va aqui porque entra en la cuenta. */
const RELLENO_EM = 0.32;

/**
 * Los dos renglones. El de arriba entra por la izquierda, el de abajo por la
 * derecha cuatro frames despues.
 *
 * **La contradiagonal es el motivo del canon**, no un adorno: el
 * constructivismo evita la simetria porque la diagonal es la que sugiere
 * movimiento. Dos bloques entrando por el mismo lado serian una lista; entrando
 * por lados opuestos, la pila se construye.
 *
 * Sin rebote y sin fundido: `Easing.out(cubic)` y peso. El rebote esta
 * prohibido por nombre.
 */
const Compuesta: React.FC<{ c: Compuesto; desde: number }> = ({ c, desde }) => {
  const frame = useCurrentFrame();
  const cuerpo = Math.round(
    Math.min(
      videoText.titleBig,
      Math.max(
        videoText.caption,
        ANCHO /
          (c.abajo.length * (AVANCE_ANTON + PISTA) + RELLENO_EM),
      ),
    ),
  );
  const entra = (retardo: number) =>
    interpolate(frame, [desde + retardo, desde + retardo + 6], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
  const p1 = entra(0);
  const p2 = entra(4);
  const oro = c.tinte === "gold";
  return (
    <>
      {/* La forma grande no lleva renglon de arriba: sin esto pintaba un
          bloque negro vacio encima del remate. */}
      {c.arriba ? (
      <span
        style={{
          alignSelf: "flex-start",
          maxWidth: ANCHO,
          backgroundColor: color.richBlack,
          color: color.lightNeutral,
          padding: "0.06em 0.24em",
          marginBottom: 8,
          opacity: p1,
          transform: `translateX(${(-(1 - p1) * layout.width * 0.35).toFixed(1)}px)`,
        }}
      >
        {c.arriba}
      </span>
      ) : null}
      <span
        style={{
          alignSelf: "flex-start",
          maxWidth: ANCHO,
          // Cinta del canon: **texto negro sobre el color**, nunca al reves.
          backgroundColor: oro ? color.gold : color.navy,
          color: oro ? color.richBlack : color.lightNeutral,
          fontFamily: fontFamily.bloque,
          fontSize: cuerpo,
          fontWeight: 400,
          lineHeight: 1.04,
          letterSpacing: videoText.tracking,
          textTransform: "uppercase",
          whiteSpace: "nowrap",
          padding: "0.04em 0.16em",
          opacity: p2,
          transform: `translateX(${((1 - p2) * layout.width * 0.35).toFixed(1)}px)`,
        }}
      >
        {c.abajo}
      </span>
    </>
  );
};

/**
 * Parte el subtitulo y **pone la palabra correcta donde suena la equivocada**.
 *
 * Crece y se queda ahi: encogerla despues seria un efecto de vuelta atras, y lo
 * que tiene que quedarse es la contradiccion.
 *
 * ## Crece por cuerpo, no por `scale`
 *
 * `transform: scale()` **no reflowea**: la caja escalada se sale y se pinta
 * encima del texto que tiene al lado. En el reel 1 la idea fuerza «lo que
 * deberia» quedo escrita sobre el «le queda» que la precede, ilegibles las dos.
 * Con `fontSize` en `em` el renglon se recompone y las palabras se apartan.
 *
 * El factor cambia segun lo que crece: **una palabra suelta aguanta 1,45**
 * —es la correccion, y tiene que dar un golpe— pero una frase entera a 1,45
 * ocupa dos renglones ella sola, asi que la idea fuerza se queda en 1,22.
 */
const Corregida: React.FC<{
  texto: string;
  corrige: { dice: string; es: string };
  desde: number;
  factor?: number;
  /**
   * Que la correccion **palpite**, y no siempre.
   *
   * Jaime, sobre un dato que el atribuye mal y el libreto tiene bien: *«el
   * libreto dice la verdad, esta es una oportunidad para que el error se
   * manifieste: el subtitulo, cuando digo ministerio de comercio, dice la
   * informacion real palpitando o haciendola notar mas»*.
   *
   * Y **puede ser una broma** — él lo dijo al momento: *«sí puede ser una
   * broma»*. Así que esto no separa dos registros, un serio y uno ligero. Lo
   * que no se negocia es que la corrección **aparezca**, porque el dato tiene
   * fuente; el tono es libre, y reírse del propio desliz es la misma marca de
   * humanidad que la pieza ya usa. El palpiteo está disponible para las dos.
   *
   * Palpita **a pasos duros**, no en seno: un latido suave es decoracion y el
   * canon la prohibe. Tres golpes y se queda — como una luz de aviso que se
   * enciende, no como algo que respira.
   */
  palpita?: boolean;
}> = ({ texto, corrige, desde, factor = 1.45, palpita }) => {
  const { dice: palabra, es } = corrige;
  const frame = useCurrentFrame();
  const p = interpolate(frame, [desde + 2, desde + 12], [1, factor], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    // Sin `back`: sobrepasa y vuelve, y eso es rebote —prohibido por nombre en
    // el canon—. La palabra crece y se queda; no hace una gracia al llegar.
    easing: Easing.out(Easing.cubic),
  });
  // Tres golpes de seis frames a partir de que la palabra ya crecio, y luego
  // se queda encendida. Escalon entero, sin rampa.
  const t = frame - desde - 12;
  const late = palpita && t >= 0 && t < 36 && Math.floor(t / 6) % 2 === 1;
  const partes = texto.split(new RegExp(`(${palabra})`, "i"));
  return (
    <span>
      {partes.map((t, i) =>
        t.toLowerCase() === palabra.toLowerCase() ? (
          <span
            key={i}
            style={{
              fontSize: `${p}em`,
              color: late ? color.richBlack : color.gold,
              background: late ? color.gold : "transparent",
              padding: palpita ? "0 0.12em" : undefined,
            }}
          >
            {es}
          </span>
        ) : (
          <React.Fragment key={i}>{t}</React.Fragment>
        ),
      )}
    </span>
  );
};
