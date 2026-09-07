import ganchoJson from "./gancho.json";

/**
 * **El gancho: dónde vive su rótulo, cómo entra y cuánto calla el subtítulo.**
 *
 * Jaime, 6-9-2026, viendo los siete puestos uno al lado del otro al segundo
 * 1,6: *«en todas hay que revisar el hook»*. Y el diagnóstico, que era de lote:
 * los siete eran **la misma lámina** —rótulo amarillo en dos líneas abajo,
 * subtítulo negro encima, plano medio— con el rótulo en el tercio que la
 * interfaz de Meta tapa, dos bloques de texto compitiendo en el primer segundo,
 * todo quieto y nada jugando con él.
 *
 * **Y el fallo no era que se parecieran.** Jaime lo precisó: *«no necesariamente
 * tiene que ser diferente»* — un tratamiento constante en el lote es un activo
 * de marca. El fallo era que **esa** lámina es mala. El sistema es uno y se
 * aplica siete veces; lo que cambia de pieza a pieza es lo que dice.
 *
 * Lo que lo sustituye está aprobado —*«me gusta cómo se ve el hook»*, sobre
 * `src/preview-gancho.tsx`— y es esto:
 *
 * - el texto **detrás de su cabeza**, en el tercio de arriba, y él delante,
 *   recortado, así que las líneas le pasan por detrás;
 * - **dos líneas escalonadas**, con la jerarquía en el peso y el color y no en
 *   el tamaño solo;
 * - entrando **creciendo y opacando**, suaves, y **nunca con rebote**;
 * - **sin subtítulo compitiendo** en los primeros 2 s.
 *
 * ## Por qué los números viven en un JSON y no aquí
 *
 * Es la lección de `franja.ts`, y es la misma avería: un número escrito en dos
 * sitios son dos números el día que uno se mueve. `gancho.json` lo declara una
 * vez; esto sólo lo traduce a lo que dibuja el componente, y
 * `scripts/reels/portada.mjs` lo lee para comprobar que se cumple.
 *
 * **Y el avance por carácter no está en el JSON**: vive en `medida.ts`, que es
 * donde ya vivía medido para las otras siete copias que hubo.
 */
const J = ganchoJson;

/**
 * **Sólo lo que este lado dibuja.**
 *
 * `arriba`, los cuerpos y el `armado` del rótulo no están: los resuelve el
 * spec y llegan en la capa —el sitio sale de su coronilla, que aquí no se puede
 * medir— o los aplica la puerta. Reexportarlos aquí sería tener el mismo número
 * disponible en dos sitios, que es exactamente como se acaba con dos.
 */
export const gancho = {
  /** Margen izquierdo: la zona segura de Meta. */
  izquierda: J.izquierda,
  /** Ancho disponible para la línea más larga. */
  ancho: J.ancho,
  /** Cuerpo de la primera línea. Sólo como respaldo si la capa no lo trae. */
  primera: J.primera,
  /** Interlineado: las dos líneas son una masa, no un párrafo. */
  interlinea: J.interlinea,
  /** Frame en que entra la primera línea. */
  entradaEn: J.entradaEn,
  /** Frames entre una línea y la siguiente. */
  escalon: J.escalon,
  /** Frames que tarda una línea en entrar. */
  entrada: J.entrada,
  /**
   * Frames entre una palabra y la siguiente dentro de una línea. **Respaldo**:
   * el frame de cada palabra llega resuelto en la capa (`rotulo.palabras`), y
   * esto sólo cubre la línea que no lo traiga.
   */
  palabra: J.palabra,
  /** Grosor del filete que se traza al ras de la línea que golpea. */
  reglaGrosor: J.reglaGrosor,
  /** Píxeles que sube al entrar. */
  sube: J.sube,
  /** Escala de partida: crece hasta 1. Nunca la pasa — eso sería rebote. */
  escala: J.escala,
} as const;
