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
 * ## Qué se queda fuera: la placa, y sólo la placa
 *
 * El fondo sigue a sangre — está detrás de todo y no compite con nadie. Lo
 * demás entra, **incluido lo que un tablero dibuja como superficie**:
 * `PanelDentro` dejaba fuera sus masas negras y su recorte por ser «superficie,
 * como la placa», y el fotograma de reel-02 e2 enseñó las dos maneras que eso
 * tiene de romperse — el subtítulo cayendo encima de su silueta, y la cola de
 * una masa colgando 300 px por debajo de todo lo que sostenía.
 *
 * La raya no es «fondo o contenido»: es **quién lo dibuja**. La placa es del
 * fondo; las masas, la figura y el texto son del tablero, y el tablero acaba en
 * el techo de la franja.
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
