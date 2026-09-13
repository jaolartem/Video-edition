import React from "react";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { color } from "../brand/tokens";
import { MotionSound } from "./MotionSound";

/**
 * **Cómo se reparte una cantidad, dicho con la cantidad y no con palabras.**
 *
 * El encargo lo escribe el paso de diseño y ya estaba escrito: reel-02 e1 pide
 * *«una barra horizontal de 100 unidades que se parte de un tajo: 54 hacia la
 * izquierda en azul pizarra apagado y 46 a la derecha en oro»*. Lo que salía en
 * pantalla eran tres bloques de texto —«DE CADA $100 QUE FACTURA», «SE VA $54»,
 * «LE QUEDA $46»— diciendo con letras lo que la figura tenía que hacer ver.
 *
 * Y ese es el fallo que Jaime señaló cuatro veces sin que cambiara nada: *«las
 * ilustraciones siguen siendo palitos y bolitas»*. No era desobediencia — la
 * figura **no existía en la biblioteca**, así que el encargo caía a texto. Su
 * regla, del 6-9-2026: *«hazlas genéricas para todo el lote, pero recuerda que
 * es responsabilidad del diseñador ampliar y construir la biblioteca para cada
 * video»*.
 *
 * ## Genérica, no de reel-02
 *
 * Sirve a cualquier reparto del lote —«de cada 100 dólares», un margen partido,
 * una jornada repartida— porque no sabe de qué habla: recibe un total, sus
 * porciones y cuál es la que importa. Si algún día aparece un `if (slug === …)`
 * aquí dentro, es que falta un prop.
 *
 * ## Las reglas que obedece, y de dónde salen
 *
 * - **Se construye mientras se explica.** Primero el riel entero, después el
 *   tajo, después cada porción con su cifra. Referencia suya del 6-9-2026
 *   (Veritasium): *«los gráficos son como los que se presentan acá»*, donde cada
 *   elemento aparece cuando se le nombra y no todos de golpe.
 * - **Un solo acento.** Sólo la porción marcada `foco` va en oro; el resto en
 *   azul secundario. El canon lo dice sin margen: si hay tres cosas en oro, dos
 *   sobran, y el oro deja de significar «mira aquí».
 * - **La cifra va SOBRE su porción**, no en un eje. Nadie lee un eje a 1,15x en
 *   vertical, y reducir la carga es el primero de los dos criterios que manda.
 * - **Entra sin rebote.** Nunca `Easing.back` ni `spring` con overshoot: *«nunca
 *   rebotando, siempre con entradas elegantes»*, y vale para todo lo que entra
 *   en pantalla, no sólo para las letras.
 * - **`source` es obligatorio** porque hay cifras rotuladas. El cumplimiento va
 *   en la API: no compila sin él, así que no se puede olvidar en la revisión.
 *
 * ## Lo que NO hace
 *
 * No dibuja el fondo ni se coloca sola: es una figura pura, como `Barra`, y la
 * sitúa quien la hospeda —un panel en el hueco libre o un tablero a pantalla—.
 * Así la misma figura vale para las dos familias sin duplicarse.
 */
export type Porcion = {
  /** Cuánto vale, en las mismas unidades que `total`. */
  valor: number;
  /**
   * Lo que se lee sobre la porción, en versales. **Opcional**: sin él la porción es sólo su
   * cifra — reel-15 e3 lo quitó para no tener dos oros y el render murió en
   * `assertShort(undefined)` (C-466).
   */
  rotulo?: string;
  /** La que importa. **Sólo una**: es la que se lleva el oro. */
  foco?: boolean;
};

/** Alto del riel, en px. Bastante para que la cifra quepa dentro y se lea. */
const ALTO = 132;

/** Hueco bajo la barra para el rótulo y, debajo, la fuente. */
const PIE = 92;

/** Hueco bajo la barra cuando sólo va el rótulo de cada porción. */
const ROTULO = 46;

/** Ancho del tajo entre porciones, en px. Un filete, no un hueco. */
const TAJO = 6;

/** Frames entre una porción y la siguiente. Una unidad cada vez para el ojo. */
const PASO = 11;

export const Reparto: React.FC<{
  /** El todo del que se reparte. Suele ser 100. */
  total: number;
  /** Las partes. Suman `total` o menos; lo que falte queda en hueco. */
  porciones: Porcion[];
  /** Ancho disponible, en px. Lo pone quien la hospeda. */
  ancho: number;
  /** Qué se antepone a cada cifra: «$», «%», o nada. */
  signo?: string;
  /** Frame en que empieza a trazarse el riel. */
  desde?: number;
  /** De dónde sale la cifra. Obligatorio: hay números en pantalla. */
  source: string;
  /**
   * La etiqueta del reparto entero: `SIN ESTRUCTURA`.
   *
   * Cuando quien la hospeda **ya imprime la fuente en su propio pie** —el panel
   * la lleva abajo, en la banda clara, para los dos repartos a la vez—, la línea
   * bajo la barra dice de qué caso es esta barra en vez de repetir la misma
   * atribución dos veces. `source` sigue siendo obligatorio: la cifra tiene que
   * poder rastrearse, y quien no imprima el pie la sigue viendo aquí.
   */
  etiqueta?: string;
  /**
   * **Si la figura dibuja su propia línea de atribución debajo.**
   *
   * Por defecto sí: quien la use suelta tiene que ver de dónde sale la cifra. Un
   * hospedador que ya imprime el pie —`SidePanel` lo lleva fuera de la zona
   * segura, en su banda— pasa `pie={false}` y entonces sólo se dibuja la
   * `etiqueta`, si la hay. Sin esto la misma atribución salía dos veces y, en el
   * panel, la segunda caía 190 px por debajo de la barra: justo sobre la cabeza.
   *
   * `source` sigue siendo obligatorio pase lo que pase: la cifra tiene que poder
   * rastrearse aunque la línea la dibuje otro.
   */
  pie?: boolean;
}> = ({ total, porciones, ancho, signo = "", desde = 0, source, etiqueta,
        pie = true }) => {
  const entra = useEntrada();
  // El riel se traza primero y entero: primero se ve el todo, después cómo se
  // parte. Al revés no hay reparto, hay dos barras que aparecen juntas.
  const riel = entra(desde, 14);
  const focos = porciones.filter((p) => p.foco).length;
  if (focos > 1) {
    throw new Error(
      `Reparto: ${focos} porciones marcadas «foco» y el oro sólo señala una.` +
        " El canon: si hay tres cosas en oro, dos sobran.",
    );
  }

  // Lo que va bajo la barra: la etiqueta si la hay, y si no la atribución —
  // salvo que la dibuje quien hospeda. Nada más, y entonces la figura tampoco
  // reserva el hueco: son 92 px que en un panel caen sobre la cabeza.
  const abajo = etiqueta ?? (pie ? source : null);

  let recorrido = 0;
  return (
    <div
      style={{
        position: "relative",
        width: ancho,
        height: ALTO + (abajo ? PIE : ROTULO),
      }}
    >
      {porciones.map((p, i) => {
        const w = (p.valor / total) * ancho;
        const x = recorrido;
        recorrido += w + TAJO;
        // Cada porción entra después de la anterior, y ninguna antes de que el
        // riel esté trazado del todo.
        const abre = entra(desde + 14 + i * PASO, 12);
        // **El porcentaje va detrás y con coma**: «53,53%», no «%53.53» —
        // `signo` se escribió para «$», que va delante (reel-15 e3, C-454).
        const cifra = signo === "%"
          ? `${String(p.valor).replace(".", ",")}%`
          : `${signo}${p.valor}`;
        return (
          <React.Fragment key={p.rotulo ?? `p${i}`}>
            <div
              style={{
                position: "absolute",
                left: x,
                top: 0,
                width: Math.max(w - TAJO, 0),
                height: ALTO,
                backgroundColor: p.foco ? color.gold : color.navyHi,
                // Crece desde su propio borde: la que se va, hacia la
                // izquierda; la que queda, hacia la derecha. El gesto dice de
                // qué lado cae cada una.
                transformOrigin: p.foco ? "right" : "left",
                transform: `scaleX(${abre})`,
                opacity: riel,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: x,
                top: 22,
                width: Math.max(w - TAJO, 0),
                textAlign: "center",
                fontFamily: fontFamily.bloque,
                fontSize: 84,
                lineHeight: 1,
                color: p.foco ? color.richBlack : color.lightNeutral,
                opacity: abre,
              }}
            >
              {cifra}
            </div>
            <div
              style={{
                position: "absolute",
                left: x,
                top: ALTO + 12,
                width: Math.max(w - TAJO, 0),
                textAlign: "center",
                whiteSpace: "nowrap",
                fontFamily: fontFamily.bloque,
                fontSize: 26,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: p.foco ? color.gold : color.secondaryBlue,
                opacity: abre,
              }}
            >
              {p.rotulo ? assertShort(p.rotulo, "label", "Reparto.porcion") : null}
            </div>
            {/* El tajo suena cuando se abre, no cuando la porción termina de
                crecer: el sonido va en el frame del movimiento. */}
            {i > 0 ? (
              <MotionSound motion="mark" at={desde + 14 + i * PASO} />
            ) : null}
          </React.Fragment>
        );
      })}
      {abajo ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: ALTO + 58,
            fontFamily: etiqueta ? fontFamily.bloque : fontFamily.data,
            fontSize: etiqueta ? 30 : 18,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: color.secondaryBlue,
            opacity: entra(desde + 14 + porciones.length * PASO, 12),
          }}
        >
          {abajo}
        </div>
      ) : null}
    </div>
  );
};
