import React from "react";
import { fontFamily } from "../../brand/fonts";
import { cuerpoQueCabe } from "../../brand/medida";
import { color, layout } from "../../brand/tokens";

/**
 * **Lo que cierra la acumulación**: la cifra que la pila demuestra, y el pie que
 * dice de dónde sale.
 *
 * Vive aparte de [`Acumulacion`](../Acumulacion.tsx) por la misma razón que
 * `panel/Cierre`: son dos trabajos. Allí se apilan capas; aquí se escribe lo que
 * remata.
 */

/** Dónde aterriza la cifra cuando el barrido se ha llevado el diagrama. */
const BANDA = { y: 430, relleno: 54 } as const;

/** Lo que la cifra tarda en llegar después de que el barrido cruce. */
const TRAS_EL_BARRIDO = 0.45;

/**
 * **La cifra que el tablero demuestra, sola en el cuadro.**
 *
 * Jaime, mirando el fotograma de reel-02 e3: *«la cifra que el tablero
 * demuestra no aparece; se llama "lo que se va cada año" y $189.000 no está en
 * pantalla. Eso es lo que el tramo prueba; sin ese número el tablero no cierra
 * nada»*.
 *
 * Estaba declarada —`resultado.figure` viajaba en el spec desde el primer
 * día— y se dibujaba a 96 px al pie del panel, al lado de la pila, con su fuente
 * en mono debajo: en la jerarquía del tablero era una nota, no el remate. Ahora
 * es lo único que queda cuando el barrido pasa, y el barrido es literalmente
 * esta banda abriéndose de izquierda a derecha por encima de lo que había.
 *
 * **El cuerpo lo decide lo que cabe, no un número redondo**: `$189,000` da de
 * sobra para el tope de gran formato y una cifra más larga baja sola en vez de
 * salirse.
 */
export const Total: React.FC<{
  figura: string;
  /** 0 → 1: el barrido cruzando. Lo emite quien conoce el horario. */
  barre: number;
}> = ({ figura, barre }) => {
  if (barre <= 0) {
    return null;
  }
  const llega = Math.max(
    0,
    (barre - TRAS_EL_BARRIDO) / (1 - TRAS_EL_BARRIDO),
  );
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: BANDA.y,
        padding: `56px ${BANDA.relleno}px 64px`,
      }}
    >
      {/* El barrido: negro que cruza el cuadro de izquierda a derecha. No es un
          efecto — es lo que borra el diagrama para que la conclusión no sea un
          renglón más al lado de lo que la demostró. */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundColor: color.richBlack,
          transformOrigin: "left",
          transform: `scaleX(${barre})`,
        }}
      />
      <div
        style={{
          position: "relative",
          fontFamily: fontFamily.bloque,
          fontSize: cuerpoQueCabe({
            ancho: layout.width - BANDA.relleno * 2,
            largo: figura.length,
            registro: "anton",
            tope: 210,
          }),
          lineHeight: 0.94,
          letterSpacing: "-0.01em",
          whiteSpace: "nowrap",
          textTransform: "uppercase",
          color: color.gold,
          opacity: llega,
          transform: `translateY(${(1 - llega) * 24}px)`,
        }}
      >
        {figura}
      </div>
    </div>
  );
};

/**
 * **El pie ya no vive aquí, y ésta es la lápida.**
 *
 * Aquí estaba `Pie`, y fue el primero que cumplió la instrucción de Jaime del
 * 6-9-2026: una línea, `JetBrains Mono`, azul secundario, pegada por debajo del
 * suelo de la zona segura. Estaba bien y estaba copiado de `PanelDentro` — con
 * el `1262` escrito a mano en los dos, que es como empiezan las cuatro copias
 * de un número derivado.
 *
 * Vive en [`PieTablero`](../PieTablero.tsx), con el número saliendo de
 * `franja.sueloPx` y montado una vez por `dibujaTablero` para las 24 láminas
 * del lote.
 */
