/**
 * **La puerta de node a la base: `consulta.py`, y nada más.**
 *
 * Node no abre `decisiones.db`. La abre `basedatos.py`, que existe justo por
 * eso: *«una sola puerta para abrir la base, y una sola conexión por proceso»*.
 * Lo que node necesita es preguntarle a esa puerta, y eso son cinco líneas de
 * `execFileSync` escritas tres veces —aquí venían de `describir.mjs`, y siguen
 * copiadas en `plan-reel.mjs` y en `reels/material.mjs`— cada una con su
 * `maxBuffer` y su forma de pasar los argumentos.
 *
 * Tres copias de una decisión son tres sitios donde puede divergir, y este
 * proyecto ya sabe cómo acaba eso: no fallan, **divergen**, y entonces las tres
 * parecen correctas. Las otras dos se traen aquí en cuanto se toquen: son de
 * otro paso y moverlas de paso sería reconstruir alrededor, no incluir.
 *
 * Devuelve el texto tal cual, sin parsear: hay consultas que contestan JSON y
 * las hay que no contestan nada —`guardar_escena` escribe y calla—, así que
 * quien pregunta es quien sabe qué esperaba.
 */
import { execFileSync } from "node:child_process";

/** El buffer. Un catálogo entero de una pieza pasa de largo del defecto de 1 MB. */
const TOPE = 32 * 1024 * 1024;

export const sql = (q, args = []) =>
  execFileSync("python", ["scripts/consulta.py", q, JSON.stringify(args)], {
    encoding: "utf8", maxBuffer: TOPE,
    // **Y el hijo escribe en UTF-8, se lo diga Windows o no.** Node lee `utf8`
    // y Python escribia en la consola del sistema —cp1252 aqui—, asi que
    // cualquier caracter fuera de esa pagina reventaba la consulta entera con
    // un `UnicodeEncodeError` y el paso se quedaba con el pedido de la vuelta
    // anterior, que es peor que fallar: parece que corrio.
    //
    // Lo tiro un signo menos de verdad (U+2212) en una descripcion de escena.
    // Un guion normal habria pasado. Eso es lo que lo hacia invisible: fallaba
    // solo cuando el contenido lo pedia, y el contenido lo pide cada vez mas
    // segun se afinan los textos.
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
