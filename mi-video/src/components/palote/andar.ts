import { HUESO, type Pose } from "./rig";

/**
 * **El andar del palote**: las piernas siguen a la cadera por el suelo, sin
 * patinar.
 *
 * Lo escribió `Mecanico` para cruzar de una tabla a la otra y vive aquí porque
 * `caminar` anda igual: dos andares serían dos maneras de patinar.
 */

/** Lo que abre la pierna al andar, en grados, y lo que avanza cada paso. */
export const PASO = 18;
export const ZANCADA = 2 * (HUESO.muslo + HUESO.pierna) * Math.sin((PASO * Math.PI) / 180);
/** Fotogramas por paso. */
export const POR_PASO = 10;

/**
 * La pose `p` andando, mezclada según `peso`. La fase sale de lo que ha
 * avanzado la cadera desde `desde`, así que el pie que pisa no se mueve: `vuelve`
 * pone el brazo y la inclinación hacia el otro lado cuando anda hacia la
 * izquierda.
 */
export const andar = (p: Pose, peso: number, desde: number, vuelve = 1): Pose => {
  if (peso <= 0) return p;
  const fase = (Math.PI * (p.x - desde)) / ZANCADA;
  const s = Math.sin(fase);
  const muslo = { D: PASO * s, I: -PASO * s };
  const dobla = -38 * vuelve;
  const rodilla = { D: dobla * Math.max(0, Math.cos(fase)), I: dobla * Math.max(0, -Math.cos(fase)) };
  const mezcla = (a: number, b: number) => a + (b - a) * peso;
  return {
    ...p,
    caderaD: mezcla(p.caderaD, muslo.D),
    rodillaD: mezcla(p.rodillaD, rodilla.D - 4 * vuelve),
    caderaI: mezcla(p.caderaI, muslo.I),
    rodillaI: mezcla(p.rodillaI, rodilla.I - 4 * vuelve),
    pieD: mezcla(p.pieD, 90 * vuelve - muslo.D - rodilla.D),
    pieI: mezcla(p.pieI, 90 * vuelve - muslo.I - rodilla.I),
    hombroI: mezcla(p.hombroI, 4 + 24 * s),
    tronco: mezcla(p.tronco, 7 * vuelve),
  };
};
