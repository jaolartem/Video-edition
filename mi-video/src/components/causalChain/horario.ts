import { Reloj } from "../../brand/horario";
import { beat } from "../../brand/tokens";
import type { CausalChainProps } from "./tipos";

export type Horario = {
  /** Frame en que se revela cada nodo. */
  at: number[];
  /**
   * Frame en que el tablero se retira y entra el límite legal, o `null` si la
   * pieza no declara ninguno.
   *
   * **Era un número siempre.** El tablero se desvanecía en ese frame llevara o
   * no llevara `limitation`, así que una cadena sin límite declarado acababa en
   * un cuadro vacío: la retirada ocurría igual y no entraba nada a ocupar el
   * sitio. Ahora la retirada es de él, no del calendario.
   */
  limiteAt: number | null;
};

/**
 * Calendario derivado del **tiempo de lectura**, no de un stagger fijo.
 *
 * Un enunciado largo necesita más pantalla que uno corto; repartir a intervalos
 * iguales deja unos ilegibles y otros muertos. `revealAt` lo sustituye entero
 * cuando el montaje ancla los nodos a palabras del transcript, que es lo que se
 * usa en la pieza final.
 */
export const horarioDe = ({
  nodes,
  revealAt,
  emphasizePayoff = true,
  limitation,
}: Pick<
  CausalChainProps,
  "nodes" | "revealAt" | "emphasizePayoff" | "limitation"
>): Horario => {
  const at: number[] = [];
  const reloj = new Reloj();

  nodes.forEach((node, index) => {
    /** Silencio antes del remate: una cadena a ritmo constante no aprieta. */
    if (emphasizePayoff && index === nodes.length - 1 && nodes.length > 1) {
      reloj.espera(beat.hold);
    }
    const entra = revealAt?.[index] ?? reloj.ahora;
    at.push(entra);
    reloj.en(entra).lee(node.text).espera(beat.stagger);
  });

  return {
    at,
    limiteAt: limitation === undefined ? null : reloj.espera(beat.hold).ahora,
  };
};
