/**
 * **Qué tratamiento lleva el subtítulo en cada escena, y por qué ése.**
 *
 * Jaime, 6-9-2026: *«los CC están feos; pueden ser a negativo solamente para
 * variar el cuadro negro, es decir, unos CC que se compongan mejor respecto a la
 * composición»*, *«hay varios que quedarían bien sin el cuadro, otras a las que
 * le queda bien y otras a las que le quedaría mejor negativo»*, y el límite: *«no
 * te cierres a un solo sistema, pero debe ser coherente con el resto del video»*.
 *
 * Aquí se **decide**; quien mide es `scripts/dominio/trasfondo.py` y quien dibuja,
 * `src/brand/cc.ts`. Los números viven en `src/brand/cc.json` y en ningún otro
 * sitio — la lección de `franja.json`.
 *
 * ## Tres reglas, y las tres tienen su caso
 *
 * 1. **El tratamiento es de la ESCENA, no de la frase.** Cambia donde cambia el
 *    plano, que es un corte y ahí no se ve; cambiar a mitad de frase se lee como
 *    un fallo de render. Es el mismo argumento de `bajarEnElGancho`.
 * 2. **Histeresis.** Una escena sólo estrena tratamiento si su medida se pasa del
 *    umbral MÁS el margen. Sin esto, dos escenas de la misma pared con 0,001 de
 *    diferencia salen distintas y la pieza deja de verse de una mano. Es lo que
 *    hace que la coherencia mande sobre la variedad, en código.
 * 3. **Una escena corta hereda.** Por debajo de `minimo_s` un tratamiento propio
 *    es un destello, y un destello no se lee como composición.
 *
 * ## Y la banda que se mira no es siempre la misma
 *
 * El cc se apoya en la barbilla, sube al hueco de encima de su cabeza cuando de
 * verdad cabe, y baja a la franja mientras el rótulo del gancho está en cuadro
 * (C-267). Son tres sitios distintos con tres fondos distintos, así que la medida
 * que decide es la de la banda donde el cc **está de verdad** en esa escena.
 */
import fs from "node:fs";
import { trasfondoDe } from "./material.mjs";

const J = JSON.parse(fs.readFileSync("src/brand/cc.json", "utf8"));
const U = J.umbrales;
const CABEZA = J.cabeza;
/** La altura del cuadro. Copia consciente de `layout.height`, como en `franja.mjs`. */
const ALTURA = 1920;

/**
 * **Si el cc de esa banda le tapa la cara** (C-624, C-632): el texto se apoya
 * en el suelo de la banda y crece hacia arriba hasta dos renglones —un cue se
 * corta a 36 caracteres—, así que tapa si ese bloque cruza entre sus ojos y su
 * boca. Por debajo de la boca, sobre la barba, es «pegado a la barbilla», que
 * es lo que Jaime pidió. Encima de la cabeza no tapa; sin medida, no se acusa.
 */
const FRANJA = JSON.parse(fs.readFileSync("src/brand/franja.json", "utf8"));
const SUELO = { barbilla: J.suelo_barbilla, franja: FRANJA.suelo };
/** Dos renglones de cc: 62 px de cuerpo con interlineado 1,2. Copia consciente. */
const DOS = (2 * 62 * 1.2) / ALTURA;
export const tapaLaCara = (banda, cara) =>
  banda !== "cabeza" && !!cara?.boca &&
  SUELO[banda] - DOS < cara.boca && SUELO[banda] > (cara.ojos ?? cara.boca);

/** Si el cc cabe en el hueco de encima de su cabeza. Ver `cabeElCcArriba`. */
export const cabeArriba = (coronilla) =>
  !!coronilla &&
  coronilla * ALTURA - CABEZA.desde - CABEZA.margen >= CABEZA.minimo;

/**
 * El tratamiento de una medida, con el margen puesto del lado que toca.
 *
 * Son las tres frases de Jaime en su orden, con **una guarda medida**:
 *
 * 1. El fondo **se mueve o está claro** — ahí un color elegido a mano vale para
 *    el fotograma en que se eligió, y la caja negra sobre claro es un agujero.
 *    Toca negativo… **si el negativo tiene con qué**: `difference` con blanco
 *    devuelve `1 - fondo`, así que muere en el gris medio. La banda de encima de
 *    su cabeza en reel-06 mide luma 0,48 y da 0,115 de contraste: ahí el
 *    negativo no es una alternativa, es un subtítulo que no está.
 * 2. El fondo **está cargado** — el contorno no basta y la caja es lo único que
 *    garantiza que se lea.
 * 3. **Oscuro y quieto** — no necesita caja: la caja sólo taparía imagen.
 *
 * **Y cuando el negativo no llega, se cae al 2 y al 3, no a la caja.** Esto
 * devolvía la caja, y era un no-op razonado al revés: el motivo de salir del
 * cuadro negro sobre un fondo claro es que ahí es un agujero, así que responder
 * con el cuadro negro deja el defecto intacto. Medido, mandaba 17 de las 20
 * escenas de reel-06 —una pared lisa, quieta y a media luz— a la caja, cuando
 * ahí la letra clara con su contorno se lee con 0,43 de diferencia de luma.
 *
 * `anterior` no lo empuja hacia nada: sólo **encarece salir** de donde estaba,
 * que es lo que distingue una decisión estable de un parpadeo.
 *
 * `oro` cierra el negativo para esa escena: ver `escenaConOro` abajo.
 */
export const trato = (m, anterior, oro = false) => {
  const u = (t, suyo) => t * (suyo ? 1 - U.margen : 1 + U.margen);
  const seguia = anterior === "negativo";
  const pide =
    m.luz >= u(U.claro, seguia) || m.movimiento >= u(U.movido, seguia);
  if (pide && !oro && m.contraste >= u(U.contraste, seguia)) return "negativo";
  if (m.grano >= u(U.cargado, anterior === "caja")) return "caja";
  return "limpio";
};

/**
 * Devuelve esos subtítulos con el tratamiento de la escena en la que **más
 * tiempo están**, y le deja a la pieza el reparto en `pieza.cc` para poder
 * contarlo desde fuera sin volver a decidirlo.
 *
 * **Recibe las cues y no las lee de la pieza** porque llega encadenada detrás de
 * `bajarEnElGancho`: el tratamiento se mide en la banda donde el cc está de
 * verdad, y bajo el gancho ésa es otra. Encadenadas, el orden no se puede
 * invertir por accidente.
 *
 * Sin medida no se inventa nada: las cues salen con `cc.por_defecto` —la caja,
 * que siempre se lee— y `pieza.cc` queda en `null`, así que quien lo lea ve que
 * no hubo medición. Apostar por el tratamiento más bonito sobre un fondo que
 * nadie ha visto es exactamente cómo se pierde una decisión.
 */
export function trataElCc(pieza, slug, captions) {
  const trasfondo = trasfondoDe(slug);
  pieza.cc = null;
  if (!trasfondo?.length) return captions;
  const titular = (pieza.recortes ?? []).find((x) => x.elemento === "titular");
  // **La cara de cada escena, no la de la pieza** (C-624). Con una sola
  // coronilla —la mediana de cuatro fotogramas— reel-19 llevaba el cc a la
  // barbilla en todas, y en sus primeros planos la boca cae en 0,68-0,74: el
  // texto se la tapaba. Sin medida de la escena, la de la pieza.
  const caras = new Map((pieza.cara?.escenas ?? []).map((x) => [x.escena, x]));
  const finGancho = titular ? titular.at + titular.duration : 0;
  const FPS = 30;

  /**
   * **La escena que lleva oro no va en negativo.**
   *
   * La corrección y la idea fuerza pintan una palabra en oro, y el oro del canon
   * dice «mira aquí». `difference` no respeta un color: lo recalcula contra el
   * fondo, así que ese oro saldría de otro color en cada fotograma y dejaría de
   * significar nada.
   *
   * **Y se cierra la ESCENA, no la cue**, que fue el primer intento y rompía la
   * regla 1 por dentro: en reel-01 el gancho salía negativo, caja y limpio en
   * cinco segundos —tres tratamientos seguidos— porque la cue del medio llevaba
   * la idea fuerza. Un cambio a mitad de plano no se lee como composición.
   */
  const escenaConOro = (a, b) =>
    (captions ?? []).some(
      (c) =>
        (c.corrige || c.realza) &&
        c.at / FPS < b &&
        (c.at + c.duration) / FPS > a,
    );

  const escenas = [];
  let previo = null;
  for (const t of trasfondo) {
    // Bajo el gancho el cc baja a la franja, así que el fondo que le toca es el
    // de la franja y no el de su sitio normal.
    const enGancho = t.desde * FPS < finGancho;
    const cara = caras.get(t.escena);
    // **Y si la barbilla le tapa la cara, baja a la franja** (C-632): reel-19,
    // en plano completo, tiene la boca en 0,53-0,57 y la barbilla la cruza;
    // apoyado en la franja el texto queda debajo, sobre la barba.
    const cual = enGancho ? "franja"
      : cabeArriba(cara?.coronilla ?? pieza.cara?.coronilla) ? "cabeza"
      : tapaLaCara("barbilla", cara) && !tapaLaCara("franja", cara) ? "franja" : "barbilla";
    const m = t.bandas[cual] ?? t.bandas.barbilla;
    if (!m) continue;
    const corta = t.hasta - t.desde < U.minimo_s;
    const suyo = trato(m, previo, escenaConOro(t.desde, t.hasta));
    // Una escena corta hereda; la primera no tiene de quién, así que se queda
    // con lo suyo — un destello al principio de la pieza no existe.
    const cual2 = corta && previo ? previo : suyo;
    escenas.push({ ...t, banda: cual, medida: m, trato: cual2, cara });
    previo = cual2;
  }
  if (!escenas.length) return captions;

  /** La escena que más tiempo ocupa esta cue: el tratamiento es suyo. */
  const dueña = (c) => {
    let mejor = null;
    let solape = 0;
    for (const e of escenas) {
      const n =
        Math.min((c.at + c.duration) / FPS, e.hasta) -
        Math.max(c.at / FPS, e.desde);
      if (n > solape) [mejor, solape] = [e, n];
    }
    return mejor ?? escenas[0];
  };

  // Con su medida al lado: un tratamiento sin el número que lo eligió no se
  // puede comprobar, sólo volver a discutir.
  pieza.cc = escenas.map((e) => ({
    escena: e.escena, beat: e.beat, desde: e.desde, hasta: e.hasta,
    banda: e.banda, trato: e.trato,
    // Sólo con cara medida: sin ella el spec de una pieza ya aprobada no cambia.
    ...(e.cara?.boca ? { boca: e.cara.boca, tapa: tapaLaCara(e.banda, e.cara) } : {}),
    luz: e.medida.luz, grano: e.medida.grano, movimiento: e.medida.movimiento,
    contraste: e.medida.contraste,
  }));
  return captions.map((c) => ({ ...c, trato: dueña(c).trato,
    ...(dueña(c).cara?.coronilla ? { coronilla: dueña(c).cara.coronilla } : {}),
    // La franja se dibuja con `abajo`, como bajo el gancho (C-632).
    ...(dueña(c).banda === "franja" ? { abajo: true } : {}) }));
}
