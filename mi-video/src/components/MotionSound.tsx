import React from "react";
import { Audio, Sequence } from "remotion";
import { sfxSrc, sfxVolume, type Motion } from "../brand/sfx";

/**
 * Emite el efecto de un movimiento en el frame exacto en que ese movimiento
 * ocurre.
 *
 * Se coloca junto al elemento que anima, no en una pista de audio aparte: los
 * tiempos de este proyecto se derivan del tiempo de lectura y del anclaje al
 * transcript, así que cambian. Una pista aparte se desincroniza en el primer
 * ajuste de copy; esto no puede desincronizarse porque lee el mismo número.
  * @clase sistema
*/
export const MotionSound: React.FC<{
  motion: Motion;
  /** El frame en que arranca el movimiento. */
  at: number;
  /** Sobrescribe el nivel por defecto. La voz sigue mandando. */
  volume?: number;
}> = ({ motion, at, volume }) => {
  if (at < 0) {
    return null;
  }
  /**
   * Nivel constante expresado como callback: es lo que pide el linter de
   * Remotion, y aquí es correcto que sea constante — un efecto puntual no
   * necesita envolvente, la trae el propio fichero.
   */
  const level = volume ?? sfxVolume[motion];

  return (
    <Sequence from={at} durationInFrames={90} layout="none">
      <Audio src={sfxSrc(motion)} volume={() => level} />
    </Sequence>
  );
};
