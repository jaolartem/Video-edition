import React from "react";

/**
 * **La losa: la única primitiva de los volúmenes.**
 *
 * Vivía dentro de [`escenas`](./escenas.tsx) y salió cuando hubo un segundo
 * fichero de escenas ([`masas`](./masas.tsx)): copiarla habría sido tener dos
 * definiciones del bloque plano del canon, y a la segunda se separan.
 *
 * Bloque de color, canto recto, material mate. Es el bloque plano del canon con
 * eje Z. Nada de esferas, cápsulas ni biseles — ahí es donde el 3D se vuelve
 * ilustración amable.
 * @clase capa
 */
export const Losa: React.FC<{
  posicion: [number, number, number];
  medida: [number, number, number];
  tinte: string;
  giro?: [number, number, number];
}> = ({ posicion, medida, tinte, giro }) => (
  <mesh position={posicion} rotation={giro ?? [0, 0, 0]}>
    <boxGeometry args={medida} />
    {/* Mate del todo: el canon prohíbe el brillo, y una losa con especular se
        lee como plástico. El volumen lo da la luz, no el material. */}
    <meshStandardMaterial color={tinte} roughness={1} metalness={0} />
  </mesh>
);
