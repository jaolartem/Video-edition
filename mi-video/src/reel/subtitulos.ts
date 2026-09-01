import type { CaptionCue } from "../Ad";
import type { ReelSpec } from "./tipos";

/**
 * **Qué calla el subtítulo, y qué no.**
 *
 * El subtítulo NO se calla casi nunca. **La mayoría ve los reels sin audio**,
 * así que un hueco sin texto es un hueco sin argumento. Convivía mal con el
 * rótulo porque compartían franja; se resolvió bajando la banda a la zona
 * segura de Reels en vez de silenciar una capa.
 *
 * - **Tarjeta y cortinilla: callan.** Ocupan el cuadro entero con su propio
 *   texto, así que debajo no queda sitio ni hay nada que añadir.
 * - **Tablero: NO calla.** Jaime: *«en los tableros también hay cc»*. Ahí la
 *   voz sigue por debajo diciendo cosas que el tablero no enseña —es un
 *   L-cut— y el argumento tiene que funcionar sin sonido. El tablero deja
 *   libre la banda de subtítulos por diseño.
 * - **Panel: TAMPOCO calla.** Estuvo callando y costó 20 de los 36
 *   subtítulos del reel 1 — 43,6 s de una pieza de 75,2 s sin una palabra en
 *   pantalla. El panel vive en la mitad superior por un lado; la banda de
 *   subtítulos, en el 50–60%. **No compiten por el sitio.** Lo que Jaime
 *   pidió en su día —*«cada letrero se debe ver»*— se resolvió dándole a
 *   cada bloque su tiempo de lectura, no borrando la capa portante. Lo que
 *   sí cede el subtítulo mientras el panel escribe es el **volumen**: ahí no
 *   se compone (ver `componer()` en `reels-spec.mjs`).
 *
 * Y calla **por mayoría, no por roce**: una cue que solapa 0,2 s con el final
 * de un panel se perdía entera. Se calla si la tapan más de la mitad.
 *
 * Esto es una **regla de montaje**, no de dibujo, y por eso vive fuera del
 * componente: decide qué se ve, y quien pinta sólo pinta lo que le llega.
 */
export const subtitulosVisibles = (r: ReelSpec): CaptionCue[] => {
  const tapan = [...r.tarjetas, ...r.cortinillas];
  /** Frames que `b` le quita a `c`. */
  const solape = (
    c: CaptionCue,
    b: { at: number; duration: number },
  ): number =>
    Math.max(
      0,
      Math.min(c.at + c.duration, b.at + b.duration) - Math.max(c.at, b.at),
    );

  return r.captions.filter(
    (c) => tapan.reduce((n, b) => n + solape(c, b), 0) <= c.duration / 2,
  );
};
