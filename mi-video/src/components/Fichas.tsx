import React from "react";
import { AbsoluteFill } from "remotion";
import { useEntrada } from "../brand/horario";
import { franja } from "../brand/franja";
import { color, layout, readingFrames } from "../brand/tokens";
import { Fondo, type Recorte } from "./Fondo";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";
import { leerDeclarado } from "./declarado/lineas";
import { Ficha, FileteFicha } from "./fichas/Ficha";

/**
 * **Bloques planos apilados y separados por filetes.** Cuatro formas declaradas
 * eran ésta con otro nombre.
 *
 * `conectado.py` las contaba una a una —`BandaFecha`, `ListaNumerada`,
 * `EvidenceCard` y la ficha de casos de reel-05 e2— y las cuatro pedían lo
 * mismo en su encargo: *«tarjeta de tres filetes apilados»*, *«tres líneas
 * numeradas que entran una a una»*, *«ficha de dato… separadas por filetes»*,
 * *«dos fichas rectangulares que entran en diagonal desde el borde derecho»*.
 * Escribir cuatro componentes para eso es cuatro sitios donde el filete acaba
 * midiendo distinto.
 *
 * Lo que cambia entre ellas cabe en dos declaraciones y las dos vienen del
 * diseño, no de un `if` por pieza:
 *
 * - **`numerada`** — la lista lleva 01, 02, 03 delante. Lo dice la forma.
 * - **`condiciones_en_fila`** — las fichas que no son la de oro se ponen en una
 *   fila separadas por filetes verticales, y la de oro ocupa el bloque grande
 *   debajo. Es la anatomía de la ficha de dato del canon.
 *
 * ## Por qué lee los props en crudo
 *
 * Porque el copy es del diseñador y llega con los nombres que él le puso
 * —`donde`, `utilidad`, `horquilla`, `lineas`, `filas`— y cerrar aquí un
 * esquema convertiría el catálogo de props en el techo del diseño. Las reglas
 * de lectura viven en [`declarado/lineas`](./declarado/lineas.ts) y son las
 * mismas para todas las formas declaradas: orden de declaración, jerarquía por
 * longitud, un solo oro y nada dicho dos veces.
 * @clase tablero
 */
export type FichasProps = {
  /** Lo que declaró el diseñador, tal cual. Ver `declarado/lineas`. */
  props: Record<string, unknown>;
  /** `01 · 02 · 03` delante de cada ficha. Lo pide `ListaNumerada`. */
  numerada?: boolean;
};

export const Fichas: React.FC<FichasProps> = ({ props, numerada = false }) => {
  const entra = useEntrada();
  const { cuerpo } = leerDeclarado(props);
  if (!cuerpo.length) return null;

  const placa = typeof props.placa === "string" ? props.placa : undefined;
  const recorte = (typeof props.recorte === "string"
    ? props.recorte
    : "lleno") as Recorte;
  const suelo = props.fondo === "navy" ? color.navy : color.richBlack;
  const enFila = props.condiciones_en_fila === true;
  const suena = props.sound === true;
  const golpe = (["mark", "draw", "fork", "land", "type"] as const).find(
    (m) => m === props.sfx,
  ) ?? "land";

  /**
   * **Cada ficha entra cuando la anterior se pudo leer.** Repartir a intervalos
   * iguales deja unas ilegibles y otras muertas; repartir por tiempo de lectura
   * hace que el tablero respire solo. Es la regla del canon, no un número
   * redondo.
   */
  const entradas: number[] = [];
  let t = 0;
  for (const l of cuerpo) {
    entradas.push(t);
    t += Math.max(14, readingFrames(l.texto));
  }

  const ancho = layout.width - layout.safe.left - layout.safe.right;
  // **Sin reserva de pie.** Se guardaban 150 px al fondo de la lámina para la
  // banda de fuente y condición; desde que el pie vive fuera de la zona segura
  // (`PieTablero.tsx`) ese hueco es de las fichas, que es lo que hay que leer.
  const alto = franja.techoPx - 150;
  const oro = cuerpo.findIndex((l) => l.oro);
  const fila = enFila ? cuerpo.filter((_l, i) => i !== oro) : [];
  const apiladas = enFila ? cuerpo.filter((_l, i) => i === oro) : cuerpo;
  const altoFila = enFila && fila.length ? 150 : 0;
  /**
   * **Una ficha no crece hasta llenar el hueco.** Repartir el alto útil entre
   * dos fichas da bloques de 448 px con dos renglones dentro y el resto navy:
   * eso no es un bloque plano, es un fondo. El tope deja la pila centrada y con
   * aire alrededor, que es como se apilan en las láminas.
   *
   * La excepción es la ficha sola: cuando el resto de condiciones se ha ido a
   * la fila de arriba, la que queda **es** el dato —*«debajo, ocupando media
   * pantalla, en oro»*, dice el encargo de reel-06 e5— y ahí sí manda el hueco.
   */
  const reparto = Math.floor(
    (alto - altoFila - (apiladas.length - 1) * 2) / Math.max(1, apiladas.length),
  );
  const altoBloque = Math.min(reparto, apiladas.length === 1 ? 420 : 240);

  return (
    <AbsoluteFill style={{ backgroundColor: suelo }}>
      {/* El fondo ocupa el cuadro entero: lo que se recorta a la franja es el
          CONTENIDO, que es lo que hay que leer. Ver `ZonaTablero`. */}
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.9} deriva={t + 90} />
      ) : null}

      {/* **El sonido sigue al movimiento, y el movimiento lo declara el
          encargo.** reel-05 e2 pide *«un golpe seco de pegado por cada ficha
          que aterriza»*: eso es `land` en las dos, no `land` y luego otra cosa
          porque el bucle empiece a contar. */}
      {suena
        ? entradas.map((f, i) => (
            <MotionSound key={cuerpo[i].texto} motion={golpe} at={f} />
          ))
        : null}

      <ZonaTablero>
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            top: 150,
            width: ancho,
            // La pila se centra en lo que queda entre la cabecera y el pie: sin
            // esto se pegaba arriba y dejaba un tercio de cuadro muerto.
            height: alto,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "stretch",
          }}
        >
          {/* Las condiciones en fila: bloques cortos separados por filetes
              verticales, que es como el canon pone un pie de tabla. */}
          {fila.length ? (
            <div style={{ display: "flex", height: altoFila, marginBottom: 2 }}>
              {fila.map((l, i) => (
                <React.Fragment key={l.texto}>
                  {i ? <FileteFicha vertical largo={altoFila} /> : null}
                  <div style={{ flex: 1, display: "flex" }}>
                    <Ficha
                      linea={l}
                      alto={altoFila}
                      ancho={Math.floor(ancho / fila.length) - 2}
                      progreso={entra(entradas[cuerpo.indexOf(l)])}
                      alterna={i % 2 === 1}
                    />
                  </div>
                </React.Fragment>
              ))}
            </div>
          ) : null}

          {apiladas.map((l, i) => (
            <React.Fragment key={l.texto}>
              {i ? <FileteFicha largo={ancho} /> : null}
              <Ficha
                linea={l}
                indice={numerada ? cuerpo.indexOf(l) + 1 : undefined}
                alto={altoBloque}
                ancho={ancho}
                progreso={entra(entradas[cuerpo.indexOf(l)])}
                alterna={i % 2 === 1}
              />
            </React.Fragment>
          ))}
        </div>

      </ZonaTablero>
    </AbsoluteFill>
  );
};
