/**
 * **Ninguna escena a cara pelada.** Regla de Jaime: *«lo que quiero es que
 * siempre haya animaciones, que no sea mi cara y ya»*.
 *
 * Aquí vive lo que audita ese reparto y lo que lo rellena cuando falla. Son tres
 * funciones y una sola responsabilidad: decir qué tratamiento lleva cada trozo
 * de la pieza, y llenar el que se quedó sin ninguno.
 *
 * ## Por qué la unidad es la ESCENA y no el beat
 *
 * Jaime: *«en la tabla de los videos siempre quede relacionado por escena: si es
 * tablero, si tiene animaciones gráficas o si tiene texto animado o CC animado.
 * Siempre debe tener una de las tres y no siento que se esté cumpliendo»*.
 *
 * Por beat no bastaba: un beat de 17 s son tres o cuatro escenas y con un panel
 * al principio el beat entero contaba como tratado mientras las otras dos iban a
 * plano seco. La escena es la unidad que el espectador ve cambiar, así que es la
 * unidad que hay que auditar.
 */
import { FPS } from "./reloj.mjs";
import { acompanaAlPlano } from "./capas.mjs";
import { COLGANTE, partirFrase } from "./texto.mjs";

/**
 * El tratamiento de cada escena, en su orden.
 *
 * Las tres vías, con su orden de prelación cuando coinciden: **tablero**
 * (reemplaza la escena), **animación** (panel detrás del hablante) y **texto**
 * (idea fuerza, remate compuesto o marca de humanidad). El CTA cuenta como la
 * suya propia — es una tarjeta a pleno cuadro. Una escena con ninguna sale
 * marcada con una raya, que es lo que el informe persigue.
 */
export const porEscena = (r, reloj) => {
  const texto = r.captions.filter((c) => c.realza || c.corrige || c.compuesto);
  return reloj.limites().map(({ n, a, b, escena }) => {
    const pisa = (x) => x.at < b && x.at + x.duration > a;
    const trato = r.boards.some((x) => pisa(x) && !acompanaAlPlano(x)) || r.tarjetas.some(pisa)
      ? "tablero"
      : r.paneles.some(pisa) || r.boards.some(pisa)
        ? "animacion"
        : texto.some(pisa)
          ? "texto"
          : r.cta && r.cta.at * FPS < b && (r.cta.at + r.cta.dur) * FPS > a
            ? "cta"
            : "—";
    return { n, a, b, trato, encuadre: escena.encuadre };
  });
};

/**
 * **La escena seca se llena con la capa más barata que no inventa nada**: su
 * propio subtítulo, compuesto.
 *
 * El texto es lo que Jaime dice, así que no hay copy nuevo que aprobar, y es una
 * de las tres formas que él pidió —«texto animado o CC animado»—. Si la escena
 * no tiene ningún subtítulo que admita reparto se queda seca y **se dice cuál**:
 * forzar una animación sobre una frase que no la aguanta es justo lo que el
 * canon prohíbe.
 *
 * Muta `r.captions` a propósito —es la misma lista que viaja en el spec— y
 * devuelve cuántas llenó, que es lo que la pieza publica como `rellenadas`.
 */
export function rellenar(r, colgantes = COLGANTE) {
  let puestas = 0;
  for (const e of r.escenas) {
    if (e.trato !== "—") continue;
    const dentro = r.captions
      .filter((c) => c.at < e.b && c.at + c.duration > e.a)
      .sort((x, y) => y.at - x.at);
    for (const c of dentro) {
      if (c.realza || c.corrige || c.compuesto) break;
      const par = partirFrase(c.text, undefined, colgantes);
      if (!par) continue;
      c.compuesto = par;
      puestas += 1;
      break;
    }
  }
  return puestas;
}

/**
 * **Beats sin ningún tratamiento.**
 *
 * Jaime, sobre los doce segundos del asesor en el reel 1: *«buena parte no tenía
 * ni subs animados ni animaciones por detrás, valdría la pena poner algunas»*. Y
 * era el único beat de la pieza sin nada encima — cosa que nadie podía ver sin
 * ir beat por beat a mano.
 *
 * El reparto dice que cada beat lleva uno: tablero si compara o cuantifica,
 * animación si explica un mecanismo, idea fuerza si afirma, marca si hay desliz.
 * **Un beat sin ninguno es un beat que se cayó del reparto**, no una decisión.
 *
 * Se avisa y no se falla: un beat puede ir a plano seco a propósito —el arranque
 * en frío del reel 5 lo hace— y forzar un tratamiento por cuota sería justo lo
 * que el canon prohíbe, movimiento que no se gana su sitio.
 */
export const sinTrato = (r) => {
  const capas = [...r.boards, ...r.tarjetas, ...r.paneles];
  const marcados = r.captions.filter((c) => c.realza || c.corrige || c.compuesto);
  return (r.ventanas ?? []).flatMap(([a, b], i) => {
    const hay =
      capas.some((x) => x.at < b && x.at + x.duration > a) ||
      marcados.some((c) => c.at < b && c.at + c.duration > a);
    return hay || b - a < 2 * FPS
      ? []
      : [`${i + 1} (${(a / FPS).toFixed(1)}-${(b / FPS).toFixed(1)}s)`];
  });
};
