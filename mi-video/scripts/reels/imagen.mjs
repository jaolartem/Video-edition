/**
 * **Lo que se le hace a la imagen, y cuándo.**
 *
 * El vocabulario —qué virados admite el canon, qué dibuja la costura animada—
 * vive en `scripts/imagen.mjs`. Aquí sólo se resuelve el **horario**, que es la
 * misma división que separa `caminos.mjs` de `capas.mjs`: lo que se pide es
 * editorial y no se escribe a mano; en qué frame cae, sí, y escrito a mano se
 * desfasa al primer reajuste del corte sin avisar.
 *
 * Las dos salen del **plan**, no del EDL, por lo de siempre: la imagen corre
 * sobre una línea más corta —`plan-reel` le quitó el aire— y el desfase crece
 * hasta casi siete segundos al final de la pieza. Ver `reloj.mjs`.
 */
import { FILETE, viradoDe } from "../imagen.mjs";

/**
 * Los tramos virados de la pieza, ya con su filtro resuelto.
 *
 * **Escenas contiguas con el mismo virado son un tramo, no varios.** Un beat de
 * 17 s se parte en tres o cuatro escenas y las tres llevan el mismo virado —lo
 * pone `plan-reel.mjs` a propósito—: emitir una capa por escena serían tres
 * tramos pegados diciendo lo mismo, y el día que uno se quedara un frame corto
 * el plano parpadearía de color en mitad de la etapa.
 *
 * Y se unen **cruzando la frontera del beat**: dos etapas seguidas viradas
 * igual son una sola decisión de color, así que si el diseñador vira dos
 * etapas consecutivas en sepia no hay ningún corte de tono entre ellas.
 */
export function viradosDe(reloj) {
  const out = [];
  for (const l of reloj.limites()) {
    const v = viradoDe(l.escena?.virado);
    if (!v) continue;
    const ultimo = out[out.length - 1];
    if (ultimo && ultimo.virado === v.virado && ultimo.at + ultimo.duration >= l.a) {
      ultimo.duration = l.b - ultimo.at;
      continue;
    }
    out.push({ at: l.a, duration: l.b - l.a, virado: v.virado, css: v.css });
  }
  return out;
}

/**
 * Las costuras que el diseñador pidió cruzar con un filete.
 *
 * **Una por etapa.** `transicion` es la costura de ENTRADA del beat y sólo la
 * lleva la primera escena de cada tramo del EDL; un beat repartido en dos
 * tramos tiene dos escenas con `k === 0`, así que sin la cuenta de vistos la
 * misma etapa se anunciaría dos veces.
 *
 * **Nunca en el frame 0.** La pieza abre con el gancho: un filete cruzando
 * sobre el primer frame no tapa ninguna costura porque no hay ninguna, y lo
 * único que hace es gastar el recurso antes de que sirva.
 */
export function filetesDe(reloj) {
  const out = [];
  const vistos = new Set();
  for (const l of reloj.limites()) {
    if (l.escena?.transicion !== "filete") continue;
    if (vistos.has(l.beat)) continue;
    vistos.add(l.beat);
    if (l.a <= 0) continue;
    out.push({ at: l.a, duration: FILETE.dura, grosor: FILETE.grosor,
               segundo: FILETE.segundo });
  }
  return out;
}

/**
 * Las dos, juntas, para que la pieza las reciba de una sola llamada.
 *
 * No es azúcar: `reels-spec.mjs` es el camino de fases y cada línea que se le
 * añade es una regla más viviendo donde no debe. Que el tratamiento de la
 * imagen entre por una puerta es lo que deja añadir un virado mañana sin volver
 * a abrir el fichero que arma la pieza.
 */
export function imagenDe(reloj) {
  return { virados: viradosDe(reloj), filetes: filetesDe(reloj) };
}
