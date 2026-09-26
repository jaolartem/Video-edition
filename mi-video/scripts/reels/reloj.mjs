/**
 * **El reloj del montaje**: de un tiempo del plan a un frame de la pieza.
 *
 * Aqui vive una sola cosa y por eso el fichero es corto: traducir. Todo lo que
 * se coloca encima del video —tableros, tarjetas, paneles, glitches— tiene que
 * decir en que frame entra, y ese frame **no sale del EDL**.
 *
 * ## Por que el EDL no vale como reloj
 *
 * `plan-reel` quita el aire de cada corte antes de repartirlo en escenas —regla
 * de Jaime, *«lo de los silencios tambien puede ser aritmetico»*— asi que la
 * imagen corre sobre una linea mas corta que el EDL. En reel-01 son 6,83 s.
 *
 * Y el desfase no es constante, **crece**: 0 en el beat 2, 2,08 s en el 4, 4,93
 * en el 6 y 6,77 en el 8 — o sea el cierre se colocaba en el segundo 119,77 de
 * un video que dura 119,32 y se caia fuera. Por el camino cada tablero entraba
 * cuando el audio ya estaba en otra frase: Jaime lo describio como *«la entrada
 * del tablero sigue hablando de los 500 antes de entrar a dar el remate»*, y
 * como glitches y perdida de continuidad.
 *
 * Dos listas describiendo la misma pieza es el aprendizaje 33 otra vez. **La que
 * manda es la que se renderiza**, y esa es el plan.
 */

import fs from "node:fs";

export const FPS = 30;

/**
 * El montaje corre acelerado — Jaime: *«ponlo a 1.1× o a 1.2×»*—, asi que
 * **los tiempos del plan no son los del video**. Todo lo que se derive de el y
 * tenga que caer sobre la linea de tiempo se divide por esto.
 *
 * Sin ello la comprobacion de coherencia gritaba en los seis reels: comparaba
 * 60,8 s de EDL contra 53,3 s de corte y concluia «el corte esta viejo». Una
 * alarma que suena siempre deja de leerse, y entonces ya no sirve para el aviso
 * que si valga. Tiene que coincidir con `VELOCIDAD` de `render-hook.mjs`.
 */
export const VELOCIDAD = 1;

/** Segundos de la linea montada a frames de la composicion. */
export const enFrames = (s) => Math.round((s / VELOCIDAD) * FPS);

export class Reloj {
  /** @param {{escenas?: object[]}} plan el `plan-full.json` de la pieza. */
  constructor(plan) {
    this.escenas = plan.escenas ?? [];
  }

  /**
   * Cada escena con su hueco en frames, en orden.
   *
   * Se acumulan duraciones en vez de leer `montado_desde` porque son la misma
   * cifra —las escenas del plan son contiguas— y esta forma no depende de que
   * lo sigan siendo el dia que alguien meta un hueco a proposito.
   */
  limites() {
    let t = 0;
    return this.escenas.map((e, i) => {
      const a = enFrames(t);
      t += e.duracion;
      return { n: i + 1, a, b: enFrames(t), beat: Number(e.beat), escena: e };
    });
  }

  /**
   * Frames donde cambia el encuadre: ahi cruza la barra que tapa el corte.
   *
   * Salen del plan, asi que no pueden desincronizarse del montaje.
   */
  get cortes() {
    return this.limites().slice(0, -1).map((l) => l.b);
  }

  /**
   * Donde cae un beat **en la linea que se renderiza**.
   *
   * Su propio hueco si el beat tiene escena; el del siguiente si no la tiene —
   * que es el sitio que el beat ausente habria ocupado. Y si ya no queda
   * ninguno, el final de la pieza.
   */
  anclaDe(beat) {
    for (const e of this.escenas) {
      if (Number(e.beat) >= beat) return enFrames(e.montado_desde);
    }
    const u = this.escenas[this.escenas.length - 1];
    return u ? enFrames(u.montado_desde + u.duracion) : 0;
  }

  /**
   * Cuanto dura la escena de un beat, en frames de la linea final.
   *
   * El tablero **reemplaza esa escena entera**, asi que su duracion no se
   * calcula por tiempo de lectura: se toma de lo que dura el beat. Jaime: *«en
   * esos cortes el tablero reemplaza la escena, y el tablero es un instrumento
   * pedagogico»*. `null` si el beat no tiene escena propia.
   */
  duracionDe(beat) {
    const suyas = this.escenas.filter((e) => Number(e.beat) === beat);
    if (!suyas.length) return null;
    return enFrames(suyas.reduce((n, e) => n + e.duracion, 0));
  }

  /** El hueco de cada beat en la pieza, en frames: `Map<beat, [desde, hasta]>`. */
  ventanas() {
    const por = new Map();
    for (const e of this.escenas) {
      const b = Number(e.beat);
      const fin = e.montado_desde + e.duracion;
      const v = por.get(b);
      if (v) v[1] = Math.max(v[1], fin);
      else por.set(b, [e.montado_desde, fin]);
    }
    return new Map(
      [...por].map(([b, [d, h]]) => [b, [enFrames(d), enFrames(h)]]),
    );
  }

  /**
   * De un corte del EDL a **donde acaba en la pieza montada**, en segundos.
   *
   * Se traduce por CONTENIDO, no por indice: las escenas del plan llevan de que
   * trozo de cinta nacen, asi que el final del corte `i` es el final montado de
   * su ultima escena. `null` si ese corte no dejo ninguna escena.
   */
  finDelCorte(edl, i) {
    const [a, b] = edl.segmentos[i];
    let fin = null;
    for (const e of this.escenas) {
      if (e.origen_desde >= a - 0.05 && e.origen_hasta <= b + 0.05) {
        fin = e.montado_desde + e.duracion;
      }
    }
    return fin;
  }

  /** Lo que el plan dice que va a durar la pieza, en segundos. */
  get previsto() {
    return this.escenas.reduce((t, e) => t + e.duracion, 0) / VELOCIDAD;
  }

  /**
   * **Aviso de corte viejo, descontando la deriva normal.**
   *
   * Lo comprueba el reloj porque es quien tiene los dos lados: lo que el plan
   * predice y lo que el vídeo dura de verdad. Lo previsto sale del PLAN y no del
   * EDL — el EDL es la intención, y el plan ya descontó el silencio interno que
   * `conHabla()` quita al cortar. Comparar dos magnitudes que no son la misma
   * cosa es C-05, y ésta fue la tercera vez.
   *
   * Y cada escena se codifica a frame entero, así que con treinta escenas hay un
   * segundo de diferencia que **no significa nada**. Avisar de eso hacía saltar
   * la alarma en piezas correctas, y una alarma que suena siempre deja de
   * leerse. Lo que sí importa es que el corte se quede **corto**: ahí la
   * composición pide frames que no existen y el render muere en un timeout de
   * 33 s sin decir por qué.
   */
  cuadraCon(slug, duracion) {
    /**
     * **Y lo que la pieza baila no es sobrante: esta declarado.** Desde el
     * 17-9-2026 una pieza puede llevar pausas en `src/brand/compas.json` para
     * que sus costuras caigan en el beat de su cancion —reel-14 son 3,28 s en
     * siete pausas—. Sin contarlas aqui, la pieza que baila avisa de que le
     * sobra corte en cada corrida, y una alarma que suena siempre deja de
     * leerse: es la misma razon que el `deriva` de dos lineas mas abajo.
     */
    let baila = 0;
    try {
      const j = JSON.parse(fs.readFileSync("src/brand/compas.json", "utf8"));
      baila = Object.values(j?.[slug]?.pausas ?? {})
        .reduce((n, x) => n + Number(x || 0), 0);
    } catch { baila = 0; }
    const previsto = this.previsto + baila;
    const deriva = this.escenas.length / 30;
    if (duracion + 0.1 < previsto - deriva) {
      console.error(
        `  ojo: ${slug} el corte (${duracion.toFixed(2)}s) es MAS CORTO que el ` +
        `EDL (${previsto.toFixed(2)}s): el corte esta viejo y el render fallara`,
      );
    } else if (duracion > previsto + deriva + 0.5) {
      console.error(
        `  ojo: ${slug} el corte (${duracion.toFixed(2)}s) sobra sobre el EDL ` +
        `(${previsto.toFixed(2)}s) mas de lo que explica el redondeo`,
      );
    }
  }
}
