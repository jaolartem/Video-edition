/**
 * **¿Está abierta una biblioteca de `src/brand/`?** Una pregunta, un sitio.
 *
 * Las bibliotecas —`figuras.json`, `volumenes.json`— son la única lista de lo
 * que se puede dibujar, y desde el 6-9-2026 pueden estar **cerradas**: Jaime,
 * *«las figuras que estás haciendo están horribles; hasta que no tengamos una
 * biblioteca de figuras decentes no las vamos a utilizar. Gráficos y palabras,
 * como tablero de clase, por el momento»*.
 *
 * Esto existe porque la respuesta la necesitan **tres pasos distintos** y cada
 * uno la resolvía por su cuenta: `escena.mjs` al ir a trazar, `formas.mjs` al
 * recibir el tablero y `reels/paneles.mjs` al montar el panel. Tres lecturas del
 * mismo JSON son tres reglas con el mismo nombre en cuanto una cambie, que es la
 * avería que este proyecto ya pagó con `limpio`/`norm`.
 *
 * La decisión no vive aquí: vive en el bloque `cerrada` del propio JSON, al lado
 * de la lista que cierra. Quitarlo la reabre en los tres sitios sin tocar
 * ninguno.
 * @clase sistema
 */
import fs from "node:fs";

/** El bloque `cerrada` de una biblioteca, o `null` si está abierta. */
export const cerrada = (fichero) => {
  try {
    return JSON.parse(
      fs.readFileSync(`src/brand/${fichero}`, "utf8"),
    ).cerrada ?? null;
  } catch {
    // Sin fichero legible se trabaja como si estuviera abierta: cerrar por no
    // haber podido mirar dejaría el lote sin una sola figura y sin decir por
    // qué, que es peor que la figura de más.
    return null;
  }
};
