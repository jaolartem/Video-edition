import { Reloj } from "../../brand/horario";
import { beat, duration } from "../../brand/tokens";
import type { AcumulacionProps } from "./tipos";

export type Horario = {
  /** La raya se traza antes de que la barra llegue. */
  raya: number;
  /** Frame en que entra cada tramo. */
  entradas: number[];
  finTramos: number;
  /**
   * **El barrido**, o `null` si esta acumulación no produce una cifra.
   *
   * Jaime, aprobando el cierre de la lámina de la e2: *«que puede borrar el
   * panel o parte de él, pero debe salir súper enfático»*. Cuando la pila está
   * entera, lo que la construyó se retira y la cifra se queda sola en el cuadro
   * — mientras el diagrama sigue puesto el ojo está en los bloques y el total es
   * un renglón más. Es la carga cognitiva llevada al tiempo: no poner menos,
   * sino que en cada instante haya **una sola cosa**.
   *
   * Sin `resultado` no hay nada que dejar solo, así que no hay barrido: en R3 y
   * R5 lo que el tablero dice es que la barra cruzó una raya, y eso se dice
   * quedándose.
   */
  barrido: number | null;
  /** La banda del pie: entra la última y con la pila ya quieta. */
  pieAt: number;
  /**
   * Cuánto dura el tablero completo, en frames.
   *
   * **Un componente con horario propio necesita su tiempo.** El spec pregunta
   * en vez de poner un número redondo: con 5,5 s el tablero mostraba sólo la
   * cabecera y el pie, y en el render parecía vacío cuando lo que estaba era a
   * medio construir.
   */
  duracion: number;
};

/** Lo que tarda el barrido en llevarse el diagrama y dejar la cifra. */
export const BARRE = 16;

/**
 * Cuándo entra cada cosa, en cadena por tiempo de lectura.
 *
 * **Estaba escrito dos veces en el mismo fichero**: el bucle de aquí y el de
 * `duracionDe`, con el mismo cálculo copiado. Que coincidieran era suerte, y la
 * avería que preparaban es de las caras: el spec reserva un hueco de un largo y
 * el tablero se construye en otro, así que la pieza sale con un tablero a medio
 * montar y nada que lo denuncie.
 */
export const horarioDe = ({
  tramos,
  condicion,
  resultado,
}: Pick<AcumulacionProps, "tramos" | "condicion" | "resultado">): Horario => {
  const raya = duration.entry * 2;
  const reloj = new Reloj(raya + duration.entry);
  const entradas: number[] = [];

  for (const tr of tramos) {
    entradas.push(reloj.ahora);
    // Suelo de entrada + 4: una etiqueta de dos palabras no puede entrar antes
    // de que el bloque que la trae haya acabado de crecer.
    reloj.lee(tr.etiqueta, duration.entry + 4);
  }
  const finTramos = reloj.ahora;
  // El silencio antes del remate: la pila entera se sostiene un momento y
  // entonces se la lleva el barrido. Sin la pausa, el último bloque y la cifra
  // llegan en el mismo suspiro y no se ve que uno produce la otra.
  const barrido = resultado ? finTramos + beat.hold : null;

  return {
    raya,
    entradas,
    finTramos,
    barrido,
    pieAt: finTramos + 14,
    duracion:
      barrido === null
        ? reloj.lee(condicion).espera(20).ahora
        : new Reloj(barrido + BARRE).lee(resultado?.figure ?? "").espera(20)
            .ahora,
  };
};

/** Lo que el spec tiene que reservar para este tablero. */
export const duracionDe = (props: AcumulacionProps): number =>
  horarioDe(props).duracion;
