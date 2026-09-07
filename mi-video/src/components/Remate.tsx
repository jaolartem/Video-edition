import React from "react";
import { color } from "../brand/tokens";
import { Cinta } from "./Fondo";

/**
 * **La cinta que cierra un tablero — y el oro NO viene puesto.**
 *
 * El canon lo dice sin margen: *«si en un tablero hay tres cosas en oro, dos
 * sobran»*. Y el motivo no es de gusto — **el oro dice «mira aquí»**, así que
 * con tres no lo dice nadie. Jaime lo repitió como criterio de diseño, junto a
 * la carga cognitiva: *«alineación y espaciado consistentes, un solo acento,
 * cantos duros, nada de ornamento»*.
 *
 * ## Por qué existe este componente y no basta con `Cinta`
 *
 * Porque `Cinta` tiene `tinte = color.gold` **por defecto**, y un defecto de oro
 * multiplica el oro: cada forma que necesitó un remate escribió
 * `<Cinta tinte={color.gold}>` sin mirar lo que ya había en su propia lámina.
 * Medido sobre los 24 tableros del lote, cuatro formas llevaban dos o tres
 * masas de oro a la vez —`Comparacion` (columna + remate), `PanelDentro`
 * (cabecera + columna + remate), `Fusion` (bloque fundido + remate) y `Desvio`
 * (señal + remate)—.
 *
 * Aquí el defecto es al revés: **el remate no es el acento salvo que se diga**.
 * Un remate no necesita oro para golpear: entra el último, va girado y en Anton
 * a cuerpo grande. Su peso es de posición y de tamaño.
 *
 * ## Cuándo SÍ lleva `acento`
 *
 * Cuando el tablero no pinta oro en ningún otro sitio — `BeliefSwap` es el caso:
 * dos bloques planos y la conclusión. Un tablero sin acento no cumple la regla,
 * la incumple por el otro lado: el ojo entra por donde puede.
 *
 * La pregunta que lo decide es siempre la misma, y es de edición, no de gusto:
 * **qué demuestra este tablero**. El oro va ahí.
 * @clase sistema
 */
export const Remate: React.FC<{
  children: React.ReactNode;
  /**
   * Si este remate **es** el acento del tablero. Por defecto no lo es: el
   * acento suele estar en la cifra o la figura que demuestra, y entonces el
   * remate va en claro.
   */
  acento?: boolean;
  /** Grados. Uno o dos bastan: es tensión, no descuido. */
  giro?: number;
  cuerpo?: number;
}> = ({ children, acento = false, giro, cuerpo }) => (
  <Cinta
    tinte={acento ? color.gold : color.lightNeutral}
    giro={giro}
    cuerpo={cuerpo}
  >
    {children}
  </Cinta>
);
