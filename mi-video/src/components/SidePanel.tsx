import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, layout, videoText, tracking } from "../brand/tokens";

/**
 * Bloques que se construyen **en el espacio libre del plano abierto**.
 *
 * Idea de Jaime: en vez de cortar, irse una vez al plano más lejano y animar en
 * el hueco que queda al lado del sujeto. El cambio de escena deja de verse
 * porque no hay corte — lo que cambia es lo que ocupa el cuadro.
 *
 * Es fotomontaje constructivista en su forma literal: geometría compuesta
 * **con** la fotografía, no encima de ella. Y es el registro Gen Z/Alpha del
 * sistema — bloques planos apilados, tipografía cinética, entrada por peso y no
 * por fundido.
 *
 * Cada bloque entra por su lado y se queda: la pila se construye, no aparece.
  * @clase capa
*/
export const SidePanel: React.FC<{
  /** Líneas del panel, de arriba abajo. Cortas: es un ancla, no un párrafo. */
  bloques: { texto: string; fuerte?: boolean; placa?: string }[];
  /** Lado libre del cuadro. Sale del ancla del sujeto, no se elige a ojo. */
  lado: "izq" | "der";
  /** Frames entre la entrada de un bloque y el siguiente. */
  escalon?: number;
  /** Frames que tarda un bloque en entrar. */
  paso?: number;
}> = ({ bloques, lado, escalon = 7, paso = 8 }) => {
  const frame = useCurrentFrame();
  /**
   * El panel ocupa el 42% del ancho. Con el sujeto descentrado —el ancla cae
   * hacia un lado en las seis tomas— ese hueco existe de verdad; medirlo es lo
   * que impide que el bloque acabe sobre la cara.
   */
  const ancho = layout.width * 0.44;
  /**
   * Cuerpo ajustado al bloque mas largo, no fijo.
   *
   * Con tamano fijo se partia «$30,00 / 0» y «FACTURACI / ÓN», y el ultimo
   * bloque se salia del cuadro. El hueco del plano da lo que da; el texto se
   * adapta a el, no al reves.
   *
   * **El interletrado cuenta.** La primera version uso 0,62 em por caracter —el
   * avance de la Montserrat 900 en versales— y siguio saliendose: las etiquetas
   * llevan `tracking.labelMono`, que son **0,2 em mas por caracter**. Sumarlo es
   * la diferencia entre caber y no caber. Aun asi se salia: el valor final
   * (1,0 em para etiquetas) esta **medido sobre render**, no derivado. Estimar
   * el ancho de un texto sin medirlo tiene un error irreducible; el margen se
   * paga en cuerpo, que es barato, y no en texto cortado, que no lo es.
   */
  const AVANCE_FUERTE = 0.78;
  const AVANCE_ETIQUETA = 1.0;
  const cuerpo = (fuerte: boolean) => {
    const tope = fuerte ? videoText.title : Math.round(videoText.caption * 0.8);
    const AVANCE = fuerte ? AVANCE_FUERTE : AVANCE_ETIQUETA;
    const largo = Math.max(
      ...bloques.filter((b) => !!b.fuerte === fuerte).map((b) => b.texto.length),
      1,
    );
    return Math.min(tope, ancho / (largo * AVANCE));
  };

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "column",
        // **Arriba, por encima de la cara.** Centrado caía en la franja del
        // rostro —que ocupa del 24 al 40% de altura— y tapaba los ojos. Jaime:
        // «misma facturación tapa la mitad de la cara, puede quedar un poco más
        // arriba». El sitio es la banda entre la zona segura y la frente.
        justifyContent: "flex-start",
        alignItems: lado === "der" ? "flex-end" : "flex-start",
        paddingLeft: lado === "der" ? 0 : layout.safe.left,
        paddingRight: lado === "der" ? layout.safe.right : 0,
        paddingTop: layout.height * 0.115,
        paddingBottom: layout.height * 0.42,
      }}
    >
      {bloques.map((b, i) => {
        const t = frame - i * escalon;
        const p = interpolate(t, [0, paso], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        if (p <= 0) return null;
        const dx = (lado === "der" ? 1 : -1) * (1 - p) * layout.width * 0.5;
        return (
          <div
            key={b.texto}
            style={{
              maxWidth: ancho,
              // Sin esto el texto en versales no partia linea y el bloque se
              // salia del cuadro por la derecha. Verificado en render.
              // Una linea por bloque: el corte lo decide quien escribe.
              whiteSpace: "nowrap",
              textAlign: lado === "der" ? "right" : "left",
              marginBottom: 10,
              padding: "0.12em 0.3em",
              position: "relative",
              overflow: "hidden",
              backgroundColor: b.fuerte ? color.gold : color.richBlack,
              // **El oro sale una vez por panel: en el bloque `fuerte`.**
              //
              // Esto pintaba en oro el texto de TODOS los bloques que no fueran
              // `fuerte`, asi que un panel de tres bloques ponia tres cosas en
              // oro. El canon dice lo contrario y dice por que: *«el oro dice
              // "mira aqui"; si en un tablero hay tres cosas en oro, dos sobran,
              // el ojo no sabe donde ir y el recurso deja de significar nada»*.
              //
              // Lo que no es el foco va en neutro claro, que es lo que el canon
              // reserva para texto sobre oscuro. La jerarquia la marca el
              // contraste —placa de oro contra negro—, no repetir el acento.
              color: b.fuerte ? color.richBlack : color.lightNeutral,
              fontFamily: fontFamily.video,
              fontSize: cuerpo(!!b.fuerte),
              fontWeight: 900,
              lineHeight: 1.02,
              letterSpacing: b.fuerte ? videoText.tracking : tracking.labelMono,
              textTransform: "uppercase",
              transform: `translateX(${dx}px)`,
              opacity: p,
            }}
          >
            {b.placa ? (
              <Img
                src={staticFile(`fondos/${b.placa}.png`)}
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  // Un recorte, no una imagen: se ve el material del collage
                  // pero el bloque sigue leyéndose como bloque plano.
                  opacity: 0.5,
                }}
              />
            ) : null}
            <span style={{ position: "relative" }}>{b.texto}</span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
