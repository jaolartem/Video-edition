/**
 * **Cuándo entra una capa y cuándo se resuelve cada cosa dentro de ella**,
 * resuelto siempre contra el corte de hoy.
 *
 * Sale de `tableros.mjs`, que hacía dos cosas de tamaños muy distintos: armar el
 * horario de tableros y paneles, y traducir lo que el diseño ancló. La segunda
 * creció el día que las casillas empezaron a resolverse con la voz, y es una
 * responsabilidad propia — la prueba es que la regla que la gobierna es una y
 * vale para las dos alturas.
 *
 * La regla, y es de Jaime: *«las anclas tienen la función de establecer los
 * lugares; si el vídeo se edita o se corta, el ancla cambia»*. Por eso un ancla
 * es **texto** y no un segundo: un segundo se queda clavado donde estaba y el
 * corte se mueve todas las semanas.
 * @clase sistema
 */
import { FPS } from "./reloj.mjs";

/** El primer subtítulo que dice `q`, o `null`. `q` ya viene en minúsculas. */
const donde = (captions, q) =>
  (captions ?? []).find((c) =>
    String(c.text ?? "").toLowerCase().includes(q),
  ) ?? null;

/**
 * **Cada casilla se resuelve CUANDO SE DICE, no a tiempo de lectura.**
 *
 * Es la regla del canon —*«los nodos aparecen anclados a palabras concretas del
 * transcript, no a tiempos fijos; es el pago real del trabajo de
 * transcripción»*— y es lo que separa una lámina que se construye al ritmo de la
 * voz de una que se monta sola y se queda quieta. Sin ella las cinco casillas de
 * reel-04 e5 se tachaban en 6,2 s mientras la voz tardaba 10 en decirlas: al
 * llegar «ponerse en la mira», el sello llevaba cuatro segundos puesto.
 *
 * Devuelve el desplazamiento en frames **desde el arranque del panel**, que es
 * la referencia con la que dibuja `Casillas` dentro de su `<Sequence>`.
 */
export function cuandoSeDice(casillas, at, captions) {
  if (!Array.isArray(casillas)) return undefined;
  return casillas.map((c) => {
    const q = typeof c?.ancla === "string" ? c.ancla.trim().toLowerCase() : "";
    if (!q) return c;
    const cue = donde(captions, q);
    return cue && cue.at > at ? { ...c, en: cue.at - at } : c;
  });
}

/**
 * El frame donde la capa tiene que entrar, si el diseño lo declaró.
 *
 * `props.anclas` son segundos de la PIEZA MONTADA —lo que se oye—, que es la
 * misma referencia con la que se compuso. Se toma el primero: es cuando se dice
 * lo que el tablero nombra.
 *
 * **Y si el ancla es TEXTO, se resuelve contra el corte de hoy.** Jaime, al ver
 * que esto era lo único que no se re-derivaba: *«hay una línea de producción,
 * ¿por qué no se deriva solo?»*. Porque `anclas` era el único dato del diseño
 * escrito en SEGUNDOS: todo lo demás está expresado contra algo estable —los
 * tableros contra su etapa, los subtítulos contra la transcripción, los
 * encuadres contra las escenas— y por eso sobrevive a que se corte. Un número
 * sigue valiendo, y sigue quedándose clavado: por eso lo dice `llega.py`.
 */
export function anclaDeclarada(b, reloj, captions) {
  // **Un panel también la declara.** En la segunda vuelta de `armarPaneles` el
  // objeto ya no lleva `props`, así que `b.props.anclas` era siempre `undefined`
  // y un panel no podía arrancar con la palabra por mucho que lo declarase.
  const a = b?.props?.anclas ?? b?.anclas;
  const s = Array.isArray(a) ? a[0] : a;
  const seg = typeof s === "object" && s !== null ? (s.segundo ?? s.en) : s;
  const inicio = reloj.anclaDe(b.beat);
  if (typeof seg === "string" && seg.trim() && Number.isNaN(Number(seg))) {
    const cue = donde(captions, seg.trim().toLowerCase());
    if (!cue) return null;
    return cue.at >= inicio ? cue.at : inicio;
  }
  const n = Number(seg);
  if (!Number.isFinite(n) || n < 0) return null;
  // No se adelanta a la etapa: una capa que entra antes de que su beat exista se
  // pinta sobre lo que dice otra cosa.
  const at = Math.round(n * FPS);
  return at >= inicio ? at : null;
}
