import { Reloj } from "../../brand/horario";
import { beat, duration, readingFrames } from "../../brand/tokens";
import type { TwoPathsProps } from "./tipos";

/**
 * Separación entre el paso de una trayectoria y el equivalente de la otra.
 * Medio segundo: suficiente para que el ojo registre que son la misma decisión
 * resuelta de dos maneras, no dos frases sueltas.
 */
const PAREJA = 14;

export type Horario = {
  startAt: number;
  forkAt: number;
  /** Frame de entrada del paso `i` en cada columna. */
  pairs: { left: number; right: number }[];
  outcomeAt: number;
  differenceAt: number;
};

/**
 * Cuándo entra cada cosa.
 *
 * Los pasos se construyen **intercalados**, no una columna entera y luego la
 * otra. El argumento no es "aquí está el camino A y aquí el B": es que en cada
 * decisión los dos hacen algo distinto. Se ve cuando el paso `i` de ambas
 * aparece casi a la vez y la bifurcación se ensancha delante del espectador.
 * Revelar cada columna de golpe convierte la divergencia en dos listas
 * paralelas, que es otra cosa y más floja.
 */
export const horarioDe = ({
  start,
  byDefault,
  deliberate,
}: Pick<TwoPathsProps, "start" | "byDefault" | "deliberate">): Horario => {
  const startAt = 0;
  const forkAt = startAt + readingFrames(start);
  const pasos = Math.max(byDefault.steps.length, deliberate.steps.length);

  const pairs: { left: number; right: number }[] = [];
  const reloj = new Reloj(forkAt + duration.standard);

  for (let i = 0; i < pasos; i++) {
    const left = reloj.ahora;
    const right = left + PAREJA;
    pairs.push({ left, right });
    // La pareja avanza al ritmo del paso más lento de las dos: los dos tienen
    // que poder leerse antes de que llegue la siguiente decisión.
    reloj
      .en(right)
      .lee(byDefault.steps[i] ?? "", readingFrames(deliberate.steps[i] ?? ""));
  }

  /** Pausa antes del resultado: la consecuencia no llega a ritmo de paso. */
  const outcomeAt = reloj.espera(beat.hold).ahora;
  const differenceAt = reloj
    .lee(byDefault.outcome, readingFrames(deliberate.outcome))
    .ahora;

  return { startAt, forkAt, pairs, outcomeAt, differenceAt };
};
