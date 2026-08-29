import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { color, layout } from "../brand/tokens";

/**
 * Barra que cruza el cuadro **para traer un gráfico**.
 *
 * **No es la transición por defecto.** Se usó en todos los cambios de encuadre
 * y quedó peor que el salto que venía a tapar: un slab negro cruzando cada tres
 * segundos es más ruidoso que un jump cut. Jaime: *«se evita esa transición con
 * un cuadrito como única herramienta, y la próxima vez, si sale, es para que
 * aparezca un gráfico y va desvaneciendo la toma anterior»*.
 *
 * Así que hace dos cosas a la vez, y sólo cuando entra una tarjeta:
 *
 * - **Revela**: la barra pasa y detrás queda el gráfico. El movimiento tiene un
 *   motivo — trae algo — en vez de decorar un corte.
 * - **Desvanece**: la toma anterior se va debajo mientras la barra cruza, así
 *   que no hay salto que tapar, hay una capa que sustituye a otra.
 *
 * Diagonal y asimétrica a propósito: el constructivismo evita la simetría
 * porque la diagonal es la que sugiere movimiento.
 */
export const BarWipe: React.FC<{
  /** Frame del corte. La barra lo cruza centrada en él. */
  en: number;
  /** Frames que tarda en atravesar. Lo decide la lectura, no la web. */
  dura?: number;
  /** Grosor de la barra como fracción de la diagonal del cuadro. */
  grosor?: number;
  tono?: "gold" | "black";
}> = ({ en, dura = 7, grosor = 0.26, tono = "black" }) => {
  const frame = useCurrentFrame();
  const t = frame - (en - dura / 2);
  if (t < 0 || t > dura) return null;

  // Recorrido: de fuera por abajo-izquierda a fuera por arriba-derecha.
  // Recorrido justo: de fuera a fuera, sin margen que alargue el barrido. Con
  // el viaje anterior la barra pasaba media transicion fuera del cuadro y
  // dentro se quedaba quieta demasiado tiempo — leia como mancha, no como algo
  // que cruza.
  const viaje = layout.height * 1.15;
  const p = interpolate(t, [0, dura], [-viaje, viaje], {
    easing: Easing.inOut(Easing.quad),
  });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          left: "-60%",
          width: "220%",
          height: `${grosor * 100}%`,
          /**
           * Centrada en el cuadro, no colgando del medio hacia abajo: en el
           * instante del corte la barra tiene que estar EN el centro, que es
           * donde esta la cara. Con `top: 50%` cubria solo la mitad inferior y
           * el salto seguia viendose arriba.
           */
          top: `${50 - (grosor * 100) / 2}%`,
          background: tono === "gold" ? color.gold : color.richBlack,
          transform: `translate(${p * 0.7}px, ${-p * 0.55}px) rotate(-22deg)`,
          transformOrigin: "center",
        }}
      />
    </AbsoluteFill>
  );
};
