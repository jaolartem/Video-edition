import { Easing } from "remotion";

/**
 * **El esqueleto del palote**: cuánto mide cada hueso, qué es una pose y dónde
 * cae cada articulación.
 *
 * Una pose son **ángulos, no posiciones**. Es lo que hace fluido el movimiento
 * de las referencias que dio Jaime —*Animation vs. Geometry*, de Alan Becker—:
 * entre dos poses no se arrastra un punto en línea recta, gira cada hueso
 * sobre su articulación, así que el codo describe un arco y la mano otro, como
 * en un cuerpo. Interpolar posiciones da muñecos que se deforman a mitad de
 * camino; interpolar ángulos da brazos que miden siempre lo mismo.
 *
 * Los ángulos van en grados con una sola convención para todo el cuerpo: `0`
 * apunta abajo, `90` a la derecha, `-90` a la izquierda y `180` arriba. Cada
 * hueso cuelga de su padre —el antebrazo del brazo, el brazo del tronco—, así
 * que inclinar el tronco se lleva los brazos con él.
 *
 * **Y los pies los pone el suelo, no la pose.** La cadera baja hasta que el
 * tobillo más bajo toca el suelo: doblar las rodillas agacha al personaje sin
 * que nadie calcule cuánto. Una pose sólo dice cómo se dobla; dónde queda lo
 * dice la gravedad.
 */

/** Lo que mide cada hueso, en unidades del personaje. De pie mide ~360. */
export const HUESO = {
  tronco: 112,
  /** Lo que cuelgan los hombros por debajo del arranque del cuello. */
  hombros: 14,
  cuello: 16,
  /** Radio de la cabeza, que va hueca. */
  cabeza: 34,
  brazo: 70,
  antebrazo: 64,
  muslo: 80,
  pierna: 78,
  pie: 18,
  /** El grosor del trazo: grueso y redondo, el registro de la referencia. */
  trazo: 13,
} as const;

/** Lo que mide de pie, de la suela a la coronilla, con su trazo. */
export const ALTURA = 360;

/**
 * Una pose. Los nombres con `I` y `D` son de su izquierda y su derecha **en
 * pantalla**; todos con la misma convención de ángulo, sin espejo.
 */
export type Pose = {
  /** Dónde está la cadera a lo ancho, en unidades. */
  x: number;
  /** Cuánto se despega del suelo: el salto. */
  alza: number;
  /** Lo que el tronco se estira por encima de su largo: la respiración. */
  pecho: number;
  /** Inclinación del tronco. Positivo, hacia la derecha. */
  tronco: number;
  /** La cabeza sobre el tronco. */
  cuello: number;
  /**
   * Medio ancho de hombros. De frente, los brazos salen a los lados y el bíceps
   * no choca con la cabeza; de perfil se cierra, porque un hombro tapa al otro.
   */
  espalda: number;
  hombroI: number;
  codoI: number;
  hombroD: number;
  codoD: number;
  /** Los muslos cuelgan de la cadera, que no gira. */
  caderaI: number;
  rodillaI: number;
  caderaD: number;
  rodillaD: number;
  pieI: number;
  pieD: number;
  /** Cuánto bíceps asoma: 0 ninguno, 1 el de la imagen de siempre. */
  biceps: number;
};

/** De pie, quieto, los brazos sueltos: de donde sale toda acción. */
export const NEUTRA: Pose = {
  x: 0, alza: 0, pecho: 0, tronco: 0, cuello: 0, espalda: 14,
  hombroI: -13, codoI: 6, hombroD: 13, codoD: -6,
  caderaI: -9, rodillaI: 4, caderaD: 9, rodillaD: -4,
  pieI: -82, pieD: 82, biceps: 0,
};

export type Punto = { x: number; y: number };

/** Dónde cae cada articulación de una pose, con los pies en el suelo (y = 0). */
export type Articulaciones = {
  cadera: Punto; pecho: Punto; hombros: Punto; nuca: Punto; cabeza: Punto;
  /** Donde nace cada brazo: a cada lado de los hombros. */
  raizI: Punto; raizD: Punto;
  codoI: Punto; manoI: Punto; codoD: Punto; manoD: Punto;
  rodillaI: Punto; tobilloI: Punto; puntaI: Punto;
  rodillaD: Punto; tobilloD: Punto; puntaD: Punto;
  /** Hacia dónde mira la coronilla, en grados: lo que lleva puesto la sigue. */
  arriba: number;
  biceps: number;
};

const RAD = Math.PI / 180;

/** El punto a `largo` de `o` en la dirección `a`. */
export const hacia = (o: Punto, a: number, largo: number): Punto => ({
  x: o.x + Math.sin(a * RAD) * largo,
  y: o.y + Math.cos(a * RAD) * largo,
});

/** La pose, puesta en el suelo: cada hueso desde su padre. */
export const articula = (p: Pose): Articulaciones => {
  const o = { x: 0, y: 0 };
  const muslo = { I: p.caderaI, D: p.caderaD };
  const pierna = { I: p.caderaI + p.rodillaI, D: p.caderaD + p.rodillaD };
  const rodI = hacia(o, muslo.I, HUESO.muslo);
  const rodD = hacia(o, muslo.D, HUESO.muslo);
  const tobI = hacia(rodI, pierna.I, HUESO.pierna);
  const tobD = hacia(rodD, pierna.D, HUESO.pierna);
  const cadera = { x: p.x, y: -Math.max(tobI.y, tobD.y) - p.alza };
  const mueve = (q: Punto) => ({ x: q.x + cadera.x, y: q.y + cadera.y });
  const pecho = hacia(cadera, 180 - p.tronco, HUESO.tronco + p.pecho);
  const hombros = hacia(cadera, 180 - p.tronco, HUESO.tronco + p.pecho - HUESO.hombros);
  const arriba = 180 - p.tronco - p.cuello;
  const nuca = hacia(pecho, arriba, HUESO.cuello);
  const raizI = hacia(hombros, -90 - p.tronco, p.espalda);
  const raizD = hacia(hombros, 90 - p.tronco, p.espalda);
  const codoI = hacia(raizI, -p.tronco + p.hombroI, HUESO.brazo);
  const codoD = hacia(raizD, -p.tronco + p.hombroD, HUESO.brazo);
  return {
    cadera, pecho, hombros, nuca, raizI, raizD,
    cabeza: hacia(nuca, arriba, HUESO.cabeza),
    codoI, manoI: hacia(codoI, -p.tronco + p.hombroI + p.codoI, HUESO.antebrazo),
    codoD, manoD: hacia(codoD, -p.tronco + p.hombroD + p.codoD, HUESO.antebrazo),
    rodillaI: mueve(rodI), tobilloI: mueve(tobI),
    puntaI: hacia(mueve(tobI), pierna.I + p.pieI, HUESO.pie),
    rodillaD: mueve(rodD), tobilloD: mueve(tobD),
    puntaD: hacia(mueve(tobD), pierna.D + p.pieD, HUESO.pie),
    arriba, biceps: p.biceps,
  };
};

/** Un ángulo llevado a (-180, 180]: para mezclar por el camino corto. */
export const corto = (a: number) => ((((a + 180) % 360) + 360) % 360) - 180;

/**
 * **La mano a un sitio**: los ángulos del brazo que la ponen ahí, mezclados
 * con los de la pose según `peso`. Lo que se coge o se conecta tiene un lugar
 * fijo en el escenario, y apuntarlo con ángulos a ojo deja la mano a un palmo
 * de la pinza en cuanto el motor cambia de tamaño. `codo` dice hacia qué lado
 * se dobla: `1` o `-1`.
 */
export const alcanza = (p: Pose, objetivo: Punto, peso: number, lado: "I" | "D", codo = 1): Pose => {
  if (peso <= 0) return p;
  const pecho = articula(p)[`raiz${lado}`];
  const a = HUESO.brazo;
  const b = HUESO.antebrazo;
  const lejos = Math.hypot(objetivo.x - pecho.x, objetivo.y - pecho.y);
  const d = Math.min(a + b - 0.5, Math.max(Math.abs(a - b) + 1, lejos));
  const recto = Math.atan2(objetivo.x - pecho.x, objetivo.y - pecho.y) / RAD;
  const abre = Math.acos((a * a + d * d - b * b) / (2 * a * d)) / RAD;
  const brazo = recto + codo * abre;
  const c = hacia(pecho, brazo, a);
  const ante = Math.atan2(objetivo.x - c.x, objetivo.y - c.y) / RAD;
  const h = `hombro${lado}` as const;
  const k = `codo${lado}` as const;
  return {
    ...p,
    [h]: p[h] + corto(brazo + p.tronco - p[h]) * peso,
    [k]: p[k] + corto(corto(ante - brazo) - p[k]) * peso,
  };
};

/** Las curvas con que se llega a una clave. */
export const CURVA = {
  /** Sale y llega despacio: el peso de un cuerpo que se mueve. */
  suave: Easing.inOut(Easing.cubic),
  /** Arranca de golpe y frena: el latigazo, la llegada a la pose. */
  sale: Easing.out(Easing.cubic),
  /** Acelera hasta el final: lo que cae, el golpe que se descarga. */
  cae: Easing.in(Easing.quad),
  lineal: Easing.linear,
} as const;

type Curva = (t: number) => number;

/** Una clave: en qué fotograma, con qué curva se llega y qué canales fija. */
export type Clave<T> = Partial<T> & { f: number; c?: Curva };

/**
 * **Una pista de claves**, canal por canal.
 *
 * Cada clave fija sólo los canales que nombra, y eso es lo que permite la
 * acción superpuesta de la animación clásica: el brazo puede salir antes de
 * que la cadera llegue, sin escribir la cadera dos veces. Antes de su primera
 * clave un canal se queda en ella; sin ninguna, vale lo de la base.
 */
export class Pista<T extends Record<string, number>> {
  private readonly canales = new Map<keyof T, { f: number; v: number; c: Curva }[]>();

  constructor(
    private readonly base: T,
    claves: Clave<T>[],
  ) {
    for (const clave of [...claves].sort((a, b) => a.f - b.f)) {
      for (const [k, v] of Object.entries(clave)) {
        if (k === "f" || k === "c" || typeof v !== "number") continue;
        const lista = this.canales.get(k) ?? [];
        lista.push({ f: clave.f, v, c: clave.c ?? CURVA.suave });
        this.canales.set(k, lista);
      }
    }
  }

  en(f: number): T {
    const fuera: Record<string, number> = { ...this.base };
    for (const [k, l] of this.canales) {
      let i = 0;
      while (i < l.length - 1 && l[i + 1].f <= f) i++;
      const a = l[i];
      const b = l[i + 1];
      if (!b || f <= a.f) {
        fuera[k as string] = a.v;
        continue;
      }
      fuera[k as string] = a.v + (b.v - a.v) * b.c((f - a.f) / (b.f - a.f));
    }
    return fuera as T;
  }
}

/** Azar con semilla: el mismo número para el mismo índice, render tras render. */
export const azar = (i: number): number => {
  const s = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};

/** Una oscilación que se apaga: el asentarse de lo que acaba de llegar. */
export const asienta = (t: number, amplitud: number, periodo = 10, amortigua = 0.22) =>
  t < 0 ? 0 : amplitud * Math.exp(-amortigua * t) * Math.cos((2 * Math.PI * t) / periodo);
