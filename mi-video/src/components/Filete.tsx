import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { color, layout } from "../brand/tokens";

/**
 * **La transición animada: dos filetes cruzan la costura en diagonal.**
 *
 * Jaime, pidiéndola: *«que haga una animación en esa transición»*. Era la
 * tercera vía y la que faltaba — el `glitch` distorsiona la imagen, la
 * `cortinilla` interrumpía con una placa y quedó retirada, y aquí no se tapa
 * nada: **pasa algo por delante** y el corte cae debajo mientras pasa.
 *
 * ## Por qué un filete y no un bloque
 *
 * El filete es el separador del canon —*«bloques planos de color separados por
 * filetes, nunca por sombra»*—, así que separar dos planos en el tiempo es esa
 * misma gramática aplicada al corte. El bloque grueso ya se probó: `BarWipe` en
 * todos los cambios de encuadre quedó peor que el salto que venía a tapar, y
 * Jaime lo acotó a traer un gráfico. Aquí no se vuelve a esa forma.
 *
 * ## Y no va en oro
 *
 * *«El oro reservado a aquello que el espectador debe atender»*, y una costura
 * no lo es: un filete dorado cruzando cada pocos segundos es oro decorativo,
 * que el canon prohíbe por nombre. Va en `lightNeutral`, con el segundo en
 * `secondaryBlue` —la jerarquía de lo que acompaña—.
 *
 * ## Se traza y se retira, no se desliza
 *
 * La línea nace en una esquina, crece hasta cruzar el cuadro y su cola la
 * alcanza: es la primitiva **trazo** de `docs/composicion.md`, no un objeto que
 * viaja. Con `ease-out` a la entrada y `ease-in` a la salida, que es como se
 * mueve lo que tiene masa; nada de rebote.
 *
 * @clase transicion
 */
export const Filete: React.FC<{
  /** Frame de la costura. Los filetes la cruzan centrados en ella. */
  en: number;
  /** Frames que tarda el cruce. Corto a propósito: 10 son 0,33 s. */
  dura?: number;
  /** Grosor del filete principal, en px de un cuadro de 1080×1920. */
  grosor?: number;
  /** Grosor del segundo, el que acompaña. */
  segundo?: number;
}> = ({ en, dura = 10, grosor = 6, segundo = 3 }) => {
  const frame = useCurrentFrame();
  const t = frame - (en - dura / 2);
  if (t < 0 || t > dura) return null;

  /**
   * El diagonal del cuadro con holgura: la línea tiene que entrar y salir
   * fuera, no aparecer y desaparecer dentro.
   */
  const largo = Math.hypot(layout.width, layout.height) * 1.2;

  /**
   * Cada filete es el mismo trazo con un desfase. `retraso` es lo que separa al
   * segundo del primero — sin él las dos líneas serían una sola más gruesa, que
   * es exactamente el bloque que no queremos.
   */
  const trazo = (retraso: number) => {
    const p = (t - retraso) / (dura - retraso);
    return {
      // La cabeza sale disparada y frena; la cola arranca después y la alcanza.
      cabeza: interpolate(p, [0, 0.6], [0, 1], {
        easing: Easing.out(Easing.quad),
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }),
      cola: interpolate(p, [0.35, 1], [0, 1], {
        easing: Easing.in(Easing.quad),
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }),
    };
  };

  const lineas = [
    { retraso: 0, alto: grosor, tono: color.lightNeutral, salto: -0.09 },
    { retraso: dura * 0.22, alto: segundo, tono: color.secondaryBlue, salto: 0.13 },
  ];

  return (
    <AbsoluteFill style={{ overflow: "hidden", pointerEvents: "none" }}>
      {lineas.map((l) => {
        const { cabeza, cola } = trazo(l.retraso);
        if (cabeza - cola <= 0) return null;
        return (
          <div
            key={l.tono}
            style={{
              position: "absolute",
              top: `${50 + l.salto * 100}%`,
              left: "50%",
              width: largo,
              height: l.alto,
              marginLeft: -largo / 2,
              /**
               * −45°: el canon acota los ángulos a un juego corto —0° y ±45°— y
               * la diagonal es lo que sugiere movimiento. Nada centrado ni
               * simétrico.
               */
              transform: "rotate(-45deg)",
              backgroundColor: l.tono,
              // El recorte es lo que traza: la línea existe entera y se enseña
              // por tramos. Sin sombra y sin degradado, que es la regla.
              clipPath: `inset(0 ${((1 - cabeza) * 100).toFixed(2)}% 0 ${(cola * 100).toFixed(2)}%)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
