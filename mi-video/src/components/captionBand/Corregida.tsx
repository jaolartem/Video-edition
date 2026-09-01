import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { color } from "../../brand/tokens";

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
export const Corregida: React.FC<{
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
