import React from "react";
import { Ad } from "./Ad";
import { BigTitle } from "./components/BigTitle";
import { FPS } from "./brand/tokens";
import spec from "./ganchos.json";

/**
 * Los seis ganchos, cada uno con su rótulo.
 *
 * **Regla del proyecto: todo gancho lleva rótulo visual.** No es adorno — el
 * playbook exige que el argumento funcione sin audio, y en los primeros
 * segundos, que es donde se decide si alguien se queda, el texto es lo único
 * que se lee sin sonido.
 *
 * El rótulo **cede en un corte posterior a su frase**, no en el primero. La
 * regla anterior —ceder en el primer cambio de plano— fallaba en los seis: el
 * texto se retiraba antes de que Jaime dijera la línea. En el reel 1 la decía en
 * el segundo 6,5 y el rótulo se iba en el 3,0. Un rótulo que no está puesto
 * cuando suena su frase no refuerza nada.
 *
 * El texto es **ancla, no transcripción**: recoge la idea que carga el gancho
 * en las menos palabras posibles. La voz lleva el resto.
 *
 * Duración y corte vienen de `ganchos.json`, que **genera
 * `scripts/ganchos-spec.mjs` desde los planes de escena**. Estuvieron a mano y
 * el primer cambio de montaje los desincronizó: al alargar la salida del reel 5
 * y rehacer la del 6, el rótulo cedía en un corte que ya no existía y la
 * composición duraba menos que el vídeo. Lo derivable se deriva; lo que es
 * decisión —el texto— vive en el generador.
 */
export type GanchoSpec = {
  id: string;
  /** Fichero en `public/`, ya cortado y con encuadres aplicados. */
  video: string;
  /** Duración total del gancho, en segundos. */
  duracion: number;
  /** Segundo en que se termina de decir la frase del rótulo. */
  dicho: number | null;
  /** Frame en que ENTRA el rótulo: el de la palabra que subraya. */
  entra: number;
  /**
   * Segundo en que cede el rótulo, o `null` si no cede.
   *
   * Es un cambio de plano que llega con el texto **leído y ya dicho**. Si
   * ninguno cumple las dos cosas, el rótulo se queda hasta el final: antes eso
   * que retirarlo justo cuando hace falta.
   */
  corte: number | null;
  /** Cuántos encuadres distintos recorre. */
  escenas: number;
  /** Dos líneas como mucho. Más no se lee a velocidad de scroll. */
  lineas: string[];
};

export const GANCHOS: GanchoSpec[] = spec;

export const Gancho: React.FC<{ spec: GanchoSpec }> = ({ spec: g }) => (
  <>
    <Ad video={g.video} mode="evidence" />
    <BigTitle
      lineas={g.lineas}
      entraEn={g.entra ?? Math.round((g.dicho ?? 0) * FPS)}
    />
  </>
);
