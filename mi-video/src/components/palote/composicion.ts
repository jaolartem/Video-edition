import type { Lienzo } from "../../brand/lienzo";
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
