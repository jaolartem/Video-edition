import React from "react";
import type { Accion, Escena, Escenario } from "./accion";
import { CURVA, articula, mezclaPose, rampa } from "./rig";

/**
 * **Varias acciones en una etapa, una detrás de otra** (`acciones` de `Palote`).
 *
 * Jaime: *«parte de research, resume, script, todo eso tiene que estar el
 * muñequito haciendo cada una de esas acciones»*. Una etapa como reel-23 e12
 * dice cuatro pasos en 9,7 s, y un personaje que hace sólo el primero se queda
 * investigando mientras la voz ya va por la solicitud.
 *
 * Cada acción se monta entera, como si la etapa fuera suya, y dura hasta que
 * entra la siguiente. El paso de una a otra **no corta**: durante `FUNDE`
 * fotogramas las dos siguen vivas, el cuerpo va de la pose de una a la de la
 * otra ángulo a ángulo —el brazo hace su arco, no salta— y lo que lleva cada
 * una se funde. Nada se queda quieto en la costura.
 */

/** Lo que tarda en pasar de una acción a la siguiente. */
export const FUNDE = 12;

export type Paso = { papel: Accion; en: number };

/** El papel de varias: el sitio que pide la más alta y la más ancha. */
export const juntas = (papeles: Accion[]): Accion => ({
  alto: Math.max(...papeles.map((p) => p.alto)),
  ancho: Math.max(...papeles.map((p) => p.ancho)),
  texto: papeles.every((p) => p.texto === "lado") ? "lado" : "arriba",
  monta: () => {
    throw new Error("Palote: un papel juntado no se monta; se encadena");
  },
});

export const encadena = (pasos: Paso[], e: Escenario): Escena => {
  const montadas = pasos.map((p, i) => {
    const fin = pasos[i + 1]?.en ?? e.dur;
    return p.papel.monta({ ...e, dur: fin - p.en + FUNDE });
  });
  const cual = (f: number) => {
    let i = 0;
    while (i < pasos.length - 1 && pasos[i + 1].en <= f) i++;
    return i;
  };
  return {
    fotograma: (f) => {
      const i = cual(f);
      const ahora = montadas[i].fotograma(f - pasos[i].en);
      const t = f - pasos[i].en;
      if (i === 0 || t >= FUNDE) return ahora;
      const antes = montadas[i - 1].fotograma(f - pasos[i - 1].en);
      const w = CURVA.suave(rampa(t, 0, FUNDE));
      const pose = mezclaPose(antes.pose, ahora.pose, w);
      const funde = (a: React.ReactNode, b: React.ReactNode) =>
        React.createElement(React.Fragment, null,
          React.createElement("g", { opacity: 1 - w }, a),
          React.createElement("g", { opacity: w }, b));
      return {
        pose,
        cuerpo: articula(pose),
        detras: funde(antes.detras, ahora.detras),
        delante: funde(antes.delante, ahora.delante),
      };
    },
    // Cada acción suena en su tramo: lo que caería después de la siguiente no
    // se oye, porque ya no se ve.
    sonidos: montadas.flatMap((m, i) => {
      const fin = (pasos[i + 1]?.en ?? e.dur) - pasos[i].en;
      return m.sonidos.filter((s) => s.at < fin).map((s) => ({ ...s, at: s.at + pasos[i].en }));
    }),
  };
};
