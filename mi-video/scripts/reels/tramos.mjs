/**
 * **Cuanto tapa un conjunto de capas.** Por UNION, nunca por suma.
 *
 * ## El fallo que este objeto viene a impedir
 *
 * La cuenta se escribio tres veces en `reels-spec.mjs` y **solo una estaba
 * bien**. Sumando solapes, dos capas que se pisan cuentan dos veces: en el reel
 * 2 la tarjeta del beat 2 (6,9-14,3 s) y el tablero del beat 3 (6,9-28,6 s)
 * daban 24,5 s de tapado dentro de un tercio de 24, asi que el hueco salia
 * **negativo** y la comprobacion paraba el montaje teniendo Jaime 6,9 s de plano
 * limpio.
 *
 * Eso se arreglo en la puerta de las tres apariciones y se quedo sin arreglar en
 * los otros dos sitios que hacen la misma cuenta: el que decide si un subtitulo
 * puede componerse —donde tableros y tarjetas se pisan por diseño, porque el
 * tablero cubre la costura de la tarjeta— y el que mide el tramo mas largo sin
 * una palabra en pantalla. Dos capas superpuestas hacian creer que el subtitulo
 * estaba tapado el doble de lo que estaba: en el primero se perdian remates que
 * si se veian, y en el segundo el hueco mudo salia mas largo de lo real, que es
 * la cifra que **para el build**.
 *
 * Es la familia de los aprendizajes 19 y 28: un detector que cuenta de mas grita
 * por casos que no existen. Y es la razon de que esto sea un objeto y no una
 * funcion suelta copiada: la regla vive en un sitio, asi que no puede volver a
 * quedarse a medio arreglar.
 */
export class Tramos {
  /** @param {{at:number,duration:number}[]} capas cualquier cosa con horario. */
  constructor(capas) {
    this.tramos = (capas ?? [])
      .map((c) => [c.at, c.at + c.duration])
      .filter(([a, b]) => b > a)
      .sort((p, q) => p[0] - q[0]);
  }

  /** Cuanto de `[a, b)` queda cubierto por alguna capa, contado una sola vez. */
  cubiertoEntre(a, b) {
    let cubierto = 0;
    let hasta = a;
    for (const [x, y] of this.tramos) {
      const desde = Math.max(x, hasta, a);
      const fin = Math.min(y, b);
      if (fin > desde) cubierto += fin - desde;
      hasta = Math.max(hasta, Math.min(y, b));
    }
    return cubierto;
  }

  /** Cuanto de una cue queda debajo de alguna capa. */
  tapa({ at, duration }) {
    return this.cubiertoEntre(at, at + duration);
  }

  /** Si una cue queda tapada **por mayoria**, no por roce. */
  sepulta(cue) {
    return this.tapa(cue) > cue.duration / 2;
  }
}
