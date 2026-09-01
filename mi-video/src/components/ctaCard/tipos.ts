import type { Accent, Mode, Tone } from "../../brand/tokens";

/**
 * **El contrato del cierre.** Un CTA incompleto no sirve, así que lo que la
 * oferta necesita para ser cierta va en el tipo y no en una revisión.
 */
export type CtaCardProps = {
  /** La promesa, en corto. No el guion entero. */
  promesa: string;
  /** Los datos duros de la oferta. Un CTA incompleto no sirve. */
  fecha: string;
  /**
   * Precio suelto. Se conserva para las piezas que no declaran `cuenta`.
   *
   * **Sólo entra con su fecha de cierre.** Sin ella caduca en silencio: «$20»
   * deja de ser cierto el día que sube y la pieza sigue publicada.
   */
  precio?: string;
  /**
   * El desliz que se señala. Se oye `dice`, se lee `es`.
   *
   * En el reel 1 Jaime dice «550» y el cálculo de su propio libreto da `$576`.
   * La diferencia es de redondeo y no cambia el mensaje — por eso se señala en
   * vez de corregirse, y por eso lo tachado es pequeño y lo cierto es lo grande.
   */
  corrige?: { dice: string; es: string };
  /**
   * **Las dos cuentas**, que es de lo que va la pieza.
   *
   * Corrección de Jaime: *«el precio del bootcamp es 20, 30 o 40 dólares; el
   * precio de NO conocerlos es de 576»*. Antes los 576 ocupaban la fila de
   * precio, así que la tarjeta decía que el bootcamp costaba 576 — el número
   * correcto en la fila equivocada.
   *
   * Van **en dos columnas, navy contra oro**, que es como el canon resuelve una
   * comparación: el navy es el camino por defecto y el oro es donde hay que
   * mirar. Y **la pregunta no se escribe**: la hace la voz —*«revise qué cuenta
   * le sale mejor»*— y aquí sólo están las dos cuentas para que tenga a qué
   * referirse.
   */
  cuenta?: { cuesta: string; vale: string; nota?: string };
  accion: string;
  kicker?: string;
  /**
   * Cuánto dura la tarjeta, en frames. **El horario se reparte sobre ella.**
   *
   * Jaime: *«todo el panel final pasa muy rápido»*. La duración la calcula
   * `reels-spec.mjs` a partir de lo que la tarjeta lleva dentro, no de un
   * número redondo: así cada bloque tiene su tiempo de lectura.
   */
  duracion?: number;
  /** Placa de fondo recortada. El CTA es el último frame: no puede ser un plano negro. */
  placa?: string;
  mode?: Mode;
  tone?: Tone;
  accent?: Accent;
};
