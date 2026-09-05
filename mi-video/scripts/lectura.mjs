/**
 * **Un tramo leído va cubierto.** El criterio, del lado del que compone.
 *
 * Instrucción de Jaime (T-01), después de verse leyendo en cámara limpia en
 * R-04: *«si en el audio se está leyendo, ese tramo va cubierto con tablero: la
 * cara no aparece en cámara limpia mientras se lee. El disparador es el
 * **audio**, no el frame, para que el compositor identifique los tramos sin
 * juzgar la mirada plano a plano. El tablero deja de ser un parche y pasa a ser
 * lo que corresponde a esos tramos por diseño»*.
 *
 * Y su diagnóstico, que es lo que decide dónde vive esto: *«no es un error de
 * edición ni una toma inservible. Es que el compositor no tenía criterio
 * escrito sobre qué hacer con los tramos leídos»*. Por eso el criterio no está
 * en un comentario: está aquí, lo llama `caminos.mjs` y lo lee el pedido del
 * que compone.
 *
 * ## El disparador es el audio, y ya estaba medido
 *
 * No hace falta detector nuevo. `seleccionar.py :: literal()` compara la toma
 * con el libreto por secuencias de cuatro palabras: decir las mismas palabras
 * en otro orden es hablar; decirlas en el mismo orden es leer. Ese número viaja
 * en el EDL como `detalle[].literal` y es lo único que se mira aquí.
 *
 * Hubo un intento de detectarlo por la imagen —la altura de la cabeza,
 * `reading-detect.py`— y **la hipótesis no se sostuvo**: rango intercuartílico
 * de 0,016, un solo grupo apretado. Juzgar la mirada plano a plano es
 * exactamente lo que Jaime pide no hacer.
 */

/**
 * Por encima de esto la toma es lectura.
 *
 * **El mismo número que `scripts/trato.py :: LEIDA`**, y no por casualidad:
 * `verdad.py` declara que la decisión vive allí y comprueba las dos líneas, así
 * que si una cambia y la otra no, el build lo dice. El umbral sale de los datos
 * —sobre los 53 fragmentos elegidos hay un salto de 0,17 entre 0,684 y 0,519— y
 * no del ojo.
 */
export const LEIDA = 0.60;

/** ¿Este segmento se está leyendo? El dato viene del EDL, ya medido. */
export const esLectura = (det) =>
  typeof det?.literal === "number" && det.literal >= LEIDA;

/**
 * Los caminos que **dejan la cara en cámara limpia**. Son todos menos el
 * tablero: `cercano` cierra sobre el rostro, `metafora` y `diapositiva` ponen
 * una capa al lado y el plano sigue siendo el plano.
 *
 * `portada` también deja la cara limpia, pero su falta se dice aparte: el
 * gancho **nunca es un tablero** —es la etapa que abre, con cara y máxima
 * expresividad— así que ahí el remedio no es taparlo con un cartel, es elegir
 * otra apertura. Cubrirlo rompería el camino `portada` entero y ya rompió el
 * argumento del reel 3 una vez.
 */
const CUBRE = new Set(["tablero"]);

/**
 * Las faltas que un segmento leído produce en el camino que le tocó.
 *
 * No para el lote: lo dice. Es la misma regla que el resto de `caminos.mjs` —
 * una indicación que sólo está escrita en un documento es una indicación que se
 * incumple; una que devuelve una falta es una que no se puede incumplir sin
 * enterarse.
 */
/**
 * **Lo mismo, del lado del pedido**: la respuesta del que compone se rechaza si
 * pone un tratamiento en cámara limpia sobre una etapa que llega marcada como
 * lectura. Devuelve el motivo, o `null` si está bien.
 *
 * El criterio viaja en el pedido —cada etapa leída con su porcentaje— así que
 * contestar otra cosa no es una interpretación distinta: es no haber mirado el
 * dato. La portada se queda fuera por lo de siempre: el gancho nunca es un
 * tablero, y ahí el remedio es de selección y no de composición.
 */
export const tratoSinCubrir = (d, leidas) => {
  const lee = leidas?.get(Number(d.etapa_orden));
  if (lee === undefined || d.trato === "tablero" || d.trato === "portada")
    return null;
  return (
    `la etapa ${d.etapa_orden} lee el libreto al ${Math.round(lee * 100)}% y` +
    ` «trato» = ${JSON.stringify(d.trato)}: un tramo leido va CUBIERTO con` +
    ` tablero, la cara no aparece en camara limpia mientras se lee`
  );
};

export const faltasDeCobertura = (camino, det) => {
  if (!esLectura(det)) return [];
  const pct = `${Math.round(det.literal * 100)}%`;
  if (camino === "portada")
    return [
      `el beat ${det.beat} abre la pieza y lee el libreto al ${pct}. El gancho` +
        " no se cubre con tablero: se elige otra apertura",
    ];
  if (CUBRE.has(camino)) return [];
  return [
    `el beat ${det.beat} lee el libreto al ${pct} y va por «${camino}», que` +
      " deja la cara en cámara limpia. Un tramo leído va cubierto con tablero",
  ];
};
