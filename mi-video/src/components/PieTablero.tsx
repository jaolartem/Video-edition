import React from "react";
import { fontFamily } from "../brand/fonts";
import { color, size, tracking } from "../brand/tokens";

/**
 * **El pie de un tablero: la fuente y la condición, sobre banda clara.**
 *
 * Es cumplimiento, no adorno. El playbook exige que toda cifra en pantalla lleve
 * de dónde sale y bajo qué supuestos vale, y el canon dice cómo se ve: banda
 * clara ligeramente girada, la fuente en mono con interletrado amplio y la
 * condición en cuerpo de lectura, las dos en negro sobre el claro para que la
 * letra pequeña se lea encima de un collage.
 *
 * Estaba escrito cuatro veces —una por forma nueva— y las cuatro con su propio
 * relleno y su propio giro. Cuatro copias de una regla del canon no fallan:
 * divergen, y entonces cuatro tableros de la misma pieza llevan cuatro pies
 * distintos. Es exactamente lo que pasó con la franja del subtítulo.
 *
 * **Se apoya en `bottom: 0` de su contenedor**, que dentro de `ZonaTablero` es
 * el techo de la franja: el pie es lo más bajo que un tablero dibuja, y ni un
 * píxel por debajo — ahí vive la interfaz de la plataforma.
 * @clase sistema
 */
export const PieTablero: React.FC<{
  /** Lo que va al pie, en orden. La primera línea es la fuente. */
  lineas: string[];
  /** Progreso de entrada, 0→1. Entra el último: es lo que menos urge leer. */
  opacidad: number;
}> = ({ lineas, opacidad }) => {
  if (!lineas.length) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: color.lightNeutral,
        transform: "rotate(0.7deg)",
        padding: "18px 74px 22px",
        opacity: opacidad,
      }}
    >
      {lineas.map((p, i) => (
        <div
          key={p}
          style={{
            fontFamily: i ? fontFamily.video : fontFamily.data,
            fontSize: i ? 26 : size.source,
            fontWeight: i ? 700 : 400,
            letterSpacing: i ? 0 : tracking.labelMono,
            textTransform: i ? "none" : "uppercase",
            lineHeight: 1.3,
            color: i ? color.richBlack : color.navy,
            marginBottom: 8,
          }}
        >
          {p}
        </div>
      ))}
    </div>
  );
};
