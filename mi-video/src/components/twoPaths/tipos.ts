import type { Mode } from "../../brand/tokens";

/**
 * **El contrato de cumplimiento de las dos trayectorias.**
 *
 * Vive aparte del dibujo a propósito: lo que el playbook exige de una
 * comparación no es una decisión de composición y no debería poder perderse al
 * reordenar un tablero. Aquí se declara, y los tipos lo hacen imposible de
 * olvidar — un incumplimiento no es una revisión pendiente, es un fallo de
 * compilación.
 */

type ComparedPathBase = {
  /** Nombre de la trayectoria, p.ej. "Por defecto". */
  label: string;
  /** Los pasos que la componen. Dos a cuatro caben legibles en media columna. */
  steps: string[];
  /** Dónde termina. */
  outcome: string;
};

/** Una cifra de resultado nunca aparece sin fuente. Lo garantiza el tipo. */
export type ComparedPath =
  | (ComparedPathBase & { figure?: never; source?: never })
  | (ComparedPathBase & { figure: string; source: string });

export type TwoPathsProps = {
  /**
   * Las condiciones iniciales, comunes a las dos trayectorias. El playbook
   * exige que el punto de partida sea el mismo: si difiere, la comparación no
   * es honesta.
   */
  start: string;
  /**
   * El horizonte temporal compartido. **Obligatorio.** El playbook exige "the
   * same time horizon" para que la comparación sea válida, así que el
   * componente no se puede instanciar sin declararlo.
   */
  horizon: string;
  byDefault: ComparedPath;
  deliberate: ComparedPath;
  /**
   * Qué condición cambiaría la comparación. **Obligatorio.** El playbook
   * prohíbe presentar el camino deliberado como universalmente superior sin
   * condiciones del caso concreto; hacerlo prop requerido impide que se caiga.
   */
  condition: string;
  /** La diferencia acumulada entre ambas. Cifra y fuente, o ninguna de las dos. */
  difference?: { figure: string; source: string };
  mode?: Mode;
  title?: string;
  /**
   * Emite el efecto de sonido de cada movimiento. **Requiere los ficheros de
   * `public/sfx/`**, que aún no existen — por eso está apagado por defecto.
   */
  sound?: boolean;
};
