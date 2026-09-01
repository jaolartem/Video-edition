import React from "react";
import { assertShort } from "../../brand/copy";
import type { Entrada } from "../../brand/horario";
import { fontFamily } from "../../brand/fonts";
import { color } from "../../brand/tokens";
import { BARRA, EJE, PANEL, SUELO, aPx, basesDe } from "./caja";
import type { Tramo } from "./tipos";

/**
 * Color de la etiqueta de un tramo: oro si el tramo asoma por encima de la
 * raya, azul secundario si no. **El oro marca lo que hay que mirar**, así que
 * la etiqueta se pone de acuerdo con su bloque en vez de ir toda del mismo
 * color y dejar que el espectador empareje a mano.
 */
const tinta = (
  umbral: { en: number } | undefined,
  base: number,
  tope: number,
): string =>
  umbral && tope > umbral.en && base < tope ? color.gold : color.secondaryBlue;

/**
 * La magnitud que se acumula, y la raya que no había que cruzar.
 *
 * **Cada tramo se parte en lo que queda debajo de la raya y lo que asoma por
 * encima, y ese corte ES el argumento**: la geometría no ilustra el tema, dice
 * la frase. Hay una cantidad que sube, hay una raya, y el momento en que la
 * cantidad pasa la raya es el momento en que la voz lo dice.
 */
export const Barra: React.FC<{
  tramos: Tramo[];
  umbral?: { etiqueta: string; en: number };
  /** Frame de entrada de cada tramo. */
  entradas: number[];
  /** Frame en que se traza la raya. */
  raya: number;
  entra: Entrada;
}> = ({ tramos, umbral, entradas, raya, entra }) => {
  const bases = basesDe(tramos);
  const yUmbral = umbral ? SUELO - aPx(umbral.en) : null;

  return (
    <>
      {tramos.map((tr, i) => {
        const crece = entra(entradas[i] ?? 0);
        const base = bases[i] ?? 0;
        const tope = base + tr.alto;
        const corte = umbral
          ? Math.min(Math.max(umbral.en, base), tope)
          : tope;
        const partes = [
          { desde: base, hasta: corte, oro: false },
          { desde: corte, hasta: tope, oro: true },
        ].filter((q) => q.hasta > q.desde);
        return (
          <React.Fragment key={tr.etiqueta}>
            {partes.map((q) => (
              <div
                key={q.oro ? "oro" : "base"}
                style={{
                  position: "absolute",
                  left: EJE.x,
                  width: BARRA,
                  top: SUELO - aPx(q.hasta),
                  height: aPx(q.hasta) - aPx(q.desde),
                  backgroundColor: q.oro
                    ? color.gold
                    : i % 2
                      ? color.navyHi
                      : color.navy,
                  transformOrigin: "bottom",
                  transform: `scaleY(${crece})`,
                }}
              />
            ))}
            {/* Etiqueta centrada en su bloque y en UNA línea. Sin `nowrap`
                «Cruza el umbral» salía en tres renglones dentro de una columna
                estrecha y se leía como tres etiquetas distintas: dónde respira
                una frase lo decide quien la escribe, no el ancho que sobra. */}
            <div
              style={{
                position: "absolute",
                left: EJE.x + BARRA + 34,
                top: SUELO - aPx((base + tope) / 2) - 22,
                whiteSpace: "nowrap",
                fontFamily: fontFamily.bloque,
                fontSize: 40,
                letterSpacing: "0.01em",
                textTransform: "uppercase",
                color: tinta(umbral, base, tope),
                opacity: crece,
              }}
            >
              {assertShort(tr.etiqueta, "label", "Acumulacion.tramo")}
            </div>
          </React.Fragment>
        );
      })}

      {/* La raya. Se traza ANTES de que la barra llegue: primero se ve el
          límite, después se ve cruzarlo. Al revés no hay drama, hay un dato. */}
      {umbral && yUmbral !== null ? (
        <>
          <div
            style={{
              position: "absolute",
              left: EJE.x - 34,
              top: yUmbral,
              width: (PANEL.w - EJE.x - 20) * entra(raya),
              height: 4,
              backgroundColor: color.gold,
            }}
          />
          {/* Al final de la raya, no al principio: al principio cae debajo de
              la barra y desaparece justo cuando la barra la cruza, que es el
              unico momento en que hace falta leerla. */}
          <div
            style={{
              position: "absolute",
              right: 56,
              top: yUmbral - 52,
              fontFamily: fontFamily.bloque,
              fontSize: 34,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: color.gold,
              opacity: entra(raya),
            }}
          >
            {assertShort(umbral.etiqueta, "label", "Acumulacion.umbral")}
          </div>
        </>
      ) : null}
    </>
  );
};
