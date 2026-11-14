import React from "react";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { color } from "../brand/tokens";
import PIE from "../brand/pie.json";
import { useLienzo } from "../brand/LienzoContexto";

/**
 * **El pie de un tablero: FUERA de la zona segura, en una línea y en afirmativo.**
 *
 * Instrucción de Jaime (6-9-2026), en dos tiempos: *«por fuera de la zona
 * segura; no me interesa que lo lean, sólo que sepan que existe»*, y acto
 * seguido *«ahora que si lo leen, pues que esté bien leído»*.
 *
 * ## Dónde, y por qué no al fondo del cuadro
 *
 * Justo por debajo del **suelo de la zona segura** (`franja.sueloPx`, 1248 px de
 * 1920), pegado a él. No al borde de abajo: la interfaz de Meta se come el 35%
 * inferior, así que un pie ahí no queda «fuera de la zona segura» — queda
 * **tapado**, y entonces no cumple ni el único trabajo que se le pide.
 *
 * Es jerarquía, no cumplimiento: la fuente sigue completa —lo que exige el
 * piso— pero deja de disputarle sitio al argumento, y la zona segura queda
 * entera para lo que hay que entender.
 *
 * ## Qué sustituye, y qué costaba
 *
 * Una banda de `lightNeutral` apoyada en el techo de la franja, con la fuente en
 * mono y la condición en Montserrat a 26 px: **la masa más clara del cuadro
 * puesta en lo que menos hay que mirar**, y dentro del tablero, compitiendo con
 * la cifra. Medido sobre los 24 fotogramas del lote: en `Reel-R2 e6` ocupaba
 * seis renglones —cuatro de mono y dos de texto— y en `Reel-R1 e3` más sitio que
 * el dato al que venía a respaldar.
 *
 * ## Y una línea, no un párrafo
 *
 * `avance.mono` está medido justamente para esto —la mono no estima, da el ancho
 * exacto— así que el cuerpo sale de lo que mide la línea. Con `CUERPO.tope` un
 * pie corto se ve como en la lámina aprobada de reel-02, y uno largo baja para
 * caber. **`CUERPO.suelo` manda sobre la línea**: por debajo no se lee ni
 * parando la pieza, así que lo que sobra es el texto, no el cuerpo — y quién
 * decide qué texto cabe es `scripts/reels/cifras.mjs`, que declara la falta
 * antes de renderizar en vez de dejar que el pie envuelva en silencio.
 *
 * ## Un solo sitio, y por eso se dibuja en `dibujaTablero`
 *
 * **Estaba escrito cinco veces**: aquí como banda clara, y otra vez dentro de
 * `Comparacion`, `PanelDentro`, `panel/Cierre` y `acumulacion/Cierre` — las dos
 * últimas ya con la forma nueva y con el `1262` escrito a mano. Cinco copias de
 * una regla del canon no fallan: divergen, y entonces cinco tableros de la
 * misma pieza llevan cinco pies distintos. Ahora lo monta
 * [`dibujaTablero`](./Tablero.tsx) para las 24 láminas del lote, así que una
 * forma nueva nace con su pie puesto y ninguna puede volver a dibujarlo a su
 * manera.
 * @clase sistema
 */
export const PieTablero: React.FC<{
  /** La línea, ya compuesta. Vacía o ausente: no se dibuja nada. */
  linea?: string;
  /**
   * Frame del tablero en el que entra. **Entra con él, y ya no el último**: la
   * razón de dejarlo para el final era que la banda clara robaba la mirada, y
   * fuera de la zona segura no le roba nada a nadie. Lo que sí gana es
   * cumplimiento: la atribución está en pantalla todo el tiempo que está la
   * cifra, y no sólo en su último tercio.
   */
  desde?: number;
}> = ({ linea, desde = 0 }) => {
  const layout = useLienzo();
  const franja = layout.franja;
  const entra = useEntrada();
  const texto = (linea ?? "").trim();
  if (!texto) return null;
  const ancho = layout.width - layout.safe.left * 2;
  return (
    <div
      style={{
        position: "absolute",
        left: layout.safe.left,
        top: franja.sueloPx + PIE.hueco,
        width: ancho,
        // Su propia banda: sobre el collage no se leía ni parando la pieza, y
        // él pidió las dos cosas — que se sepa que está, y que si la leen esté
        // bien leída. Pequeña no es descuidada.
        padding: "14px 18px",
        backgroundColor: color.richBlack,
        fontFamily: fontFamily.data,
        fontSize: Math.max(
          PIE.suelo,
          cuerpoQueCabe({
            ancho: ancho - 36,
            largo: texto.length,
            registro: "mono",
            pista: PIE.pista,
            holgura: PIE.holgura,
            tope: PIE.tope,
          }),
        ),
        lineHeight: 1.45,
        letterSpacing: `${PIE.pista}em`,
        color: color.secondaryBlue,
        opacity: entra(desde),
      }}
    >
      {texto}
    </div>
  );
};
