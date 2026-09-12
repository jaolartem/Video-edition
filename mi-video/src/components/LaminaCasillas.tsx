import React from "react";
import { AbsoluteFill } from "remotion";
import { franja } from "../brand/franja";
import { color, layout } from "../brand/tokens";
import type { Motion } from "../brand/sfx";
import { Casillas, type Casilla } from "./Casillas";
import { Fondo, type Recorte } from "./Fondo";
import { ZonaTablero } from "./ZonaTablero";

/**
 * **Casillas a cuadro completo: la lámina que se tacha mientras se dice.**
 *
 * `Casillas` sólo vivía dentro de `SidePanel`, así que un tablero a pleno que
 * declaraba casillas —`tachadura` en reel-04 e5— caía en `TableroDeclarado`:
 * los textos en bloques, el oro puesto desde el primer frame y nada tachado.
 * El diseñador lo devolvió tres veces (tiquets 295, 300 y el `visto` del
 * 11-9) con los mismos props, que estaban bien. Esto es sólo el suelo y la
 * zona; lo que se tacha y cuándo lo decide `Casillas` con el `en` que resuelve
 * `reels/anclas.mjs :: cuandoSeDice`.
 * @clase tablero
 */
export const LaminaCasillas: React.FC<{ props: Record<string, unknown> }> = ({
  props,
}) => {
  const casillas = (props.casillas ?? []) as Casilla[];
  if (!casillas.length) return null;
  const placa = typeof props.placa === "string" ? props.placa : undefined;
  const recorte = (typeof props.recorte === "string"
    ? props.recorte
    : "lleno") as Recorte;
  const ancho = layout.width - layout.safe.left - layout.safe.right;
  return (
    <AbsoluteFill
      style={{ backgroundColor: props.fondo === "navy" ? color.navy : color.richBlack }}
    >
      {placa ? <Fondo placa={placa} recorte={recorte} fuerza={0.9} /> : null}
      <ZonaTablero>
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            top: 150,
            width: ancho,
            height: franja.techoPx - 150,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <Casillas
            casillas={casillas}
            eje={props.eje === "fila" ? "fila" : "columna"}
            ancho={ancho}
            sfx={props.sound === true ? ((props.sfx as Motion) ?? "mark") : null}
            alinea="izq"
          />
        </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};
