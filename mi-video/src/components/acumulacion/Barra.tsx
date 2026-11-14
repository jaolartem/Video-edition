import React from "react";
import { assertShort } from "../../brand/copy";
import type { Entrada } from "../../brand/horario";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe } from "../../brand/medida";
import { color } from "../../brand/tokens";
import { ALTO, EJE, FICHA, acentua, aPx, basesDe, sueloEn, techoEn } from "./caja";
import { useLienzo } from "../../brand/LienzoContexto";
import type { Tramo } from "./tipos";

/**
 * La magnitud que se acumula, y la raya que no había que cruzar.
 *
 * **Cada tramo se parte en lo que queda debajo de la raya y lo que asoma por
 * encima, y ese corte ES el argumento**: la geometría no ilustra el tema, dice
 * la frase. Hay una cantidad que sube, hay una raya, y el momento en que la
 * cantidad pasa la raya es el momento en que la voz lo dice.
 *
 * ## Y sin raya, lo que se ve es que SUMA
 *
 * Jaime, sobre el tablero de reel-02 e3: *«los bloques ya están puestos, no se
 * ve acumular nada, cuando el sentido de esa figura es que cada año suma hasta
 * un total»*. Entrar de uno en uno ya se hacía; lo que faltaba era que se viera
 * **de dónde a dónde**. Por eso el hueco de la pila entera se dibuja desde el
 * principio como un filete de un píxel: la caja donde va a caber todo está
 * puesta antes que el primer bloque, así que cada uno que entra se lee como un
 * paso hacia el borde de arriba y no como un rectángulo suelto.
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
  const layout = useLienzo();
  // Del techo de SU franja, no de la vertical (C-670).
  const SUELO = sueloEn(layout);
  const TECHO = techoEn(layout);
  const bases = basesDe(tramos);
  const yUmbral = umbral ? SUELO - aPx(umbral.en) : null;

  return (
    <>
      {/* La caja de lo que va a caber: filete de un píxel, nunca sombra. Marca
          el total antes de que exista, que es lo que convierte cinco bloques en
          una acumulación. */}
      <div
        style={{
          position: "absolute",
          left: EJE.x,
          top: TECHO,
          width: EJE.barra,
          height: ALTO,
          border: `1px solid ${color.secondaryBlue}`,
          opacity: 0.34 * entra(0),
        }}
      />

      {tramos.map((tr, i) => {
        const crece = entra(entradas[i] ?? 0);
        const base = bases[i] ?? 0;
        const tope = base + tr.alto;
        const acento = acentua(tramos, umbral, i);
        const corte = umbral
          ? Math.min(Math.max(umbral.en, base), tope)
          : tope;
        const partes = [
          { desde: base, hasta: corte, oro: acento },
          { desde: corte, hasta: tope, oro: true },
        ].filter((q) => q.hasta > q.desde);
        return (
          <React.Fragment key={tr.etiqueta}>
            {partes.map((q) => (
              <div
                key={q.oro && !acento ? "oro" : "base"}
                style={{
                  position: "absolute",
                  left: EJE.x,
                  width: EJE.barra,
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
            {/* **La etiqueta va en su propia ficha negra**, no sobre el panel
                que había debajo. Es el negro de la lámina aprobada: sostiene lo
                que hay que leer y no un píxel más. En UNA línea — sin `nowrap`,
                «Cruza el umbral» salía en tres renglones y se leía como tres
                etiquetas distintas. */}
            {tr.etiqueta ? (
              <div
                style={{
                  position: "absolute",
                  left: FICHA.x,
                  top: SUELO - aPx((base + tope) / 2),
                  transform: "translateY(-50%)",
                  padding: "10px 24px",
                  backgroundColor: color.richBlack,
                  whiteSpace: "nowrap",
                  fontFamily: fontFamily.bloque,
                  fontSize: FICHA.cuerpo,
                  letterSpacing: "0.01em",
                  textTransform: "uppercase",
                  color: acento || (umbral && tope > umbral.en)
                    ? color.gold
                    : color.secondaryBlue,
                  opacity: crece,
                }}
              >
                {assertShort(tr.etiqueta, "label", "Acumulacion.tramo")}
                {/* **Y cuánto es, debajo del nombre.** La altura ya lo dice en
                    proporción; el número lo dice en la unidad de la raya, que
                    es lo que convierte la columna en una medida y no en un
                    dibujo. Va en la misma ficha —un negro por etiqueta, no
                    dos— y en cuerpo menor: manda el nombre, el importe lo
                    respalda. Ver `Tramo.valor`. */}
                {tr.valor ? (
                  <div
                    style={{
                      fontSize: Math.round(FICHA.cuerpo * 0.72),
                      letterSpacing: "0.02em",
                      color: color.lightNeutral,
                    }}
                  >
                    {assertShort(tr.valor, "label", "Acumulacion.tramo.valor")}
                  </div>
                ) : null}
              </div>
            ) : null}
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
              width: (layout.width - EJE.x - 20) * entra(raya),
              height: 4,
              backgroundColor: color.gold,
            }}
          />
          {/**
           * **Dentro de la columna de la barra y POR DEBAJO de la raya.**
           *
           * Encajonada en el ancho de la barra el choque con la ficha del tramo
           * que cruza deja de ser posible —la columna de fichas empieza
           * `EJE.hueco` más a la derecha—, y ése fue el arreglo de reel-03,
           * donde salían una encima de otra: «EL DÓL▮▮ SIGUIENTE».
           *
           * Pero quedó **encima de la raya**, que es exactamente la banda donde
           * ocurre el argumento: lo que asoma por arriba es el único oro del
           * cuadro y es lo que hay que ver cruzar. En reel-05 el bloque dorado
           * medía 103 px y esta chapa negra le tapaba la mitad de abajo, así
           * que en el fotograma **la barra no cruzaba nada** — la lámina decía
           * lo contrario de lo que su rótulo afirmaba. Debajo de la raya no
           * tapa nada: ahí sólo hay masa sin información.
           *
           * Y el cuerpo cede antes que el texto, que es la regla de la casa —
           * una etiqueta de 26 caracteres baja de cuerpo en vez de salirse.
           */}
          <div
            style={{
              position: "absolute",
              left: EJE.x,
              top: yUmbral + 14,
              maxWidth: EJE.barra,
              padding: "8px 20px",
              backgroundColor: color.richBlack,
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoQueCabe({
                ancho: EJE.barra - 40,
                largo: umbral.etiqueta.length,
                registro: "anton",
                pista: 0.06,
                tope: 34,
              }),
              letterSpacing: "0.06em",
              whiteSpace: "nowrap",
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
