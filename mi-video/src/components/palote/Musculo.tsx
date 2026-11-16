import React from "react";
import { color } from "../../brand/tokens";
import type { Accion, Escena, Escenario } from "./accion";
import { bulto } from "./Cuerpo";
import { CURVA, NEUTRA, Pista, articula, type Articulaciones, type Clave, type Pose } from "./rig";
import { conVida } from "./vida";

/**
 * **Músculo**: se planta derecho, sube los dos brazos y le sale el bíceps.
 *
 * Para lo que se gana con repetición — *judgment is muscle memory*.
 *
 * Jaime: *«que se pare derecho y flexione los dos brazos y que de los brazos
 * le salga músculo, la imagen tradicional»*. Coge impulso agachándose, da un
 * saltito y cae abierto de piernas en el 18; los brazos llegan arriba pasados
 * de vuelta y el bíceps revienta en el 21 —más grande de lo que se queda— y se
 * asienta. Luego se mira un brazo, el otro, y sigue sacando bola cada segundo
 * y medio mientras dure el tablero.
 */

/** La pose de los dos bíceps, la de siempre: codos a la altura del hombro. */
const ARRIBA = { hombroI: -98, codoI: -74, hombroD: 98, codoD: 74 };
const ABIERTO = { caderaI: -17, rodillaI: 6, caderaD: 17, rodillaD: -6 };

const claves: Clave<Pose>[] = [
  { f: 0, ...NEUTRA },
  { f: 5, ...NEUTRA },
  // Impulso: se agacha y junta los puños delante, cargando.
  { f: 11, c: CURVA.suave, caderaI: -24, rodillaI: 36, caderaD: 24, rodillaD: -36,
    hombroI: -25, codoI: 70, hombroD: 25, codoD: -70, pecho: -6, cuello: 0 },
  // Saltito: estira las piernas y los brazos salen hacia arriba.
  { f: 15, c: CURVA.sale, alza: 20, caderaI: -14, rodillaI: 0, caderaD: 14, rodillaD: 0,
    hombroI: -70, codoI: -40, hombroD: 70, codoD: 40, pecho: 4 },
  // Cae abierto, amortigua y se planta.
  { f: 18, c: CURVA.cae, alza: 0, ...ABIERTO },
  { f: 21, c: CURVA.sale, caderaI: -25, rodillaI: 24, caderaD: 25, rodillaD: -24 },
  { f: 27, c: CURVA.suave, ...ABIERTO },
  // Los brazos llegan pasados de vuelta y vuelven a su sitio.
  { f: 20, c: CURVA.sale, hombroI: -110, codoI: -86, hombroD: 110, codoD: 86, pecho: 7 },
  { f: 28, c: CURVA.suave, ...ARRIBA, pecho: 3 },
  // El bíceps revienta y se asienta.
  { f: 19, biceps: 0 },
  { f: 23, c: CURVA.sale, biceps: 1.34 },
  { f: 28, c: CURVA.suave, biceps: 0.9 },
  { f: 33, c: CURVA.suave, biceps: 1.04 },
  { f: 37, c: CURVA.suave, biceps: 1 },
  // Se mira un brazo y luego el otro, orgulloso.
  { f: 30, cuello: 0, tronco: 0 },
  { f: 40, cuello: 18, tronco: 4 },
  { f: 54, cuello: 16, tronco: 3 },
  { f: 64, cuello: -18, tronco: -4 },
  { f: 76, cuello: -16, tronco: -3 },
  { f: 84, cuello: 0, tronco: 0 },
];

/** Desde aquí, cada cuánto vuelve a sacar bola. */
const PRIMER_BOMBEO = 90;
const PERIODO = 44;
/** En qué fotograma del bombeo revienta. */
const REVIENTA = 11;

/** Un bombeo: baja un poco los puños, aprieta y el bíceps se hincha y vuelve. */
const bombeo = (s: number, n: number): Clave<Pose>[] => [
  { f: s, ...ARRIBA, biceps: 1, ...ABIERTO, pecho: 3 },
  { f: s + 6, c: CURVA.suave, hombroI: -92, codoI: -56, hombroD: 92, codoD: 56, biceps: 0.92,
    caderaI: -21, rodillaI: 16, caderaD: 21, rodillaD: -16, pecho: 0 },
  { f: s + REVIENTA, c: CURVA.sale, hombroI: -104, codoI: -86, hombroD: 104, codoD: 86, biceps: 1.2,
    ...ABIERTO, pecho: 6 },
  { f: s + 20, c: CURVA.suave, ...ARRIBA, biceps: 1, pecho: 3 },
  { f: s + 14, cuello: 0, tronco: 0 },
  { f: s + 24, c: CURVA.suave, cuello: n % 2 ? -12 : 12, tronco: n % 2 ? -2 : 2 },
  { f: s + 38, c: CURVA.suave, cuello: 0, tronco: 0 },
];

/** Las tres rayas del «¡pop!», saliendo del bíceps en el golpe. */
const Pop: React.FC<{ a: Articulaciones; t: number }> = ({ a, t }) => {
  if (t < 0 || t > 9) return null;
  const sale = Math.min(1, t / 3);
  const opacidad = 1 - Math.max(0, (t - 5) / 4);
  const lados = [
    bulto(a.raizI, a.codoI, a.manoI, a.biceps),
    bulto(a.raizD, a.codoD, a.manoD, a.biceps),
  ];
  return (
    <g stroke={color.lightNeutral} strokeWidth={6} strokeLinecap="round" opacity={opacidad}>
      {lados.flatMap((b, i) =>
        b
          ? [-38, 0, 38].map((g) => {
              const r = (g * Math.PI) / 180;
              const dx = b.nx * Math.cos(r) - b.ny * Math.sin(r);
              const dy = b.nx * Math.sin(r) + b.ny * Math.cos(r);
              const d0 = 24 + 6 * sale;
              const d1 = d0 + 16 * sale;
              return (
                <line
                  key={`${i}${g}`}
                  x1={b.cx + dx * d0}
                  y1={b.cy + dy * d0}
                  x2={b.cx + dx * d1}
                  y2={b.cy + dy * d1}
                />
              );
            })
          : [],
      )}
    </g>
  );
};

const monta = (e: Escenario): Escena => {
  const bombeos: number[] = [];
  for (let s = PRIMER_BOMBEO; s + REVIENTA < e.dur; s += PERIODO) bombeos.push(s);
  const pista = new Pista<Pose>(NEUTRA, [...claves, ...bombeos.flatMap(bombeo)]);
  const golpes = [21, ...bombeos.map((s) => s + REVIENTA)];
  return {
    fotograma: (f) => {
      // Entre bombeo y bombeo, posa: pasa el peso de una pierna a otra y el
      // bíceps late. Nunca se queda clavado en la pose.
      const posa = Math.min(1, Math.max(0, (f - 40) / 30));
      const pose = conVida((g) => pista.en(g), f, 1.2 + 2.6 * posa);
      pose.biceps += 0.05 * posa * Math.sin((2 * Math.PI * f) / 18);
      const cuerpo = articula(pose);
      const ultimo = golpes.filter((g) => g <= f).pop() ?? -99;
      return { cuerpo, delante: <Pop a={cuerpo} t={f - ultimo} /> };
    },
    sonidos: [
      { motion: "whoosh", at: 12 },
      { motion: "land", at: 18 },
      { motion: "mark", at: 21 },
      ...bombeos.slice(0, 1).map((s) => ({ motion: "mark" as const, at: s + REVIENTA })),
    ],
  };
};

export const musculo: Accion = { alto: 405, ancho: 340, texto: "lado", monta };
