import { limit } from "../../brand/copy";

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

/** Props que son estructura, no texto en pantalla. */
const NO_ES_TEXTO = new Set([
  // **`duracion` la mete el motor, no quien compone.** `armarTableros` la anade
  // a los props para saber cuanto dura el tablero, y esto la trataba como una
  // linea mas: el tablero del precio del reel-01 salia rotulando **«430»** en
  // versales, junto a $576 y $20. Un numero que nadie escribio, en el sitio
  // donde una cifra de mas es una cifra falsa.
  "duracion",
  // **Y las otras claves de motor, por la misma razon.** `sfx`/`sound` los pone
  // quien declara el movimiento que suena, `rotulo` es el texto del gancho que
  // lleva `BigTitle`, y `camara` la declaracion de plano. Ninguna es copy.
  "sfx", "rotulo", "camara", "motion",
  "familia", "zona", "cubre", "oro", "sound", "fondo", "filete", "source",
  "paso", "entrada", "giro", "placa", "cede_el_cuadro", "sin_pie", "anclas",
  // Los otros tres props de `Fondo`: declarar como se recorta la placa —lo que
  // separa el collage del papel pintado— habria rotulado «cuna» en versales.
  "recorte", "fuerza", "deriva",
  "ancla", "alinea", "a_la_vez", "no_rotular", "solo_si", "se_queda",
  "al_entrar_la_siguiente", "abajo_se_tacha", "sin_cifra_en_pantalla",
  "tachado", "corte", "eje", "saltos", "franja", "lastre", "suelo",
  "fondo_filetes", "filetes", "flecha", "universo", "capas", "escalones",
  "tramos", "marcas", "lineas", "palabras", "renglones", "condiciones_en_fila",
  "etiquetas", "figura",
  // **Y la condición que viaja para el copy del post, no para el frame.**
  // `condicion_completa` se escribe para acompañar la publicación; rotularla
  // metía cien palabras de nota de método dentro del tablero.
  "condicion_completa", "numerada", "ventana",
]);

/** Lo que se dice al pie: fuente y condición, que son cumplimiento. */
const AL_PIE = new Set(["source", "fuente", "condicion", "condition", "legal"]);

export type Linea = {
  texto: string;
  /** Rótulo corto que encabeza la ficha, si el diseño declaró el par. */
  etiqueta?: string;
  grande: boolean;
  oro: boolean;
};

export type Declarado = { cuerpo: Linea[]; pie: string[] };

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
  const pie: string[] = [];
  const quiereOro = String(props.oro ?? "").toLowerCase();

  const mete = (texto: string, etiqueta?: string) => {
    if (texto.length > limit.legal) return;
    cuerpo.push({ texto, etiqueta, grande: texto.length <= limit.label, oro: false });
  };

  for (const [k, v] of Object.entries(props)) {
    if (AL_PIE.has(k)) {
      pie.push(...aLineas(v));
      continue;
    }
    if (Array.isArray(v) && v.some(esFila)) {
      for (const f of v) if (esFila(f)) mete(f.texto.trim(), f.etiqueta?.trim());
      continue;
    }
    if (esFila(v)) {
      mete(v.texto.trim(), v.etiqueta?.trim());
      continue;
    }
    if (NO_ES_TEXTO.has(k) && !Array.isArray(v) && typeof v !== "object") continue;
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
  // **Y un `oro` declarado que no aparece deja el tablero sin oro.** El respaldo
  // —dorar la primera línea corta— es para el que no declaró nada. Con él
  // corriendo siempre, el `oro: "fecha"` de reel-05 e9 no encontraba ninguna
  // fecha —el diseño no la escribe: la fecha se deriva (C-184)— y el oro caía
  // sobre «EN ESPAÑOL», que es oro decorativo, prohibido por nombre en el canon.
  // Si lo que hay que mirar no está en pantalla, no hay nada que mirar.
  const iOro = (() => {
    if (props.oro === false || quiereOro === "ninguno") return -1;
    if (quiereOro) {
      return unicas.findIndex((l) =>
        limpio(l.texto).includes(limpio(quiereOro).slice(0, 14)));
    }
    return unicas.findIndex((l) => l.grande);
  })();
  if (iOro >= 0) unicas[iOro].oro = true;

  return { cuerpo: unicas, pie };
};
