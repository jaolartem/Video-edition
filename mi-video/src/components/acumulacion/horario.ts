import { Reloj } from "../../brand/horario";
import { duration } from "../../brand/tokens";
import type { AcumulacionProps } from "./tipos";

export type Horario = {
  /** La raya se traza antes de que la barra llegue. */
  raya: number;
  /** Frame en que entra cada tramo. */
  entradas: number[];
  finTramos: number;
  /** La cifra de resultado, y el golpe que la acompaña. */
  resultadoAt: number;
  /** La banda de la condición: entra la última y con la barra ya quieta. */
  condicionAt: number;
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
}: Pick<AcumulacionProps, "tramos" | "condicion">): Horario => {
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

  return {
    raya,
    entradas,
    finTramos,
    resultadoAt: finTramos + 6,
    condicionAt: finTramos + 14,
    duracion: reloj.lee(condicion).espera(20).ahora,
  };
};

/** Lo que el spec tiene que reservar para este tablero. */
export const duracionDe = (props: AcumulacionProps): number =>
  horarioDe(props).duracion;
