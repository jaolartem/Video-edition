/**
 * **Lo que alguien DECLARO para esta pieza**, leido una vez y en un sitio.
 *
 * Se saca de `plan-reel.mjs` por responsabilidad: alli se decide como se parte
 * el montaje, y esto solo LEE decisiones que ya se tomaron —las pausas que se
 * conservan y los tramos que no se vuelven a partir—. Dos cosas distintas en el
 * mismo fichero es el lio que el techo de 300 lineas existe para evitar.
 */
import { execFileSync } from "child_process";

const leer = (verbo, slug, vacio) => {
  try {
    return JSON.parse(
      execFileSync("python", ["scripts/consulta.py", verbo,
                              JSON.stringify([slug])], { encoding: "utf8" }),
    );
  } catch (e) {
    // **Y NO se traga el fallo.** Este `catch` devolvia vacio en silencio, y
    // como `execFileSync` ni siquiera estaba importado, se comio un
    // `ReferenceError` durante semanas: las pausas declaradas del libreto no
    // llegaron nunca al plan y nadie se entero (C-258).
    console.error(`${verbo}: no se pudieron leer —`,
                  String(e.message).slice(0, 120));
    return vacio;
  }
};

/**
 * **Las pausas que se conservan, declaradas en el libreto.**
 *
 * Jaime: *«lo de los silencios tambien puede ser aritmetico… excepto cuando
 * aporta: antes de una revelacion o de una afirmacion importante, siempre y
 * cuando el silencio sea mirando a camara»*. Quitar aire es aritmetica y corre
 * sola; **conservarlo es una decision**, y por eso se declara — con `[pausa]`
 * en el texto del libreto de esa etapa.
 *
 * En la etapa marcada **no se recorta el silencio**. El resto del aire de la
 * pieza se sigue yendo.
 */
export const pausasDe = (slug) => leer("pausas", slug, {});

/**
 * **De que lado se conserva el silencio de esa etapa**, sobre los trozos que
 * `conHabla` ya midio.
 *
 * La marca decia «esta etapa entera» y no habia forma de decir menos. En el
 * beat 7 de reel-01 eso son dos silencios y solo uno es de Jaime: quiere el de
 * despues de «semanales» —*«solo uno es intencional»*— y mando quitar el de
 * 1,0 s de dentro de la frase. Declarar la etapa devolvia los dos, asi que la
 * pausa que el pidio costaba la que no (tiquet #278).
 *
 * Con el lado declarado el aire de dentro se sigue yendo y **solo el borde
 * declarado vuelve a donde el EDL dijo**: `entrada` estira el primer trozo
 * hasta `a`, `salida` estira el ultimo hasta `b`, `ambas` es la etapa entera.
 */
export function conPausa(pausas, beat, a, b, trozos) {
  const donde = pausas?.[String(beat)]?.donde;
  if (!donde) return trozos;
  if (donde === "ambas") return [[a, b]];
  if (donde === "entrada") trozos[0][0] = a;
  if (donde === "salida") trozos[trozos.length - 1][1] = b;
  return trozos;
}

/**
 * **Los tramos que alguien declaro, y por que no se vuelven a partir.**
 *
 * `conHabla` recorta el silencio interno y devuelve trozos; cada trozo acaba
 * siendo una escena, o sea **un corte de plano**. Eso esta bien cuando el
 * segmento lo eligio el automatismo, y esta mal cuando alguien dijo «esta frase
 * va entera»: la declaracion existia justo para quitar ese corte.
 *
 * Paso tres veces con el mismo sitio de reel-01. La tercera, el tramo se declaro
 * entero —562,932-571,050— y el plan salio con dos escenas: un cambio de plano
 * entre «550 dolares» y «semanales». Jaime, la cuarta vez: *«en el reel 1 el
 * problema del semanales persiste»*.
 */
export const fijosDe = (slug) => leer("fijos", slug, []);

/** Si ese rango es uno de los declarados. Tolerancia: el recorte mueve el borde. */
export const esDeclarado = (fijos) => (a, b) =>
  fijos.some(([x, y]) => Math.abs(x - a) < 0.35 && Math.abs(y - b) < 0.35);
