import type { Lienzo } from "../../brand/lienzo";
import type { ElEnElPlano } from "../ZonaTablero";
import type { Accion } from "./accion";

/**
 * **Dónde va él y dónde va el texto, leído del lienzo** (C-716).
 *
 * No se elige a ojo ni por formato: se prueban las composiciones que el cuadro
 * admite y gana la que deja al personaje más grande, que es el que actúa. Todas
 * acaban sobre la franja del subtítulo.
 *
 * - `lado` — él en su columna y el texto centrado en la otra. Sólo en un cuadro
 *   apaisado y si su escenario no necesita el ancho entero.
 * - `arriba` — el texto encima, sin pasar del 30 % del alto, y él debajo.
 * - `esquina` — el texto arriba a la izquierda y él de pie a su derecha, de
 *   arriba abajo. Sólo donde los tableros se alinean a la izquierda, y sólo si
 *   el texto es lo bastante corto para dejarle sitio: con una línea larga gana
 *   `arriba` solo.
 *
 * Centrado —el horizontal— no hay `esquina`: Jaime, *«que las letras no queden
 * pegadas a un solo lado»*.
 */
export type Caja = { x: number; y: number; w: number; h: number };

export type Composicion = {
  /** Donde va el texto, y cómo se alinea dentro. */
  caja: Caja;
  centra: boolean;
  /** Si el texto se centra también a lo alto de su caja. */
  enMedio: boolean;
  cuerpoTexto: number;
  /** Donde actúa él: el suelo es su borde de abajo. */
  escena: Caja;
  /** Píxeles por unidad del personaje. */
  k: number;
  /** Las líneas que se pintan, si no son las de `texto`, con la línea de la que salen. */
  lineas?: { t: string; de: number }[];
};

/** Anton en versales gasta ~0,47 em por carácter: medido en `Tarjeta`. */
const AVANCE = 0.47;
/** Lo que el texto se separa del personaje. */
const HUECO = 40;

export const compone = (layout: Lienzo, papel: Accion, texto: string[], aire: number): Composicion => {
  const util: Caja = {
    x: layout.safe.left,
    y: layout.safe.top,
    w: layout.width - layout.safe.left - layout.safe.right,
    h: layout.height - layout.franja.reserva - aire - layout.safe.top,
  };
  const centra = layout.tablero.alinea === "center";
  const larga = Math.max(1, ...texto.map((l) => l.length));
  const base = 112 * layout.tablero.cuerpo;
  /** El cuerpo que cabe en una caja: por la línea más larga y por el alto. */
  const cabe = (c: Caja, parte: number) =>
    Math.min(base, c.w / (larga * AVANCE), (c.h * parte - HUECO) / Math.max(1, texto.length * 0.96));
  const escala = (e: Caja) => Math.min(e.h / papel.alto, e.w / papel.ancho);

  const encima = cabe(util, 0.3);
  const altoEncima = texto.length ? texto.length * encima * 0.96 + HUECO : 0;
  const arriba: Composicion = {
    caja: { ...util, h: altoEncima },
    centra,
    enMedio: false,
    cuerpoTexto: encima,
    escena: { ...util, y: util.y + altoEncima, h: util.h - altoEncima },
    k: escala({ ...util, h: util.h - altoEncima }),
  };
  const opciones = [arriba];

  if (util.w > util.h * 1.4 && papel.texto === "lado") {
    const corte = util.w * 0.42;
    const caja = { ...util, x: util.x + corte, w: util.w - corte };
    const escena = { ...util, w: corte };
    opciones.push({ caja, centra, enMedio: true, cuerpoTexto: cabe(caja, 0.8), escena, k: escala(escena) });
  }
  if (!centra && papel.texto === "lado") {
    const ancho = texto.length ? larga * AVANCE * encima + HUECO : 0;
    const escena = { ...util, x: util.x + ancho, w: util.w - ancho };
    opciones.push({ ...arriba, caja: { ...arriba.caja, w: ancho }, escena, k: escala(escena) });
  }
  return opciones.reduce((a, b) => (b.k > a.k ? b : a));
};

/** Dónde va él cuando acompaña el plano en vez de taparlo. */
export type Sitio = "arriba" | "abajo" | "izquierda" | "derecha";

/** Dónde va el texto cuando él va a un lado: enfrente, al otro lado de Jaime, o encima del muñeco. */
export type TextoAl = "frente" | "encima";
/** Lo que mide a su lado: lo segundo del cuadro después de Jaime. */
const A_SU_LADO = 0.56;
/** Lo menos que mide a su lado: por debajo deja de competir con su cara (C-729). */
const MINIMO = 0.45;
/** La columna que ocupa cada uno, en fracción del ancho útil. */
const COLUMNA = 0.3;

/**
 * **A su lado, el muñeco es lo segundo del cuadro** (C-729). Jaime, 16-11,
 * viendo e14 de reel-23 con el muñeco a un quinto del alto: *«tiene que ser
 * muchísimo más grande… aparte de mí, lo segundo; tiene que competir con mi
 * cara… bien formado, no un muñequito perdido en la mitad de la nada; métele
 * composición»*, y *«si estoy yo en la mitad, en un lado MUSCLE MEMORY y en el
 * otro el muñeco»*.
 *
 * Mide algo más de la mitad del alto y está de pie sobre la franja, centrado en
 * su columna (`COLUMNA` del ancho útil, en el borde de `sitio`). El texto va:
 * - `frente` (por defecto): en la columna del otro borde, grande, a la altura
 *   de su cara. Medido en e14 de reel-23: el muñeco sale el doble de alto que
 *   con el texto encima.
 * - `encima`: sobre el muñeco, en su misma columna, cuando él ocupa la otra
 *   mitad.
 * Si una línea no cabe grande, se parte por palabras.
 */
const aSuLado = (
  layout: Lienzo, papel: Accion, texto: string[], sitio: Sitio, plano: ElEnElPlano, aire: number,
  textoAl: TextoAl,
): Composicion => {
  const suelo = layout.height - layout.franja.reserva - aire;
  const util = layout.width - layout.safe.left - layout.safe.right;
  const col = util * COLUMNA;
  const izq = (s: Sitio) => (s === "izquierda" ? layout.safe.left : layout.width - layout.safe.right - col);
  const otro: Sitio = sitio === "izquierda" ? "derecha" : "izquierda";
  // El texto es el otro peso del cuadro: grande, hasta un noveno del alto.
  const base = layout.height * 0.11;
  const medir = (lineas: string[], ancho: number) =>
    Math.min(base, ancho / (Math.max(1, ...lineas.map((l) => l.length)) * AVANCE));
  // Apilado por palabras si así sale más grande: «MUSCLE / MEMORY» es un
  // bloque que se lee de un golpe; en una línea era una tira fina.
  const partir = (ancho: number) => {
    const palabras = texto.flatMap((l) => l.split(/\s+/));
    return medir(palabras, ancho) > medir(texto, ancho) * 1.2 ? palabras : texto;
  };
  const deCual = (lineas: string[]) => lineas === texto ? texto.map((t, de) => ({ t, de }))
    : texto.flatMap((l, de) => l.split(/\s+/).map((t) => ({ t, de })));
  const cara = (plano.coronilla ?? CORONILLA) * layout.height;
  // `encima` sólo si con el texto arriba el muñeco sigue siendo lo segundo
  // del cuadro (`MINIMO` del alto); si no, el texto se va enfrente.
  const lineasEncima = partir(col);
  const altoEncima = suelo - (Math.max(layout.safe.top, cara)
    + lineasEncima.length * medir(lineasEncima, col) * 0.96 + HUECO / 2);
  if (textoAl === "frente" || altoEncima < layout.height * MINIMO) {
    const lineas = partir(col);
    const cuerpoTexto = medir(lineas, col);
    const h = lineas.length * cuerpoTexto * 0.96;
    const k = Math.min((layout.height * A_SU_LADO) / papel.alto, col / papel.ancho);
    const w = papel.ancho * k;
    const escena = { x: izq(sitio) + (col - w) / 2, y: suelo - papel.alto * k, w, h: papel.alto * k };
    // **Una línea que cruza el cuadro por encima de él**: el texto arranca a
    // la altura de la cabeza del muñeco, sin subir de su coronilla.
    const caja = { x: izq(otro), y: Math.max(cara, escena.y), w: col, h };
    return { caja, centra: true, enMedio: false, cuerpoTexto, escena, k, lineas: deCual(lineas) };
  }
  const lineas = partir(col);
  const cuerpoTexto = medir(lineas, col);
  const h = lineas.length * cuerpoTexto * 0.96;
  const caja = { x: izq(sitio), y: Math.max(layout.safe.top, cara), w: col, h };
  const alto = Math.min(layout.height * A_SU_LADO, suelo - (caja.y + h + HUECO / 2));
  const k = Math.min(alto / papel.alto, col / papel.ancho);
  const w = papel.ancho * k;
  const escena = { x: izq(sitio) + (col - w) / 2, y: suelo - papel.alto * k, w, h: papel.alto * k };
  return { caja, centra: true, enMedio: false, cuerpoTexto, escena, k, lineas: deCual(lineas) };
};

/** Lo que mide acompañando: un quinto del lado corto del cuadro, con lo que lleve. */
const QUINTO = 0.2;
/** Lo que deja por encima de la coronilla cuando va arriba. */
const SOBRE_EL = 18;
/** Por defecto, dónde cae la coronilla: la medida en reel-23 es 0,197–0,217. */
const CORONILLA = 0.2;

/**
 * **Él acompañando: pequeño, en su sitio y sin taparle la cara** (`cubre:
 * "panel"` + `lado`).
 *
 * Jaime: *«deja que el muñequito aparezca, solamente ponlo en un sitio que no
 * estorbe tanto: ponlo arriba, ponlo abajo, ponlo a un lado»*, y *«tampoco
 * estoy viendo las ayudas visuales»*: lo que él saca a cámara —la calavera—
 * no se tapa. Así que mide un quinto del cuadro y vive en el borde que se
 * declara, dentro de la zona segura y sobre la franja del subtítulo:
 *
 * - `izquierda` / `derecha` — a su lado y grande: ver `aSuLado` (C-729).
 * - `abajo` — de pie sobre la franja, en el centro de la mitad que él deja
 *   libre (el `lado` de la pieza, que llega por `DondeEstaEl`).
 * - `arriba` — colgado del margen de arriba, en esa misma mitad libre. Si la
 *   pieza no dice cuál es, va al centro y entonces **no baja de su
 *   coronilla** —la mide `sujeto.py`; sin ella, el 0,2 de reel-23—: se encoge
 *   lo que haga falta, nunca le pisa la cabeza. Medido en reel-23: centrado,
 *   arriba le cabían 40 px y abajo caía sobre la barbilla; en la mitad libre,
 *   los dos caben enteros.
 */
export const acompana = (
  layout: Lienzo, papel: Accion, texto: string[], sitio: Sitio, plano: ElEnElPlano, aire: number,
  textoAl?: TextoAl,
): Composicion => {
  if (sitio === "izquierda" || sitio === "derecha")
    return aSuLado(layout, papel, texto, sitio, plano, aire, textoAl ?? "frente");
  const suelo = layout.height - layout.franja.reserva - aire;
  const util = layout.width - layout.safe.left - layout.safe.right;
  const hueco = (plano.coronilla ?? CORONILLA) * layout.height - layout.safe.top - SOBRE_EL;
  const sobreEl = sitio === "arriba" && !plano.libre;
  const alto = Math.max(40, Math.min(Math.min(layout.width, layout.height) * QUINTO, sobreEl ? hueco : Infinity));
  const k = Math.min(alto / papel.alto, (util * 0.4) / papel.ancho);
  const w = papel.ancho * k;
  const h = papel.alto * k;
  /** El centro de la mitad libre; sin ella, el del cuadro. */
  const medio = plano.libre === "izq" ? layout.width / 4 : plano.libre === "der" ? layout.width * 0.75 : layout.width / 2;
  const x = medio - w / 2;
  const escena = { x, y: sitio === "arriba" ? layout.safe.top + alto - h : suelo - h, w, h };
  const larga = Math.max(1, ...texto.map((l) => l.length));
  const base = 40 * layout.tablero.cuerpo;
  if (sitio === "arriba") {
    const caja = { x: escena.x + w + HUECO / 2, y: escena.y, w: util * 0.3, h };
    const cuerpoTexto = Math.min(base, caja.w / (larga * AVANCE), h / Math.max(1, texto.length * 0.96));
    return { caja, centra: false, enMedio: true, cuerpoTexto, escena, k };
  }
  const ancho = w + HUECO * 2;
  const cuerpoTexto = Math.min(base, ancho / (larga * AVANCE));
  const altoTexto = texto.length * cuerpoTexto * 0.96;
  const caja = { x: escena.x - HUECO, y: escena.y - altoTexto - HUECO / 4, w: ancho, h: altoTexto };
  return { caja, centra: true, enMedio: false, cuerpoTexto, escena, k };
};
