/**
 * **Lo que se pone encima del plano, y cuándo.**
 *
 * El contenido de cada capa lo decide el diseñador y vive en `escena_desc`; aquí
 * sólo se resuelve el horario — en qué frame entra y cuánto dura— que es lo que
 * **no se escribe a mano**: escrito a mano se desfasa al primer reajuste del
 * corte y no avisa.
 *
 * Tres reglas ordenan todo el fichero y se repiten en cada función:
 *
 * 1. **La duración la decide la lectura.** Un dato que no da tiempo a leer no
 *    está en el vídeo aunque esté en el frame.
 * 2. **Dos capas no se apilan.** Cuando dos ocupan el mismo frame la de abajo no
 *    existe, y nadie se entera: se pintan una encima de otra sin error.
 * 3. **Una capa sin sitio no se emite.** Duración cero o negativa hace que
 *    Remotion aborte con «durationInFrames must be positive», que no dice nada
 *    de qué capa fue.
 */
import { FPS, enFrames } from "./reloj.mjs";
import { duracionTarjeta } from "./lectura.mjs";
import { delPaso2 } from "./material.mjs";
import { TARJETAS } from "./copy.mjs";
import { DICE } from "./texto.mjs";
import { construir, revisarPieza } from "../caminos.mjs";

/**
 * **`cubre` reparte en tres vías, y lo decide el diseñador.**
 *
 * Regla de Jaime: *«tableros son para contenido complejo o para tapar cortes muy
 * fuertes; panel para contenido complejo que requiere activación emocional, o
 * que no es tan complejo para un tablero; y cc dinámico en el resto»*.
 *
 * Entraba **todo** como tablero, así que un elemento marcado `panel` se dibujaba
 * dos veces —como tablero y como panel— y encima a pleno cuadro. Con seis a
 * pleno, reel-01 quedó con 90 de sus 142,8 s tapados y Jaime sin aparecer en el
 * tercio de en medio: la puerta paró la pieza.
 *
 * Y el reparto se hace **de una vez y aquí**, no con dos filtros sueltos donde
 * se usan: eran complementarios y nada obligaba a que siguieran siéndolo, así
 * que un valor nuevo de `cubre` podía caer en los dos lados —dibujado dos
 * veces— o en ninguno —perdido sin decir nada—, que es justo el fallo que este
 * reparto vino a arreglar.
 *
 * `cc` no emite nada: esa etapa la lleva el subtítulo dinámico, que ya tiene la
 * idea. No es un hueco, es la opción por defecto del resto.
 */
export function repartirPorCubre(declarados) {
  const pleno = [];
  const panel = [];
  for (const b of declarados) {
    const c = String(b.props?.cubre ?? "pleno");
    if (c === "panel" || c === "banda") panel.push(b);
    else if (c !== "cc") pleno.push(b);
  }
  return { pleno, panel };
}

/**
 * Las tarjetas de los beats sin toma: **elegidas y colocadas**.
 *
 * ## Quién lleva tarjeta
 *
 * **Sólo el beat que NO tiene toma.** La tarjeta es lo que sustituye a un plano
 * que no existe; si el beat tiene audio, ponerla encima es taparlo. Faltaba esta
 * comprobación y se veía en el reel 1: el beat 5 llevaba tarjeta de cuando no
 * tenía toma, y al corregirlo —ahora sí la tiene— la tarjeta siguió puesta,
 * tapando el plano y de paso la costura, que se quedó sin su glitch porque el
 * spec la daba por cubierta.
 *
 * Y **lo declarado a mano gana**: si una pieza trae su tarjeta escrita en
 * `TARJETAS`, ésa se queda; la del paso 2 rellena las etapas que falten.
 *
 * ## Y cuánto dura
 *
 * **La tarjeta no se come el beat sobre el que cae.** Jaime: *«no quitar partes
 * ni poner partes»*. Una etapa sin audio no se saca de la pieza —eso es quitar
 * una parte— pero su tarjeta tampoco puede tapar entera la etapa siguiente: en
 * el reel 3 los 9 s de la demolición se comían los tres beats finales y la pieza
 * acababa sin Jaime en cuadro. Se acota a **la mitad** del beat en el que
 * aterriza, y si con eso baja de lo que tarda en leerse se dice por consola.
 *
 * **Y hacen cola, no se apilan.** Varios beats seguidos sin material se anclan
 * todos donde empieza el primero que sí lo tiene, así que salían los tres en el
 * mismo frame: sólo se veía el último y las otras dos etapas no existían. Van en
 * el orden del argumento, cada una cuando acaba la anterior.
 */
export function tarjetasDe(slug, { marco, edl, reloj }) {
  const conToma = new Set(
    (edl.detalle ?? []).filter((u) => u.texto).map((u) => u.beat),
  );
  const aMano = TARJETAS[slug] ?? [];
  return [
    ...aMano,
    ...delPaso2(slug, marco.estructura, marco.beats).filter(
      (t) => !aMano.some((m) => m.beat === t.beat),
    ),
  ]
    .filter((t) => !conToma.has(t.beat))
    .map((t) => ({
      at: reloj.anclaDe(t.beat),
      duration: (() => {
        const quiere = duracionTarjeta(t.props);
        const a0 = reloj.anclaDe(t.beat);
        const a1 = reloj.anclaDe(t.beat + 2);
        const sitio = a1 > a0 ? Math.floor((a1 - a0) / 2) : quiere;
        if (sitio < quiere) {
          console.log(
            `    ojo: la tarjeta del beat ${t.beat} pide ${(quiere / FPS).toFixed(1)}s ` +
            `y solo caben ${(sitio / FPS).toFixed(1)}s sin tapar la etapa siguiente. ` +
            `Se acorta: repasa que el copy siga leyendose.`,
          );
        }
        return Math.max(FPS, Math.min(quiere, sitio));
      })(),
      props: t.props,
    }))
    .sort((x, y) => x.at - y.at || x.props.beat[0] - y.props.beat[0])
    .map((t, i, todas) => {
      const previa = todas[i - 1];
      return previa && previa.at + previa.duration > t.at
        ? { ...t, at: previa.at + previa.duration }
        : t;
    });
}

/**
 * **Un glitch en cada costura que no tape ya un tablero.**
 *
 * Jaime: *«hay cortes muy fuertes todavía… lo ideal es que no se note. Se puede
 * poner una transición discreta, un efecto glitch que distorsione la imagen y el
 * sonido como un TV antiguo cambiando de canal, durante poco tiempo»*.
 *
 * **Sólo donde la costura salta, no en todas.** Una máscara que se pone siempre
 * deja de ser máscara: se convierte en el efecto, y entonces el corte limpio y
 * el malo se ven igual de raros. `costuras.py` mueve lo que se puede mover **sin
 * perder voz** y deja en `costuras_duras` lo que no tuvo arreglo. Eso, y sólo
 * eso, se disimula.
 *
 * Va **centrado en la costura** —mitad antes, mitad después— para que el corte
 * caiga dentro de la distorsión y no en su borde. Y **donde está la costura en
 * la pieza, no en el EDL**: acumulando el EDL entraba hasta 6,8 s tarde, o sea
 * en mitad de una frase en vez de encima del salto que venía a tapar.
 */
/**
 * Cuánto dura la distorsión que tapa una costura. 5 frames, 0,17 s.
 *
 * Muy corta a propósito: lo que tapa dura un frame, y un efecto más largo deja
 * de esconder el corte para pasar a ser el corte.
 */
const DUR_GLITCH = 5;

export function glitchesDe(edl, reloj, cubren) {
  const duras = new Set(edl.costuras_duras ?? []);
  const out = [];
  for (let i = 0; i < edl.segmentos.length - 1; i++) {
    if (!duras.has(i)) continue;
    const fin = reloj.finDelCorte(edl, i);
    if (fin === null) continue;
    const at = enFrames(fin) - Math.round(DUR_GLITCH / 2);
    if (at < 0) continue;
    // Donde ya hay tablero o tarjeta el plano cambió: no hay salto que tapar.
    const cubierto = cubren.some(
      (b) => at < b.at + b.duration && at + DUR_GLITCH > b.at,
    );
    if (!cubierto) out.push({ at, duration: DUR_GLITCH });
  }
  return out;
}

/**
 * **Las capas de cada segmento salen de su camino, no de un literal.**
 *
 * Jaime: *«creo que el renderizado también debe ser por código, tres caminos y
 * cada camino con sus propias indicaciones; hay muchas decisiones sueltas que
 * simplemente no se están cumpliendo»*. `trato.py` decidía el tratamiento de
 * cada segmento desde hacía días y **el render no lo leía**: por eso la portada
 * salía como un plano con subtítulo.
 *
 * **La unidad es el beat, no el corte.** `depurar.py` parte una etapa en varios
 * trozos al quitar el aire, y todos heredan el mismo `detalle` —con el mismo
 * `trato`—: recorriendo segmentos, la portada de reel-05 emitía sus capas dos
 * veces. Y **el reloj es el del plan**: el `detalle` sigue viniendo del EDL, que
 * es donde vive lo que dice y cómo se trata la etapa; lo único que cambia de
 * sitio es **cuándo**.
 *
 * El lado libre se calcula por escena y no una vez por pieza: el sujeto no está
 * en el mismo sitio en todos los encuadres, y una figura en el lado ocupado tapa
 * justo lo que el camino `cercano` protege.
 */
export function caminosDe({ slug, plan, edl, desc }) {
  const detPorBeat = new Map();
  for (let i = 0; i < edl.segmentos.length; i++) {
    const det = edl.detalle[i] ?? {};
    if (!detPorBeat.has(det.beat)) detPorBeat.set(det.beat, { det, i });
  }
  const porBeat = new Map();
  for (const e of plan.escenas ?? []) {
    const beat = Number(e.beat);
    const dur = enFrames(e.duracion);
    const previo = porBeat.get(beat);
    if (previo) {
      previo.duration += dur;
      continue;
    }
    const d = detPorBeat.get(beat) ?? { det: {}, i: 0 };
    porBeat.set(beat, { at: enFrames(e.montado_desde), duration: dur,
                        det: d.det, i: d.i });
  }
  const out = [];
  const faltas = [];
  for (const { at, duration, det, i } of porBeat.values()) {
    const e = plan.escenas[i] ?? plan.escenas[0];
    const cx = e?.crop ? (e.crop.x + e.crop.w / 2) / 2160 : 0.5;
    const r = construir({ at, duration, desc: desc[det.beat], det,
                          lado: cx < 0.5 ? "der" : "izq" });
    out.push(...r.capas);
    for (const f of r.faltas) faltas.push(`${slug}: ${f}`);
  }
  for (const f of revisarPieza(out)) faltas.push(`${slug}: ${f}`);
  return { capas: out, faltas };
}

/**
 * El contraste se ancla al subtítulo: la cifra entra **cuando se dice**. Si una
 * de las dos no se llega a decir, no se emite — media comparación es peor que
 * ninguna.
 */
export function contrasteDe(id, c, captions) {
  if (!c) return null;
  const cuando = (t) =>
    captions.find((x) => DICE(x.text).includes(DICE(t)))?.at ?? null;
  const a1 = cuando(c.izq.ancla);
  const a2 = cuando(c.der.ancla);
  if (a1 === null || a2 === null) {
    console.log(
      `    ojo: ${id} declara contraste ${c.izq.cifra}/${c.der.cifra} y ` +
      `el montaje no dice ${a1 === null ? c.izq.ancla : c.der.ancla}.`,
    );
    return null;
  }
  const at = Math.min(a1, a2);
  return {
    at,
    duration: Math.max(a1, a2) + 5 * FPS - at,
    props: {
      izq: { ...c.izq, ancla: undefined, at: a1 - at },
      der: { ...c.der, ancla: undefined, at: a2 - at },
      pie: c.pie,
    },
  };
}
