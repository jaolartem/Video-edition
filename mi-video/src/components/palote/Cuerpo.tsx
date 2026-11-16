import React from "react";
import { HUESO, type Articulaciones, type Punto } from "./rig";

/**
 * **El cuerpo del palote**, desde sus articulaciones. Pieza interna.
 *
 * No se pide aparte: lo usa cada acción de `Palote`.
 *
 * Un solo color y un solo trazo, grueso y de punta redonda, con la cabeza
 * hueca: el registro de las figuras de Alan Becker que trajo Jaime, sin su
 * naranja. Las rodillas y los codos son la unión redonda de dos tramos de la
 * misma línea —no círculos puestos encima—, que es lo que hace que una pierna
 * doblada se lea como pierna y no como dos palos.
 */
const traza = (puntos: Punto[]) =>
  puntos
    .map((p, i) => `${i ? "L" : "M"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(" ");

/**
 * Dónde asoma el bíceps: sobre el brazo, del lado al que se dobla el
 * antebrazo, y hacia dónde empuja. Con el brazo estirado no hay lado: `null`.
 */
export const bulto = (hombro: Punto, codo: Punto, mano: Punto, cuanto: number) => {
  const ux = (codo.x - hombro.x) / HUESO.brazo;
  const uy = (codo.y - hombro.y) / HUESO.brazo;
  const fx = (mano.x - codo.x) / HUESO.antebrazo;
  const fy = (mano.y - codo.y) / HUESO.antebrazo;
  const proyeccion = fx * ux + fy * uy;
  const n = Math.hypot(fx - proyeccion * ux, fy - proyeccion * uy);
  if (cuanto <= 0.01 || n < 0.2) return null;
  const nx = (fx - proyeccion * ux) / n;
  const ny = (fy - proyeccion * uy) / n;
  const sobre = HUESO.trazo * 0.32 + 6 * cuanto;
  return {
    cx: hombro.x + ux * HUESO.brazo * 0.6 + nx * sobre,
    cy: hombro.y + uy * HUESO.brazo * 0.6 + ny * sobre,
    nx,
    ny,
    giro: (Math.atan2(uy, ux) * 180) / Math.PI,
  };
};

const Biceps: React.FC<{
  hombro: Punto;
  codo: Punto;
  mano: Punto;
  cuanto: number;
  tinte: string;
}> = ({ hombro, codo, mano, cuanto, tinte }) => {
  const b = bulto(hombro, codo, mano, cuanto);
  if (!b) return null;
  const { cx, cy, giro } = b;
  return (
    <ellipse
      cx={cx}
      cy={cy}
      rx={HUESO.brazo * 0.3 * Math.min(cuanto, 1.4)}
      ry={HUESO.brazo * 0.19 * cuanto}
      transform={`rotate(${giro.toFixed(2)} ${cx.toFixed(2)} ${cy.toFixed(2)})`}
      fill={tinte}
    />
  );
};

export const Cuerpo: React.FC<{ a: Articulaciones; tinte: string }> = ({ a, tinte }) => (
  <g
    fill="none"
    stroke={tinte}
    strokeWidth={HUESO.trazo}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d={traza([a.puntaI, a.tobilloI, a.rodillaI, a.cadera])} />
    <path d={traza([a.puntaD, a.tobilloD, a.rodillaD, a.cadera])} />
    <path d={traza([a.cadera, a.pecho, a.nuca])} />
    <path d={traza([a.hombros, a.raizI, a.codoI, a.manoI])} />
    <path d={traza([a.hombros, a.raizD, a.codoD, a.manoD])} />
    <circle cx={a.cabeza.x} cy={a.cabeza.y} r={HUESO.cabeza} />
    <g stroke="none">
      <Biceps hombro={a.raizI} codo={a.codoI} mano={a.manoI} cuanto={a.biceps} tinte={tinte} />
      <Biceps hombro={a.raizD} codo={a.codoD} mano={a.manoD} cuanto={a.biceps} tinte={tinte} />
    </g>
  </g>
);
