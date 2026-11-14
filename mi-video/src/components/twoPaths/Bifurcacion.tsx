import React from "react";
import { useLienzo } from "../../brand/LienzoContexto";


const ALTO = 72;

/**
 * La bifurcación en diagonal. La asimetría diagonal es recurso obligatorio del
 * sistema en composiciones editoriales, y aquí además es literal: el dibujo ES
 * el argumento — dos trayectorias que se separan desde el mismo origen.
 *
 * Se traza, no aparece: `strokeDashoffset` sobre `pathLength={1}` hace que la
 * línea se dibuje como se dibujaría a mano, y por eso el sonido que le
 * corresponde es el del trazo y no un golpe.
 */
export const Bifurcacion: React.FC<{
  progress: number;
  defaultInk: string;
  deliberateInk: string;
}> = ({ progress, defaultInk, deliberateInk }) => {
  const layout = useLienzo();
  const w = layout.width - (layout.safe.left + layout.safe.right);
  const mid = w / 2;
  const rama = (hasta: number, tinta: string) => (
    <path
      d={`M ${mid} 0 L ${hasta} ${ALTO}`}
      stroke={tinta}
      strokeWidth={2}
      fill="none"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - progress}
    />
  );

  return (
    <svg
      width={w}
      height={ALTO}
      viewBox={`0 0 ${w} ${ALTO}`}
      style={{ display: "block", flexShrink: 0, marginTop: 16 }}
    >
      {rama(w * 0.25, defaultInk)}
      {rama(w * 0.75, deliberateInk)}
    </svg>
  );
};
