import type { Accion, Escena, Escenario } from "./accion";
import { Libro, Lupa, MANGO, CRISTAL } from "./Oficina";
import { reposo } from "./reposo";
import { CURVA, NEUTRA, Pista, alcanza, articula, asienta, azar, hacia, rampa, type Clave, type Pose } from "./rig";
import { conVida } from "./vida";

/**
 * **Investigar**: le cae una pila de libros al lado y la repasa con la lupa.
 *
 * Para el *research* —lo que se averigua antes de escribir nada—. Los libros
 * caen uno encima de otro y el último aterriza en el 19; él los mira caer,
 * saca la lupa en el 22 y en el segundo ya está inclinado barriendo los lomos.
 * Cada dos segundos y medio se acerca la lupa al ojo —¡ajá!— y vuelve a lo
 * suyo, con la otra mano en jarras.
 */

const LIBROS = 5;
const GRUESO = 24;
/** Dónde está él y dónde la pila: a su derecha, que es hacia donde se inclina. */
const EL = -70;
const PILA = 92;
const SACA = 22;
/** Cada cuánto se acerca la lupa al ojo, y desde cuándo. */
const AJA = 76;
const PRIMER_AJA = 64;

const claves: Clave<Pose>[] = [
  { f: 0, ...NEUTRA, x: EL },
  // Los mira caer: la cabeza sigue a la pila, un poco echado atrás.
  { f: 6, c: CURVA.suave, cuello: -16, tronco: -4 },
  { f: 18, c: CURVA.suave, cuello: 10, tronco: 2 },
  // Se inclina sobre la pila, rodillas sueltas, a mirar de cerca.
  { f: SACA + 10, c: CURVA.suave, tronco: 24, cuello: 14, caderaI: -16, rodillaI: 16, caderaD: 18,
    rodillaD: -20, pecho: 2 },
];

/** Un ¡ajá!: se yergue un poco, el cuello atrás, y vuelve a inclinarse. */
const aja = (s: number): Clave<Pose>[] => [
  { f: s, tronco: 24, cuello: 14 },
  { f: s + 8, c: CURVA.sale, tronco: 8, cuello: -4, pecho: 6 },
  { f: s + 26, c: CURVA.suave, tronco: 24, cuello: 14, pecho: 2 },
];

const monta = (e: Escenario): Escena => {
  const ajas: number[] = [];
  for (let s = PRIMER_AJA; s + 20 < e.dur; s += AJA) ajas.push(s);
  const pista = new Pista<Pose>(NEUTRA, [...claves, ...ajas.flatMap(aja)]);
  const libros = Array.from({ length: LIBROS }, (_, i) => ({
    cae: 3 * i,
    ancho: 84 + 14 * azar(i * 3),
    dx: (azar(i * 5) - 0.5) * 14,
    giro: (azar(i * 7) - 0.5) * 7,
  }));
  const tope = -LIBROS * GRUESO;
  const varia = reposo({ desde: PRIMER_AJA + 10, libres: ["I"], semilla: 1 });
  /** Dónde está el cristal: barriendo los lomos, o al ojo en un ¡ajá!. */
  const cristal = (f: number, cabeza: { x: number; y: number }) => {
    const barre = Math.sin((2 * Math.PI * (f - SACA)) / 46);
    const enPila = { x: PILA + 26 * barre, y: tope - 48 + 6 * Math.cos((2 * Math.PI * f) / 23) };
    const ultimo = ajas.filter((s) => s <= f).pop();
    const ojo = ultimo === undefined ? 0 : Math.sin(Math.PI * rampa(f, ultimo + 2, ultimo + 26));
    return {
      x: enPila.x + (cabeza.x + 58 - enPila.x) * ojo * 0.8,
      y: enPila.y + (cabeza.y - enPila.y) * ojo * 0.8,
      cerca: ojo,
    };
  };
  const poseEn = (f: number) => {
    const p = conVida((g) => pista.en(g), f, 1);
    const a = articula(p);
    const enJarras = alcanza(p, { x: a.cadera.x - 16, y: a.cadera.y - 20 }, CURVA.sale(rampa(f, 20, 30)), "I", -1);
    const c = cristal(f, a.cabeza);
    const largo = (MANGO + CRISTAL) * (1 + 0.25 * c.cerca);
    const mano = hacia(c, -40, largo);
    return varia(alcanza(enJarras, mano, CURVA.suave(rampa(f, SACA - 2, SACA + 8)), "D", 1), f);
  };
  return {
    fotograma: (f) => {
      const pose = poseEn(f);
      const cuerpo = articula(pose);
      const c = cristal(f, cuerpo.cabeza);
      const angulo = 140;
      return {
        cuerpo,
        pose,
        detras: (
          <>
            {libros.map((l, i) => {
              const t = f - l.cae;
              const cae = CURVA.cae(rampa(t, 0, 7));
              const base = -i * GRUESO;
              const y = base - (1 - cae) * (e.techo + 60) + asienta(t - 7, 3, 8, 0.35);
              return t < 0 ? null : (
                <Libro key={i} x={PILA + l.dx} y={y} ancho={l.ancho} giro={l.giro * cae} tono={i % 2} />
              );
            })}
          </>
        ),
        delante:
          f >= SACA - 4 ? (
            <Lupa mano={cuerpo.manoD} angulo={angulo} escala={CURVA.sale(rampa(f, SACA - 4, SACA + 4)) * (1 + 0.25 * c.cerca)}
              fase={f * 0.21} />
          ) : null,
      };
    },
    sonidos: [
      { motion: "land", at: 7 },
      { motion: "mark", at: SACA },
    ],
  };
};

export const investigar: Accion = { alto: 380, ancho: 340, texto: "lado", monta };
