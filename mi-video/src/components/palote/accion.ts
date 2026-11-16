import type React from "react";
import type { Motion } from "../../brand/sfx";
import type { Articulaciones, Pose } from "./rig";

/**
 * **Lo que una acción del palote le debe al tablero**, y lo que el tablero le
 * da a cambio.
 *
 * El tablero no sabe qué hace el personaje: sabe dónde cabe. La acción le dice
 * cuánto sitio necesita; el tablero le da el ancho del escenario y lo que dura,
 * y la acción le devuelve, fotograma a fotograma, el cuerpo y lo que lleva
 * alrededor —el sombrero, los billetes, los motores—, más lo que suena. Una
 * acción nueva es un fichero que cumple esto, y `Palote` la monta sin cambiar.
 */
export type Escenario = {
  /** El ancho del escenario en unidades del personaje, centrado en 0. */
  ancho: number;
  /** Del suelo al borde de arriba del cuadro, en unidades: lo que cae, cae de ahí. */
  techo: number;
  /** Lo que dura el tablero, en fotogramas: la acción vive hasta el último. */
  dur: number;
  /** Los nombres de las dos tablas, para quien las dibuja. */
  tablas: [string, string];
  /**
   * Hacia dónde queda lo que acompaña, `1` a la derecha y `-1` a la izquierda:
   * a pleno, el texto; acompañándolo, él. Hacia ahí señala, y lo que lanza sale
   * hacia el otro lado, que es el borde del cuadro y no su cara.
   */
  senal: 1 | -1;
};

/** Un fotograma de la acción: el cuerpo y lo que va detrás y delante de él. */
export type Fotograma = {
  cuerpo: Articulaciones;
  /** La pose de la que sale el cuerpo: lo que se mezcla al pasar de una acción a otra. */
  pose: Pose;
  detras?: React.ReactNode;
  delante?: React.ReactNode;
};

/** La acción montada sobre su escenario. */
export type Escena = {
  fotograma: (f: number) => Fotograma;
  /** El efecto de cada movimiento, en el fotograma en que se mueve. */
  sonidos: { motion: Motion; at: number }[];
};

export type Accion = {
  /** Cuánto sube por encima del suelo, en unidades, con lo que lleva puesto. */
  alto: number;
  /** El ancho mínimo que necesita su escenario, en unidades. */
  ancho: number;
  /**
   * Dónde va el texto en un cuadro apaisado: a su `lado`, o `arriba` cuando el
   * escenario necesita el ancho entero. En vertical va siempre arriba.
   */
  texto: "lado" | "arriba";
  monta: (e: Escenario) => Escena;
};
