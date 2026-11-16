import { articula, type Pose } from "./rig";

/**
 * **Lo que hace que el palote esté vivo y no posando**: el arrastre de lo que
 * cuelga y la respiración.
 *
 * Las claves dicen a dónde va cada hueso; esto dice cómo lo sigue lo que
 * cuelga de él. En la referencia de Jaime nada para en seco: el brazo frena y
 * el antebrazo se pasa un poco y vuelve; el tronco gira y la cabeza llega
 * tarde. Escrito a mano serían tres claves más por movimiento, en cada acción,
 * y en cada una medirían distinto — así que es física, y la misma para todas.
 *
 * Y la respiración va siempre, también encima de la acción. El detector de
 * congelados de la línea (`freezedetect`, medio segundo) falla una pieza en
 * cuanto el cuadro se queda quieto; un personaje que respira no se queda
 * quieto nunca, dure lo que dure el tablero.
 */

/** Quién arrastra a quién y con cuánta inercia. */
const ENLACES: [keyof Pose, keyof Pose, number][] = [
  ["tronco", "cuello", 0.5],
  ["hombroD", "codoD", 0.42],
  ["hombroI", "codoI", 0.42],
  ["caderaD", "rodillaD", 0.25],
  ["caderaI", "rodillaI", 0.25],
];

/** Fotogramas de historia que mira el muelle: con esto ya se ha calmado. */
const VENTANA = 20;
/** Frecuencia propia del muelle, en radianes por fotograma: ~11 de periodo. */
const OMEGA = 0.56;
/** Amortiguación: por debajo de 1 se pasa y vuelve, que es lo que se busca. */
const ZETA = 0.34;
/** Lo más que se deja ir un hueso por arrastre, en grados. */
const TOPE = 32;

const TAU = Math.PI * 2;

/**
 * La pose del fotograma `f`, con su arrastre, su respiración y su vaivén: el
 * peso que pasa de una pierna a otra, en grados. Los pies no patinan: la
 * cadera se corre lo que hace falta para que se queden donde estaban.
 */
export const conVida = (poseEn: (f: number) => Pose, f: number, vaiven = 1.2): Pose => {
  const p = { ...poseEn(f) };
  const historia: Pose[] = [];
  for (let t = f - VENTANA - 2; t <= f; t++) historia.push(poseEn(Math.max(0, t)));
  for (const [padre, hijo, inercia] of ENLACES) {
    let o = 0;
    let v = 0;
    for (let i = 2; i < historia.length; i++) {
      const acel =
        historia[i][padre] - 2 * historia[i - 1][padre] + historia[i - 2][padre];
      v += -OMEGA * OMEGA * o - 2 * ZETA * OMEGA * v - inercia * acel;
      o += v;
    }
    p[hijo] += Math.max(-TOPE, Math.min(TOPE, o));
  }
  const aire = Math.sin((TAU * f) / 72);
  p.pecho += 3 * aire;
  p.hombroD += 2 * aire;
  p.hombroI -= 2 * aire;
  p.cuello += 1.6 * Math.sin((TAU * f) / 97 + 0.8);
  p.tronco += 0.8 * Math.sin((TAU * f) / 131);
  if (vaiven > 0) {
    const antes = articula(p);
    const d = vaiven * Math.sin((TAU * f) / 96);
    p.caderaD += d;
    p.caderaI += d;
    const despues = articula(p);
    p.x += (antes.tobilloD.x + antes.tobilloI.x - despues.tobilloD.x - despues.tobilloI.x) / 2;
  }
  return p;
};
