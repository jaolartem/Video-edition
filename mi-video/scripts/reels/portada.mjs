/**
 * **La puerta del gancho: lo que el canon declara, comprobado.**
 *
 * Jaime, 6-9-2026, sobre los siete a la vez: *«en todas hay que revisar el
 * hook»*. Y el tiquet de máquina que salió con él dice por qué pudo pasar:
 * **el gancho no pasaba por ninguna puerta**. La de paneles
 * (`paneles.mjs :: faltaDelPanel`) le exige `volumen` a un panel, pero el gancho
 * es `cubre: cc` y no es un panel, así que quedaba fuera — y por eso la misma
 * lámina sobrevivió a cuatro instrucciones suyas.
 *
 * Es la avería de la casa otra vez, la que `paneles.mjs` documenta palabra por
 * palabra: una regla declarada sin nadie que la comprobara. Estaba escrita en
 * `docs/canon.md`, en el contrato del diseñador y en `src/preview-gancho.tsx`, y
 * las siete piezas salieron igual.
 *
 * Aquí vive **lo que se exige y lo que se aplica**; quién para la pieza es
 * `puerta.mjs`. Mismo reparto que `paneles.mjs`, y por eso esto devuelve **el
 * motivo** y no un booleano: un guarda que dice «no» sin decir qué falta cuesta
 * la vuelta entera.
 *
 * ## Y la geometría no está aquí
 *
 * Está en `rotulo.mjs` —el cuerpo que cabe, el alto del bloque, el sitio que le
 * toca mirando su coronilla—, que es lo que mide. Aquí se arma la capa y se
 * comprueba que cumple, que es lo que decide. Los números de los dos salen de
 * `src/brand/gancho.json`, en un solo sitio.
 */
import fs from "node:fs";
import { franja } from "../franja.mjs";
import { FPS } from "./reloj.mjs";
import { CABEN, CANON } from "./rotulo.mjs";

/**
 * **El gancho, metido en la lista de recortes, si el recorte existe de verdad.**
 *
 * Va ahí y no en un campo suyo porque es literalmente eso: algo que le pasa por
 * detrás. `Detras` ya apila el elemento y encima su silueta con alfa, que es el
 * orden entero del efecto; una pila propia para el gancho sería el mismo apilado
 * escrito dos veces, y una de las dos se quedaría atrás.
 *
 * **Y la ventana del gancho es del gancho.** Un elemento que otro camino
 * quisiera meterle por detrás ahí serían dos cosas detrás de la misma cabeza: en
 * reel-05 la columna sube de 780 a 236 y el rótulo vive de 250 a 501, o sea
 * encima. Es el mismo defecto que se vino a quitar —dos bloques compitiendo— con
 * otra ropa. Se retira y se dice, que es lo que distingue una decisión de una
 * pérdida.
 *
 * **Si falta el recorte no se emite nada y se dice.** `staticFile` de algo que
 * no está no avisa: mata el render entero con un 404 y el motivo que se lee
 * habla de una URL. Sin capa, `puerta.mjs` para la pieza — caerse en silencio a
 * la lámina de antes es cómo ésta sobrevivió cuatro vueltas.
 */
export function armarGancho(capas, imagen, slug) {
  const t = (capas ?? []).find((c) => c.tipo === "titular");
  if (!t) return [];
  const src = String(t.props.src ?? "");
  const faltas = [];
  if (!fs.existsSync(`public/${src}`)) {
    faltas.push(
      // **`--desde` es el del gancho, no el 0 de la pieza.** El recorte se
      // reproduce desde su propio frame 0 dentro de la ventana del rótulo, así
      // que una silueta cortada del principio del vídeo puesta en un gancho que
      // empieza más tarde va desfasada y no avisa: el bloque le pasa por delante
      // de la cara en vez de por detrás. Pasa en cuanto el gancho no abre la
      // pieza — reel-03, con el adelanto por delante (ver `capas.mjs`).
      `${slug}: el gancho pide su recorte con alfa y no hay public/${src} —` +
        ` falta \`python scripts/text-behind.py --video public/${slug}.mp4` +
        ` --canto limpio --desde ${(t.at / FPS).toFixed(2)}` +
        ` --hasta ${((t.at + t.duration) / FPS + 0.2).toFixed(1)}` +
        ` --out public/${src}\`. Sin él el rótulo se apoya encima de su cara en` +
        ` vez de pasarle por detrás.`,
    );
    return faltas;
  }
  const fin = t.at + t.duration;
  const libres = (imagen.recortes ?? []).filter((r) => {
    if (r.at >= fin || r.at + r.duration <= t.at) return true;
    faltas.push(
      `${slug}: el beat ${r.beat} pidió «${r.elemento}» por detrás dentro del` +
        ` gancho, y ahí ya va el rótulo detrás de su cabeza. Se retira: dos` +
        ` cosas detrás de la misma cabeza son los dos bloques compitiendo otra` +
        ` vez. Muévelo a otra etapa si lo quieres.`,
    );
    return false;
  });
  imagen.recortes = [
    ...libres,
    {
      at: t.at,
      duration: t.duration,
      beat: t.beat,
      elemento: "titular",
      src,
      // Cada línea entra en su frame; se declaran para que la puerta compruebe
      // el escalonado sin volver a calcularlo.
      entradas: t.props.entradas ?? [],
      // Dónde empieza su pelo, en píxeles. No es del dibujo —el componente no
      // lo usa— pero sí de la comprobación: es contra esto contra lo que se
      // mira si el bloque le pasa por detrás o por encima.
      coronilla: t.props.coronilla ?? null,
      rotulo: {
        lineas: t.props.lineas ?? [],
        cuerpos: t.props.cuerpos ?? [],
        arriba: t.props.arriba ?? CANON.arriba,
        // **Lo que hace que los tres segundos no se queden quietos.** El frame
        // de cada palabra y el trazo del filete que cierra el bloque: los
        // resolvió `rotulo.mjs :: ritmo` y viajan resueltos, que es la misma
        // regla que el cuerpo y el sitio — el componente dibuja, no calcula.
        palabras: t.props.palabras ?? [],
        regla: t.props.regla ?? 0,
        reglaDura: t.props.reglaDura ?? 0,
        anchos: t.props.anchos ?? [],
        // De qué margen cuelga y cuál de las líneas lleva el oro: lo resolvió
        // `rotulo.mjs :: colocar` mirando dónde está él, y viaja para que el
        // componente dibuje y la puerta compruebe el mismo número.
        lado: t.props.lado ?? "izq",
        oro: t.props.oro ?? Math.max(0, (t.props.lineas ?? []).length - 1),
      },
    },
  ];
  return faltas;
}

/**
 * **Y el panel que caía dentro del gancho se va detrás de él.**
 *
 * Es la misma regla que aparta un elemento de por detrás, aplicada a la otra
 * capa que trae texto. Medido en el contacto de los siete: reel-02 abría con un
 * panel de cuatro renglones —«DE CADA $100 / QUE FACTURA / SE VA $54 / LE QUEDA
 * $46»— empezando en el frame 0 y pintado justo encima del rótulo, y reel-03
 * con otro de dos. O sea **los dos bloques de texto compitiendo en el primer
 * segundo**, que es el defecto que el gancho nuevo vino a quitar, entrando por
 * la otra puerta.
 *
 * Se mueve, no se borra: el panel dice lo suyo igual cinco segundos después, y
 * la etapa del gancho dura mucho más que el gancho. Y se dice, que es lo que
 * distingue una decisión de una pérdida.
 */
export function apartaDelGancho(pieza, slug) {
  const titular = titularDe(pieza);
  if (!titular) return [];
  const fin = titular.at + titular.duration;
  const faltas = [];
  // **Y el que repite el rótulo no se corre: se quita** (C-591). reel-18 y
  // reel-21, 19-10: el panel de e1 decía lo mismo que el titular —«A MÍ
  // TAMBIÉN / ME DA MIEDO.»— y, corrido a 5 s, lo volvía a decir en e2. Nada se
  // dice dos veces.
  const plano = (t) => String(t ?? "").normalize("NFD").replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim().toLowerCase();
  const rotulo = plano((titular.rotulo?.lineas ?? []).join(" "));
  pieza.paneles = (pieza.paneles ?? []).flatMap((p) => {
    if (rotulo && plano((p.bloques ?? []).map((b) => b?.texto).join(" ")) === rotulo) {
      faltas.push(`${slug}: el panel del beat ${p.beat ?? "?"} repite el rótulo del` +
        " gancho: se quita, nada se dice dos veces.");
      return [];
    }
    return [p];
  }).map((p) => {
    if (p.at >= fin || p.at + p.duration <= titular.at) return p;
    faltas.push(
      `${slug}: el panel del beat ${p.beat ?? "?"} empieza dentro del gancho` +
        ` (${(p.at / FPS).toFixed(1)}s) y se pinta encima del rótulo. Se corre a` +
        ` ${(fin / FPS).toFixed(1)}s: en esos segundos el rótulo es lo único que` +
        ` se lee, y dos bloques de texto a la vez es el defecto que el gancho` +
        ` vino a quitar.`,
    );
    return { ...p, at: fin };
  });
  return faltas;
}

/** El titular de la pieza, o `undefined`. Una sola representación, y es ésta. */
export const titularDe = (r) =>
  (r.recortes ?? []).find((x) => x.elemento === "titular");

/**
 * **El subtítulo del gancho baja a su franja. No calla.**
 *
 * Esto callaba los primeros 2 s, y el diagnóstico era bueno con la solución
 * mala: los dos bloques de texto del primer segundo se separaban quitando uno.
 * Jaime lo corrigió el 6-9-2026 — *«puedes mantener el subtítulo los primeros 5
 * segundos, con el cc abajo de mí»*—, y tiene razón por dónde duele: **la
 * mayoría mira sin sonido**, así que dos segundos sin subtítulo son dos
 * segundos sin argumento justo donde se decide si alguien se queda.
 *
 * **La separación pasa a ser de sitio.** El rótulo vive arriba, detrás de su
 * cabeza; el cc, abajo, apoyado en el suelo de la franja. Conviven porque no
 * comparten píxeles, no porque se turnen.
 *
 * Se marca **la cue entera**, no la parte que cae dentro: así el cambio de sitio
 * ocurre donde cambia el texto —que es un corte, y ahí no se ve— y no a mitad de
 * frase. Y se marca aquí y no en `subtitulos.mjs` porque es lo del gancho: el
 * único tramo de la pieza donde el sitio del subtítulo lo manda otra capa.
 */
export function bajarEnElGancho(captions, titular) {
  if (!titular) return captions;
  const fin = titular.at + titular.duration;
  return (captions ?? []).map((c) =>
    c.at < fin && c.at + c.duration > titular.at ? { ...c, abajo: true } : c,
  );
}

/**
 * Los motivos por los que esta pieza no se monta, del lado del gancho. Lista
 * vacía = el gancho está. Lo llama `puerta.mjs`, que es quien para.
 */
export function faltasDelGancho(r) {
  const out = [];
  const g = titularDe(r);
  if (!g) {
    out.push(
      `${r.id}: no lleva el gancho del canon. Sin él el rótulo se dibuja en el` +
        ` 62-76% de la altura, que es el tercio donde la interfaz de Meta pone` +
        ` nombre, caption y botones — la lámina que los siete compartían.`,
    );
    return out;
  }
  const abajo = Math.round(
    g.rotulo.arriba +
      (g.rotulo.cuerpos ?? []).reduce((n, c) => n + c, 0) * CANON.interlinea,
  );
  // **El filete cuenta como bloque.** Se dibuja al ras de la línea que golpea,
  // así que el suelo real del rótulo son sus píxeles y no los del texto: medir
  // sólo el texto dejaría que un rótulo largo metiera el filete en el tercio de
  // la interfaz sin que esto dijera nada. El margen y el grosor están en
  // `Gancho.tsx :: Regla` y aquí se suman los mismos números.
  const suelo = abajo + (g.rotulo.reglaDura ? Math.round(CANON.reglaGrosor * 2.6) : 0);
  if (suelo > CANON.tercioPx)
    out.push(
      `${r.id}: el rótulo del gancho baja hasta ${suelo} px —filete incluido— y` +
        ` el tercio de abajo empieza en ${CANON.tercioPx}. Ahí lo tapa la` +
        ` interfaz.`,
    );
  // **Y tiene que llegar a él.** Un rótulo que acaba por encima de su coronilla
  // no pasa por detrás de nadie: flota sobre la cortina. Se vio en el contacto
  // de los siete —reel-06 abría en plano abierto, con la coronilla en el 0,375
  // del cuadro, y el bloque quedaba 219 px por encima de su pelo—. No es un
  // defecto del gancho: es el encuadre, y se arregla cerrándolo.
  if (typeof g.coronilla === "number" && abajo < g.coronilla)
    out.push(
      `${r.id}: el rótulo del gancho acaba en ${abajo} px y su coronilla está` +
        ` en ${g.coronilla}: le pasa por encima, no por detrás. El` +
        ` bloque ya bajó todo lo que el tercio de Meta deja; lo que queda es` +
        ` cerrar el encuadre de esos primeros segundos, que es re-corte.`,
    );
  if ((g.entradas ?? []).length > 1 && g.entradas[1] - g.entradas[0] < 1)
    out.push(
      `${r.id}: las dos líneas del gancho entran en el mismo frame. Escalonadas` +
        ` se leen en orden; a la vez son un bloque.`,
    );
  // **Y el cc convive con él porque está en otro sitio, no en otro momento.**
  //
  // Esto exigía cero subtítulo en los primeros 2 s. Jaime lo cambió — *«puedes
  // mantener el subtítulo los primeros 5 segundos, con el cc abajo de mí»*— y lo
  // que hay que comprobar es lo que de verdad describe el defecto: **que los dos
  // bloques no se toquen**. Son dos mitades, y las dos tienen su caso medido.
  //
  // 1 · Por arriba: el suelo del rótulo contra el techo de la franja del cc, que
  //     lo declara `src/brand/franja.json` y aquí sólo se lee.
  if (suelo >= franja.techoPx)
    out.push(
      `${r.id}: el rótulo del gancho baja hasta ${suelo} px y la banda del` +
        ` subtítulo empieza en ${franja.techoPx}. Se tocan: o sube el bloque, o` +
        ` sobra una línea.`,
    );
  // 2 · Por abajo: que ninguna cue del gancho se quede sin bajar. Sin la marca,
  //     `CaptionBand` se sube al hueco de encima de su cabeza cuando lo hay —en
  //     reel-06 lo hay, 544 px— y ahí ya vive el rótulo: medido, el cc se comía
  //     «NADA HA» de «NADA HA PASADO».
  const suben = (r.captions ?? []).filter(
    (c) => !c.abajo && c.at < g.at + g.duration && c.at + c.duration > g.at,
  );
  if (suben.length)
    out.push(
      `${r.id}: ${suben.length} subtítulo(s) del gancho sin bajar a su franja` +
        ` («${String(suben[0].text).slice(0, 40)}…»). Sin eso el cc se le sube a` +
        ` la cara, que es donde está el rótulo.`,
    );
  // Lo que no se puede mover se dice y para: un tablero o una tarjeta dentro del
  // gancho no es una capa que acompañe, es el gancho tapado.
  const tapan = [...(r.boards ?? []), ...(r.tarjetas ?? []), ...(r.paneles ?? [])]
    .filter((b) => b.at < g.at + g.duration && b.at + b.duration > g.at);
  if (tapan.length)
    out.push(
      `${r.id}: ${tapan.length} capa(s) de texto dentro del gancho` +
        ` (${tapan.map((b) => (b.at / FPS).toFixed(1) + "s").join(", ")}).` +
        ` Ahí el rótulo es lo único que se lee.`,
    );
  for (const l of g.rotulo.lineas) {
    if (l.length > CABEN)
      out.push(
        `${r.id}: la línea «${l}» tiene ${l.length} caracteres y a cuerpo` +
          ` ${CANON.suelo} sólo caben ${CABEN}. No se arregla encogiendo más:` +
          ` sobra copy.`,
      );
  }
  return out;
}
