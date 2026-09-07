import "./index.css";
import React from "react";
import { AbsoluteFill, Composition, Img, registerRoot, staticFile } from "remotion";
import { fontFamily } from "./brand/fonts";
import { useEntrada } from "./brand/horario";
import { color } from "./brand/tokens";

/**
 * **El gancho, rehecho.** Los siete eran la misma lámina y ninguno paraba el
 * scroll: rótulo en el tercio que la interfaz de Meta tapa, dos bloques de texto
 * compitiendo en el primer segundo, todo quieto y nada jugando con él.
 *
 * Esto es lo que Jaime dio por bueno en el panel, aplicado al gancho: el texto
 * **detrás de su cabeza**, en el tercio de arriba, entrando por partes y sin
 * rebote, y su figura delante. El sistema es uno para las siete; lo que cambia
 * de pieza a pieza es lo que dice.
 */
const Gancho: React.FC = () => {
  const entra = useEntrada();
  // Dos líneas escalonadas: la segunda alcanza a la primera. La jerarquía la da
  // el peso, no el tamaño ni el color — es lo leído en la referencia de Platzi.
  const a = entra(2, 13);
  const b = entra(15, 13);
  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      <Img src={staticFile("hook-plano.jpg")}
           style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <div style={{ position: "absolute", left: 54, top: 250, width: 980 }}>
        <div style={{
          fontFamily: fontFamily.bloque, fontSize: 118, lineHeight: 0.94,
          letterSpacing: "-0.01em", textTransform: "uppercase",
          color: color.lightNeutral,
          opacity: a, transform: `translateY(${(1 - a) * 26}px) scale(${0.965 + a * 0.035})`,
        }}>
          TRABAJA MÁS
        </div>
        <div style={{
          fontFamily: fontFamily.bloque, fontSize: 152, lineHeight: 0.92,
          letterSpacing: "-0.015em", textTransform: "uppercase", color: color.gold,
          opacity: b, transform: `translateY(${(1 - b) * 26}px) scale(${0.965 + b * 0.035})`,
        }}>
          LE QUEDA MENOS
        </div>
      </div>
      {/* Él delante: el texto pasa por detrás de la cabeza y los hombros. */}
      <Img src={staticFile("hook-recorte.png")}
           style={{ position: "absolute", inset: 0, width: "100%", height: "100%",
                    objectFit: "cover" }} />
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition id="Gancho" component={Gancho} durationInFrames={90}
               fps={30} width={1080} height={1920} />
);

registerRoot(Root);
