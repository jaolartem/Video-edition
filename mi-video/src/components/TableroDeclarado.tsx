import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, layout, tracking, videoText } from "../brand/tokens";
import { ZonaTablero } from "./ZonaTablero";
import { leerDeclarado } from "./declarado/lineas";

/**
 * Dibuja **lo que el diseñador declaró**, sea cual sea la forma que le puso.
 *
 * Regla de Jaime, dicha hasta que la entendí: *«lo que hace el diseñador no
 * llega a renderizarse»*, *«el punto es que lo que sale del diseñador sea lo que
 * renderice»*.
 *
 * ## Para qué sigue existiendo
 *
 * Al abrir el catálogo de formas —*«las limitaciones de código se acaban de
 * inmediato»*— los diseñadores montaron 38 tableros con 23 formas. `Ad.tsx`
 * sabía dibujar **cuatro**, así que 29 caían por el final del ternario y **no
 * salían en pantalla, sin decirlo**.
 *
 * Las siete que quedaban sin componente ya lo tienen —`Fichas`, `Anidado`,
 * `Fusion`, `Desvio`— y esto deja de ser el vertedero para ser lo que su nombre
 * dice: **la forma que se llama `TableroDeclarado` porque el diseño no quiso
 * ninguna otra**, dos frases planas con una en oro, y el respaldo de cualquier
 * forma nueva mientras no tenga la suya.
 *
 * ## Cómo decide qué dibujar, sin interpretar
 *
 * No sabe qué es un `Filtro` ni un `PieLink`. Las reglas de lectura viven en
 * [`declarado/lineas`](./declarado/lineas.ts) y son las mismas para todas las
 * formas declaradas: un texto por línea en orden de declaración, la jerarquía
 * por longitud, un solo oro y nada dicho dos veces.
 *
 * Lo que **no** hace es rellenar huecos. Un tablero sin textos no dibuja nada y
 * eso se ve, que es mejor que dibujar una caja vacía con pinta de tablero.
 * @clase tablero
 */
export type TableroDeclaradoProps = {
  /** El `kind` que puso el diseñador. Se usa para el diagnóstico, no para dibujar. */
  kind: string;
  props: Record<string, unknown>;
};

export const TableroDeclarado: React.FC<TableroDeclaradoProps> = ({
  props,
}) => {
  const frame = useCurrentFrame();
  const { cuerpo, pie } = leerDeclarado(props);

  if (!cuerpo.length) return null;

  const tranquila = String(props.familia ?? "tranquila") !== "cargada";

  /**
   * **`cubre` decide si el elemento ES el plano o lo acompaña, y lo dice el
   * diseñador.**
   *
   * Esto vivía en una vía aparte —`PANELES`, un literal escrito a mano— y por
   * eso llevaba cinco ciclos idéntico. `pleno` toma el cuadro; `panel` y
   * `banda` acompañan al plano sin taparle la cara.
   */
  const cubre = String(props.cubre ?? "pleno");
  const acompana = cubre === "panel" || cubre === "banda";

  return (
    <AbsoluteFill
      style={{
        // La familia decide el fondo, y viene declarada: `cargada` deja ver el
        // plano, `tranquila` va sobre placa lisa para que las cifras se lean.
        // Acompañando **nunca** hay placa: taparía el plano que acompaña.
        background: acompana || !tranquila ? "transparent" : color.richBlack,
      }}
    >
      {/**
       * **La franja del subtítulo no se toca, y aquí se hace imposible tocarla.**
       *
       * Esto reservaba `layout.safe.bottom + layout.captionBand` dentro de su
       * `padding`, que es el mismo número escrito por cuarta vez — y por eso
       * `Comparacion` y `Acumulacion` pudieron ignorarlo sin que nadie se
       * enterara. `ZonaTablero` lo recorta por construcción: lo que se salga se
       * ve cortado en el render, que es un fallo visible, en vez de irse bajo la
       * interfaz de la plataforma, donde el fallo es invisible.
       */}
      <ZonaTablero>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            justifyContent: acompana ? "flex-end" : "center",
            padding: `${layout.safe.top}px ${layout.safe.right}px ` +
              `${acompana ? 40 : 24}px ${layout.safe.left}px`,
            boxSizing: "border-box",
          }}
        >
          {cuerpo.map((l, i) => {
            // Cada línea entra cuando la anterior ya se pudo leer: 0,75 s por
            // bloque, que es la regla del canon, no un número redondo.
            const entra = i * Math.round(0.75 * 30);
            const o = interpolate(frame, [entra, entra + 8], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const dx = interpolate(frame, [entra, entra + 10], [-24, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={`${l.texto}-${i}`}
                style={{
                  opacity: o,
                  transform: `translateX(${dx}px)`,
                  marginBottom: l.grande ? 18 : 10,
                  padding: l.oro ? "6px 16px" : 0,
                  background: l.oro ? color.gold : "transparent",
                  alignSelf: "flex-start",
                  maxWidth: "100%",
                }}
              >
                <span
                  style={{
                    fontFamily: l.grande ? fontFamily.bloque : fontFamily.video,
                    fontWeight: l.grande ? 400 : 800,
                    fontSize: l.grande ? videoText.title : videoText.caption,
                    letterSpacing: l.grande ? tracking.display : 0,
                    textTransform: l.grande ? "uppercase" : "none",
                    color: l.oro ? color.richBlack : color.lightNeutral,
                    lineHeight: 1.05,
                  }}
                >
                  {l.texto}
                </span>
              </div>
            );
          })}

          {/* El pie lleva la fuente y la condición: cumplimiento, no adorno. */}
          {pie.length ? (
            <div style={{ marginTop: 24 }}>
              {pie.map((p) => (
                <div
                  key={p}
                  style={{
                    fontFamily: fontFamily.video,
                    fontWeight: 700,
                    fontSize: 30,
                    color: color.secondaryBlue,
                    lineHeight: 1.25,
                  }}
                >
                  {p}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </ZonaTablero>

      {/* **Aquí NO va el nombre de la forma.**

          Estaba, y con buena intención —«para que se vea qué falta
          construir»—, pero esto se dibuja en la pieza que se publica: las
          entregas del 5 de septiembre llevaban escritas en pantalla las
          palabras FUSION, DESVIO, LISTANUMERADA, EVIDENCECARD y ANIDADO,
          porque diecinueve formas declaradas caen aquí. Cinco de las siete
          piezas salieron con un rótulo de diagnóstico encima.

          El dato es útil y no se pierde: que una forma declarada no tenga
          componente es un cable suelto, y lo dice `scripts/conectado.py`, que
          corre al empezar cualquier sesión. Un informe se lee cuando toca; un
          rótulo en el frame se publica. */}
    </AbsoluteFill>
  );
};
