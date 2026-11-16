import type { Accion, Escena } from "./accion";
import { HOJA, Hoja, Lapiz } from "./Oficina";
import { reposo } from "./reposo";
import { CURVA, NEUTRA, Pista, alcanza, articula, rampa, type Clave, type Pose, type Punto } from "./rig";
import { conVida } from "./vida";

/**
 * **Currículum**: le cae una hoja, la escribe y la levanta para que se vea.
 *
 * Para el *résumé* —lo que se escribe de uno mismo—. La hoja baja planeando y
 * la coge en el 10; escribe de arriba abajo hasta el 44, con el hueco de la
 * foto y sus renglones; en el 58 la tiene en alto con los dos brazos, con un
 * saltito. Luego la baja al pecho y la va señalando con el lápiz, como quien
 * la enseña en una entrevista.
 */

const ESCRIBE = [12, 44] as const;
const ALZA = 58;
const BAJA = 104;
/** Cada cuánto da un toque con el lápiz en la hoja, ya enseñándola. */
const TOQUE = 40;

const PECHO = { x: 30, y: -214, giro: -3, esc: 1 };
const ARRIBA = { x: 14, y: -408, giro: 2, esc: 1.15 };
const ENSENA = { x: 46, y: -236, giro: 4, esc: 1.08 };

const hoja = new Pista({ x: 60, y: -900, giro: 30, esc: 1 }, [
  { f: 0, x: 70, y: -560, giro: 28 },
  { f: 10, c: CURVA.sale, ...PECHO },
  { f: ALZA - 12, ...PECHO },
  { f: ALZA, c: CURVA.sale, ...ARRIBA },
  { f: ALZA + 14, c: CURVA.suave, giro: -3 },
  { f: ALZA + 28, c: CURVA.suave, giro: 4 },
  { f: BAJA - 8, c: CURVA.suave, giro: 0, x: ARRIBA.x },
  { f: BAJA + 8, c: CURVA.suave, ...ENSENA },
]);

/** Las manos: la izquierda sujeta, la derecha escribe o sujeta la otra esquina. */
const manos = new Pista({ izq: 0, sube: 0, lapiz: 0 }, [
  { f: 5, izq: 0, lapiz: 0 },
  { f: 11, c: CURVA.sale, izq: 1, lapiz: 1 },
  { f: ALZA - 12, sube: 0 },
  { f: ALZA - 2, c: CURVA.suave, sube: 1 },
  { f: BAJA - 4, sube: 1, lapiz: 1 },
  { f: BAJA + 8, c: CURVA.suave, sube: 0 },
]);

const claves: Clave<Pose>[] = [
  { f: 0, ...NEUTRA },
  // Mira la hoja que baja, y la mira mientras escribe.
  { f: 4, c: CURVA.suave, cuello: -10 },
  { f: 12, c: CURVA.suave, cuello: 12, tronco: 3 },
  // Arriba, de un saltito, sacando pecho.
  { f: ALZA - 6, c: CURVA.suave, alza: 0, caderaI: -16, rodillaI: 22, caderaD: 16, rodillaD: -22, cuello: 0 },
  { f: ALZA, c: CURVA.sale, alza: 12, caderaI: -10, rodillaI: 2, caderaD: 10, rodillaD: -2, pecho: 7, cuello: -8 },
  { f: ALZA + 6, c: CURVA.cae, alza: 0 },
  { f: ALZA + 10, c: CURVA.sale, caderaI: -14, rodillaI: 12, caderaD: 14, rodillaD: -12 },
  { f: ALZA + 16, c: CURVA.suave, caderaI: -10, rodillaI: 4, caderaD: 10, rodillaD: -4, pecho: 4 },
  { f: BAJA + 8, c: CURVA.suave, cuello: 6, pecho: 1, tronco: 2 },
];

const pista = new Pista<Pose>(NEUTRA, claves);

/** Dónde escribe la punta: renglón a renglón, con su garabato. */
const renglon = (centro: Punto, esc: number, escrito: number, f: number): Punto => {
  const n = 4;
  const i = Math.min(n - 1, Math.floor(escrito * n));
  const dentro = escrito * n - i;
  return {
    x: centro.x + (-HOJA.ancho / 2 + 9 + (HOJA.ancho - 18) * dentro) * esc,
    y: centro.y + (-HOJA.alto / 2 + HOJA.alto * (0.42 + 0.14 * i)) * esc + Math.sin(f * 2.3) * 3,
  };
};

const monta = (): Escena => {
  const varia = reposo({ desde: BAJA + 20, libres: ["D"], semilla: 2 });
  const poseEn = (f: number) => {
    const p = conVida((g) => pista.en(g), f, 1.2);
    const h = hoja.en(f);
    const m = manos.en(f);
    const medio = { w: (HOJA.ancho / 2) * h.esc, h: (HOJA.alto / 2) * h.esc };
    const izq = { x: h.x - medio.w + 3, y: h.y + 8 + (medio.h - 14) * m.sube };
    const sujeta = alcanza(p, izq, m.izq, "I", 1);
    const escrito = rampa(f, ...ESCRIBE);
    const ultimo = f - BAJA - 12 - Math.floor((f - BAJA - 12) / TOQUE) * TOQUE;
    const toca = f > BAJA + 12 ? Math.max(0, Math.sin((Math.PI * ultimo) / 10)) * (ultimo < 10 ? 1 : 0) : 0;
    const punta = f < ALZA - 12
      ? renglon(h, h.esc, escrito, f)
      : { x: h.x + 10 + toca * 4, y: h.y + 6 - 16 * (1 - toca) };
    const esquina = { x: h.x + medio.w - 4, y: h.y + medio.h - 6 };
    const der = { x: punta.x + (esquina.x - punta.x) * m.sube, y: punta.y + 8 + (esquina.y - punta.y - 8) * m.sube };
    return varia(alcanza(sujeta, der, m.izq, "D", -1), f);
  };
  return {
    fotograma: (f) => {
      const pose = poseEn(f);
      const cuerpo = articula(pose);
      const h = hoja.en(f);
      const m = manos.en(f);
      const lapiz = m.lapiz * (1 - m.sube);
      return {
        cuerpo,
        pose,
        delante: (
          <>
            <Hoja en={h} giro={h.giro} escala={h.esc} escrito={rampa(f, ...ESCRIBE)} cara />
            {lapiz > 0.02 ? (
              <g opacity={lapiz}>
                <Lapiz punta={{ x: cuerpo.manoD.x, y: cuerpo.manoD.y - 8 }} angulo={150} />
              </g>
            ) : null}
          </>
        ),
      };
    },
    sonidos: [
      { motion: "draw", at: ESCRIBE[0] + 2 },
      { motion: "mark", at: ALZA },
    ],
  };
};

export const curriculum: Accion = { alto: 470, ancho: 300, texto: "lado", monta };
