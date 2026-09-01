import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe } from "../../brand/medida";
import { color, layout, videoText } from "../../brand/tokens";

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

/** Ancho util de la banda, ya descontadas las zonas seguras. */
const ANCHO = layout.width - layout.safe.left - layout.safe.right;
/** El tracking, en em, para poder sumarlo al avance. */
const PISTA = Number.parseFloat(videoText.tracking);
/**
 * Relleno horizontal del bloque, en em. Va aqui porque **entra en la cuenta**.
 *
 * El aprendizaje 40 lo dice con estas palabras: el ancho real de un bloque no
 * es `cuerpo * n * avance`, es `cuerpo * (n * (avance + tracking) + relleno)`.
 * Despejar el cuerpo sin el interletrado y sin este relleno daba **siempre** un
 * bloque mas ancho que la banda — medido sobre el lote, ocho de trece se salian
 * entre 39 y 58 px, y con `nowrap` no envuelven: se salen y punto.
 *
 * El avance de la Anton en esta banda vive en `brand/medida` (`antonBanda`),
 * que es donde se declara una sola vez para las siete piezas que lo usaban.
 */
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
export const Compuesta: React.FC<{ c: Compuesto; desde: number }> = ({
  c,
  desde,
}) => {
  const frame = useCurrentFrame();
  const cuerpo = Math.round(
    Math.max(
      videoText.caption,
      cuerpoQueCabe({
        ancho: ANCHO,
        largo: c.abajo.length,
        registro: "antonBanda",
        pista: PISTA,
        relleno: RELLENO_EM,
        tope: videoText.titleBig,
      }),
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
