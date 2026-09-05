import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { Marco } from "./Canon";
import { Fondo, Cinta } from "./Fondo";
import type { Recorte } from "./Fondo";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { color, duration, ease, readingFrames } from "../brand/tokens";

/**
 * Lo que entra, la compuerta que atraviesa, y lo que sale distinto.
 * @clase tablero
 */
export type CompuertaProps = {
  /** Lo que va antes de la compuerta. */
  entra: string;
  /** La compuerta: lo que cambia el resultado. Es lo único en oro. */
  compuerta: string;
  /** Lo que sale al otro lado. */
  sale: string;
  /** Placa de `public/fondos/`. `r1-mecanismo` es literalmente esto. */
  /**
   * Como se recorta la placa. A cuadro completo va `lleno`.
   *
   * Estaba escrito a fuego aqui, y con eso la diagonal dejaba ver el VIDEO por
   * debajo — y lo que se ve depende de donde cayera el encuadre: en la sesion de
   * noche, las rodillas. Jaime: *«se ve feo ese tablero; mejor dejar el tablero
   * sin video»*.
   *
   * A `cubre: pleno` lo pone `armarTableros` en `lleno`: alli la placa ES el
   * plano. El valor de aqui es el respaldo para los que acompanan.
   */
  recorte?: Recorte;
  placa?: string;
  condicion?: string;
  duracion?: number;
};

/**
 * **El mecanismo: lo mismo entra y sale distinto, y en medio hay algo.**
 *
 * La pidieron dos piezas por su cuenta con la misma idea —«vender más» que
 * cruza «estructura» y sale como «quedar más»; el dinero que ya pasó y nadie
 * desvió— y ninguna figura del catálogo la dice: `bifurcacion` reparte en dos,
 * `escalera` acumula, `flecha` sólo apunta. Ninguna tiene el paso por algo.
 *
 * ## Y la imagen ya estaba hecha
 *
 * Jaime: *«que utilicen los fondos que ya existen, para generar texto encima de
 * ellos, como lo muestran los ejemplos de carruseles; no es reinventar la
 * rueda, es seguir la identidad gráfica»*.
 *
 * `r1-mecanismo` en `public/fondos/` es, palabra por palabra de su ficha, *«un
 * canal que lleva bloques hacia el punto de fuga y una derivación que se los
 * lleva fuera del cuadro»*. Es este tablero, fotografiado. Llevaba semanas en
 * el repositorio y el paso que componía no la había visto nunca — el pedido
 * mandaba las 26 láminas del canon, que son para mirar, y no las catorce
 * placas, que son las que se pueden usar.
 *
 * ## La anatomía es la de 03_Causal_Reveal/slide-04
 *
 * Placa a sangre detrás, dos paneles opacos girados encima —uno oscuro, uno en
 * oro—, y la cinta clara de remate abajo. Aquí los paneles son tres en fila
 * porque el argumento es una secuencia y no una comparación: **entra → pasa →
 * sale**, y el del medio es el único dorado porque es el único que explica.
 *
 * El orden de entrada es el argumento. Ver los tres a la vez es un esquema;
 * verlos aparecer en fila es un mecanismo — y por eso la compuerta entra
 * **después** de lo que la atraviesa y **antes** del resultado.
 */
export const Compuerta: React.FC<CompuertaProps> = ({
  entra,
  compuerta,
  sale,
  placa,
  recorte = "columna",
  condicion,
  duracion,
}) => {
  const frame = useCurrentFrame();
  assertShort(entra, "outcome", "Compuerta.entra");
  assertShort(compuerta, "label", "Compuerta.compuerta");
  assertShort(sale, "outcome", "Compuerta.sale");

  const total =
    duracion ?? readingFrames(entra) + readingFrames(sale) + 72;
  const tEntra = 0;
  const tCompuerta = tEntra + readingFrames(entra);
  const tSale = tCompuerta + duration.entry * 2;

  const p = (at: number) =>
    interpolate(frame, [at, at + duration.entry], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });

  /**
   * El raíl que une los tres. Se traza de arriba abajo y **llega antes que cada
   * bloque**: primero se ve por dónde va a pasar, luego pasa. Sin él son tres
   * cajas apiladas; con él son un recorrido.
   */
  const rail = interpolate(frame, [tEntra, tSale], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease.linear,
  });

  const bloque = (
    texto: string,
    at: number,
    dorado: boolean,
    giro: number,
  ) => {
    const o = p(at);
    return (
      <div
        style={{
          opacity: o,
          transform: `translateX(${((1 - o) * (dorado ? 30 : -30)).toFixed(1)}px)`,
          marginBottom: 18,
          alignSelf: dorado ? "flex-end" : "flex-start",
          maxWidth: "88%",
        }}
      >
        <Cinta
          tinte={dorado ? color.gold : color.navy}
          giro={giro}
          cuerpo={dorado ? 60 : 52}
          style={{
            color: dorado ? color.richBlack : color.lightNeutral,
            whiteSpace: "normal",
          }}
        >
          <span style={{ fontFamily: fontFamily.bloque }}>{texto}</span>
        </Cinta>
      </div>
    );
  };

  return (
    <Marco style={{ justifyContent: "center" }}>
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.9} deriva={total} />
      ) : null}

      {/* El raíl, detrás de los bloques y a la izquierda de todo. */}
      <div
        style={{
          position: "absolute",
          left: 62,
          top: "24%",
          width: 6,
          height: `${(rail * 46).toFixed(1)}%`,
          background: color.secondaryBlue,
        }}
      />

      {bloque(entra, tEntra, false, -1.6)}
      {bloque(compuerta, tCompuerta, true, 2.1)}
      {bloque(sale, tSale, false, -1.2)}

      {condicion ? (
        <div
          style={{
            marginTop: 22,
            opacity: p(tSale + duration.standard * 2),
            color: color.secondaryBlue,
            fontFamily: fontFamily.video,
            fontSize: 26,
            lineHeight: 1.25,
          }}
        >
          {condicion}
        </div>
      ) : null}
    </Marco>
  );
};
