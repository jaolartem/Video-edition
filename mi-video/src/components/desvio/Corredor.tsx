import React from "react";
import { interpolate } from "remotion";
import { color, layout } from "../../brand/tokens";

/**
 * **El corredor de fuga: adónde va la que se desvía.**
 *
 * Jaime, sobre R-07 e2: *«15,9 s con el 75 % del cuadro en negro vacío»*. Y era
 * literal — el choque de `Desvio` acababa en 520 px y de ahí al techo de la
 * franja no había nada, con el subtítulo flotando en el medio. Esto es lo que
 * ocupa esa mitad, y no es relleno: es el canon —*«punto de fuga, geometría
 * rota, líneas»*— con el elemento conceptual diciendo lo que dice el beat.
 *
 * El beat de `Desvio` es *hay otra manera y alguien la encuentra*, así que las
 * líneas convergen desde el ancho del cuadro hacia un punto: se abre un espacio
 * donde antes había un muro. Entran de fuera hacia dentro conforme la banda que
 * se despega escapa, no antes — el corredor es **consecuencia** del desvío.
 *
 * Y es lo que el canon acaba de pedir en lugar de lo que retiró —*«las
 * animaciones de bolitas y palitos se acaban, quitan más de lo que dan; ahora
 * sólo animaciones complejas que muestren luz o movimiento, en consonancia con
 * la idea del tablero»*—: no es una viñeta que aparece, es profundidad que se
 * abre.
 *
 * Vive en su propio fichero porque es su propia responsabilidad —la
 * profundidad— y porque `Desvio` ya estaba en el techo de 300 líneas: una regla
 * nueva no engorda el fichero de al lado.
 * @clase tablero
 */
export const Corredor: React.FC<{
  /** Desde dónde arrancan las líneas: el borde inferior de la vía. */
  desdeY: number;
  /** El punto de fuga, en píxeles del cuadro. */
  fuga: { x: number; y: number };
  /** Cuántas líneas. Impar, para que haya una central en oro. */
  lineas: number;
  /** Progreso de apertura, 0→1. */
  abre: number;
}> = ({ desdeY, fuga, lineas, abre }) => {
  const centro = Math.floor(lineas / 2);
  return (
    <>
      {Array.from({ length: lineas }).map((_, i) => {
        const k = (i + 1) / (lineas + 1);
        const p = interpolate(abre, [i / lineas, 1], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const x0 = k * layout.width;
        const dx = fuga.x - x0;
        const dy = fuga.y - desdeY;
        return (
          <div
            key={`fuga-${k}`}
            style={{
              position: "absolute",
              left: x0,
              top: desdeY,
              width: Math.hypot(dx, dy) * p,
              // La central es la que sale, y es la única en oro: el oro dice
              // dónde mirar y deja de decirlo si está en las nueve.
              height: i === centro ? 3 : 1,
              backgroundColor: i === centro ? color.gold : color.secondaryBlue,
              opacity: i === centro ? 0.9 : 0.32,
              transformOrigin: "left center",
              transform: `rotate(${(Math.atan2(dy, dx) * 180) / Math.PI}deg)`,
            }}
          />
        );
      })}
    </>
  );
};
