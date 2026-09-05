import React from "react";
import { franja } from "../brand/franja";

/**
 * **La caja dentro de la que dibuja un tablero.** Del borde de arriba al techo
 * de la franja del subtítulo, y ni un píxel más abajo.
 *
 * Instrucción de Jaime (T-02), en su segunda mitad: *«ningún tablero baja hasta
 * esa franja, que queda reservada al subtítulo»*.
 *
 * ## Por qué es un recorte y no una indicación
 *
 * La regla estaba escrita —`CausalChain` y `TwoPaths` reservaban
 * `layout.safe.bottom + layout.captionBand` cada uno por su cuenta— y aun así
 * **los seis tableros del lote la incumplían**: `Comparacion` ponía el remate en
 * el 1390 y el pie en el 1570, y `Acumulacion` un panel de 300 a 1390 con su
 * banda de condición en el 1452. Todo eso cae por debajo del 65%, o sea **bajo
 * la interfaz de la plataforma**: no es que compitiera con el subtítulo, es que
 * el espectador no lo veía. Cuatro copias del mismo número y dos componentes
 * que no lo miraban.
 *
 * Con el recorte, incumplirlo deja de ser posible: lo que se salga se ve
 * cortado en el render —un fallo visible— en vez de irse a una zona donde el
 * fallo es invisible, que es lo caro.
 *
 * El fondo NO va aquí dentro: la placa y el color de la superficie siguen
 * ocupando el cuadro entero. Lo que se recorta es **el contenido**, que es lo
 * que hay que leer.
 */
export const ZonaTablero: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <div
    style={{
      position: "absolute",
      left: 0,
      right: 0,
      top: 0,
      bottom: franja.reserva,
      overflow: "hidden",
    }}
  >
    {children}
  </div>
);
