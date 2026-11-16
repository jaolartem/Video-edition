import { CURVA, alcanza, articula, hacia, rampa, type Pose } from "./rig";

/**
 * **Lo que hace mientras espera**: gestos pequeños y creíbles que se turnan en
 * los reposos largos.
 *
 * El diseñador lo pidió mirando reel-23: *«el `mecanico` de e8 y el `musculo`
 * de e14 repiten el mismo gesto durante toda la etapa»*. Una etapa de 8 a 12 s
 * con un solo gesto en bucle se lee como un GIF; con un personaje que entre
 * bombeo y bombeo mira alrededor, se rasca la cabeza o mira el reloj, se lee
 * como alguien que está ahí. Es lo que le da el papel de *segundo al mando*
 * que pidió Jaime: no posa, acompaña.
 *
 * No sustituye el bucle de la acción: se le pone **encima**, con su propia
 * entrada y salida suaves, y la acción sigue debajo. Cada acción dice desde
 * cuándo está leída y qué manos tiene libres —el millonario tira billetes con
 * la derecha, así que sólo le queda la izquierda—, y esto no toca lo demás.
 */
export type Mano = "I" | "D";
export type Gesto = "mira" | "rasca" | "pie" | "reloj" | "peina";

/** Lo que dura un gesto, entrada y salida incluidas, y cada cuánto vuelve uno. */
const DURA = 50;
const CICLO = 76;
/** Lo que deja de bucle propio antes de cada gesto. */
const ANTES = 20;
/** El orden en que se turnan: nunca el mismo dos veces seguidas. */
const ORDEN: Gesto[] = ["rasca", "reloj", "mira", "peina", "pie"];
const MANOS: Record<Gesto, boolean> = { mira: false, rasca: true, pie: false, reloj: true, peina: true };

const TAU = Math.PI * 2;

/** El gesto en su fotograma `t`, con su peso `w` ya puesto. */
const haz = (g: Gesto, p: Pose, t: number, w: number, mano: Mano): Pose => {
  const s = mano === "D" ? 1 : -1;
  if (g === "mira") {
    // Mira a un lado, se detiene, y al otro: el que busca a alguien.
    const giro = Math.sin((TAU * t) / DURA) * 26;
    return { ...p, cuello: p.cuello + w * giro, tronco: p.tronco + w * giro * 0.25 };
  }
  if (g === "pie") {
    // Tres golpecitos de punta, impaciente, con la cabeza de lado.
    const golpe = Math.max(0, Math.sin((TAU * t) / 13));
    return { ...p, pieD: p.pieD + w * 26 * golpe, rodillaD: p.rodillaD - w * 6 * golpe,
             cuello: p.cuello + w * 7 };
  }
  const a = articula(p);
  const r = 34;
  if (g === "rasca") {
    // Se rasca un lado de la cabeza, con la cabeza ladeada al otro.
    const cabeza = hacia(a.cabeza, a.arriba - 50 * s, r + 4);
    const roce = Math.sin(t * 1.4) * 7;
    const q = { ...p, cuello: p.cuello - w * 9 * s };
    return alcanza(q, { x: cabeza.x + roce * 0.5, y: cabeza.y + roce }, w, mano, -s);
  }
  if (g === "reloj") {
    // El antebrazo cruzado delante del pecho, la cabeza hacia la muñeca, y la
    // sacude: ¿se ha parado?
    const sacude = t > 26 ? Math.sin(t * 1.9) * 6 * rampa(t, 26, 30) : 0;
    const muneca = { x: a.pecho.x + s * 14 + sacude, y: a.pecho.y + 30 };
    const q = { ...p, cuello: p.cuello - w * 14 * s };
    return alcanza(q, muneca, w, mano, -s);
  }
  // `peina`: la mano a la coronilla, de delante atrás: se coloca el sombrero o
  // el pelo, el que lleve.
  const barre = Math.sin((Math.PI * t) / DURA) * 18 * s;
  const coronilla = hacia(a.cabeza, a.arriba + barre, r + 10);
  return alcanza({ ...p, cuello: p.cuello + w * 5 * s }, coronilla, w, mano, -s);
};

/**
 * Los gestos de una acción, desde el fotograma `desde` en que ya está leída.
 * `libres` son las manos que puede usar; `sin`, los gestos que la acción ya
 * hace por su cuenta (el mecánico ya lleva el compás con el pie). `semilla`
 * cambia por cuál empieza, para que dos acciones seguidas no abran igual.
 */
export const reposo = ({ desde, libres, sin = [], semilla = 0, cada = CICLO }: {
  desde: number;
  libres: Mano[];
  sin?: Gesto[];
  semilla?: number;
  /** Cada cuánto, si la acción tiene su propio ciclo y el gesto va en su hueco. */
  cada?: number;
}) => {
  const gestos = ORDEN.filter((g) => !sin.includes(g) && (libres.length || !MANOS[g]));
  return (p: Pose, f: number): Pose => {
    const n = Math.floor((f - desde) / cada);
    const t = f - desde - n * cada - ANTES;
    if (f < desde || t < 0 || t > DURA || !gestos.length) return p;
    const w = CURVA.suave(rampa(t, 0, 11)) * (1 - CURVA.suave(rampa(t, DURA - 13, DURA)));
    const g = gestos[(n + semilla) % gestos.length];
    const mano = libres[(n + semilla) % Math.max(1, libres.length)] ?? "D";
    return haz(g, p, t, w, mano);
  };
};
