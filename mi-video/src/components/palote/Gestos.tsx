import type React from "react";
import type { Motion } from "../../brand/sfx";
import { color } from "../../brand/tokens";
import type { Accion, Escena, Escenario } from "./accion";
import { andar, POR_PASO, ZANCADA } from "./andar";
import { reposo, type Mano } from "./reposo";
import {
  CURVA, NEUTRA, Pista, alcanza, articula, espejo, hacia, rampa,
  type Articulaciones, type Clave, type Pose,
} from "./rig";
import { conVida } from "./vida";

/**
 * **Los gestos del segundo al mando**: señala, piensa, aprueba, celebra, se
 * encoge, saluda y entra andando.
 *
 * Jaime: *«el muñequito tiene que estar ahí como segundo al mando, ¿me
 * entiendes? En todo»*. Las acciones de oficio —investigar, escribir, enviar—
 * cuentan un paso del proceso; éstas acompañan lo que él dice: le señalan,
 * asienten, se encogen de hombros con él. Son cortas a propósito: cada una se
 * lee en un segundo y medio y luego **sigue viva** —repite su gesto de vez en
 * cuando y entre medias hace lo de cualquiera que espera (`reposo`)—.
 *
 * Están escritas mirando a la derecha. Cuando lo que acompaña queda a la
 * izquierda (`senal` del escenario), la pose se refleja entera: señala a él,
 * no al borde del cuadro.
 */

type Def = {
  /** Lo que se lee: la entrada del gesto. */
  claves: Clave<Pose>[];
  /** El gesto que vuelve, cada `cada` fotogramas desde `desde`. */
  vuelve?: { desde: number; cada: number; claves: (s: number) => Clave<Pose>[] };
  /** Lo que se le pone encima a la pose en cada fotograma: manos a un sitio, el saludo. */
  ajusta?: (p: Pose, f: number) => Pose;
  /** Lo que lleva además del cuerpo: el pulgar, los puntos del que piensa. */
  dibuja?: (a: Articulaciones, f: number) => React.ReactNode;
  /** Desde cuándo y con qué manos hace los gestos de espera, y por cuál empieza. */
  espera: { desde: number; libres: Mano[]; semilla: number };
  sonidos?: { motion: Motion; at: number }[];
  /** Si entra andando desde el borde del escenario hasta el centro. */
  anda?: boolean;
};

/** La mano izquierda en la cadera, en jarras: la de quien señala o espera. */
const jarra = (p: Pose, w: number) => {
  const c = articula(p).cadera;
  return alcanza(p, { x: c.x - 16, y: c.y - 20 }, w, "I", -1);
};

const gesto = (def: Def, alto = 400, ancho = 320): Accion => ({
  alto,
  ancho,
  texto: "lado",
  monta: (e: Escenario): Escena => {
    const vueltas: Clave<Pose>[] = [];
    if (def.vuelve)
      for (let s = def.vuelve.desde; s < e.dur; s += def.vuelve.cada) vueltas.push(...def.vuelve.claves(s));
    const desde = -(e.ancho / 2 + 40);
    const pasos = Math.max(2, Math.round(-desde / ZANCADA));
    const llega = pasos * POR_PASO;
    const andando = def.anda ? [{ f: 0, x: desde }, { f: llega, c: CURVA.lineal, x: 0 }] : [];
    const pista = new Pista<Pose>(NEUTRA, [...def.claves, ...vueltas, ...andando]);
    const varia = reposo(def.espera);
    const base = (f: number) => {
      const p = pista.en(f);
      return def.anda ? andar(p, 1 - rampa(f, llega - 4, llega), desde) : p;
    };
    const poseEn = (f: number) => {
      const vivo = conVida(base, f, def.anda ? 1.2 * rampa(f, llega, llega + 12) : 1.2);
      const p = varia(def.ajusta ? def.ajusta(vivo, f) : vivo, f);
      return e.senal < 0 ? espejo(p) : p;
    };
    return {
      fotograma: (f) => {
        const pose = poseEn(f);
        const cuerpo = articula(pose);
        const extra = def.dibuja?.(e.senal < 0 ? articula(espejo(pose)) : cuerpo, f);
        return {
          cuerpo,
          pose,
          delante: extra ? <g transform={e.senal < 0 ? "scale(-1 1)" : undefined}>{extra}</g> : null,
        };
      },
      sonidos: def.sonidos ?? [],
    };
  },
});

/** Señala hacia lo que acompaña —él o el texto— y lo repite: ¡ahí! */
export const senalar = gesto({
  claves: [
    { f: 0, ...NEUTRA },
    { f: 6, c: CURVA.suave, tronco: -5, hombroD: 24, codoD: 50, cuello: 4 },
    { f: 12, c: CURVA.sale, tronco: 7, hombroD: 96, codoD: -6, cuello: 14, caderaI: -14, rodillaI: 8, caderaD: 6 },
    { f: 18, c: CURVA.suave, hombroD: 86, codoD: 0 },
  ],
  vuelve: { desde: 46, cada: 58, claves: (s) => [
    { f: s, hombroD: 86, codoD: 0, cuello: 14 },
    { f: s + 4, c: CURVA.sale, hombroD: 100, codoD: -10, cuello: 18 },
    { f: s + 9, c: CURVA.suave, hombroD: 86, codoD: 0 },
    { f: s + 13, c: CURVA.sale, hombroD: 98, codoD: -8 },
    { f: s + 22, c: CURVA.suave, hombroD: 86, codoD: 0, cuello: 12 },
  ] },
  ajusta: (p, f) => jarra(p, CURVA.sale(rampa(f, 8, 16))),
  espera: { desde: 60, libres: ["I"], semilla: 1 },
  sonidos: [{ motion: "mark", at: 12 }],
});

/** Los tres puntos del que piensa, saliendo de la cabeza uno tras otro. */
const Puntos: React.FC<{ a: Articulaciones; f: number }> = ({ a, f }) => {
  const t = (f - 14) % 48;
  if (f < 14) return null;
  return (
    <g fill={color.lightNeutral}>
      {[0, 1, 2].map((i) => {
        const o = rampa(t, i * 8, i * 8 + 5) * (1 - rampa(t, 38, 46));
        const c = hacia(a.cabeza, a.arriba + 38, 50 + i * 24);
        return o > 0 ? <circle key={i} cx={c.x} cy={c.y} r={5 + i * 3} opacity={o} /> : null;
      })}
    </g>
  );
};

/** Mano al mentón, la otra cruzada, la cabeza ladeada: le da vueltas. */
export const pensar = gesto({
  claves: [
    { f: 0, ...NEUTRA },
    { f: 12, c: CURVA.suave, cuello: -12, tronco: -3, caderaD: 16, rodillaD: -10, caderaI: -6, rodillaI: 2 },
  ],
  vuelve: { desde: 40, cada: 72, claves: (s) => [
    { f: s, cuello: -12 },
    { f: s + 14, c: CURVA.suave, cuello: 8, tronco: 2 },
    { f: s + 44, c: CURVA.suave, cuello: -12, tronco: -3 },
  ] },
  ajusta: (p, f) => {
    const a = articula(p);
    const w = CURVA.suave(rampa(f, 3, 14));
    const menton = hacia(a.cabeza, a.arriba + 180 + 14, 36 + 3 * Math.max(0, Math.sin(f * 0.42)));
    const codo = { x: a.pecho.x + 34, y: a.pecho.y + 74 };
    return alcanza(alcanza(p, codo, w, "I", -1), { x: menton.x + 6, y: menton.y + 6 }, w, "D", 1);
  },
  dibuja: (a, f) => <Puntos a={a} f={f} />,
  espera: { desde: 60, libres: [], semilla: 2 },
  sonidos: [{ motion: "mark", at: 16 }],
});

/** El pulgar arriba, en la mano cuyo antebrazo apunta al cielo. */
const Pulgares: React.FC<{ a: Articulaciones }> = ({ a }) => (
  <g stroke={color.lightNeutral} strokeWidth={9} strokeLinecap="round" fill={color.lightNeutral}>
    {[[a.codoD, a.manoD], [a.codoI, a.manoI]].map(([codo, mano], i) => {
      const sube = (codo.y - mano.y) / 64;
      if (sube < 0.75) return null;
      const punta = hacia(mano, a.arriba, 16 + 10 * (sube - 0.75) * 4);
      return (
        <g key={i} opacity={Math.min(1, (sube - 0.75) * 6)}>
          <circle cx={mano.x} cy={mano.y} r={10} stroke="none" />
          <line x1={mano.x} y1={mano.y - 6} x2={punta.x} y2={punta.y - 4} />
        </g>
      );
    })}
  </g>
);

/** Pulgar arriba y asiente: aprobado. A ratos, los dos pulgares. */
export const aprobar = gesto({
  claves: [
    { f: 0, ...NEUTRA },
    { f: 6, c: CURVA.suave, hombroD: 22, codoD: 40, caderaI: -16, rodillaI: 16, caderaD: 16, rodillaD: -16 },
    { f: 12, c: CURVA.sale, hombroD: 74, codoD: 108, pecho: 4, cuello: 8, caderaI: -10, rodillaI: 4,
      caderaD: 10, rodillaD: -4 },
    { f: 16, c: CURVA.suave, hombroD: 70, codoD: 102 },
    ...[20, 32].flatMap((s) => [{ f: s, c: CURVA.suave, pecho: -6 }, { f: s + 6, c: CURVA.suave, pecho: 3 }]),
  ],
  vuelve: { desde: 70, cada: 90, claves: (s) => [
    { f: s, hombroI: -13, codoI: 6, pecho: 3 },
    { f: s + 8, c: CURVA.sale, hombroI: -74, codoI: -108, pecho: 6 },
    { f: s + 14, c: CURVA.suave, pecho: -5 },
    { f: s + 20, c: CURVA.suave, pecho: 3 },
    { f: s + 40, hombroI: -74, codoI: -108 },
    { f: s + 52, c: CURVA.suave, hombroI: -13, codoI: 6 },
  ] },
  dibuja: (a) => <Pulgares a={a} />,
  espera: { desde: 60, libres: [], semilla: 3 },
  sonidos: [{ motion: "mark", at: 12 }],
});

/** Brazos en uve en el aire: un saltito y celebra con los puños. */
const UVE = { hombroI: -150, codoI: -12, hombroD: 150, codoD: 12 };
export const celebrar = gesto({
  claves: [
    { f: 0, ...NEUTRA },
    { f: 6, c: CURVA.suave, caderaI: -24, rodillaI: 36, caderaD: 24, rodillaD: -36, hombroI: -24, hombroD: 24,
      codoI: 20, codoD: -20, pecho: -6 },
    { f: 11, c: CURVA.sale, alza: 34, caderaI: -14, rodillaI: 22, caderaD: 14, rodillaD: -22, ...UVE, pecho: 7 },
    { f: 17, c: CURVA.cae, alza: 0, caderaI: -22, rodillaI: 28, caderaD: 22, rodillaD: -28 },
    { f: 23, c: CURVA.sale, caderaI: -14, rodillaI: 6, caderaD: 14, rodillaD: -6, pecho: 4 },
  ],
  vuelve: { desde: 34, cada: 44, claves: (s) => [
    { f: s, ...UVE },
    { f: s + 6, c: CURVA.suave, hombroI: -128, codoI: -50, hombroD: 128, codoD: 50, alza: 0 },
    { f: s + 11, c: CURVA.sale, ...UVE, alza: 8 },
    { f: s + 16, c: CURVA.cae, alza: 0 },
  ] },
  espera: { desde: 60, libres: [], semilla: 4 },
  sonidos: [{ motion: "whoosh", at: 7 }, { motion: "land", at: 17 }],
}, 440);

/** Se encoge de hombros con las palmas arriba: ni idea. */
const ENCOGE = { hombroI: -26, codoI: -84, hombroD: 26, codoD: 84, pecho: 8 };
export const encoger = gesto({
  claves: [
    { f: 0, ...NEUTRA },
    { f: 5, c: CURVA.suave, pecho: -3, caderaI: -12, rodillaI: 10, caderaD: 12, rodillaD: -10 },
    { f: 11, c: CURVA.sale, ...ENCOGE, cuello: 14, caderaI: -9, rodillaI: 4, caderaD: 9, rodillaD: -4 },
    { f: 18, c: CURVA.suave, pecho: 5 },
    { f: 34, c: CURVA.suave, codoI: -60, codoD: 60, pecho: 2, cuello: 8 },
  ],
  vuelve: { desde: 50, cada: 66, claves: (s) => [
    { f: s, codoI: -60, codoD: 60, pecho: 2 },
    { f: s + 7, c: CURVA.sale, ...ENCOGE, cuello: s % 2 ? -14 : 14 },
    { f: s + 26, c: CURVA.suave, codoI: -60, codoD: 60, pecho: 2, cuello: 6 },
  ] },
  espera: { desde: 60, libres: ["D", "I"], semilla: 5 },
  sonidos: [{ motion: "mark", at: 11 }],
});

/** Saluda con la mano en alto, y vuelve a saludar de vez en cuando. */
const OLA = 12;
export const saludar = gesto({
  claves: [
    { f: 0, ...NEUTRA },
    { f: 6, c: CURVA.suave, hombroD: 40, codoD: 20, cuello: 4 },
    { f: 12, c: CURVA.sale, hombroD: 140, codoD: 30, cuello: 10, tronco: -4 },
    { f: 58, hombroD: 140, codoD: 30 },
    { f: 68, c: CURVA.suave, hombroD: 13, codoD: -6, cuello: 0, tronco: 0 },
  ],
  vuelve: { desde: 110, cada: 110, claves: (s) => [
    { f: s, hombroD: 13, codoD: -6 },
    { f: s + 8, c: CURVA.sale, hombroD: 140, codoD: 30, cuello: 10 },
    { f: s + 40, hombroD: 140, codoD: 30 },
    { f: s + 50, c: CURVA.suave, hombroD: 13, codoD: -6, cuello: 0 },
  ] },
  ajusta: (p, f) => ({ ...p, codoD: p.codoD + 26 * Math.sin((2 * Math.PI * f) / OLA) * rampa(p.hombroD, 90, 130) }),
  espera: { desde: 70, libres: ["I"], semilla: 6 },
});

/** Entra andando desde el borde hasta su sitio, se planta y mira. */
export const caminar = gesto({
  claves: [
    { f: 22, pecho: 0, cuello: 0 },
    { f: 30, c: CURVA.sale, pecho: 5, cuello: -8, hombroI: -24, hombroD: 24 },
    { f: 44, c: CURVA.suave, pecho: 1, cuello: 0, hombroI: -13, hombroD: 13 },
  ],
  anda: true,
  espera: { desde: 50, libres: ["D", "I"], semilla: 7 },
});
