/**
 * **Una placa de fondo por pieza, y se comprueba sobre lo que se pinta.**
 *
 * Jaime, 6-9-2026: *«es un FONDO de tablero por reel»*.
 *
 * ## Por qué esto es un fichero y no una línea en `fondos.json`
 *
 * **Porque la regla ya estaba escrita al revés y nadie la miraba.** El catálogo
 * decía —con estas palabras— *«lo que sí no se repite es la placa DENTRO de una
 * misma pieza»*, o sea justo lo contrario, y mapeaba placa → beat: cada tablero
 * pedía la suya y salía la suya. Medido el 6 de septiembre sobre `src/reels.json`:
 * R6 con cuatro placas distintas, R2 y R5 con tres, R1, R3 y R4 con dos, y sólo
 * R7 con una. Tres placas en una pieza son tres piezas cosidas.
 *
 * Cambiar el catálogo arregla el reparto de hoy y no impide el de mañana: la
 * placa declarada en `escena_desc.tablero` **gana** sobre la de la pieza —y así
 * tiene que ser, porque declarar sin poder aplicar es la avería de la casa—, de
 * modo que un diseño puede volver a meter una segunda placa sin que nadie se
 * entere. Esto lo cuenta y lo dice.
 *
 * Es el mismo reparto que `paneles.mjs`: aquí vive lo que se exige y quién para
 * la pieza es `puerta.mjs`. Y devuelve **el motivo**, no un booleano.
 *
 * ## Qué cuenta como fondo de la pieza
 *
 * Lo que pinta placa: los tableros a cuadro completo, los bloques de panel que
 * la llevan detrás, las cortinillas y la tarjeta de cierre. Todo lo que el
 * espectador ve como suelo. Si dos de esas capas dibujan placas distintas, la
 * pieza no se ve de una sola mano — que es lo único innegociable.
 */

/** De dónde puede salir una placa en una pieza ya armada, con su nombre. */
const CAPAS = [
  ["el tablero", (r) => (r.boards ?? []).map((b) => [b.props?.placa, b.beat])],
  ["el panel", (r) => (r.paneles ?? []).flatMap(
    (p) => (p.bloques ?? []).map((b) => [b.placa, p.beat]))],
  ["la cortinilla", (r) => (r.cortinillas ?? []).map(
    (c) => [c.props?.placa, c.props?.etapa])],
  ["el cierre", (r) => (r.cta ? [[r.cta.placa, "CTA"]] : [])],
];

/**
 * Las placas que pinta esta pieza, cada una con dónde sale. `Map` de nombre a
 * lista de sitios, para poder decir **dónde** y no sólo cuántas.
 */
export function placasDe(r) {
  const donde = new Map();
  for (const [capa, saca] of CAPAS) {
    for (const [placa, beat] of saca(r)) {
      if (!placa) continue;
      if (!donde.has(placa)) donde.set(placa, []);
      donde.get(placa).push(`${capa} del beat ${beat ?? "?"}`);
    }
  }
  return donde;
}

/**
 * Los motivos por los que esta pieza no se monta: ninguno, o uno. Lista vacía =
 * el fondo es uno solo. Lo llama `puerta.mjs`, que es quien para, y devuelve
 * lista —y no un motivo suelto— para que allí sea la misma línea que los
 * paneles y el gancho.
 *
 * **Cero placas no es una falta aquí**: una pieza sin placa declarada la
 * denuncia `cierreSinPlaca`, que es quien mira ese hueco. Lo que esto mira es
 * lo contrario — que haya más de una.
 */
export function faltasDeFondo(r) {
  const donde = placasDe(r);
  if (donde.size < 2) return [];
  const detalle = [...donde.entries()]
    .map(([placa, sitios]) => `«${placa}» en ${sitios.join(" y ")}`)
    .join("; ");
  return [`${r.id}: pinta ${donde.size} placas de fondo y tiene que pintar UNA` +
    ` — ${detalle}. Jaime: «es un FONDO de tablero por reel». Se elige la que` +
    ` sirve al argumento central de la pieza, no la que le viene bien a un beat` +
    ` suelto; un beat que pida otra cosa se resuelve con la composicion encima` +
    ` —masas, figura, encuadre—, no cambiando el suelo. La de la pieza esta en` +
    ` \`ads/fondos.json\` (\`pieza\`); una capa que pinte otra la declaro su` +
    ` tablero en \`escena_desc\` y hay que quitarsela.`];
}
