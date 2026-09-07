import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { cc, pintaDelCc, type Trato } from "../../brand/cc";

/**
 * La forma plana, **con entrada y con el fondo que le toque**.
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
 *
 * ## El cuadro negro dejo de ser el unico
 *
 * Jaime, 6-9-2026, viendo las siete: *«los CC estan feos; pueden ser a negativo
 * solamente para variar el cuadro negro, es decir, unos CC que se compongan
 * mejor respecto a la composicion»*. Aqui vivia el bloque de `richBlack` a pelo,
 * o sea el mismo parche en los 90 segundos de las siete piezas — la zona de
 * pantalla que mas tiempo esta ocupada, resuelta sin componer.
 *
 * Ahora el suelo de la letra lo pone `pintaDelCc`, y **es lo unico que cambia**:
 * el sitio, la familia, el cuerpo, el peso, la alineacion y la entrada son los
 * mismos en los tres. Por eso pueden convivir en una pieza sin que se lea como
 * tres piezas cosidas.
 *
 * Cual toca no se elige aqui ni se opina: lo mide `dominio/trasfondo.py` sobre
 * la banda que este subtitulo ocupa en esa escena y lo decide `reels/cc.mjs`.
 *
 * **Y el negativo se compone contra el video, no contra este `<span>`.** La
 * fusion `difference` mira lo que hay pintado debajo dentro del mismo contexto
 * de apilamiento; una capa aislada entre medias la apaga sin dar error. El
 * `transform` y la `opacity` de la entrada van en este mismo elemento —el que se
 * fusiona— y eso no aisla nada: aislaria un ANCESTRO que no contuviera el plano.
 */
export const Plana: React.FC<{
  desde: number;
  /** Como se resuelve el fondo. Ver `src/brand/cc.ts`. */
  trato?: Trato;
  children: React.ReactNode;
}> = ({ desde, trato = cc.porDefecto, children }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [desde, desde + 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    /* **El envoltorio de bloque hace que el `<span>` siga siendo INLINE.**
       Como hijo directo del flex se blockifica, y entonces `clone` no recorta
       renglon a renglon: pinta UN rectangulo del ancho de la columna. Es lo que
       hacia que la caja saliera como una banda negra de borde a borde con un
       hueco negro debajo de la ultima linea corta —«asi.» ocupando 950 px— en
       vez de la cinta del canon a tamaño de letra. `CaptionDiscreta` ya lo
       habia aprendido y esta capa, que es la que se ve 90 segundos, no. */
    <div style={{ maxWidth: "100%" }}>
      <span
        style={{
          ...pintaDelCc(trato),
          opacity: p,
          transform: `translateY(${((1 - p) * 14).toFixed(1)}px)`,
        }}
      >
        {children}
      </span>
    </div>
  );
};
