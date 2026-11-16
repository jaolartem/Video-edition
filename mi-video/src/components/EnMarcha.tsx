import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

/** Lo más que se acerca un tablero, por larga que sea su etapa. */
const TOPE = 0.14;

/**
 * **Un tablero a pleno no se queda quieto** (C-727).
 *
 * reel-23, 16-11-2026: el render salió con 22 congelados de medio segundo o
 * más —24,7 s— y todos en tableros: entran animados, terminan y se quedan
 * fijos hasta el corte. e5 pasaba 9 s quieta. Jaime: *«nada quieto»*, y desde
 * el 18-9, *«vídeo en marcha, nunca congelado»*.
 *
 * El tablero se acerca despacio durante toda su etapa, `empuje` en fracción
 * de escala por segundo y a ritmo constante —con frenada al final volvería a congelarse—.
 * Es un empuje de cámara y no una animación del contenido: no
 * rebota ni vuelve, y no cambia lo que se lee. Lo declara el lienzo
 * (`lienzos.json`, `tablero.empuje`). Sin él vale 0 y el tablero se dibuja
 * igual que antes, byte a byte. Lo que acompaña a la toma (`cubre: panel` o
 * `banda`) no se empuja, porque el plano de debajo ya va en marcha.
 */
export const EnMarcha: React.FC<{ empuje: number; dura: number; children: React.ReactNode }> = ({
  empuje,
  dura,
  children,
}) => {
  const frame = useCurrentFrame();
  const { width, fps } = useVideoConfig();
  if (!empuje) return <>{children}</>;
  // Lo que se acerca en total sale del ritmo por segundo, con tope para que
  // uno largo no se salga del cuadro, y se reparte en TODA la etapa: un tope
  // que parase el empuje a mitad volvía a congelarla (e5, 3,3 s).
  const total = Math.min(TOPE, (empuje * dura) / fps);
  const k = 1 + (total * Math.min(frame, dura)) / Math.max(1, dura);
  // Y deriva hacia un lado mientras se acerca: con el origen en el centro, lo
  // que está en el centro sólo crecía, y un tablero de una sola etiqueta
  // seguía midiéndose quieto (reel-23, 0:39).
  const x = (k - 1) * width * 0.4;
  return (
    <AbsoluteFill
      style={{ transform: `translateX(${(-x).toFixed(2)}px) scale(${k.toFixed(5)})`, transformOrigin: "50% 50%" }}
    >
      {children}
    </AbsoluteFill>
  );
};
