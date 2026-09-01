import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { color } from "../../brand/tokens";

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
export const Plana: React.FC<{ desde: number; children: React.ReactNode }> = ({
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
