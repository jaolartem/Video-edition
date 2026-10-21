import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { gancho } from "../brand/gancho";
import { color } from "../brand/tokens";

/**
 * **El rótulo del gancho: el que va DETRÁS de su cabeza.**
 *
 * Es lo que sustituye a la lámina que los siete compartían —rótulo amarillo
 * abajo, subtítulo negro encima, todo quieto—. El porqué, los números y la cita
 * de Jaime que lo aprueba viven en [`brand/gancho`](../brand/gancho.ts); aquí
 * sólo se dibuja.
 *
 * ## Por qué es un elemento de `Detras` y no una capa suya
 *
 * Porque es literalmente eso: algo que le pasa por detrás. `Detras` ya apila el
 * elemento y encima el recorte del sujeto con alfa, que es el orden entero del
 * efecto; darle una pila propia al gancho sería escribir dos veces el mismo
 * apilado —y una de las dos se quedaría atrás el día que cambie.
 *
 * ## Y aquí SÍ va el copy, que en `Detras` estaba prohibido
 *
 * Con motivo: se probó el texto detrás de la figura y el sujeto tapaba la mayor
 * parte —*«el efecto se lucía a costa del mensaje»*—. **El límite era de sitio,
 * no de capa**: aquello se midió a la altura del pecho, donde él ocupa el cuadro
 * entero. Esto vive por encima de su coronilla, donde lo único que le tapa es el
 * pelo, y ahí el mensaje se lee y además gana profundidad. Jaime lo dio por
 * bueno mirándolo, y para que no vuelva a ser cuestión de criterio,
 * `scripts/reels/portada.mjs` comprueba que el bloque no baje del tercio que la
 * interfaz tapa.
 *
 * ## Sin rebote, y no es una preferencia
 *
 * Crece de `escala` a 1 y sube `sube` píxeles con `Easing.out(quad)`, que es
 * masa frenando. Nada de `spring` con poca amortiguación, `Easing.back` ni
 * `Easing.elastic`: eso convierte a un asesor financiero en un anuncio de
 * refrescos, y `scripts/guardas.mjs` lo caza por nombre y falla el build.
 * @clase capa
 */
export type Rotulo = {
  /** Una o dos líneas, y **cuál de las dos lo decide la frase**. Tres no se
   * leen a velocidad de scroll; una aguanta cuando la frase es una sola —Jaime:
   * *«"NADA HA PASADO" aguanta una sola línea enorme»*. */
  lineas: string[];
  /**
   * Cuerpo de cada línea, ya resuelto. **Aquí no se decide**: lo calcula
   * `scripts/reels/portada.mjs :: cuerposDe`, que es donde vive el ancho medido
   * y donde la puerta lo puede comprobar.
   */
  cuerpos: number[];
  /**
   * Dónde empieza el bloque, en píxeles. **Sale de su coronilla**, no de un
   * número fijo: con `arriba` clavado, en reel-01 la segunda línea entera caía
   * detrás de su cabeza —«MALA S···RTE»— y en otra pieza flotaba sin tocarle.
   * Lo mide la pasada del recorte y lo resuelve `portada.mjs :: colocar`.
   */
  arriba: number;
  /**
   * **De qué margen cuelga el bloque**, y lo decide dónde está él: el texto
   * ocupa el hueco que deja su cuerpo. Lo resuelve `reels/rotulo.mjs :: colocar`
   * midiendo su cabeza en la ficha del recorte, no el gusto de nadie.
   */
  lado: "izq" | "der";
  /**
   * **Cuál de las líneas lleva el oro**, por índice. No es siempre la última:
   * Jaime, sobre la variedad del gancho, *«el oro va en la mitad que golpea»*.
   * Y arrastra el cuerpo con él —`cuerposDe` da el tope grande a ésta—, porque
   * la jerarquía es del papel de la línea, no de su renglón. Quien lo declara
   * es el diseño, en `escena_desc.props.rotulo`.
   */
  oro: number;
  /**
   * **El frame de cada palabra**, línea por línea. Lo resuelve
   * `scripts/reels/rotulo.mjs :: ritmo`; aquí sólo se dibuja.
   *
   * Es la mitad del encargo de Jaime del 6-9-2026 —*«con mucho movimiento,
   * porque la idea es capturar la atención esos tres segundos»*—: la frase se
   * escribe por partes en vez de aparecer en dos bloques y quedarse quieta.
   */
  palabras?: number[][];
  /** Frame en que empieza a trazarse el filete, y lo que tarda. Ver `Regla`. */
  regla?: number;
  reglaDura?: number;
  /** Lo ancho que sale cada línea, en px. El filete mide lo que la del oro. */
  anchos?: number[];
  /**
   * **Un bloque navy plano detrás de cada renglón** (C-635). Jaime, reel-19:
   * *«el título con letras blancas en un cielo gris… no se lee y no hay
   * contraste»*. A escuadra y del ancho de su línea: sin sombra ni degradado,
   * que el canon no admite. Lo declara el diseño en las props del titular.
   */
  bloque?: boolean;
};

/** Lo entrada que va una cosa que arranca en `en`. Nunca se pasa de 1. */
const entrando = (frame: number, en: number) =>
  interpolate(frame, [en, en + gancho.entrada], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

/**
 * **Una línea, escribiéndose por palabras.**
 *
 * Lo que había entraba entera: dos movimientos —el frame 2 y el 15— y a partir
 * del 28 la lámina quieta hasta el subtítulo. Jaime, 6-9-2026: *«con mucho
 * movimiento, porque la idea es capturar la atención esos tres segundos»*.
 *
 * **Y el gesto aprobado no se toca, se reparte.** La escala de 0,965 a 1 sigue
 * siendo de la LÍNEA —es una masa que crece, no letras sueltas encogiendo— y lo
 * que se escalona por palabra es la subida y la opacidad. Así la frase se
 * escribe y el bloque sigue entrando como el día que se aprobó.
 *
 * El frame de cada palabra llega resuelto en `palabras`; si no llega, todas
 * entran con la línea, que es exactamente lo que había.
 */
const Linea: React.FC<{
  texto: string;
  cuerpo: number;
  oro: boolean;
  en: number;
  palabras?: number[];
  lado: "izq" | "der";
  bloque?: boolean;
}> = ({ texto, cuerpo, oro, en, palabras, lado, bloque }) => {
  const frame = useCurrentFrame();
  const partes = texto.trim().split(/\s+/);
  const cuando = (k: number) => palabras?.[k] ?? en;
  const p = entrando(frame, cuando(0));
  return (
    <div
      style={{
        fontFamily: fontFamily.bloque,
        fontSize: cuerpo,
        lineHeight: gancho.interlinea,
        letterSpacing: "-0.012em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        color: oro ? color.gold : color.lightNeutral,
        transform: `scale(${(gancho.escala + p * (1 - gancho.escala)).toFixed(4)})`,
        // Crece desde el margen del que cuelga. Con el origen fijo a la
        // izquierda, un bloque alineado a la derecha entra despegándose del
        // borde: el mismo movimiento leído como deslizamiento.
        transformOrigin: lado === "der" ? "right bottom" : "left bottom",
      }}
    >
      <span style={bloque
        // `inline-block`: el bloque mide su renglón y no la caja entera de la
        // fuente, que con este interlineado se mete en el de arriba y le corta
        // el pie de las letras («EL GOBIERNO» salía «FI GORIFRNO», reel-19).
        ? { display: "inline-block", verticalAlign: "top", background: color.navy,
            padding: "0 0.14em", opacity: p }
        : undefined}>
      {partes.map((w, k) => {
        const pw = entrando(frame, cuando(k));
        return (
          <React.Fragment key={`${k}-${w}`}>
            {k > 0 ? " " : null}
            <span
              style={{
                display: "inline-block",
                opacity: pw,
                transform: `translateY(${((1 - pw) * gancho.sube).toFixed(1)}px)`,
              }}
            >
              {w}
            </span>
          </React.Fragment>
        );
      })}
      </span>
    </div>
  );
};

/**
 * **El filete que se traza al ras de la línea que golpea.**
 *
 * Es lo que llena el hueco entre el bloque puesto y el subtítulo, que era donde
 * el gancho se quedaba quieto casi un segundo. Y **no dura un número fijo**:
 * arranca cuando la última palabra ha entrado y se traza hasta que el subtítulo
 * llega, así que el hueco no existe por construcción y cada pieza lo dibuja a
 * su propio ritmo — la variedad sale del copy, como el lado sale de dónde
 * está él.
 *
 * Mide lo que mide la línea de oro, no el cuadro: es **su suelo**, no una raya
 * que cruza. Va en oro porque señala exactamente lo mismo que ella —una sola
 * cosa en oro por lámina, y ésta y la línea son la misma— y se **traza**: la
 * línea existe entera y se enseña por tramos con `clipPath`, que es la
 * primitiva del canon. Canto duro, sin degradado y sin sombra.
 *
 * Va dentro del bloque, así que le pasa por detrás de la cabeza igual que el
 * texto: el trazo entra por el margen, desaparece tras él y sale por el otro
 * lado.
 */
const Regla: React.FC<{
  ancho: number;
  en: number;
  dura: number;
  lado: "izq" | "der";
}> = ({ ancho, en, dura, lado }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [en, en + dura], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  if (p <= 0) return null;
  const corte = ((1 - p) * 100).toFixed(2);
  return (
    <div
      style={{
        width: ancho,
        height: gancho.reglaGrosor,
        marginTop: Math.round(gancho.reglaGrosor * 1.6),
        marginLeft: lado === "der" ? "auto" : 0,
        background: color.gold,
        // Nace en el margen del que cuelga el bloque y crece hacia dentro.
        clipPath:
          lado === "der"
            ? `inset(0 0 0 ${corte}%)`
            : `inset(0 ${corte}% 0 0)`,
      }}
    />
  );
};

/**
 * Las líneas, escalonadas. Lo que va **debajo** del recorte del sujeto.
 *
 * La jerarquía la dan el peso y el color, no el tamaño solo: la que golpea en
 * oro y la que la acompaña en `lightNeutral`. Y el oro es de una sola cosa por
 * lámina — con tres cosas en oro no lo dice ninguna.
 *
 * **Y el bloque cuelga de un margen, no de la izquierda siempre.** Las líneas
 * van al ras de ese margen, así que el borde irregular cambia de lado con él:
 * es lo que hace que dos piezas con el mismo tratamiento no sean la misma
 * lámina. De qué lado no se decide aquí — llega medido en `rotulo.lado`.
 */
export const Titular: React.FC<{ rotulo: Rotulo }> = ({ rotulo }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div
      style={{
        position: "absolute",
        left: gancho.izquierda,
        top: rotulo.arriba,
        width: gancho.ancho,
        textAlign: rotulo.lado === "der" ? "right" : "left",
      }}
    >
      {rotulo.lineas.map((l, i) => (
        <Linea
          key={l}
          texto={l}
          cuerpo={rotulo.cuerpos[i] ?? gancho.primera}
          oro={i === rotulo.oro}
          en={gancho.entradaEn + i * gancho.escalon}
          palabras={rotulo.palabras?.[i]}
          lado={rotulo.lado}
          bloque={rotulo.bloque}
        />
      ))}
      {rotulo.reglaDura ? (
        <Regla
          ancho={rotulo.anchos?.[rotulo.oro] ?? gancho.ancho}
          en={rotulo.regla ?? 0}
          dura={rotulo.reglaDura}
          lado={rotulo.lado}
        />
      ) : null}
    </div>
  </AbsoluteFill>
);
