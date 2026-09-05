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
import { delPaso2, placaDe } from "./material.mjs";
import { TOPE } from "../formas.mjs";
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
// **Y el reparto se MIDE, no se confia.** Jaime, viendo lo que volvio del paso
// de diseno: *«el uso de tableros debe complementarse con los paneles, no todo
// puede ser tablero»*.
//
// La regla de los tres ya estaba escrita —tablero para lo complejo o para tapar
// un corte duro, panel para lo complejo con carga emocional o lo que no da para
// tablero, cc para el resto— y aun asi volvieron 16 plenos contra 13 paneles, y
// una pieza con CINCO plenos y CERO paneles. Una regla que solo esta escrita se
// cumple de media y se incumple en la pieza concreta.
//
// No es un tope de porcentaje: es que la distincion se haya hecho. Una pieza
// que manda todo a pleno no eligio entre las tres vias — uso una.
export function faltaMezcla(slug, declarados) {
  const con = declarados.filter(
    (b) => String(b.props?.cubre ?? "pleno") !== "cc",
  );
  const plenos = con.filter(
    (b) => String(b.props?.cubre ?? "pleno") === "pleno",
  ).length;
  if (con.length < 3 || plenos < con.length) return [];
  return [
    `${slug}: los ${plenos} graficos de la pieza van a pleno y ninguno` +
      " acompana el plano. «No todo puede ser tablero»: un grafico que no lleva" +
      " contenido complejo ni tapa un corte duro le esta quitando el sitio a la" +
      " cara, y sin panel la pieza no tiene registro intermedio.",
  ];
}

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

// Lo que dura la cortinilla: 21 frames, 0,7 s. Es lo que se desvanece dentro
// del propio componente, asi que acortarla la corta a media salida.
const DUR_CORTINILLA = 21;

// Cortinillas pedidas y sin placa, o con la etapa demasiado larga.
export const cortinillasSinSitio = [];

// **Las cortinillas que pidio quien compuso.**
//
// El componente estaba escrito, el hueco estaba en el spec y `Reel.tsx` lo
// dibujaba — y el spec ponia `cortinillas: []` fijo desde que se probaron en
// todas las costuras y quedaron mal. Jaime entonces: «en el segundo 7 se ve
// raro; esos cortes de escena no vale la pena dejarlos como cortes de escena».
//
// Y tenia razon SOBRE PONERLAS EN TODAS, que es lo que se hizo. La conclusion
// que se saco fue otra —quitarlas del todo— y con ella se perdio la pieza
// entera: una mascara que se pone siempre deja de ser mascara, pero una que no
// se puede poner nunca no es una decision, es una ausencia.
//
// Ahora sale donde se pide y solo ahi: `escena_desc.camara.transicion`. Sin
// nadie que la pida no hay ninguna, asi que el estado de hoy no se mueve.
//
// Dos cosas la dejan fuera y las dos se CUENTAN en vez de reventar el render:
// una etapa sin placa en `ads/fondos.json` —la cortinilla ES la placa— y un
// nombre de etapa por encima del tope, que `assertShort` aborta a mitad de
// render diciendo poco.
export function cortinillasDe(slug, reloj, marco) {
  const out = [];
  const total = marco?.beats?.length ?? 0;
  const vistos = new Set();
  for (const e of reloj.escenas ?? []) {
    // **Y una peticion vieja no vuelve por la puerta de atras.** `cortinilla`
    // esta RETIRADA en `camara.mjs`, pero lo que el disenador escribio hace
    // dias sigue en `escena_desc.camara.transicion`: sin esto, quitarla del
    // menu no quita la que ya esta pedida. Se cuenta para que se vea, no se
    // calla — es la diferencia entre retirar un mecanismo y esconderlo.
    if (e.transicion === "cortinilla") {
      cortinillasSinSitio.push(
        `${slug} e${e.beat}: pide «cortinilla», que esta retirada`
        + " (Jaime: «eso ya lo habiamos depreciado… para eso esta el glitch»)."
        + " La costura la tapa el glitch.");
      continue;
    }
    if (e.transicion !== "cortinilla") continue;
    const beat = Number(e.beat);
    // Una por etapa: un beat partido en tres escenas se anuncia una vez.
    if (vistos.has(beat)) continue;
    vistos.add(beat);
    const at = enFrames(e.montado_desde);
    // Nunca en el frame 0: la pieza abre con el gancho, no con una placa.
    if (at <= 0) continue;
    const etapa = marco?.beats?.[beat - 1]?.etapa ?? "";
    const placa = placaDe(slug, beat);
    const por = !placa ? "no hay placa para esa etapa en ads/fondos.json"
      : etapa.length > TOPE.label ? `«${etapa}» pasa de ${TOPE.label} caracteres`
      : null;
    if (por) {
      cortinillasSinSitio.push(`${slug} e${beat}: ${por}`);
      continue;
    }
    out.push({
      at,
      duration: DUR_CORTINILLA,
      props: { placa, etapa, beat: [beat, total], framework: marco.estructura,
               sound: true },
    });
  }
  return out;
}

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
