import React from "react";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe, masLarga } from "../brand/medida";
import { color, duration, ease, readingFrames } from "../brand/tokens";
import { MotionSound } from "./MotionSound";
import type { Motion } from "../brand/sfx";

/**
 * **Casillas iguales a escuadra, y lo que le pasa a cada una: se queda, se tacha
 * o se sella.**
 *
 * Es la lámina que la biblioteca cerrada dejó sin construir. Jaime, 6-9-2026:
 * *«las figuras que estás haciendo están horribles; hasta que no tengamos una
 * biblioteca de figuras decentes no las vamos a utilizar. **Gráficos y palabras,
 * como tablero de clase**, por el momento»*. Cerradas `figuras.json` y
 * `volumenes.json`, un panel se quedó sin nada que dibujar: los cuatro de
 * reel-04 salían como bloques negros de texto apilados en una esquina, tres
 * formas declaradas distintas —`tachadura`, `tira-de-dias`, `filtro`— con el
 * mismo aspecto, porque `cubre: panel` tira el `kind` y sólo deja los textos.
 *
 * Esto es el otro medio de la instrucción, el que no existía: **tipografía y
 * geometría plana a escuadra**. Una línea recta que cruza y un bloque que pasa a
 * oro no son ilustración — son las dos cosas que hace un profesor en una pizarra
 * cuando descarta y cuando subraya.
 *
 * ## Qué afirma
 *
 * Una serie de unidades iguales de la que **una** se señala. Sirve a cualquier
 * pieza del lote: los síntomas que se van descartando, el filtro con dos salidas
 * —una para usted, la otra no—, la tira de días con la fecha marcada, la lista
 * de requisitos que se cumplen. Si aparece un `if (slug === …)` aquí dentro, es
 * que falta un prop.
 *
 * ## Las reglas que obedece, y de dónde salen
 *
 * - **Un solo acento.** Sólo una casilla puede llevar `sella`, y lanza si hay
 *   dos: *«si en un tablero hay tres cosas en oro, dos sobran»*.
 * - **Se construye mientras se habla.** Cada casilla entra cuando la anterior se
 *   pudo leer, y se resuelve cuando entra la siguiente: el espectador ve *cómo*
 *   se cae, que es lo que un carrusel no puede hacer.
 * - **La tacha se traza**, lineal y de izquierda a derecha. Puesta de golpe no
 *   tacha nada: se lee como una frase con una raya encima.
 * - **El negro sólo bajo lo que hay que leer.** Cada casilla es su propia masa;
 *   no hay faja de borde a borde.
 * - **Sin rebote.** `ease.out` o `ease.linear`, que es lo único que el sistema
 *   admite.
 * - **El sonido va en el frame del movimiento**, emitido desde aquí: la línea se
 *   traza y suena el trazo, el sello aterriza y suena el golpe.
 *
 * ## Lo que NO hace
 *
 * No dibuja fondo ni se coloca sola: es una figura pura, como `Reparto`, y la
 * sitúa quien la hospeda —`SidePanel` en el hueco libre del plano—. Así la misma
 * lámina vale para el panel y para un tablero a pleno sin duplicarse.
 * @clase tablero
 */
export type Casilla = {
  /**
   * Lo que se lee dentro. **Vacío es una unidad anónima**: la tira de días del
   * canon son casillas iguales «sin números salvo uno», y ahí la casilla no
   * dice, cuenta.
   */
  texto?: string;
  /** Se tacha: una línea recta la cruza y el bloque baja de tono. */
  tacha?: boolean;
  /** Se sella: pasa a oro con el texto en negro. **Sólo una por lámina.** */
  sella?: boolean;
  /**
   * **Cuándo se resuelve, en frames desde el arranque de la lámina.**
   *
   * Lo pone `scripts/reels/tableros.mjs :: _cuandoSeDice` buscando en los
   * subtítulos de hoy el `ancla` que declaró quien compone: la casilla se tacha
   * o se sella **cuando se dice**, no cuando toca por tiempo de lectura. Sin
   * esto la lámina se monta sola y se queda quieta mientras la voz sigue.
   */
  en?: number;
  /** El texto del subtítulo con el que se resuelve. Lo lee el spec, no esto. */
  ancla?: string;
  /** El dueño del que sale su texto. Lo resuelve `reels/paneles.mjs`. */
  dato?: string;
};

export type CasillasProps = {
  casillas: Casilla[];
  /**
   * `columna` apila —una lista que se descarta—; `fila` pone la serie de lado —
   * una tira de unidades iguales—. Lo decide qué se está contando, no el gusto.
   */
  eje?: "columna" | "fila";
  /** Ancho disponible en px. Lo pone quien la hospeda. */
  ancho: number;
  /** Frame en que entra la primera. */
  desde?: number;
  /** El movimiento con el que entra cada casilla. `null` para que no suene. */
  sfx?: Motion | null;
  alinea?: "izq" | "der";
};

/** Alto de una casilla con texto dentro, y de una unidad anónima de la tira. */
const ALTO = 96;
const ALTO_UNIDAD = 64;

/** El filete que separa dos casillas. Un filete, no un hueco. */
const FILETE = 2;

/** Lo que tarda la línea en cruzar. Corta: es un tachón, no una animación. */
const TACHA = 9;

/** Grosor de la tacha. Un `line-through` se escala con la fuente y se pierde. */
const RAYA = 7;

/** Lo que tarda en entrar una unidad anónima: no hay nada que leer. */
const PASO_UNIDAD = 5;

export const Casillas: React.FC<CasillasProps> = ({
  casillas,
  eje = "columna",
  ancho,
  desde = 0,
  sfx = null,
  alinea = "der",
}) => {
  const entra = useEntrada();
  const sellos = casillas.filter((c) => c.sella).length;
  if (sellos > 1) {
    throw new Error(
      `Casillas: ${sellos} casillas marcadas «sella» y el oro sólo señala una.` +
        " El canon: si hay tres cosas en oro, dos sobran.",
    );
  }
  for (const c of casillas)
    if (c.texto) assertShort(c.texto, "label", "Casillas.texto");

  const fila = eje === "fila";
  // **Cada casilla entra cuando la anterior se pudo leer, y una unidad sin
  // texto no se lee: se cuenta.** Repartir a intervalos iguales deja unas
  // ilegibles y otras muertas.
  // En la tira ninguna casilla se lee —el texto va en el sello de encima—, así
  // que la serie se traza y no se deletrea: siete días son siete cuadrados.
  const paso = (c: Casilla) =>
    !fila && c.texto ? readingFrames(c.texto) : PASO_UNIDAD;
  // **Y se resuelve cuando se dice, si el spec resolvió su ancla.** El cursor de
  // resoluciones es monótono a propósito: con una casilla anclada tarde y la
  // siguiente sin ancla, la segunda se tachaba ANTES que la primera y la lista
  // dejaba de leerse como una secuencia.
  const horario: { entra: number; resuelve: number }[] = [];
  // **Una casilla anclada que no se tacha solo puede querer decir una cosa:
  // que entra cuando se dice** (C-474). El `en` sólo movía la resolución, así
  // que en reel-14 e5 —cuatro casillas ancladas a «país», «corporativo»,
  // «quién» y «crecer», ninguna tachada— la lista entera estaba montada a
  // 48,8 s, ocho segundos antes de que la voz la acabara. Con una sola así, la
  // lámina entra con la voz; la lista que se tacha según se nombra no cambia.
  const conVoz = casillas.some((c) => typeof c.en === "number" && !c.tacha && !c.sella);
  let t = desde;
  // **En la tira, primero está la serie entera y después se sella.** Un sello
  // que cae con la mitad de los días todavía por trazar no marca un día de una
  // serie: marca el final de lo que se estaba dibujando.
  let r = eje === "fila"
    ? desde + casillas.length * PASO_UNIDAD + duration.entry
    : desde;
  for (const c of casillas) {
    const conSuPalabra = conVoz && typeof c.en === "number";
    // **Entra en su palabra, no antes** (C-480): arrancar la entrada 0,4 s antes
    // del ancla dejaba «CRECER CON ESTRATEGIA» entera en pantalla con el
    // subtítulo todavía en «usted tiene que conocer las».
    const entraEn = conSuPalabra ? Math.max(t, desde + (c.en as number)) : t;
    t = entraEn + paso(c);
    // **Y la que entra con su palabra se resuelve con ella, no una lectura
    // después** (C-477): en reel-14 e5 el sello de «crecer» caía tras el final
    // de la etapa. La sellada entra ya en oro.
    r = conSuPalabra
      ? Math.max(r, entraEn)
      : Math.max(r, t, typeof c.en === "number" ? desde + c.en : 0);
    horario.push({ entra: entraEn, resuelve: r });
    r += TACHA;
  }

  const paso1 = fila ? Math.floor(ancho / casillas.length) : ancho;
  const alto = fila
    ? ALTO_UNIDAD
    : Math.max(...casillas.map((c) => (c.texto ? ALTO : ALTO_UNIDAD)));
  // **Un cuerpo para toda la lámina, el del renglón más largo.** Ajustando cada
  // casilla por su cuenta, «AHORRO» salía al doble que «SIN REGISTROS LIMPIOS»
  // y la pila dejaba de leerse como una lista: seis palabras del mismo peso
  // dichas con seis voces. Es la misma cuenta que ya hace `SidePanel`.
  const cuerpo = cuerpoQueCabe({
    ancho: paso1 - 44,
    largo: masLarga(casillas.map((c) => c.texto ?? "")),
    registro: "anton",
    tope: 62,
  });
  const sellada = casillas.findIndex((c) => c.sella);
  const textoSello = sellada >= 0 ? (casillas[sellada].texto ?? "") : "";
  // En la tira el sello va ENCIMA de la unidad marcada y no dentro: la casilla
  // mide 64 px y la fecha no cabe ahí sin bajar del suelo de legibilidad. La
  // tira queda entera debajo, que es lo que hace ver que es un día de una serie.
  const SELLO = fila && textoSello ? 84 : 0;
  const arriba = SELLO ? SELLO + FILETE * 3 : 0;

  return (
    <div
      style={{
        position: "relative",
        width: ancho,
        height: (fila ? alto : casillas.length * (alto + FILETE)) + arriba,
        marginBottom: 18,
        alignSelf: alinea === "der" ? "flex-end" : "flex-start",
      }}
    >
      {casillas.map((c, i) => {
        const p = entra(horario[i].entra, duration.entry);
        if (p <= 0) return null;
        const q = c.tacha || c.sella
          ? entra(horario[i].resuelve, TACHA, ease.linear)
          : 0;
        // El día marcado también pasa a oro: es lo que ata el bloque de la
        // fecha a su casilla y hace ver que es UNO de la serie.
        const oro = c.sella && q > 0.5;
        return (
          <div
            key={`c${i}`}
            style={{
              position: "absolute",
              left: fila ? i * paso1 : 0,
              top: arriba + (fila ? 0 : i * (alto + FILETE)),
              width: paso1 - FILETE,
              height: alto,
              backgroundColor: oro
                ? color.gold
                : c.tacha && q > 0.9
                  ? color.navy
                  : color.navyHi,
              opacity: p,
              // Entra desde su lado y se queda. Nunca rebote.
              transform: `translateX(${((1 - p) * (alinea === "der" ? 60 : -60)).toFixed(1)}px)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
            }}
          >
            {c.texto && !fila ? (
              <span
                style={{
                  fontFamily: fontFamily.bloque,
                  fontSize: cuerpo,
                  lineHeight: 1,
                  letterSpacing: "0.01em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  color: oro
                    ? color.richBlack
                    : c.tacha && q > 0.9
                      ? color.secondaryBlue
                      : color.lightNeutral,
                }}
              >
                {c.texto}
              </span>
            ) : null}
            {/* **La tacha: una barra que cruza, no un `line-through`.** Y va en
                claro, no en oro: mirando el fotograma salían cuatro rayas de
                oro y un sello de oro en la misma esquina, o sea cinco cosas
                diciendo «mira aquí». Lo que hay que mirar es lo que queda. */}
            {c.tacha ? (
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: `${(alto - RAYA) / 2}px`,
                  height: RAYA,
                  width: `${(q * 100).toFixed(1)}%`,
                  backgroundColor: color.lightNeutral,
                  opacity: 0.92,
                }}
              />
            ) : null}
          </div>
        );
      })}

      {/* **El sello de la tira: un bloque de oro ENCIMA de la unidad marcada.**
          En la tira las casillas son iguales y sin números; lo que la marca es
          este bloque, que se sella sobre ella y es lo único que se lee. */}
      {SELLO ? (
        <div
          style={{
            position: "absolute",
            left: Math.min(
              Math.max(0, (sellada + 0.5) * paso1 - ancho * 0.33),
              ancho - ancho * 0.66,
            ),
            top: 0,
            width: ancho * 0.66,
            height: SELLO,
            backgroundColor: color.gold,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: entra(horario[sellada].resuelve, duration.entry),
            // Se sella: baja sobre el día y se queda. Sin rebote.
            transformOrigin: "bottom",
            transform: `scaleY(${entra(horario[sellada].resuelve, duration.entry).toFixed(3)})`,
          }}
        >
          <span
            style={{
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoQueCabe({
                ancho: ancho * 0.66 - 28,
                largo: textoSello.length,
                registro: "anton",
                tope: 64,
              }),
              lineHeight: 1,
              letterSpacing: "0.01em",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              color: color.richBlack,
            }}
          >
            {textoSello}
          </span>
        </div>
      ) : null}

      {/* **El sonido sigue al movimiento y se emite desde aquí**, que es lo
          único que conoce el frame exacto: la casilla entra con el movimiento
          que declaró quien compone, la línea se traza y el sello aterriza. */}
      {sfx
        ? casillas.map((_c, i) => (
            <MotionSound key={`s${i}`} motion={sfx} at={horario[i].entra} />
          ))
        : null}
      {casillas.map((c, i) =>
        c.tacha ? (
          <MotionSound key={`t${i}`} motion="draw" at={horario[i].resuelve} />
        ) : null,
      )}
      {casillas.map((c, i) =>
        c.sella ? (
          <MotionSound key={`l${i}`} motion="land" at={horario[i].resuelve} />
        ) : null,
      )}
    </div>
  );
};
