/**
 * **La puerta: qué se renderiza y qué no, y por qué.**
 *
 * El embudo de Jaime ordena los peldaños por coste, y el caro es su atención.
 * Esta puerta existe para no gastarla en una pieza que ya sabemos que no está —
 * *«renderizamos, pero sólo lo que ya sabemos que está bien»*.
 *
 * Cuatro motivos paran una pieza, y los cuatro tienen un vídeo detrás:
 *
 * 1. **Jaime no aparece** en alguno de los tres tercios (y sale poco en total).
 * 2. **Un tablero se come más de un tercio** de la pieza.
 * 3. **Una etapa obligatoria se quedó sin fragmento** y sin copy que la ejecute.
 * 4. **Un hueco largo sin subtítulo** — el argumento tiene que funcionar sin
 *    audio, así que eso no es un detalle de acabado, es la pieza rota.
 *
 * Lo demás que este fichero imprime **no para nada**: es el informe por pieza,
 * que existe para que un defecto no haga falta buscarlo.
 */
import { FPS } from "./reloj.mjs";
import { Tramos } from "./tramos.mjs";
import { DICE } from "./texto.mjs";
import { marcoDe } from "./material.mjs";
import { sinTrato } from "./escenas.mjs";

/**
 * Cuánto metraje con Jaime en cuadro basta por sí solo.
 *
 * Jaime, calibrando: *«más del 60% del vídeo, o en esos tres puntos»*. Si su
 * cara ocupa más de esto la pieza cumple sin mirar dónde caen los tableros —
 * porque entonces la pieza **es** él, y un tablero largo en un sitio no lo hace
 * desaparecer. Por debajo, se exige el reparto en los tres tercios.
 */
const MINIMO_CARA = 0.60;

/**
 * El tramo más largo que se tolera sin una palabra en pantalla.
 *
 * El subtítulo es capa portante: el playbook exige que el argumento funcione sin
 * audio, y **el 85% del vídeo social se ve sin sonido**. Los paneles callaban la
 * banda entera y en el reel 1 eso costó **20 de los 36 subtítulos** —43,6 s de
 * una pieza de 75,2— sin un solo aviso.
 */
const MUDO_MAX = 10 * FPS;

/**
 * Suelo de encaje de un segmento en su etapa: por debajo, lo grabado no cabe
 * dentro de lo que el guion espera ahí. Es el mismo umbral con que
 * `seleccionar.py` admite una candidata, y por eso significa lo mismo en los dos
 * sitios.
 */
const ENCAJE = 0.14;
/**
 * Y cuánto de lo ALCANZABLE hay que cubrir. Es el mismo criterio relativo con
 * que `beats.py` deja competir a una candidata: lo que importa no es el valor
 * absoluto, es la distancia al mejor posible.
 */
const RELATIVO = 0.5;

/**
 * **Una pieza rota no para el lote.** `reels-spec` genera las seis siempre
 * —necesita el spec entero— pero **sólo falla por las que se están montando**.
 *
 * Sin esto, el reel 3 —que se quedó sin material y está esperando decisión— no
 * dejaba renderizar el 1 ni el 2, que estaban bien. Y el trabajo es de uno en
 * uno por instrucción de Jaime, así que bloquear el lote por una pieza en
 * revisión es exactamente lo contrario de lo que hace falta.
 */
const PEDIDOS = (process.env.REELS_PEDIDOS ?? "")
  .split(/[^0-9]+/)
  .filter(Boolean)
  .map((n) => `Reel-R${Number(n)}`);
const bloquea = (r) => !PEDIDOS.length || PEDIDOS.includes(r.id);

/**
 * **Marca la pieza como no renderizable y sigue.** Antes lanzaba, y una pieza
 * incompleta paraba el lote entero.
 *
 * **Y `REELS_VER=1` la renderiza igual, con los motivos escritos.** Jaime: *«el
 * render se necesita, quiero ver lo que va a salir; no importan restricciones,
 * quiero aprobarlo»*. La puerta existe para no gastar su atención en una pieza
 * que no está; cuando el que decide dice que quiere verla, la puerta deja de
 * proteger nada. No se borran los motivos ni se silencian: se imprimen igual y
 * la pieza sale. Lo que cambia es quién decide si se mira, y eso nunca fue del
 * código.
 */
const para = (r, msg) => {
  (r.bloqueado ??= []).push(msg);
  console.log(`    ${bloquea(r) ? "PARA AL PUBLICAR" : "en revisión"} · ${msg}`);
};

/**
 * **El tramo más largo sin una palabra en pantalla.**
 *
 * Sale de repetir aquí el mismo filtro que aplica `Reel.tsx`, porque el defecto
 * que caza es exactamente ése: una capa que tapa el subtítulo más de lo que
 * cree.
 *
 * La tarjeta de CTA se pinta ENCIMA del subtítulo y lleva su propio texto: para
 * esta cuenta tapa igual que una tarjeta. Sin eso el número saldría optimista
 * justo donde la pieza se juega el registro.
 */
export const mudo = (r) => {
  const tapan = new Tramos([
    ...r.tarjetas,
    ...r.cortinillas,
    ...(r.cta ? [{ at: r.cta.at * FPS, duration: r.cta.dur * FPS }] : []),
  ]);
  const vis = r.captions
    .filter((c) => !tapan.sepulta(c))
    .sort((x, y) => x.at - y.at);
  let peor = { a: 0, b: 0 };
  let t = 0;
  for (const c of vis) {
    if (c.at - t > peor.b - peor.a) peor = { a: t, b: c.at };
    t = Math.max(t, c.at + c.duration);
  }
  const fin = Math.round(r.duracion * FPS);
  if (fin - t > peor.b - peor.a) peor = { a: t, b: fin };
  return { ...peor, dur: peor.b - peor.a, visibles: vis.length };
};

/**
 * **Jaime aparece mínimo tres veces**: al comienzo, hacia la mitad y al final o
 * justo antes. Regla suya, y es un suelo: más está bien, menos no. Es lo que
 * impide que la pieza se convierta en una sucesión de tableros con una voz en
 * off.
 *
 * **Dos formas de cumplir, y basta con una.** Jaime, calibrando: *«más del 60%
 * del vídeo, o en esos tres puntos»*. Por proporción, si está en cuadro más del
 * `MINIMO_CARA` del metraje. Por reparto, si sale menos, al menos una vez en
 * cada tercio.
 *
 * Y es **un suelo, no una cuota**: *«pero si yo aparezco en mayor proporción no
 * hay problema»*. Aparecer más nunca bloquea. Importa decirlo porque la
 * tentación al leer «mínimo tres veces» es recortar cara para hacer sitio a los
 * tableros, y es al revés.
 *
 * La cuenta va **por unión, no por suma** — ver `Tramos`: sumando solapes, en el
 * reel 2 dos capas que se pisan daban 24,5 s de tapado dentro de un tercio de
 * 24, así que el hueco salía negativo y la comprobación paraba el montaje
 * teniendo Jaime 6,9 s de plano limpio.
 */
function presencia(r) {
  const fin = Math.round(r.duracion * FPS);
  const tapa = new Tramos([...r.boards, ...r.tarjetas]);
  const libres = [0, 1, 2].filter((i) => {
    const a = (fin * i) / 3;
    const b = (fin * (i + 1)) / 3;
    // Al menos un segundo de plano real en el tercio.
    return b - a - tapa.cubiertoEntre(a, b) > FPS;
  });
  const enCuadro = fin > 0 ? (fin - tapa.cubiertoEntre(0, fin)) / fin : 1;
  /**
   * **Un tablero que se come un tercio de la pieza es un tablero, no la pieza.**
   *
   * Va **antes** de la comprobación de presencia a propósito. En reel-01 el
   * tablero de la etapa 3 duraba 40,9 s sobre 101,5 —el 40% del anuncio— y lo
   * único que se leía era «Jaime no aparece en mitad»: el motivo correcto, pero
   * la causa equivocada. Nadie iba a mover la cara; había que simplificar el
   * tablero. Un diagnóstico que apunta al sitio equivocado cuesta la vuelta
   * entera. El tope es un tercio porque es exactamente lo que la regla de
   * presencia necesita para poder cumplirse por reparto.
   */
  for (const b of r.boards) {
    if (b.duration <= fin / 3) continue;
    const cond = (b.props?.condicion ?? "").trim().split(/\s+/).filter(Boolean).length;
    para(r,
      `${r.id}: el tablero del beat ${b.beat ?? "?"} dura ` +
      `${(b.duration / FPS).toFixed(1)}s de una pieza de ${(fin / FPS).toFixed(1)}s ` +
      `— mas de un tercio. La duracion la decide la lectura, asi que hay que ` +
      `simplificarlo: menos bloques y mas animacion` +
      (cond ? `, y su condicion lleva ${cond} palabra(s) en pantalla` : ""),
    );
  }
  if (enCuadro <= MINIMO_CARA && libres.length < 3) {
    const donde = ["comienzo", "mitad", "final"].filter((_, i) => !libres.includes(i));
    para(r,
      `${r.id}: Jaime no aparece en ${donde.join(" ni ")}. La regla es minimo ` +
      `tres veces —comienzo, mitad y final—; hay que mover o acortar un tablero.`,
    );
  }
}

/**
 * **Un segmento encaja si hace su trabajo, no si repite el libreto.**
 *
 * La cobertura sola mide literalidad: comparada contra un párrafo largo, decir
 * sólo lo esencial puntúa bajo aunque la etapa quede cumplida. En el reel 2 la
 * etapa 2 dice «por cada 100 dólares se quedan con 67» —que es exactamente lo
 * que el libreto pide ahí— y sacaba 0,10 porque el párrafo además habla de la
 * mansión, el yate y Muskoka.
 *
 * Así que se mira contra **lo alcanzable en esa etapa** (`cubre_max`), y además
 * se acepta el segmento que trae el dato que la etapa declara.
 */
const encaja = (u) =>
  u.dice ||
  (u.cobertura ?? 0) >= Math.max(ENCAJE, RELATIVO * (u.cubre_max ?? 0));

/** La línea de cada pieza y lo que hay que mirar en ella. No para nada. */
function informe(r, m) {
  console.log(
    `${r.id}  ${r.duracion.toFixed(1)}s  ${m.visibles}/${r.captions.length} cc (${r.compuestos} compuestos)  mudo max ${(m.dur / FPS).toFixed(1)}s  ` +
    `rotulo entra en ${(r.entra / FPS).toFixed(1)}s  ` +
    `${r.paneles.length} panel(es) · ${r.boards.length} tablero(s)${r.boards.length ? " en " + r.boards.map((b) => (b.at / FPS).toFixed(1) + "s").join(",") : ""}  ` +
    `CTA ${r.cta ? "en " + r.cta.at.toFixed(1) + "s" : "NO HAY (falta el copy del cierre)"}`,
  );
  /**
   * **La cifra es secundaria respecto al segmento.** Jaime: *«no creo que las
   * cifras sean el parámetro para medir; lo que tenemos que encontrar son los
   * segmentos específicos de lo grabado que caben dentro de los segmentos
   * esperados por el guion. Acá hay falsos positivos»*.
   *
   * Medido: «estructura. 30.000 dolares no de ventas de estructura» **contiene
   * el 30** y es un tropiezo de cuatro segundos con cobertura -0,07. Así que la
   * cifra es aviso y la puerta baja a donde está la unidad de análisis.
   */
  const exige = marcoDe(`reel-0${r.id.slice(-1)}`)?.debe_decir ?? [];
  const dicho = DICE(r.captions.map((c) => c.text).join(" "));
  // Mismo criterio que en `beats.py`: el termino admite alternativas con `|`,
  // porque lo que se comprueba es la intencion comunicativa y no la letra.
  const faltan = exige.filter(
    (t) => !String(t).split("|").some((x) => dicho.includes(DICE(x))),
  );
  if (faltan.length) {
    console.log(
      `    aviso: no suena ${faltan.map((x) => `«${x}»`).join(", ")}.` +
      ` Es un dato declarado, no el criterio: lo que decide es si cada segmento` +
      ` encaja en su etapa.`,
    );
  }
  const det = r.edl?.detalle ?? [];
  if (det.length) {
    const flojas = det.filter((u) => !encaja(u));
    /**
     * **Parecerse poco al libreto no es un defecto.** Jaime separó tres cosas:
     * *«una cosa el libreto o el mensaje esperado, otra el mensaje entregado,
     * otra la intención comunicativa; se respeta la última»*. La cobertura mide
     * el parecido con el mensaje ESPERADO, que es la preferencia, no el
     * criterio. Llamarlo «flojo» hacía perseguir el parecido y no el sentido.
     */
    console.log(
      `    encaje por segmento: ` +
      det.map((u) => `${u.beat}:${(u.cobertura ?? 0).toFixed(2)}`).join(" ") +
      (flojas.length
        ? `  · mas lejos del libreto: ${flojas.map((u) => u.beat).join(",")}`
        + ` (no es defecto: lo que decide es la integridad)`
        : ""),
    );
  }
  const secas = (r.escenas ?? []).filter((e) => e.trato === "—");
  if (secas.length) {
    console.log(
      `    escenas a plano seco: ${secas.map((e) => `${e.n} (${(e.a / FPS).toFixed(1)}-${(e.b / FPS).toFixed(1)}s)`).join(", ")}` +
      ` — cada escena tiene que llevar tablero, animacion o texto animado.`,
    );
  }
  const pelados = sinTrato(r);
  if (pelados.length) {
    console.log(
      `    beats sin tratamiento: ${pelados.join(", ")} - ni tablero, ni panel, ` +
      `ni idea fuerza, ni marca. Plano seco todo el beat.`,
    );
  }
}

/**
 * Las dos vueltas, y en este orden a propósito: **primero lo que para y después
 * lo que informa**. Un motivo de bloqueo enterrado bajo veinte líneas de datos
 * es un motivo que no se lee.
 */
export function revisar(spec) {
  for (const r of spec) presencia(r);
  for (const r of spec) {
    const m = mudo(r);
    informe(r, m);
    /**
     * **Un tablero SÍ ejecuta la etapa.** La puerta contaba como «sin material»
     * cualquier etapa sin fragmento, y ahí caían dos cosas distintas: la que no
     * tiene nada en la cinta, y la que se mandó a tablero **a propósito** porque
     * la toma leía plano. La segunda está resuelta —lleva su copy, que es la
     * propia lectura y por eso es exacta— y bloquearla contradice la regla que
     * la creó: *«no es aceptado leer; para leer prefiero el tablero»*.
     */
    const huecos = (r.edl?.sin_toma ?? []).filter((u) => u.obligatorio && !u.copy);
    if (huecos.length) {
      para(r,
        `${r.id}: la${huecos.length > 1 ? "s" : ""} etapa${huecos.length > 1 ? "s" : ""} ` +
        `${huecos.map((u) => `${u.beat} (${u.etapa})`).join(", ")} ` +
        `${huecos.length > 1 ? "son obligatorias y no tienen" : "es obligatoria y no tiene"} ` +
        `fragmento. La unidad de analisis es el segmento: sin el, la estructura no ` +
        `se ejecuta — y renderizar bajo otro criterio es gastar el peldaño caro en ` +
        `lo que ya sabemos que no esta.`,
      );
    }
    if (m.dur > MUDO_MAX) {
      para(r,
        `${r.id}: ${(m.dur / FPS).toFixed(1)}s sin subtitulo entre ` +
        `${(m.a / FPS).toFixed(1)}s y ${(m.b / FPS).toFixed(1)}s. El subtitulo es ` +
        `capa portante -el argumento tiene que funcionar sin audio- asi que un ` +
        `hueco asi es la pieza rota, no un detalle de acabado. Mira que capa lo ` +
        `esta tapando de mas.`,
      );
    }
  }
}
