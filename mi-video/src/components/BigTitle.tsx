import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, videoText, accentChoice, type Accent } from "../brand/tokens";
import { useLienzo } from "../brand/LienzoContexto";

/**
 * Rótulo de gran formato que **atraviesa** el cuadro.
 *
 * La versión anterior entraba en el frame 0, se quedaba quieta y se iba con un
 * fundido. Jaime lo dijo exacto: *«los títulos en pantalla no hacen nada si no
 * son dinámicos, o si son la misma idea que llega sin sorpresa porque se avisó
 * hace 5 segundos»*. Las dos mitades son el mismo fallo:
 *
 * - **Quieto no es un rótulo, es una marca de agua.** Ahora entra por un lado y
 *   sale por el otro; el movimiento es lo que lo hace mirar.
 * - **Y llegaba antes que la voz.** Si el texto anuncia en el segundo 0 lo que
 *   se dice en el 5, cuando llega la frase ya no sorprende — el rótulo se
 *   quedó con el remate. Ahora entra **en la palabra**, no antes.
 *
 * **Estética: el nieto GenX del constructivismo ruso.** No es el sistema de la
 * web trasladado — es constructivismo con actitud de zine:
 *
 * - **Bloque plano de color, tipo encima.** El contorno flotante era una
 *   solución de web sobre fondo limpio; aquí manda el bloque. Rodchenko usaba la
 *   forma geométrica como un tipógrafo usa el blanco: activamente, dirigiendo la
 *   mirada, no decorando.
 * - **Diagonal y asimétrico.** El constructivismo evita la simetría porque la
 *   diagonal es la que sugiere movimiento. El bloque entra girado y alineado a
 *   la izquierda, nunca centrado.
 * - **El texto ES la composición.** Quita las palabras y no queda nada — que es
 *   precisamente la prueba de que el rótulo está haciendo su trabajo.
 *
 * La duración la decide la lectura, no un techo heredado de la web: el canon es una
 * referencia, no un mandato, y esto es vídeo. Lo que sí se mantiene del canon es el
 * registro — nada de rebote ni de micro-animación juguetona.
  * @clase capa
*/
export const BigTitle: React.FC<{
  lineas: string[];
  accent?: Accent;
  /**
   * Franja vertical donde vive el rotulo, en fraccion de altura.
   *
   * Va **por debajo de los subtitulos**, no sobre el torso.
   *
   * Antes ocupaba del 44 al 63%, que es justo donde ahora van los subtitulos
   * —pegados a la barbilla, por peticion de Jaime—. De los dos, el subtitulo es
   * la capa permanente y se queda con el mejor sitio; el rotulo es un golpe de
   * dos segundos y cede.
   *
   * 62-76% sigue muy por encima de la interfaz de la plataforma, que ocupa los
   * 400 px inferiores (a partir del 79%).
   */
  desde?: number;
  hasta?: number;
  /** Frame en que ENTRA — el de la palabra que subraya, no antes. */
  entraEn?: number;
  /** Cuantos frames se sostiene una vez dentro. */
  sostiene?: number;
  /** Frames de entrada y de salida. Lo decide la lectura. */
  paso?: number;
  /** Grados de giro del bloque. Cero solo si la pieza lo pide. */
  angulo?: number;
}> = ({
  lineas,
  accent = "gold",
  desde = 0.62,
  hasta = 0.76,
  entraEn = 0,
  sostiene = 54,
  paso = 9,
  angulo = -3.5,
}) => {
  const layout = useLienzo();
  const frame = useCurrentFrame();
  const t = frame - entraEn;
  const fin = paso + sostiene;

  if (t < 0 || t > fin + paso) return null;

  /** Entra desde la izquierda; sale por la derecha. Nunca vuelve por donde vino. */
  const x =
    t < paso
      ? interpolate(t, [0, paso], [-layout.width, 0], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.quad),
        })
      : t > fin
        ? interpolate(t, [fin, fin + paso], [0, layout.width], {
            extrapolateLeft: "clamp",
          })
        : 0;
  /**
   * La opacidad acompaña, no sustituye. Sola leería como fallo técnico; con el
   * desplazamiento, lee como algo que pasa por delante.
   */
  const o =
    t < paso
      ? interpolate(t, [0, paso], [0, 1], { extrapolateRight: "clamp" })
      : t > fin
        ? interpolate(t, [fin, fin + paso], [1, 0], { extrapolateLeft: "clamp" })
        : 1;

  /**
   * El cuerpo se ajusta para que CADA entrada de `lineas` sea una linea.
   *
   * El corte de linea es una decision de quien escribe el rotulo —donde respira
   * la frase— y dejarselo al ancho disponible la anula. Verificado en render:
   * «mala suerte» salia partido en dos y «su contador no es estratega» en
   * cuatro.
   *
   * El ancho se ESTIMA en vez de medirse porque el render debe ser determinista
   * y no hay layout al que preguntar. 0,70 em por caracter, medido sobre render
   * con la Montserrat 900 en versales.
   */
  const AVANCE_VERSAL = 0.7;
  /**
   * **Y el relleno de la placa, que faltaba.**
   *
   * El rotulo se pinta sobre un plano de color con `padding: 0.10em 0.28em`, o
   * sea 0,56 em de ancho que el calculo no contaba. Con la linea justa —«MALA
   * SUERTE», 11 caracteres— eso es lo que hacia que la ultima letra saliera del
   * cuadro. Es el mismo fallo que ya esta escrito en el canon: el ancho estimado
   * tiene que ser `cuerpo * (n * avance + relleno)`, no `cuerpo * n * avance`.
   *
   * Se ve ahora y no antes porque el rotulo entraba en el frame 106, ya con el
   * plano avanzado; al adelantarlo al 12 se mira de frente.
   */
  const RELLENO_PLACA = 0.56;
  const ancho = layout.width - layout.safe.left - layout.safe.right;
  const masLarga = Math.max(...lineas.map((l) => l.length), 1);
  const fontSize = Math.min(
    videoText.titleBig,
    ancho / (masLarga * AVANCE_VERSAL + RELLENO_PLACA),
  );

  return (
    <AbsoluteFill
      style={{
        paddingLeft: layout.safe.left,
        paddingRight: layout.safe.right,
        paddingTop: desde * layout.height,
        paddingBottom: (1 - hasta) * layout.height,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "flex-start",
        opacity: o,
        transform: `translateX(${x}px) rotate(${angulo}deg)`,
      }}
    >
      {lineas.map((l) => (
        <div
          key={l}
          style={{
            /**
             * Bloque plano con la tipografía dentro, no texto flotante con
             * contorno. Los bloques se separan por filete, nunca por sombra.
             */
            backgroundColor: accentChoice[accent],
            color: color.richBlack,
            padding: "0.10em 0.28em",
            marginBottom: 6,
            /**
             * Montserrat pesada, no la serif del sistema: sobre video los
             * remates finos se emborronan con la compresion y se leen mas
             * despacio.
             */
            fontFamily: fontFamily.video,
            fontSize,
            fontWeight: 900,
            letterSpacing: videoText.tracking,
            lineHeight: 0.98,
            whiteSpace: "nowrap",
            textTransform: "uppercase",
          }}
        >
          {l}
        </div>
      ))}
    </AbsoluteFill>
  );
};
