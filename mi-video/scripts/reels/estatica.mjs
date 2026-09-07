/**
 * **La distorsion: la que tapa una costura y la que marca una cita.**
 *
 * Salio de `capas.mjs` por el techo de 300 lineas, que es un contrato. Y sale
 * entera, no cortada por la mitad: las dos funciones son la misma
 * responsabilidad —donde se rompe la senal y cuanto dura— y comparten
 * `DUR_GLITCH`, que es el numero que las hace la misma cosa. Partir por lineas
 * habria dejado la constante en un lado y su motivo en el otro.
 */
import { enFrames } from "./reloj.mjs";
import { eco } from "./eco.mjs";

/**
 * **Un glitch en cada costura que no tape ya un tablero.**
 *
 * Jaime: *«hay cortes muy fuertes todavía… lo ideal es que no se note. Se puede
 * poner una transición discreta, un efecto glitch que distorsione la imagen y el
 * sonido como un TV antiguo cambiando de canal, durante poco tiempo»*.
 *
 * **Sólo donde la costura salta, no en todas.** Una máscara que se pone siempre
 * deja de ser máscara: se convierte en el efecto, y entonces el corte limpio y
 * el malo se ven igual de raros. `costuras.py` mueve lo que se puede mover **sin
 * perder voz** y deja en `costuras_duras` lo que no tuvo arreglo. Eso, y sólo
 * eso, se disimula.
 *
 * Va **centrado en la costura** —mitad antes, mitad después— para que el corte
 * caiga dentro de la distorsión y no en su borde. Y **donde está la costura en
 * la pieza, no en el EDL**: acumulando el EDL entraba hasta 6,8 s tarde, o sea
 * en mitad de una frase en vez de encima del salto que venía a tapar.
 */
/**
 * Cuánto dura la distorsión que tapa una costura. 5 frames, 0,17 s.
 *
 * Muy corta a propósito: lo que tapa dura un frame, y un efecto más largo deja
 * de esconder el corte para pasar a ser el corte.
 */
const DUR_GLITCH = 5;

export function glitchesDe(edl, reloj, cubren) {
  const duras = new Set(edl.costuras_duras ?? []);
  const out = [];
  for (let i = 0; i < edl.segmentos.length - 1; i++) {
    if (!duras.has(i)) continue;
    const fin = reloj.finDelCorte(edl, i);
    if (fin === null) continue;
    const at = enFrames(fin) - Math.round(DUR_GLITCH / 2);
    if (at < 0) continue;
    // Donde ya hay tablero o tarjeta el plano cambió: no hay salto que tapar.
    const cubierto = cubren.some(
      (b) => at < b.at + b.duration && at + DUR_GLITCH > b.at,
    );
    if (!cubierto) out.push({ at, duration: DUR_GLITCH });
  }
  return out;
}

/**
 * **La frase traída de más adelante entra con la señal rota.**
 *
 * Jaime, 7-9-2026, sobre el adelanto de reel-03: *«ya está a blanco y negro,
 * algunos puntos de estática serán buenos, pero la idea es que se note que es
 * una frase que no va ahí, se pone como gancho y cuando se dice más adelante se
 * dice normal, manteniendo la lógica del video»*.
 *
 * El blanco y negro ya lo pone `reels/eco.mjs` sobre esa misma ventana. Le
 * faltaba la otra mitad de lo que él pidió al cambiar el gancho —*«y ponle
 * distorsión»*—, y esa mitad **es el glitch que ya tapa las costuras**:
 * distorsiona la imagen y suena, que es exactamente «estática». No hay
 * mecanismo nuevo; hay un segundo motivo para usar el que existe.
 *
 * **Y sólo sobre la cita.** Lo que se repite después entra limpio: si las dos
 * llevaran tratamiento no habría adelanto, habría un efecto.
 *
 * **Puntos, no un filtro corrido.** Tres —entrada, medio y salida— de cinco
 * frames, los mismos que la costura: una distorsión larga deja de ser un
 * tropiezo de señal y pasa a ser el tratamiento del plano.
 *
 * @param ventanas las de `eco()`, en frames: `[{at, duration}]`.
 * @param ya los glitches que ya hay, para no poner dos en el mismo frame.
 */
export function estaticaDe(ventanas = [], ya = []) {
  const out = [];
  for (const v of ventanas ?? []) {
    // Sin sitio para los tres no se reparte de otra forma: una ventana más
    // corta que eso es medio segundo de plano, y ahí la estática es el plano.
    if (v.duration < DUR_GLITCH * 3) continue;
    for (const at of [
      v.at,
      v.at + Math.round((v.duration - DUR_GLITCH) / 2),
      v.at + v.duration - DUR_GLITCH,
    ]) {
      const pisa = [...ya, ...out].some(
        (g) => at < g.at + g.duration && at + DUR_GLITCH > g.at,
      );
      if (!pisa) out.push({ at, duration: DUR_GLITCH });
    }
  }
  return out;
}

/**
 * **Las ventanas que son cita, calculadas UNA vez.**
 *
 * Un plano que se vuelve a ver mas adelante es una frase traida al principio, y
 * de eso cuelgan tres cosas: va en gris (`eco`), lleva estatica (`estaticaDe`)
 * y no la viste ninguna capa (`caminosDe`). Calcularlas tres veces seria la
 * averia de la casa —la misma decision leida de dos sitios— esperando a que una
 * de las tres se quede atras. Vive aqui, con el mecanismo que la usa.
 */
export const citasDe = (edl, cortes) => eco(edl, cortes);

/**
 * **Toda la senal rota de la pieza, en una lista y en orden.**
 *
 * Las costuras y las citas se rompen por motivos distintos y con el mismo
 * efecto, asi que se juntan aqui y no en el spec: la estatica entra DETRAS y
 * mirando lo que ya hay, porque dos glitches en el mismo frame son uno mas
 * fuerte, no dos.
 */
export function distorsionDe(edl, reloj, cubren, citas) {
  const g = glitchesDe(edl, reloj, cubren);
  return [...g, ...estaticaDe(citas, g)].sort((a, b) => a.at - b.at);
}
