import { color } from "../../brand/tokens";
import type { Accion, Escena, Escenario } from "./accion";
import { Avion } from "./Oficina";
import { reposo } from "./reposo";
import { CURVA, NEUTRA, Pista, alcanza, articula, espejo, rampa, type Clave, type Pose, type Punto } from "./rig";
import { conVida } from "./vida";

/**
 * **Aplicación**: pliega la hoja en avión de papel y lo lanza.
 *
 * Para *the application* —lo que por fin se envía—. La hoja le cae en las
 * manos, la pliega en dos golpes y en el 28 ya es un avión con el pliegue de
 * oro; coge impulso por encima del hombro y lo suelta en el 40. El avión sale
 * hacia el borde del cuadro —nunca hacia él, ni hacia el texto— dejando su
 * estela de oro, y el palote se hace visera con la mano para verlo irse.
 * Cada cuatro segundos manda otra: las solicitudes no se mandan de una en una.
 */

/** Lo que dura un envío entero, de la hoja que cae al avión que se pierde. */
const CICLO = 120;
const PLIEGA = [10, 28] as const;
const SUELTA = 40;

const claves: Clave<Pose>[] = [
  { f: 0, ...NEUTRA },
  { f: 6, c: CURVA.suave, cuello: -8 },
  { f: 12, c: CURVA.suave, cuello: 10, pecho: -2 },
  // Impulso: se echa atrás, el peso en la pierna de detrás.
  { f: 32, c: CURVA.suave, tronco: -4, cuello: -6, caderaI: -14, rodillaI: 14, caderaD: 18, rodillaD: -12 },
  // Lo suelta y el cuerpo sigue al brazo.
  { f: SUELTA, c: CURVA.sale, tronco: 12, cuello: 10, caderaI: -10, rodillaI: 2, caderaD: 12, rodillaD: -6, pecho: 4 },
  { f: 48, c: CURVA.suave, tronco: 7, cuello: 16 },
  { f: 66, c: CURVA.suave, tronco: 5, cuello: 18 },
  { f: 86, c: CURVA.suave, ...NEUTRA },
  { f: CICLO, ...NEUTRA },
];

/** La hoja: cae a las manos y se queda delante del pecho mientras se pliega. */
const hoja = new Pista({ x: 20, y: -560, giro: 24 }, [
  { f: 0, x: 20, y: -560, giro: 24 },
  { f: 10, c: CURVA.sale, x: 0, y: -215, giro: 0 },
]);
/** La derecha: borde de la hoja, impulso por encima del hombro, suelta y sigue. */
const derecha = new Pista({ x: 37, y: -215 }, [
  { f: 26, x: 30, y: -222 },
  { f: 34, c: CURVA.suave, x: 118, y: -356 },
  { f: SUELTA, c: CURVA.cae, x: 96, y: -330 },
  { f: 48, c: CURVA.sale, x: 112, y: -250 },
]);
const manos = new Pista({ sujeta: 0, lanza: 0, visera: 0 }, [
  { f: 6, sujeta: 0, lanza: 0 },
  { f: 12, c: CURVA.sale, sujeta: 1 },
  { f: 26, sujeta: 1, lanza: 0 },
  { f: 30, c: CURVA.suave, sujeta: 0, lanza: 1 },
  { f: 46, lanza: 1 },
  { f: 60, c: CURVA.suave, lanza: 0 },
  { f: SUELTA + 2, visera: 0 },
  { f: 50, c: CURVA.suave, visera: 1 },
  { f: 66, visera: 1 },
  { f: 78, c: CURVA.suave, visera: 0 },
]);

/** El vuelo desde donde se suelta, hacia `d`: sube, se aplana y sigue. */
const vuelo = (desde: Punto, t: number, d: number) => ({
  x: desde.x + d * 15 * t,
  y: desde.y - 11 * t + 0.11 * t * t,
  giro: -24 + 0.9 * t,
});

const monta = (e: Escenario): Escena => {
  const d = -e.senal;
  const pista = new Pista<Pose>(NEUTRA, claves);
  const enCiclo = (f: number) => ((f % CICLO) + CICLO) % CICLO;
  const varia = reposo({ desde: 40, libres: d > 0 ? ["I", "D"] : ["D", "I"], cada: CICLO, semilla: 4 });
  /** La pose de cara a la derecha, que es como está escrita; se refleja si sale a la izquierda. */
  const canonica = (f: number): Pose => {
    const r = enCiclo(f);
    const p = conVida((g) => pista.en(enCiclo(g)), f, 1);
    const m = manos.en(r);
    const h = hoja.en(r);
    const borde = 37 * (1 - CURVA.suave(rampa(r, ...PLIEGA))) + 26;
    const izq = { x: h.x - borde, y: h.y + 4 };
    const cab = articula(p).cabeza;
    const visera = { x: cab.x + 8, y: cab.y - 6 };
    const conIzq = alcanza(alcanza(p, izq, m.sujeta, "I", 1), visera, m.visera, "I", 1);
    const der = r < 26 ? { x: h.x + borde, y: h.y + 4 } : derecha.en(r);
    return alcanza(conIzq, der, Math.max(m.sujeta, m.lanza), "D", -1);
  };
  const poseEn = (f: number) => varia(d > 0 ? canonica(f) : espejo(canonica(f)), f);
  return {
    fotograma: (f) => {
      const pose = poseEn(f);
      const cuerpo = articula(pose);
      const r = enCiclo(f);
      const vuelta = Math.floor(f / CICLO);
      const h = hoja.en(r);
      const manoLanza = d > 0 ? cuerpo.manoD : cuerpo.manoI;
      const suelta = articula(poseEn(vuelta * CICLO + SUELTA))[d > 0 ? "manoD" : "manoI"];
      const enMano = r >= 26 && r < SUELTA;
      const t = r - SUELTA;
      const avion = r < 26
        ? { x: h.x * d, y: h.y, giro: h.giro }
        : enMano
          ? { x: manoLanza.x + 8 * d, y: manoLanza.y - 8, giro: -14 }
          : vuelo(suelta, t, d);
      const estela = t > 0
        ? [0, 3, 6, 9, 12].map((k) => vuelo(suelta, Math.max(0, t - k), d))
          .map((v) => `${v.x.toFixed(1)} ${v.y.toFixed(1)}`)
        : [];
      return {
        cuerpo,
        pose,
        delante: (
          <>
            {estela.length ? (
              <path d={`M ${estela.join(" L ")}`} fill="none" stroke={color.gold} strokeWidth={5}
                strokeDasharray="10 12" strokeLinecap="round" opacity={1 - rampa(t, 30, 50)} />
            ) : null}
            {t < 60 ? (
              <Avion en={avion} pliega={CURVA.suave(rampa(r, ...PLIEGA))} giro={avion.giro} d={d} />
            ) : null}
          </>
        ),
      };
    },
    sonidos: [0, CICLO].filter((s) => s + SUELTA < e.dur).flatMap((s) => [
      { motion: "mark" as const, at: s + PLIEGA[1] },
      { motion: "whoosh" as const, at: s + SUELTA - 2 },
    ]),
  };
};

export const aplicacion: Accion = { alto: 450, ancho: 320, texto: "lado", monta };
