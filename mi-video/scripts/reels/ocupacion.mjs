/**
 * **Quien cede cuando dos capas quieren el mismo tramo.**
 *
 * Salen de `tableros.mjs`, donde ya estaban juntas y con su motivo escrito
 * —*«vive aqui, con las otras dos reglas de ocupacion, y no en el spec: el spec
 * arma, esto decide quien cede»*—. Lo que faltaba era que ese reparto se viera:
 * mezcladas con el horario de tableros y paneles, las tres reglas de ocupacion
 * no se leian como una sola cosa.
 *
 * Dos capas que ocupan el mismo frame **no fallan**: la de abajo no existe y
 * nadie se entera. Por eso esto es codigo y no una convencion.
 * @clase sistema
 */

/**
 * **Una tarjeta y un tablero no pueden empezar en el mismo frame.**
 *
 * Un beat sin material se ancla donde empieza el siguiente —no tiene sitio
 * propio— y si ese siguiente lleva tablero, los dos ocupan el cuadro entero a la
 * vez: se pintan uno encima del otro y la tarjeta no existe. En el reel 2 la del
 * beat 2 y el tablero del beat 3 salían los dos en 6,9 s. La tarjeta va primero
 * —es el beat anterior— y el tablero entra cuando ella termina, que además es el
 * orden del argumento.
 */
export const empujaTablero = (cartas) => (at) =>
  cartas.reduce(
    (t, c) => (c.at <= t && t < c.at + c.duration ? c.at + c.duration : t),
    at,
  );

/**
 * ¿Este trozo se pisa con alguno de los que ya ocupan el cuadro?
 *
 * El contraste es la tercera capa que toma el frame entero y la unica que no
 * pasaba por ningun empujon: en reel-02 se pintaba sobre la cabecera del tablero
 * que venia detras. Vive aqui, con las otras dos reglas de ocupacion, y no en el
 * spec: el spec arma, esto decide quien cede.
 */
export const sePisa = (x, ocupantes = []) =>
  !!x && ocupantes.some((o) => o.at < x.at + x.duration &&
                               o.at + o.duration > x.at);


/**
 * **Un tramo lo dibuja UNA capa, y con un tablero puesto es el tablero.**
 *
 * Dice si el contraste cede, y de paso limpia lo que sobra debajo del que sí
 * entra. Vive aquí y no en el spec por lo mismo que `sePisa`: **el spec arma,
 * esto decide quién cede** — allí eran veinticinco líneas de por qué dentro del
 * bucle que monta las siete piezas, o sea la regla escrita en el sitio donde
 * nadie la busca.
 *
 * La regla ya estaba escrita y **no podía cumplirse por dos motivos a la vez**,
 * que es lo que la dejó invisible:
 *
 * 1. Se preguntaba por `pieza.tableros`, y el campo se llama `boards`. O sea
 *    que la lista de ocupantes era siempre `[]` y `sePisa` contestaba «no» sin
 *    mirar nada.
 * 2. Aunque hubiera contestado «sí», la retirada se deshacía doce líneas más
 *    abajo: `if (contraste) pieza.contraste = contraste` volvía a publicar la
 *    capa que se acababa de quitar.
 *
 * Lo que salió por ahí, medido en el render 7 de reel-02 y visto en los
 * fotogramas: el contraste ocupaba 463–946 y encima de él vivían el tablero de
 * comparación (494–863) y la acumulación (839–1238). En pantalla, la tarjeta de
 * `$44` —la cifra HABLADA, la que el CC corrige— tapaba media tarjeta de `$46`
 * —la cifra buena—, las dos del mismo dato en el mismo frame; y de la
 * acumulación sólo se leía «AÑO 1» porque los otros cuatro años quedaban debajo.
 *
 * Gana el tablero y no el contraste, y no es un desempate de composición: el
 * tablero lleva `$46` con su fuente y su condición, que es el par 54/46 de la
 * tabla `dato`; el contraste lleva el `$44` de antes de la corrección.
 *
 * **Y bajo el contraste que sí entra, el remate compuesto sobra.** Las dos
 * cifras ya están arriba y grandes: repetir una debajo es la misma información
 * en dos capas. El subtítulo sigue, plano.
 */
export function contrastePisado(x, ocupantes = [], captions = []) {
  if (sePisa(x, ocupantes)) return true;
  for (const c of (x ? captions : [])) {
    if (c.compuesto && c.at < x.at + x.duration && c.at + c.duration > x.at) {
      delete c.compuesto;
    }
  }
  return false;
}
