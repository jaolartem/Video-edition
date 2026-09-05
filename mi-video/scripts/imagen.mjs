/**
 * **El tratamiento de la imagen: lo que se le hace al plano y a la costura.**
 *
 * Jaime, pidiendo las dos en la misma frase: *«que me ponga en sepia… que haga
 * una animación en esa transición, ya tiene más herramientas de diseño, está
 * muy mediocre el diseñador»*.
 *
 * Y ninguna de las dos existía. Lo único que teñía el plano era `desatura` —el
 * blanco y negro de la marca de humanidad—, que no es del diseñador: lo coloca
 * `marcaDeHumanidad` junto a la corrección de lo dicho. La costura sólo tenía
 * tapaderas automáticas. O sea que el canon nombra el virado y la animación
 * desde hace semanas y no había por dónde pedirlos, que es la avería que este
 * proyecto lleva repitiendo: **declarar sin implementar**.
 *
 * ## Por qué vive aparte de `camara.mjs`
 *
 * Son dos responsabilidades. Allí se decide **de qué habla el plano** —encuadre
 * y movimiento— y aquí **cómo se ve** el plano ya elegido. El menú del
 * diseñador sigue siendo uno solo: `camara.mjs` empalma estas dos familias en
 * el vocabulario que viaja al pedido, así que él no ve la costura.
 *
 * ## Se declara y se resuelve en el mismo sitio
 *
 * Igual que `movimientoDe`: el nombre **y** el filtro salen de aquí, y lo que
 * viaja al spec es el filtro ya resuelto. Un catálogo de nombres en un lado y
 * una tabla de filtros dentro del render son dos copias de la misma decisión, y
 * la segunda se desvía el día que alguien añada un virado.
 *
 * ## Y la familia sale del canon, no del gusto
 *
 * `docs/canon.md` fija una paleta **oscura y desaturada con el oro como único
 * tono vivo**, y prohíbe por nombre el oro decorativo, los degradados suaves y
 * las sombras. Un virado es un tono encima de la cara de Jaime durante toda una
 * etapa: si no pertenece a esa familia, no es un recurso, es un filtro de
 * teléfono. Los tres de abajo pertenecen; `NO_ENTRAN` dice cuáles no y por qué,
 * que es la mitad que evita que vuelvan dentro de un mes.
 */

/**
 * Los virados que el canon admite. `css` es el filtro que se aplica al plano.
 *
 * `que` dice qué hace y `porque` de dónde sale en el canon: un valor de menú
 * sin su motivo se elige por variar, y variar por variar es justo lo que
 * convierte un recurso en un tic.
 */
export const VIRADOS = {
  sepia: {
    que: "el plano se vira a cálido apagado. Dice «esto ya pasó» sin decirlo:"
      + " el antes de un then/now, lo heredado, la escena de recuerdo",
    porque: "el canon ya usa el 4:3 como cita —«esto es de antes»— y la paleta"
      + " es oscura y desaturada, así que un cálido bajo de saturación"
      + " pertenece a la familia. Un sepia subido no",
    css: "sepia(0.68) saturate(0.85) contrast(1.06)",
  },
  navy: {
    que: "el plano se vira al navy de la paleta: frío, institucional, de"
      + " oficina. Para la etapa que habla del sistema y no de la persona",
    porque: "`navy` (#252A44) es la superficie alterna del canon y el azul es"
      + " su jerarquía media —lo que NO es el foco—. Virar ahí no mete un color"
      + " nuevo: usa el que ya está",
    css: "sepia(0.9) hue-rotate(185deg) saturate(1.35) brightness(0.95)"
      + " contrast(1.06)",
  },
  duro: {
    que: "el plano se endurece sin cambiar de tono: negros cerrados, color"
      + " bajo, contraste alto. Para el remate y para la acusación",
    porque: "«contraste alto» está literal en el canon como piel Gen Z/Alpha, y"
      + " bajar el color acerca el plano a la paleta en vez de alejarlo",
    css: "contrast(1.3) saturate(0.78) brightness(0.95)",
  },
};

/**
 * Lo que **no** entra en la familia, dicho con su motivo.
 *
 * Es la lección de C-191 aplicada antes de que cueste una entrega: la lista de
 * lo que se puede pedir **es** la política, así que un virado que el canon
 * prohíbe tiene que aparecer prohibido y no simplemente ausente. Ausente se
 * reinventa; prohibido con motivo, no.
 */
export const NO_ENTRAN = {
  oro: "un virado dorado sobre el plano es ORO DECORATIVO, que el canon prohíbe"
    + " por nombre. El oro es lo que el espectador debe mirar; si tiñe la cara"
    + " entera deja de señalar nada",
  blanco_negro: "existe y no es tuyo. Es la MARCA DE HUMANIDAD y la coloca"
    + " `marcaDeHumanidad` pegada a la corrección de lo dicho, una o dos por"
    + " minuto. Poder pedirlo por etapa sería una segunda fuente de la misma"
    + " decisión, y entonces el desliz reconocido pasa a ser un efecto",
  brillo: "halo, bloom, viñeta o desenfoque de fondo: «degradados suaves» y"
    + " `backdrop-filter` están en la lista de prohibiciones sin excepción",
};

/** El virado ya resuelto, o `null` si no se pidió ninguno. */
export const viradoDe = (nombre) => {
  const v = VIRADOS[nombre];
  return v ? { virado: nombre, css: v.css } : null;
};

/** El bloque del menú, para que `camara.mjs` lo empalme sin repetirlo. */
export const bloqueVirado = () => ({
  que: "un tratamiento de color sobre el PLANO de esa etapa. No es una capa"
    + " encima: es la propia imagen la que cambia, así que dura lo que dura la"
    + " etapa y el subtítulo y el tablero van por encima sin enterarse.",
  valores: Object.fromEntries(
    Object.entries(VIRADOS).map(([k, v]) => [k, `${v.que}. ${v.porque}`])),
  no_entran: NO_ENTRAN,
  cuantos: "Uno o dos por pieza. Un virado que se repite en cinco etapas deja"
    + " de decir nada y pasa a ser el look del vídeo, que es otra cosa y no la"
    + " pediste.",
  si_no_dices: "el plano sale como se grabó, que es lo normal y lo que se"
    + " espera de una etapa que no necesita comentario",
});

/**
 * **La costura animada.** Es la tercera vía y la que Jaime pidió por su nombre.
 *
 * Las otras dos tapan: el `glitch` distorsiona la imagen y la retirada
 * `cortinilla` interrumpía con una placa. Ésta no tapa — **pasa algo por
 * delante** y el corte cae debajo mientras pasa.
 *
 * Y es un filete, no un bloque, por dos razones que son del canon:
 *
 * - **El filete es el separador del canon**: *«bloques planos de color
 *   separados por filetes, nunca por sombra»*. Separar dos planos en el tiempo
 *   es esa misma gramática aplicada al corte.
 * - **No va en oro.** *«El oro reservado a aquello que el espectador debe
 *   atender»*, y una costura no lo es. Va en `lightNeutral` con un segundo
 *   filete en `secondaryBlue`, que es la jerarquía de lo que acompaña.
 *
 * Lo que **no** es: la barra gruesa de `BarWipe`. Ésa se probó en todos los
 * cambios de encuadre y quedó peor que el salto —*«se evita esa transición con
 * un cuadrito como única herramienta; la próxima vez, si sale, es para que
 * aparezca un gráfico»*—, así que sigue reservada a la entrada de una tarjeta.
 */
export const ANIMADAS = {
  filete: {
    que: "dos filetes cruzan el cuadro en diagonal sobre la costura, el segundo"
      + " un poco detrás del primero. Es la transición ANIMADA: no distorsiona"
      + " la imagen ni interrumpe con una placa, pasa algo por delante y el"
      + " corte cae debajo. 0,33 s. Pídela en la costura donde el salto se ve y"
      + " el glitch sobra — dos efectos en la misma costura son ruido",
    placa: false,
  },
};

/** Lo que dura el cruce y de qué grosor va cada filete, en px de 1080×1920. */
export const FILETE = { dura: 10, grosor: 6, segundo: 3 };

/** Transiciones que hoy no se pueden hacer, con lo que cuestan. */
export const POR_HACER = {
  fundido: {
    que: "la toma anterior se desvanece dentro de la siguiente en vez de"
      + " cortar",
    cuesta: "el render abre UN solo `OffthreadVideo` sobre el corte ya montado,"
      + " así que no hay dos imágenes a la vez. Haría falta emitir el solape en"
      + " el propio corte (`render-hook.mjs`) y una segunda capa de vídeo en"
      + " `src/Ad.tsx` que se cruce con la primera",
  },
  empuje: {
    que: "la toma siguiente empuja a la anterior fuera del cuadro, en diagonal",
    cuesta: "lo mismo que `fundido` y por lo mismo: dos imágenes a la vez. Con"
      + " eso hecho, las dos salen del mismo mecanismo",
  },
};
