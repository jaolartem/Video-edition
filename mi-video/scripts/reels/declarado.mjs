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
 * En la etapa marcada **no se recorta el silencio de entrada**. El resto del
 * aire de la pieza se sigue yendo.
 */
export const pausasDe = (slug) => leer("pausas", slug, {});

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
