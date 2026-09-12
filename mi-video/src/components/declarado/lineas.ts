import { limit } from "../../brand/copy";
import CIFRAS from "../../../scripts/reels/cifras.json";

/**
 * **Lo que el diseñador declaró, leído como líneas de copy.**
 *
 * Vivía dentro de `TableroDeclarado`, que era el único que lo necesitaba
 * mientras diecinueve formas caían allí. Ahora las formas tienen componente
 * propio —`Fichas`, `Anidado`, `Fusion`, `Desvio`— y las cinco reglas de
 * lectura son las mismas para todas: si se copian, divergen, y entonces la
 * misma declaración se dibuja distinta según quién la lea.
 *
 * Las reglas, y ninguna interpreta el contenido:
 *
 * - **Un texto por línea, en orden de declaración.** El diseñador escribe los
 *   props en el orden en que se leen.
 * - **La jerarquía sale de la longitud**: lo corto va grande en versales, lo
 *   largo en cuerpo de lectura.
 * - **El oro es uno solo.** Lo dice `props.oro`; si no coincide con nada, se le
 *   da al primer texto corto.
 * - **Nada se dice dos veces**, tampoco aquí: se compara sin tildes ni signos y
 *   se cae la línea contenida en otra.
 * - **Lo que es motor no es copy.** `duracion`, `sfx`, `camara`, `placa` y
 *   compañía las escribe quien compone para que las lea el render, no la
 *   pantalla. El «430» rotulado en reel-01 salió por ahí.
 */

/**
 * **Props que son estructura, no texto en pantalla**, de la MISMA lista que
 * lee quien cuenta las cifras (`scripts/reels/cifras.json`). Aquí había una
 * copia a mano: se separaron, y la ventana de reel-08 e2 —que esta lista ya
 * callaba— salió como cuatro cifras sin respaldo en el otro lado (C-427).
 * `duracion` la mete el motor; `sfx`, `sonidos`, `sujeto*` y compañía los
 * escribe quien compone para el render: el «430» de reel-01 y el MARK/LAND de
 * reel-08 v1 salieron por aquí.
 */
const NO_ES_TEXTO = new Set<string>(CIFRAS.no_es_texto);

/**
 * **Y lo de motor no se aplana, venga como venga.** Un objeto bajo una clave de
 * motor —`ventana: {entra_con, desde…}`, `sonidos: {…}`, `anclas: {…}`— es
 * datos, no copy. Las listas sí se leen: `lineas` y `palabras` son texto.
 */
export const esMotor = (k: string, v: unknown) =>
  NO_ES_TEXTO.has(k) && !Array.isArray(v);

/**
 * **Lo que se dice al pie, y que este tablero ya no dibuja.**
 *
 * Fuente y condición son cumplimiento, pero desde la instrucción de Jaime del
 * 6-9-2026 van **fuera de la zona segura y en una línea**, así que las monta
 * `dibujaTablero` con `PieTablero` para las 24 láminas. Aquí sólo hay que
 * saber cuáles son para **no rotularlas como copy**: `TableroDeclarado` pinta
 * lo que no reconoce, y sin esta lista una nota de método de cien palabras
 * entraba en el cuerpo del tablero.
 */
const AL_PIE = new Set([
  "pie", "source", "fuente", "condicion", "condition", "limitation", "legal",
]);

export type Linea = {
  texto: string;
  /** Rótulo corto que encabeza la ficha, si el diseño declaró el par. */
  etiqueta?: string;
  grande: boolean;
  oro: boolean;
};

export type Declarado = { cuerpo: Linea[] };

/** Aplana un valor declarado a las líneas de texto que lleva dentro. */
export const aLineas = (v: unknown, prof = 0): string[] => {
  if (prof > 2) return [];
  if (typeof v === "string") return v.trim() ? [v.trim()] : [];
  if (typeof v === "number") return [String(v)];
  if (Array.isArray(v)) return v.flatMap((x) => aLineas(x, prof + 1));
  if (v && typeof v === "object")
    return Object.entries(v as Record<string, unknown>)
      .filter(([k]) => !NO_ES_TEXTO.has(k))
      .flatMap(([, x]) => aLineas(x, prof + 1));
  return [];
};

/** Sin tildes ni signos: «Vender más.» y «VENDER MAS» son la misma línea. */
const limpio = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ").trim();

/**
 * **El par etiqueta/texto, cuando el diseño lo declara.**
 *
 * `filas: [{ etiqueta: "REALTOR", texto: "TRES CASAS EN UN TRIMESTRE" }]` es lo
 * que pide una ficha del canon: el oficio arriba en cuerpo pequeño y el hecho
 * debajo en versales. Aplanado a dos líneas sueltas se pierde el par, que es
 * justo lo que la ficha significa.
 */
const esFila = (v: unknown): v is { etiqueta?: string; texto: string } =>
  !!v && typeof v === "object" && !Array.isArray(v) &&
  typeof (v as { texto?: unknown }).texto === "string";

export const leerDeclarado = (props: Record<string, unknown>): Declarado => {
  const cuerpo: Linea[] = [];
  const quiereOro = String(props.oro ?? "").toLowerCase();

  const mete = (texto: string, etiqueta?: string) => {
    if (texto.length > limit.legal) return;
    cuerpo.push({ texto, etiqueta, grande: texto.length <= limit.label, oro: false });
  };

  for (const [k, v] of Object.entries(props)) {
    if (AL_PIE.has(k)) continue;
    if (Array.isArray(v) && v.some(esFila)) {
      for (const f of v) if (esFila(f)) mete(f.texto.trim(), f.etiqueta?.trim());
      continue;
    }
    if (esFila(v)) {
      mete(v.texto.trim(), v.etiqueta?.trim());
      continue;
    }
    if (esMotor(k, v)) continue;
    for (const t of aLineas(v)) mete(t);
  }

  // **Nada se dice dos veces.** Aplanar los props repite texto en cuanto dos
  // campos comparten palabras: el `BeliefSwap` de reel-01 salió con «VENDER
  // MÁS» arriba y «VENDER MÁS» tres líneas más abajo, en el mismo tablero.
  const visto: string[] = [];
  const unicas = cuerpo.filter((l) => {
    const c = limpio(l.texto);
    if (!c) return false;
    if (visto.some((x) => x === c || x.includes(c) || c.includes(x))) return false;
    visto.push(c);
    return true;
  });

  // **El oro es uno.** Lo declarado si coincide con alguna línea; si no, el
  // primer texto corto, que es el que hace de ancla.
  //
  // **Y puede no haber ninguno.** `oro: false` es una declaración, no un hueco:
  // el encargo de reel-05 e2 dice *«sin oro: aquí no hay nada que mirar
  // todavía»*, y ése es el trabajo del beat — poner cara a los casos antes de
  // que aparezca el dato. Sin esta salida, el respaldo doraba la primera ficha
  // y el tablero decía «mira aquí» donde el diseño dijo que no.
  //
  // **Y un `oro` declarado que no aparece NO se resuelve solo.** El respaldo
  // —dorar la primera línea corta— es para el que no declaró nada. Con él
  // corriendo siempre, el `oro: "fecha"` de reel-05 e9 no encontraba ninguna
  // fecha —el diseño no la escribe: la fecha se deriva (C-184)— y el oro caía
  // sobre «EN ESPAÑOL», que es oro decorativo, prohibido por nombre en el canon.
  //
  // Quitar el respaldo arregló eso y abrió el fallo por el otro lado: la lámina
  // salía **sin un solo acento**. Ahora no se elige por él ni se calla — se
  // lanza. Ver el bloque de abajo.
  const iOro = (() => {
    if (props.oro === false || quiereOro === "ninguno") return -1;
    if (quiereOro) {
      const i = unicas.findIndex((l) =>
        limpio(l.texto).includes(limpio(quiereOro).slice(0, 14)));
      /**
       * **Un `oro` que no apunta a ninguna línea deja el tablero sin acento, y
       * eso falla el render.**
       *
       * Hasta aquí caía en silencio —«si lo que hay que mirar no está en
       * pantalla, no hay nada que mirar»—, y el silencio produjo la lámina de
       * reel-05 e9: `oro: "fecha"` contra una única línea que decía «EN
       * ESPAÑOL», o sea **cero acentos** en una tarjeta de tres datos. El canon
       * lo dice por los dos lados: *«si en un tablero hay tres cosas en oro, dos
       * sobran»* y *«un tablero sin acento incumple la regla por el otro lado,
       * porque el ojo entra por donde puede»*.
       *
       * No hay respaldo a propósito: dorar la primera línea corta sería el
       * código eligiendo qué demuestra la lámina, que es editorial. Quien
       * compone escribe el texto exacto, o escribe `oro: false` —que es una
       * declaración y sigue pasando—.
       */
      if (i < 0 && unicas.length) {
        throw new Error(
          `Tablero declarado: \`oro: "${String(props.oro)}"\` no casa con ` +
            `ninguna de sus líneas (${unicas.map((l) => `«${l.texto}»`).join(", ")}), ` +
            `así que la lámina saldría sin un solo acento. El oro apunta al ` +
            `TEXTO exacto de la línea que el tablero demuestra; si esta lámina ` +
            `no tiene nada que señalar, decláralo \`oro: false\`.`,
        );
      }
      return i;
    }
    return unicas.findIndex((l) => l.grande);
  })();
  if (iOro >= 0) unicas[iOro].oro = true;

  return { cuerpo: unicas };
};
