import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, tracking, videoText } from "../brand/tokens";
import { Fondo, type Recorte } from "./Fondo";
import { ZonaTablero } from "./ZonaTablero";
import { leerDeclarado } from "./declarado/lineas";
import { useLienzo } from "../brand/LienzoContexto";

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
  const layout = useLienzo();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { cuerpo } = leerDeclarado(props);

  if (!cuerpo.length) return null;

  const tranquila = String(props.familia ?? "tranquila") !== "cargada";
  /**
   * **La placa de la pieza, en marcha, debajo de lo que es plano** (C-703). Una
   * forma declarada sin componente propio caía aquí sobre negro liso, y negro
   * liso es quieto: reel-23 e9 («CODE IS / CHEAP») fue lo único que emisión
   * siguió midiendo congelado cuando las fichas ya iban sobre la placa. La placa
   * llega en `props.placa` como a toda forma —la de la pieza, de respaldo— y
   * sólo va cuando el tablero ES el plano, nunca acompañando.
   */
  const placa = typeof props.placa === "string" ? props.placa : undefined;
  const recorte = (typeof props.recorte === "string" ? props.recorte : "lleno") as Recorte;

  /**
   * **`cubre` decide si el elemento ES el plano o lo acompaña, y lo dice el
   * diseñador.**
   *
   * Esto vivía en una vía aparte —`PANELES`, un literal escrito a mano— y por
   * eso llevaba cinco ciclos idéntico. `pleno` toma el cuadro; `panel` y
   * `banda` acompañan al plano sin taparle la cara.
   */
  const cubre = String(props.cubre ?? "pleno");
  /**
   * **Y `zona` dice dónde cae dentro del cuadro, que no es lo mismo.**
   *
   * `acompana` sólo puede ser cierto para un tablero que `repartirPorCubre`
   * mande aquí, y esa función manda `panel` y `banda` al `SidePanel`: la rama de
   * abajo estaba escrita y era **inalcanzable**. `zona` lleva declarada en el
   * cromo de `formas.mjs` desde que existe —*«dónde cae en el cuadro, sin tapar
   * la cara»*— y no la leía nadie, que es la avería de la casa.
   *
   * Con una sola línea, centrar la deja **sobre la boca**: medido en reel-05 e11,
   * el bloque de «EL LINK ESTÁ ABAJO» caía en el 29–35% de altura, que en un
   * primerísimo es la cara. `zona: "pie"` lo apoya en el suelo de la zona del
   * tablero —justo encima de la franja del subtítulo, nunca dentro— que es donde
   * el encargo lo pedía: *«al pie, el filete y EL LINK ESTÁ ABAJO»*.
   */
  const acompana = cubre === "panel" || cubre === "banda";
  const alPie = acompana || String(props.zona ?? "") === "pie";

  return (
    <AbsoluteFill
      style={{
        // La familia decide el fondo, y viene declarada: `cargada` deja ver el
        // plano, `tranquila` va sobre placa lisa para que las cifras se lean.
        // Acompañando **nunca** hay placa: taparía el plano que acompaña.
        background: acompana || !tranquila ? "transparent" : color.richBlack,
      }}
    >
      {placa && tranquila && !acompana ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.9} deriva={durationInFrames} />
      ) : null}
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
            justifyContent: alPie ? "flex-end" : "center",
            padding: `${layout.safe.top}px ${layout.safe.right}px ` +
              `${alPie ? 40 : 24}px ${layout.safe.left}px`,
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
                  /**
                   * **Ninguna línea se pinta sin su bloque plano detrás.**
                   *
                   * Sólo la de oro llevaba superficie; las demás iban en
                   * `lightNeutral` sobre `transparent`, o sea sobre el plano. Y
                   * el plano es lo que sea: en reel-05 e11 «SI PAGÓ DE MÁS SIN
                   * SABERLO» caía sobre la pared clara y el tablero blanco del
                   * fondo, y no se leía **nada** — texto claro sobre claro, que
                   * el canon prohíbe por su nombre.
                   *
                   * La legibilidad es criterio de diseño y no acabado, así que
                   * no puede depender de dónde cayera el encuadre. El negro va
                   * **sólo bajo lo que hay que leer** —el bloque abraza su
                   * texto, no hay faja de borde a borde— que es la lámina que
                   * Jaime aprobó.
                   */
                  padding: "6px 16px",
                  background: l.oro ? color.gold : color.richBlack,
                  alignSelf: layout.tablero.alinea,
                  maxWidth: "100%",
                }}
              >
                <span
                  style={{
                    fontFamily: l.grande ? fontFamily.bloque : fontFamily.video,
                    fontWeight: l.grande ? 400 : 800,
                    fontSize: (l.grande ? videoText.title : videoText.caption) *
                      layout.tablero.cuerpo,
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

          {/* **El pie ya no va aquí.** Fuera de la zona segura y en una
              línea, montado por `dibujaTablero`. Ver `PieTablero.tsx`. */}
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
