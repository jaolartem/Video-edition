import React from "react";
import { fontFamily } from "../../brand/fonts";
import { color } from "../../brand/tokens";
import type { Accion, Escena, Escenario } from "./accion";
import { CURVA, NEUTRA, Pista, alcanza, articula, asienta, azar, type Clave, type Pose, type Punto } from "./rig";
import { reposo } from "./reposo";
import { conVida } from "./vida";

/**
 * **Millonario**: chistera, mano al bolsillo y a tirar billetes. Lo barato.
 *
 * Le cae una chistera, se mete la mano al bolsillo y se pone a tirar billetes.
 * Para lo que de pronto sobra — *code is cheap*.
 *
 * Jaime: *«para el cheap ponle un sombrero de millonario que se meta la mano al
 * bolsillo y empiece a tirar dólares»*. Se lee en 3,3 s (reel-23 e9): la
 * chistera aterriza en el fotograma 9, la mano entra al bolsillo en el 26 y el
 * primer puñado sale en el 43. Después sigue tirando mientras dure el tablero,
 * con la otra mano en jarras: el chiste no se acaba, se sostiene.
 */

/** Cuándo empieza a tirar, y cada cuánto. */
const PRIMER_TIRO = 36;
const PERIODO = 20;
/** Billetes por puñado. */
const PUNADO = 6;
/** En qué fotograma del tiro se sueltan los billetes. */
const SUELTA = 8;

const claves: Clave<Pose>[] = [
  { f: 0, ...NEUTRA },
  // La chistera llega en el 9: aguanta, se aplasta y se estira orgulloso.
  { f: 9, caderaI: -9, rodillaI: 4, caderaD: 9, rodillaD: -4, pecho: 0, hombroI: -13, hombroD: 13 },
  { f: 13, c: CURVA.sale, caderaI: -22, rodillaI: 28, caderaD: 22, rodillaD: -28, pecho: -6,
    hombroI: -34, hombroD: 30 },
  { f: 19, c: CURVA.suave, caderaI: -12, rodillaI: 5, caderaD: 12, rodillaD: -5, pecho: 7,
    hombroI: -20, hombroD: 18 },
  { f: 25, pecho: 0, tronco: -2 },
  { f: PRIMER_TIRO - 4, hombroD: 18, codoD: -6 },
  { f: PRIMER_TIRO, c: CURVA.sale, hombroD: 40, codoD: 52 },
];

/**
 * Las manos que van a un sitio del cuerpo: la izquierda en jarras y la derecha
 * al bolsillo, escarbando. Se miden desde la cadera, que se mueve.
 */
const manos = new Pista({ jarra: 0, bolsillo: 0, escarba: 0 }, [
  { f: 14, jarra: 0 },
  { f: 22, c: CURVA.sale, jarra: 1 },
  { f: 16, bolsillo: 0 },
  { f: 25, c: CURVA.sale, bolsillo: 1 },
  { f: 27, escarba: 0 },
  { f: 29, escarba: 8 },
  { f: 31, escarba: -4 },
  { f: 33, escarba: 6 },
  { f: 35, escarba: 0 },
  { f: 33, bolsillo: 1 },
  { f: 38, c: CURVA.sale, bolsillo: 0 },
]);

/** Un tiro: recoge abajo, latigazo hacia arriba, se pasa y vuelve al fajo. */
const tiro = (s: number): Clave<Pose>[] => [
  { f: s + 4, c: CURVA.suave, hombroD: 8, codoD: 62, tronco: 4,
    caderaI: -16, rodillaI: 18, caderaD: 16, rodillaD: -18 },
  { f: s + SUELTA, c: CURVA.cae, hombroD: 150, codoD: 18, tronco: -6,
    caderaI: -12, rodillaI: 5, caderaD: 12, rodillaD: -5, pecho: 5 },
  { f: s + 12, c: CURVA.sale, hombroD: 163, codoD: 2, tronco: -5 },
  { f: s + PERIODO, c: CURVA.suave, hombroD: 40, codoD: 52, tronco: -2, pecho: 0 },
];

/** Un billete: de dónde sale, con qué impulso y cómo revolotea. */
type Billete = { sale: number; desde: Punto; vx: number; vy: number; fase: number; giro: number };

/** La caída de un papel: frena en el aire y baja a su velocidad, meciéndose. */
const TAU_AIRE = 5;
const CAIDA = 4.6;
const vuela = (b: Billete, t: number) => {
  const k = TAU_AIRE * (1 - Math.exp(-t / TAU_AIRE));
  const mece = Math.sin(0.21 * t + b.fase) * 16 * Math.min(1, t / 12);
  return {
    x: b.desde.x + b.vx * k + mece,
    y: b.desde.y + CAIDA * t + (b.vy - CAIDA) * k,
    giro: b.giro * k + 26 * Math.sin(0.21 * t + b.fase),
    vuelta: Math.cos(0.27 * t + b.fase * 2),
  };
};

/** El fotograma en que toca el suelo, buscado: la caída no tiene fórmula cerrada. */
const aterriza = (b: Billete) => {
  let t = 1;
  while (t < 900 && vuela(b, t).y < -4) t++;
  return t;
};

const Papel: React.FC<{ x: number; y: number; giro: number; vuelta: number; opacidad: number }> = ({
  x, y, giro, vuelta, opacidad,
}) => (
  <g
    transform={`translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${giro.toFixed(2)}) scale(1 ${vuelta.toFixed(3)})`}
    opacity={opacidad}
  >
    <rect x={-28} y={-14} width={56} height={28} fill={color.gold} />
    <rect x={-23} y={-9} width={46} height={18} fill="none" stroke={color.richBlack} strokeWidth={2} />
    <text y={7.5} textAnchor="middle" fontFamily={fontFamily.bloque} fontSize={21} fill={color.richBlack}>
      $
    </text>
  </g>
);

/** El papel en su fotograma: volando, posándose o ya en el suelo y yéndose. */
const enSuFotograma = (b: Billete, toca: number, f: number, i: number) => {
  const t = f - b.sale;
  if (t < 0) return null;
  if (t < toca) return <Papel key={i} {...vuela(b, t)} opacidad={1} />;
  const ultimo = vuela(b, toca);
  const posa = Math.min(1, (t - toca) / 6);
  const reposo = (azar(i * 7) - 0.5) * 30;
  const opacidad = 1 - Math.min(1, Math.max(0, (t - toca - 40) / 14));
  if (opacidad <= 0) return null;
  return (
    <Papel
      key={i}
      x={ultimo.x}
      y={-5}
      giro={ultimo.giro + (reposo - ultimo.giro) * posa}
      vuelta={ultimo.vuelta + (0.3 - ultimo.vuelta) * posa}
      opacidad={opacidad}
    />
  );
};

/** La chistera, sentada en la coronilla y torcida con gracia. */
const Chistera: React.FC<{ en: Punto; giro: number }> = ({ en, giro }) => (
  <g
    transform={`translate(${en.x.toFixed(2)} ${en.y.toFixed(2)}) rotate(${giro.toFixed(2)})`}
    stroke={color.lightNeutral}
    strokeWidth={5}
    strokeLinejoin="round"
  >
    <rect x={-27} y={-74} width={54} height={68} fill={color.richBlack} />
    <rect x={-27} y={-24} width={54} height={12} fill={color.secondaryBlue} />
    <rect x={-48} y={-8} width={96} height={8} fill={color.richBlack} />
  </g>
);

/** El fajo en la mano: tres billetes desplazados, que no se acaban. */
const Fajo: React.FC<{ en: Punto; giro: number }> = ({ en, giro }) => (
  <g transform={`translate(${en.x.toFixed(2)} ${en.y.toFixed(2)}) rotate(${giro.toFixed(2)}) scale(0.62)`}>
    {[-6, 0, 6].map((d) => (
      <g key={d} transform={`translate(${d} ${-d}) rotate(${d * 2})`}>
        <Papel x={0} y={0} giro={0} vuelta={1} opacidad={1} />
      </g>
    ))}
  </g>
);

const monta = (e: Escenario): Escena => {
  const tiros: number[] = [];
  for (let s = PRIMER_TIRO; s + SUELTA < e.dur; s += PERIODO) tiros.push(s);
  const pista = new Pista<Pose>(NEUTRA, [...claves, ...tiros.flatMap(tiro)]);
  // Mientras tira, la izquierda deja la jarra de vez en cuando: se rasca, mira
  // el reloj, se coloca la chistera.
  const varia = reposo({ desde: 90, libres: ["I"] });
  const poseEn = (f: number) => {
    const p = conVida((g) => pista.en(g), f);
    const m = manos.en(f);
    const c = articula(p).cadera;
    const enJarras = alcanza(p, { x: c.x - 16, y: c.y - 20 }, m.jarra, "I", -1);
    const bolsillo = { x: c.x + 26 + m.escarba * 0.5, y: c.y + 10 + m.escarba };
    return varia(alcanza(enJarras, bolsillo, m.bolsillo, "D", 1), f);
  };
  const cuerpoEn = (f: number) => articula(poseEn(f));
  // Salen de la mano en tres tandas seguidas, cada una de donde está la mano.
  const billetes: Billete[] = tiros.flatMap((s, n) => {
    const desde = [0, 1, 2].map((d) => cuerpoEn(s + SUELTA + d).manoD);
    return Array.from({ length: PUNADO }, (_, j) => {
      const r = (k: number) => azar(n * 31 + j * 7 + k);
      const angulo = ((155 + 95 * r(1)) * Math.PI) / 180;
      const fuerza = 17 + 9 * r(2);
      return {
        sale: s + SUELTA + (j % 3),
        desde: desde[j % 3],
        vx: Math.sin(angulo) * fuerza,
        vy: Math.cos(angulo) * fuerza,
        fase: r(3) * 6.28,
        giro: (r(4) - 0.5) * 16,
      };
    });
  });
  const tocan = billetes.map(aterriza);
  return {
    fotograma: (f) => {
      const pose = poseEn(f);
      const cuerpo = articula(pose);
      const cae = Math.min(1, CURVA.cae(Math.min(1, f / 9)));
      const asiento = {
        x: cuerpo.cabeza.x + Math.sin((cuerpo.arriba * Math.PI) / 180) * 30,
        y: cuerpo.cabeza.y + Math.cos((cuerpo.arriba * Math.PI) / 180) * 30 - (1 - cae) * (e.techo + 100),
      };
      const giroSombrero = 180 - cuerpo.arriba + 8 + (1 - cae) * 30 + asienta(f - 9, -14, 9, 0.22);
      const brazo = cuerpo.manoD;
      const antebrazo =
        (Math.atan2(cuerpo.manoD.y - cuerpo.codoD.y, cuerpo.manoD.x - cuerpo.codoD.x) * 180) / Math.PI;
      return {
        cuerpo,
        pose,
        delante: (
          <>
            <Chistera en={asiento} giro={giroSombrero} />
            {f >= 33 ? <Fajo en={brazo} giro={antebrazo + 90} /> : null}
            {billetes.map((b, i) => enSuFotograma(b, tocan[i], f, i))}
          </>
        ),
      };
    },
    sonidos: [
      { motion: "land", at: 9 },
      ...tiros.slice(0, 3).map((s) => ({ motion: "whoosh" as const, at: s + 4 })),
    ],
  };
};

export const millonario: Accion = { alto: 445, ancho: 360, texto: "lado", monta };
