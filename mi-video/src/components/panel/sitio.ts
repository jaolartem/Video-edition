import type { Lienzo } from "../../brand/lienzo";
import { type Lado } from "../Recorte";

/**
 * **Dónde y cuándo va cada cosa del panel con él dentro.**
 *
 * Vive aparte de [`PanelDentro`](../PanelDentro.tsx) por la misma razón que
 * `Cierre`: **lo que decide y lo que dibuja son dos trabajos**. Allí quedan las
 * capas y su orden; aquí, el horario, la columna, la masa que lo separa del
 * collage y la única colocación que hay que refutar.
 *
 * Todo lo de este fichero se calibró **mirando fotogramas**, no razonando sobre
 * el código: los números que traía la lámina aprobada estaban medidos sobre los
 * 1.920 enteros y el panel acaba en el techo de la franja (C-257).
 */

/**
 * El horario, en frames y no en segundos.
 *
 * Cada cosa entra cuando la anterior se pudo leer: 0,75 s por bloque más medio
 * segundo de respiro, que es la regla del canon y no un número redondo. Un
 * `Reparto` de dos porciones tarda 48 frames en construirse (riel 14, porción
 * cada 11, entrada 12), así que el siguiente no puede entrar antes.
 */
export const T = { premisa: 0, el: 10, unoA: 22, unoB: 76, remate: 130,
                   pregunta: 152, pie: 172 };

/**
 * La columna de contenido: el lado libre, el contrario al suyo.
 *
 * `alto` es lo que ocupa un `Reparto` (barra 132 + pie 92) y `salto` lo que va
 * de uno al siguiente. **No sobran píxeles**: `ZonaTablero` recorta en 1048 y
 * debajo de los repartos vive la pila del remate, la pregunta y el pie. La
 * primera versión los puso 50 px más abajo y la pila se comió la etiqueta `CON
 * ESTRUCTURA` y media línea del remate — sin error, sin log, y sólo se vio al
 * sacar el fotograma.
 */
export const RITMO = { arriba: 200, salto: 240 } as const;

/**
 * **La columna entera en un lienzo.** Dónde empieza y cuánto mide es del
 * lienzo —`columna` en `lienzos.json`, 470 y 540 en vertical—, porque es ancho
 * del cuadro; el ritmo de arriba abajo es del panel (C-670).
 */
export const columnaEn = (layout: Lienzo) => ({ ...layout.columna, ...RITMO });

//: `MASA` se retiro el 6-9-2026. Era la columna negra bajo su figura, y Jaime
//: la quito al verla: *«yo no deberia tener cuadrado negro de contraste, el
//: efecto de papel recortado cumple esa funcion»*. La orla clara de fibra ya lo
//: separa del collage por todo el contorno; la masa hacia dos veces el mismo
//: trabajo y encima tapaba la placa. Una regla nueva quita codigo, no lo anade.


/**
 * **Dónde empieza la columna de contenido: en el lado que él no ocupa.**
 *
 * Si él va a la derecha, el contenido se va a la izquierda. Con él abajo la
 * columna se queda donde está y el texto de abajo lo tapa menos.
 */
export const columnaDe = (sujeto: Lado, layout: Lienzo): number =>
  sujeto === "derecha" ? layout.safe.left : layout.columna.x;

/**
 * **`abajo` sólo cabe en un panel ligero, y se sabe midiendo.**
 *
 * `izquierda` y `derecha` le dan una columna entera —de la premisa al pie—,
 * pero `abajo` le da lo que sobra entre el último reparto y la pila del cierre,
 * y bajo el techo de la franja eso casi nunca es nada. Medido en
 * `work/still/panel-abajo.png`: con dos repartos el último acaba en el 664, la
 * pila del cierre empieza en el 690, y de él se veían **26 px de pelo** — una
 * colocación declarada que en pantalla es un agujero.
 *
 * Con un reparto y sin pregunta quedan 416 px, que sí es un sitio. Así que la
 * condición no es «abajo no vale»: es que el panel tiene que dejarle el hueco,
 * y quien lo declara se entera aquí y no en el fotograma.
 *
 * @throws si `abajo` se pide con un panel que no le deja sitio.
 */
export function cabeElSujeto(
  sujeto: Lado,
  repartos: number,
  pregunta: boolean,
): void {
  if (sujeto !== "abajo" || (repartos <= 1 && !pregunta)) return;
  throw new Error(
    `PanelDentro: \`sujeto: abajo\` con ${repartos} repartos` +
      `${pregunta ? " y pregunta" : ""} no deja hueco: bajo el techo de la` +
      " franja el cierre se le come entero. Con `abajo` va UN reparto y sin" +
      " pregunta, o él se pone a un lado.",
  );
}
