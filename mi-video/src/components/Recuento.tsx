import React from "react";
import { AbsoluteFill } from "remotion";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe, masLarga } from "../brand/medida";
import { color, duration, ease, layout } from "../brand/tokens";
import { Cinta, Fondo, type Recorte } from "./Fondo";
import { MotionSound } from "./MotionSound";
import { Remate } from "./Remate";
import { ZonaTablero } from "./ZonaTablero";
import { CAJA, DER, IZQ, MEDIO, SUELO, altoDe, marcaEn } from "./recuento/caja";
import { horarioDe } from "./recuento/horario";
import { Cabecera, Condicion, Trazo } from "./recuento/piezas";

/**
 * **Cuántos hay de un lado y cuántos del otro, y para quién está hecho cada
 * lado.**
 *
 * La composición es la que Jaime aprobó el 6-9-2026 mirando `g2050.png` —*«esa
 * composición me encanta»*—: placa de collage a sangre, dos columnas con su
 * filete vertical, rótulos en cajas negras, la marca sola en oro como remate,
 * pie en una línea y las marcas entrando de una en una. Lo que cambió ese mismo
 * día es **lo que dice**, y son sus palabras:
 *
 * 1. *«en inglés no hay tantos, hay como cinco o seis»*. Las 63 marcas
 *    afirmaban una abundancia que no existe. Una cantidad dibujada dice algo y
 *    tiene que ser verdad, así que **la cantidad se declara** (`cuantos`) y ya
 *    no se deduce de la geometría: antes salían las que cupieran.
 * 2. *«abajo de las cinco o cuatro de inglés, su condición: para contadores y
 *    abogados expertos»*.
 * 3. *«podemos cerrar con esa antes de pasar a la siguiente: este 21, virtual,
 *    para emprendedores — que se note la diferencia»*.
 *
 * ## Y con eso el eje deja de ser el idioma
 *
 * Que es lo que la corrección persigue, y por qué no bastaba con bajar el
 * número: *«es un recurso escaso en todos los idiomas, y las del CRA es para
 * abogados y contadores únicamente… entonces no es para que los emprendedores lo
 * apliquen o lo sepan, siquiera»*. Inglés-contra-español desplaza el problema a
 * la traducción; **para-quién** lo deja donde está. Las dos columnas siguen,
 * porque son la forma; lo que las califica es nuevo.
 *
 * Con cinco contra una la desproporción se sigue viendo —es un 5:1— y no se
 * compensa la pérdida de espectáculo con otra cosa: la lámina queda más
 * callada, que es lo honesto.
 *
 * El oro sigue siendo la marca sola y sólo ella: las cabeceras van las dos en
 * claro, la condición hereda el azul de las marcas que califica y el cierre va
 * en cinta clara con `Remate`, que por defecto no dora.
 * @clase tablero
 */
export type RecuentoProps = {
  /** Titular del tablero: qué se está contando. Va en cinta, arriba. */
  titulo?: string;
  /** Cabecera de la columna que se llena. */
  muchos: string;
  /** Cabecera de la columna donde hay una sola marca. */
  uno: string;
  /**
   * **Cuántas marcas van bajo `muchos`, declaradas y no deducidas.**
   *
   * Es cumplimiento: una cantidad dibujada afirma igual que una cifra rotulada.
   * Por eso no tiene valor por defecto y falla el render si no viene — un
   * respaldo aquí sería el componente inventándose un número que nadie escribió.
   */
  cuantos: number;
  /** Para quién está hecho lo que hay. Un renglón por línea, bajo las marcas. */
  condicion?: string[];
  /** El contraste que cierra el tramo. Un renglón por línea, abajo. */
  cierre?: string[];
  /** La descripción del movimiento, para quien compone. Aquí no se dibuja. */
  entrada?: string;
  placa?: string;
  recorte?: Recorte;
  /** Lo que dura el hueco, en frames. Lo pone `armarTableros`. */
  duracion?: number;
  sound?: boolean;
};

/** Lo que el cierre deja libre por debajo, antes del techo de la franja. */
const CIERRE_ABAJO = 40;

/** El aire entre la última marca y la condición que la califica. */
const BAJO_LAS_MARCAS = 44;

export const Recuento: React.FC<RecuentoProps> = ({
  titulo,
  muchos,
  uno,
  cuantos,
  condicion,
  cierre,
  placa,
  recorte = "lleno",
  duracion = 420,
  sound = false,
}) => {
  const entra = useEntrada();

  if (titulo) assertShort(titulo, "title", "Recuento.titulo");
  assertShort(muchos, "label", "Recuento.muchos");
  assertShort(uno, "label", "Recuento.uno");
  for (const l of condicion ?? []) assertShort(l, "label", "Recuento.condicion");
  for (const l of cierre ?? []) assertShort(l, "label", "Recuento.cierre");
  // **Sin cantidad declarada no se dibuja nada.** Ver `cuantos`: el respaldo
  // sería el componente afirmando una cantidad que nadie escribió.
  if (!Number.isInteger(cuantos) || cuantos < 1) {
    throw new Error(
      `Recuento.cuantos tiene que ser un entero positivo y trae «${cuantos}».` +
        ` Las marcas AFIRMAN una cantidad, así que la declara quien compone.`,
    );
  }

  const t = horarioDe(duracion, cuantos);
  // El cierre es la cinta más ancha de la lámina y va con `nowrap`: si el
  // ajuste se queda corto no envuelve, se sale de la zona segura. La `holgura`
  // paga ese error irreducible en cuerpo, que es barato, y no en texto cortado.
  const cuerpoCierre = cuerpoQueCabe({
    ancho: layout.width - layout.safe.left - layout.safe.right,
    largo: masLarga(cierre ?? [""]),
    registro: "anton",
    relleno: 1.2,
    holgura: 1.06,
    tope: 92,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {/* **La placa, más apagada que en otras láminas, y es legibilidad.** A
          `fuerza: 0.7` la banda clara de `r2-horizontes` deja las marcas de
          `secondaryBlue` casi sin contraste. Y aquí no vale tapar —Jaime lo paró
          en C-253, *«la mitad del panel está inutilizado»*—: se baja la placa
          entera, que sigue a sangre y sigue dando el suelo. */}
      {placa ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.45} deriva={duracion} />
      ) : null}

      {sound ? (
        <>
          {/* El filete se traza: suena el trazo. */}
          <MotionSound motion="draw" at={t.filete} />
          {/* Y cada marca suena, porque cada marca es un movimiento: con cinco
              ya no hay ráfaga que tapar. Antes sonaba la fila entera. */}
          {Array.from({ length: cuantos }, (_, i) => (
            <MotionSound key={`m${i}`} motion="mark" at={t.primera + i * t.paso} />
          ))}
          {condicion?.length ? <MotionSound motion="mark" at={t.condicion} /> : null}
          {/* La que está sola aterriza, y es el remate del tablero. */}
          <MotionSound motion="land" at={t.uno} />
          {(cierre ?? []).map((l, i) => (
            <MotionSound key={`c${l}`} motion="mark" at={t.cierre + i * 8} />
          ))}
        </>
      ) : null}

      <ZonaTablero>
        {titulo ? (
          <div
            style={{
              position: "absolute",
              top: 120,
              left: layout.safe.left,
              right: layout.safe.right,
              display: "flex",
              justifyContent: "flex-start",
              opacity: entra(0),
              fontFamily: fontFamily.bloque,
            }}
          >
            <Cinta tinte={color.lightNeutral} giro={-1.6} cuerpo={48}>
              {titulo}
            </Cinta>
          </div>
        ) : null}

        {/* El filete que separa. Se traza de arriba abajo antes de que entre
            nada: primero está la raya, después se ve de qué lado cae cada cosa.
            Cuatro píxeles y no uno: el filete de un píxel del canon separa
            bloques que ya se tocan, y aquí lo que separa son dos columnas con
            aire en medio. A 1 px sobre la placa no se veía. */}
        <div
          style={{
            position: "absolute",
            left: MEDIO - 2,
            top: CAJA.filete,
            width: 4,
            height: (SUELO - CAJA.filete) * entra(t.filete, 14, ease.linear),
            backgroundColor: color.secondaryBlue,
          }}
        />

        <Cabecera texto={muchos} x={IZQ} p={entra(t.cabeceras)} />
        <Cabecera texto={uno} x={DER} p={entra(t.cabeceras)} />

        {Array.from({ length: cuantos }, (_, i) => {
          const { x, y } = marcaEn(IZQ, i);
          return (
            <Trazo
              key={`m${i}`}
              x={x}
              y={y}
              p={entra(t.primera + i * t.paso, duration.max)}
            />
          );
        })}

        {/* Y una sola, en oro, en el mismo sitio que la primera de la otra
            columna: se comparan sin mover el ojo. El resto de la columna se
            queda vacío, que es lo que hay que ver. */}
        <Trazo x={DER} y={CAJA.arriba} p={entra(t.uno)} oro />

        {condicion?.length ? (
          <Condicion
            lineas={condicion}
            x={IZQ}
            y={CAJA.arriba + altoDe(cuantos) + BAJO_LAS_MARCAS}
            p={entra(t.condicion)}
            tinte={color.secondaryBlue}
          />
        ) : null}

        {/* **El cierre: el contraste con el que se pasa a la etapa siguiente.**
            Cruza las dos columnas a propósito —no es de ninguna— y va abajo, que
            es donde se lee lo último. Cinta clara y no oro: el acento ya está en
            la marca sola, y *«si en un tablero hay tres cosas en oro, dos
            sobran»*. */}
        {cierre?.length ? (
          <div
            style={{
              position: "absolute",
              left: layout.safe.left,
              right: layout.safe.right,
              bottom: CIERRE_ABAJO,
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              gap: 10,
              fontFamily: fontFamily.bloque,
            }}
          >
            {cierre.map((l, i) => (
              <div key={l} style={{ opacity: entra(t.cierre + i * 8) }}>
                <Remate cuerpo={cuerpoCierre} giro={-1.6}>
                  {l}
                </Remate>
              </div>
            ))}
          </div>
        ) : null}
      </ZonaTablero>
    </AbsoluteFill>
  );
};
