/**
 * **La lengua**: normalizar una frase y saber por donde se parte.
 *
 * Todo lo que compara texto —el rotulo contra lo que se dice, la correccion
 * contra el subtitulo, el dato declarado contra lo que suena— pasa por aqui. Es
 * la leccion de las cuatro funciones `limpio`/`norm` que **no eran copias: eran
 * cuatro reglas distintas con el mismo nombre**.
 */
import fs from "fs";
import { idioma } from "../idioma.mjs";

export const sinTildes = (t) =>
  t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Lo que se dice, sin tildes y con los separadores de millar fuera. */
export const DICE = (t) =>
  sinTildes(String(t)).replace(/(?<=\d)[.,](?=\d)/g, "");

export const pal = (t) => sinTildes(t).match(/[a-z]+/g) ?? [];

/**
 * Raiz de cinco letras para emparejar el rotulo con lo que se dice.
 *
 * El rotulo del reel 2 dice «Trabaja mas» y en la toma suena «trabajÓ fines de
 * semana»: distinta persona, misma palabra. Comparando la forma exacta no
 * casaba, asi que el primer emparejamiento caia en «se queda con 44» —por el
 * «queda» del rotulo, que ahi no significa lo mismo— y el rotulo se quedaba
 * puesto 18,5 s.
 *
 * Cinco letras separan «trabaj-» de «trabalenguas» sin exigir conjugacion.
 */
export const raiz = (w) => w.slice(0, 5);

/**
 * Oro **solo donde hay algo que mirar**: una cifra o una fecha. El resto, navy.
 * El oro decorativo esta prohibido por nombre.
 */
export const CIFRA =
  /\d|\$|(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)/i;

const CONJUNCION = new Set([
  "y", "o", "ni", "pero", "porque", "que", "para", "sin", "con", "cuando",
  "si", "aunque", "mientras", "como", "donde", "hasta", "desde", "sino",
]);

/**
 * **Palabras que dejan la frase colgando.**
 *
 * Es el filtro que separa un remate de un fragmento, y sale de mirar los dos
 * casos reales. «PIERDA LA MITAD EN IMPUESTOS» era un fragmento peligroso -dice
 * lo contrario que la frase: la completa es *«sin que se pierda la mitad en
 * impuestos»*- y «POR SUPUESTO.» es un remate perfectamente bueno. La diferencia
 * no esta en el trozo: esta en **como acaba lo que va justo antes**.
 *
 * Delante del fragmento malo hay «sin que se»; delante del bueno, «reglas». Una
 * preposicion, un articulo, una conjuncion o un clitico **abren una dependencia
 * que la palabra siguiente tiene que cerrar**, asi que cortar ahi parte una
 * unidad sintactica. Detras de un sustantivo o de un verbo pleno, no.
 *
 * Es una lista cerrada y por eso es fiable: el espanol tiene muchas palabras de
 * contenido y muy pocas de funcion.
 */
export const COLGANTE = idioma().colgantes;

export const ultimaPalabra = (t) =>
  sinTildes(String(t).trim()).replace(/[^a-z]+$/, "").split(/\s+/).pop() ?? "";

/**
 * **El subtitulo compuesto**: dos renglones, dos fuentes, dos superficies.
 *
 * Peticion de Jaime: *«el cc tambien puede ser grande, o compuesto —una frase
 * luego otra abajo— con dos fuentes y con mas colores. De esa manera los
 * animamos»*. Ver `Compuesta` en `CaptionBand.tsx` para la parte grafica; aqui
 * vive solo **por donde se parte**.
 *
 * Devuelve `{arriba, abajo, tinte}` o `null` si la frase no admite reparto.
 */
export function partirFrase(texto, preferido) {
  const t = texto.trim();
  const w = t.split(/\s+/).filter(Boolean);
  // Por encima de 62 caracteres no hay reparto que quepa en dos renglones.
  if (t.length > 62) return null;

  const medio = w.length / 2;
  const dentro = (i) => i >= 1 && i <= w.length - 1;

  const arma = (i, tinte) => {
    const arriba = w.slice(0, i).join(" ");
    const abajo = w.slice(i).join(" ");
    // **No se parte detras de una palabra de funcion**: ahi la frase cuelga y
    // el renglon de abajo -que va grande y en versales- deja de ser un remate
    // para ser un fragmento. Misma regla que decide que cue se compone.
    if (COLGANTE.has(ultimaPalabra(arriba))) return null;
    // El remate tiene que ser un remate: ni una palabra suelta ni un parrafo.
    if (abajo.length < 5 || abajo.length > 34) return null;
    // Y el de arriba tampoco puede ser un parrafo: por encima de 40 caracteres
    // envuelve a tres renglones y el bloque sube hasta la cara.
    if (arriba.length < 4 || arriba.length > 40) return null;
    return { arriba, abajo, tinte };
  };

  const tinteDe = (i) => (CIFRA.test(w.slice(i).join(" ")) ? "gold" : "navy");

  if (w.length >= 3) {
    /**
     * **La juntura preferida: donde acababa una cue y empezaba la otra.**
     *
     * Cuando dos cues se juntan para dar tiempo al remate, el sitio por el que
     * partir ya lo eligio whisper al trocear: ahi hubo una pausa. Es la misma
     * razon por la que una frontera de tramo de habla se considera limpia por
     * definicion (aprendizaje 19).
     */
    if (dentro(preferido ?? -1)) {
      const par = arma(preferido, tinteDe(preferido));
      if (par) return par;
    }
    /**
     * **Si hay una cifra, la cifra manda donde se parte.**
     *
     * El canon reserva el oro a lo que el espectador debe mirar, y en una frase
     * hablada eso es el numero. Partiendo justo antes, la cifra encabeza el
     * renglon de abajo y se lleva la superficie dorada: el subtitulo se compone
     * **alrededor del dato**, que es lo que hacen las laminas del canon.
     */
    const cifra = w.findIndex((x) => /\d/.test(x));
    if (dentro(cifra)) {
      const oro = arma(cifra, "gold");
      if (oro) return oro;
    }
    const comas = w.map((x, i) => (x.endsWith(",") ? i + 1 : -1)).filter(dentro);
    const conj = w
      .map((x, i) =>
        CONJUNCION.has(x.toLowerCase().replace(/[^a-zñáéíóú]/gi, "")) ? i : -1)
      .filter(dentro);
    /**
     * Se prueban **todas** las junturas, de la mas centrada hacia fuera, y vale
     * la primera que da dos mitades legibles. Quedarse solo con la mas centrada
     * costaba remates por un caracter.
     */
    const cand = (comas.length ? comas : conj.length ? conj : [Math.round(medio)])
      .slice()
      .sort((x, y) => Math.abs(x - medio) - Math.abs(y - medio));
    for (const corte of cand) {
      const par = arma(corte, tinteDe(corte));
      if (par) return par;
    }
  }

  /**
   * **La otra forma: grande, de un solo renglon.**
   *
   * Jaime da las dos: *«el cc tambien puede ser GRANDE, O compuesto una frase
   * luego otra abajo»*. Una frase corta no se puede partir sin dejar fragmentos,
   * pero entera en Anton versales ocupa el ancho de la banda y **es** el golpe:
   * «POR SUPUESTO.» son dos palabras y a cuerpo 128 cierran el beat.
   *
   * Va **despues** del reparto y no antes: si la frase admite dos renglones, dos
   * renglones dicen mas. Y no depende del numero de palabras -eso bloqueaba las
   * de dos, que son justo las que mejor funcionan aqui.
   */
  return t.length >= 10 && t.length <= 30
    ? { arriba: "", abajo: t, tinte: CIFRA.test(t) ? "gold" : "navy" }
    : null;
}
