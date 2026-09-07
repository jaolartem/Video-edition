/**
 * **Los tramos en los que no hay NADA en pantalla.**
 *
 * Jaime, 7-9-2026, sobre reel-04: *«segundo 30 a 37 estoy leyendo»*. Un tramo
 * largo con el plano pelado —sin tablero, panel, tarjeta, recorte, cortinilla
 * ni punch— no es dejarlo respirar: es que ahi no se compuso nada.
 *
 * ## Por que vive aqui y no en `caminos.mjs`, que fue la leccion
 *
 * El primer intento midio sobre `capas` a secas y dio **147 s repartidos en las
 * siete**. El numero era falso y se le llego a informar: los tableros estaban
 * puestos, solo que en `boards`, `paneles` y `tarjetas`, que son listas
 * hermanas de la misma pieza. Medido sobre todas: **25 s, en reel-01 y
 * reel-07**.
 *
 * O sea la averia de siempre por la puerta de la comprobacion — mirar una parte
 * y hablar del todo—, y por eso esto se llama desde `reels-spec.mjs`, que es el
 * unico punto del proceso donde la pieza esta entera.
 */
import { FPS } from "../capa.mjs";

/**
 * Lo que puede durar un tramo pelado, en frames.
 *
 * Seis segundos, y el numero sale de la propia pieza: el gancho dura cinco y es
 * el tramo mas trabajado que tiene. Un trozo del cuerpo mas largo que el gancho
 * entero sin nada encima no es una decision, es un olvido.
 */
const TOPE = 6 * FPS;

/** Todo lo que dibuja, con su ventana. Si falta una lista, sobran huecos. */
const ventanas = (p) => [
  ...(p.caminos ?? []).filter(
    (c) => c.duration && c.tipo !== "sonido" && c.tipo !== "subtitulo"),
  ...(p.boards ?? []), ...(p.paneles ?? []), ...(p.tarjetas ?? []),
  ...(p.recortes ?? []), ...(p.cortinillas ?? []),
  ...(p.cta ? [{ at: p.cta.at * FPS, duration: p.cta.dur * FPS }] : []),
].map((x) => [x.at, x.at + x.duration]).sort((a, b) => a[0] - b[0]);

/** Una falta por cada tramo pelado que pase de `TOPE`. */
export function pelado(pieza, slug) {
  const faltas = [];
  let hasta = 0;
  for (const [a, b] of ventanas(pieza)) {
    if (a - hasta >= TOPE)
      faltas.push(`${slug}: del segundo ${(hasta / FPS).toFixed(1)} al ` +
        `${(a / FPS).toFixed(1)} no hay nada en pantalla — ` +
        `${((a - hasta) / FPS).toFixed(1)} s de plano pelado y el tope son ` +
        `${TOPE / FPS}: esa etapa no se compuso`);
    hasta = Math.max(hasta, b);
  }
  return faltas;
}
