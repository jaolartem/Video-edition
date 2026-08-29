import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { color } from "../brand/tokens";

/**
 * **Pictogramas geométricos**: señales de tránsito y figuras de palitos.
 *
 * Idea de Jaime: *«también se pueden señales de tránsito, o elementos
 * figurativos simples, imágenes humanas con palitos y bolitas»*. Resuelve lo
 * que el texto solo no puede — *«que no sea mi cara y ya»*— sin escribir copy
 * nuevo que haya que aprobar.
 *
 * ## Por qué esto NO es la ilustración que el canon prohíbe
 *
 * La prohibición es de **ilustración amable**: blobs, dibujitos, iconografía
 * Material redondeada. Un pictograma no es eso. Es el registro del
 * constructivismo: formas primarias —círculo, rectángulo, triángulo, línea— en
 * plano de color, sin degradado, sin sombra y sin esquina redondeada. Una señal
 * de tránsito es, literalmente, geometría que significa; y la figura de palitos
 * es la convención del diagrama, no un personaje.
 *
 * Tres reglas para que siga siéndolo:
 *
 * - **Trazo recto y grosor constante.** Nada de curvas suaves ni de línea que
 *   engorda.
 * - **La paleta manda.** Oro lo que hay que mirar; navy y azul pizarra lo
 *   demás. Sin rojo, tampoco en una señal de alto — el octógono se reconoce por
 *   su forma.
 * - **Entra dibujándose, no apareciendo.** El movimiento es el trazo, que es lo
 *   que el sonido puede seguir.
 */
export type Figura =
  | "persona"
  | "dos-personas"
  | "alto"
  | "ceda"
  | "desvio"
  | "bifurcacion"
  | "escalera"
  | "flecha"
  | "barras"
  | "serie";

/** Un trazo que se dibuja: se revela por longitud, no por opacidad. */
const Traza: React.FC<{
  d: string;
  p: number;
  largo: number;
  tinte: string;
  grosor?: number;
}> = ({ d, p, largo, tinte, grosor = 7 }) => (
  <path
    d={d}
    fill="none"
    stroke={tinte}
    strokeWidth={grosor}
    strokeLinecap="butt"
    strokeDasharray={largo}
    strokeDashoffset={largo * (1 - p)}
  />
);

/** La figura de palitos y bolitas, en la posición y escala que se le pida. */
const Palitos: React.FC<{ x: number; p: number; tinte: string }> = ({
  x,
  p,
  tinte,
}) => (
  <>
    <circle
      cx={x}
      cy={26}
      r={14}
      fill={tinte}
      opacity={interpolate(p, [0, 0.25], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })}
    />
    <Traza d={`M ${x} 42 L ${x} 88`} p={p} largo={46} tinte={tinte} />
    <Traza d={`M ${x - 26} 60 L ${x + 26} 60`} p={p} largo={52} tinte={tinte} />
    <Traza d={`M ${x} 88 L ${x - 22} 124`} p={p} largo={42} tinte={tinte} />
    <Traza d={`M ${x} 88 L ${x + 22} 124`} p={p} largo={42} tinte={tinte} />
  </>
);

export const Pictograma: React.FC<{
  figura: Figura;
  /** Frame en que empieza a dibujarse, relativo a la secuencia. */
  desde?: number;
  /** Frames que tarda el trazo. La duración la decide la lectura, no un tope. */
  dura?: number;
  /** El que hay que mirar va en oro; el resto en azul pizarra. */
  oro?: boolean;
  alto?: number;
}> = ({ figura, desde = 0, dura = 14, oro, alto = 150 }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [desde, desde + dura], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const tinte = oro ? color.gold : color.secondaryBlue;

  const dibujo = () => {
    switch (figura) {
      case "persona":
        return <Palitos x={100} p={p} tinte={tinte} />;
      case "dos-personas":
        return (
          <>
            <Palitos x={54} p={p} tinte={color.secondaryBlue} />
            <Palitos
              x={146}
              p={interpolate(p, [0.35, 1], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })}
              tinte={color.gold}
            />
          </>
        );
      case "alto":
        // Octógono. Se reconoce por la forma: **no hay rojo en el sistema.**
        return (
          <Traza
            d="M 62 24 L 138 24 L 176 62 L 176 118 L 138 156 L 62 156 L 24 118 L 24 62 Z"
            p={p}
            largo={430}
            tinte={tinte}
            grosor={9}
          />
        );
      case "ceda":
        return (
          <Traza
            d="M 26 32 L 174 32 L 100 156 Z"
            p={p}
            largo={430}
            tinte={tinte}
            grosor={9}
          />
        );
      case "desvio":
        return (
          <>
            <Traza d="M 100 156 L 100 84" p={p} largo={72} tinte={tinte} grosor={9} />
            <Traza d="M 100 84 L 40 34" p={p} largo={78} tinte={color.secondaryBlue} grosor={9} />
            <Traza d="M 100 84 L 160 34" p={p} largo={78} tinte={color.gold} grosor={9} />
          </>
        );
      case "bifurcacion":
        return (
          <>
            <Traza d="M 20 90 L 92 90" p={p} largo={72} tinte={tinte} grosor={9} />
            <Traza d="M 92 90 L 180 36" p={p} largo={104} tinte={color.gold} grosor={9} />
            <Traza d="M 92 90 L 180 144" p={p} largo={104} tinte={color.secondaryBlue} grosor={9} />
          </>
        );
      case "escalera":
        return (
          <Traza
            d="M 20 150 L 60 150 L 60 114 L 100 114 L 100 78 L 140 78 L 140 42 L 180 42"
            p={p}
            largo={296}
            tinte={tinte}
            grosor={9}
          />
        );
      case "barras":
        /**
         * Dos cantidades enfrentadas, y **el hueco es lo que se mira**.
         *
         * Sale literal de la descripcion de escena mas repetida del lote —«una
         * barra de facturacion llena y, debajo, la de lo que queda a un tercio;
         * el hueco entre las dos en oro»— y es geometria plana: dos trazos y el
         * resto. El oro va en el hueco, no en las barras: lo que el
         * espectador tiene que ver no es cuanto entra, es cuanto falta.
         */
        return (
          <>
            <Traza d="M 22 62 L 178 62" p={p} largo={156} tinte={color.secondaryBlue} grosor={22} />
            <Traza
              d="M 22 122 L 74 122"
              p={interpolate(p, [0.25, 1], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })}
              largo={52}
              tinte={color.secondaryBlue}
              grosor={22}
            />
            <Traza
              d="M 74 122 L 178 122"
              p={interpolate(p, [0.6, 1], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })}
              largo={104}
              tinte={color.gold}
              grosor={22}
            />
          </>
        );
      case "serie":
        /**
         * Tres marcas en fila, tachadas una tras otra. Tambien literal: *«tres
         * senales tachadas una tras otra: carta, banco, telefono»*, *«tres
         * pictogramas de oficio en fila»*.
         *
         * Se tachan **en orden**, no a la vez: la escena dice «una tras otra» y
         * eso es lo que hace el trabajo — la tercera confirma el patron que las
         * dos primeras insinuaron. La ultima en oro porque es la que cierra.
         */
        return (
          <>
            {[30, 84, 138].map((x, i) => {
              const q = interpolate(p, [i * 0.22, i * 0.22 + 0.34], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              const ultimo = i === 2;
              return (
                <React.Fragment key={x}>
                  <Traza
                    d={`M ${x} 62 L ${x + 34} 62 L ${x + 34} 118 L ${x} 118 Z`}
                    p={q}
                    largo={180}
                    tinte={ultimo ? tinte : color.secondaryBlue}
                    grosor={7}
                  />
                  <Traza
                    d={`M ${x - 4} 124 L ${x + 38} 56`}
                    p={interpolate(q, [0.55, 1], [0, 1], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    })}
                    largo={80}
                    tinte={ultimo ? color.gold : color.secondaryBlue}
                    grosor={9}
                  />
                </React.Fragment>
              );
            })}
          </>
        );
      default:
        return (
          <>
            <Traza d="M 20 90 L 160 90" p={p} largo={140} tinte={tinte} grosor={9} />
            <Traza d="M 160 90 L 128 58" p={p} largo={45} tinte={tinte} grosor={9} />
            <Traza d="M 160 90 L 128 122" p={p} largo={45} tinte={tinte} grosor={9} />
          </>
        );
    }
  };

  return (
    <svg
      viewBox="0 0 200 180"
      height={alto}
      width={(alto * 200) / 180}
      style={{ display: "block" }}
    >
      {dibujo()}
    </svg>
  );
};
