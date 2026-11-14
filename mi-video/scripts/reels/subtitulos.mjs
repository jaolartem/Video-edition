/**
 * **Las capas que se ponen sobre el subtitulo.**
 *
 * El playbook exige que el argumento funcione sin audio y esa carga la lleva el
 * subtitulo, asi que es capa portante y no acabado. Encima de el caben cuatro
 * cosas, y aqui se decide cual va donde:
 *
 * - **La idea fuerza** — la frase clave de un beat crece cuando se dice.
 * - **La marca de humanidad** — el desliz se señala, no se corrige de tapadillo.
 * - **La correccion de cumplimiento** — la verdad encima de lo que se dijo mal.
 * - **El remate compuesto** — dos renglones, dos fuentes, cuando cierra una idea
 *   y no hay otra capa de texto ese segundo.
 *
 * Ninguna se puede sumar a otra: dos capas subrayando lo mismo en el mismo
 * segundo no es enfasis, es ruido (aprendizaje 38). Por eso las tres primeras
 * bloquean la cuarta.
 */
import { FPS } from "./reloj.mjs";
import { Tramos } from "./tramos.mjs";
import { COLGANTE, partirFrase, ultimaPalabra } from "./texto.mjs";

/**
 * **Y la quinta: cómo se resuelve el suelo de la letra** — caja, limpio o
 * negativo, según lo que haya detrás en esa escena (T-04). Vive en `cc.mjs`
 * porque lleva su propia medida y sus umbrales, y sale por esta puerta porque es
 * una decisión sobre el subtítulo como las otras cuatro: quien arma el spec pide
 * aquí lo que se le pone al cc, y no tiene que saber en qué fichero está.
 */
export { trataElCc } from "./cc.mjs";

/**
 * **Las ideas fuerza.** Es el tratamiento de los beats que **afirman, provocan o
 * prometen**: ahi la fuerza esta en la voz y el texto solo marca donde cae el
 * golpe. Frente a un tablero es mas barato —no roba el plano— y frente a nada,
 * sostiene la atencion en el tramo en que solo hay una cara hablando.
 *
 * **La ventana es la del plan.** Esto acumulaba las duraciones del EDL y las
 * cruzaba con `captions`, que salen de transcribir el video ya montado: dos
 * relojes distintos, asi que el realce caia sobre la frase de al lado. Se busca
 * dentro del hueco real del beat, no en toda la pieza: la misma frase puede
 * repetirse y solo debe realzarse donde ese beat la dice.
 */
export function ideasFuerza(slug, reloj, beats, captions) {
  const ventanas = [];
  for (const [b, [desde, hasta]] of reloj.ventanas()) {
    const frase = beats[b - 1]?.idea_fuerza;
    if (frase) ventanas.push({ desde, hasta, frase });
  }
  const hechas = new Set();
  const salida = captions.map((c) => {
    const v = ventanas.find(
      (w) =>
        !hechas.has(w.frase) &&
        c.at >= w.desde &&
        c.at < w.hasta &&
        c.text.toLowerCase().includes(w.frase.toLowerCase()),
    );
    if (!v) return c;
    hechas.add(v.frase);
    return { ...c, realza: v.frase };
  });
  for (const w of ventanas) {
    if (!hechas.has(w.frase)) {
      console.error(
        `  ojo: ${slug} declara la idea fuerza «${w.frase}» y no aparece en el ` +
        `subtitulo de su beat. Falla en silencio: el subtitulo sale normal.`,
      );
    }
  }
  return salida;
}

/**
 * La marca de humanidad: el desliz se señala, no se corrige de tapadillo.
 *
 * Dos capas de una sola marca, no dos marcas: **el subtitulo dice lo que ES**
 * —se oye «550», se lee **$576**— y **el plano se va a blanco y negro** mientras
 * dura, si la marca lo pide. Jaime: *«no pones lo mismo que yo digo sino lo que
 * esta bien y lo amplias, de manera que la contradiccion se note»*.
 *
 * **Y es CORTA a proposito.** El tope sale del propio `senala` y ronda 1,6 s,
 * porque el desliz suele no cambiar nada — *«esos dolares no cambian
 * absolutamente nada del mensaje»*. Una marca larga sobre un desliz trivial hace
 * que parezca grave: el chiste vive de que sea breve.
 *
 * ## Y no siempre la lleva el subtitulo
 *
 * En el reel 1 el «550» se dice en 73,7 y el CTA entra en 69,7 — la tarjeta tapa
 * la cara y los subtitulos, asi que el chiste se emitia debajo de ella y no lo
 * veia nadie. No es un fallo de posicion: **el precio se dice DENTRO del CTA
 * porque el precio ES el CTA**, y la tarjeta ya tiene su fila de precio.
 *
 * @returns `captions` con la marca puesta donde toque, `desatura` con las
 *   ventanas de blanco y negro, y `enCta` si se la queda la tarjeta.
 */
export function marcaDeHumanidad(slug, senala, captions, cta) {
  if (!senala) return { captions, desatura: [], enCta: null };
  const tope = Math.round((senala.maximo_s ?? 1.6) * FPS);
  // **Solo la PRIMERA aparicion.** Si la palabra vuelve, la broma se repite y
  // deja de serlo — y la tasa se dispara sin que nadie lo haya decidido.
  let hecha = false;
  let enCta = null;
  const desatura = [];
  const out = captions.map((c) => {
    if (hecha || !c.text.toLowerCase().includes(senala.dice.toLowerCase()))
      return c;
    hecha = true;
    // Dentro del CTA la lleva la tarjeta, no el subtitulo.
    if (cta && c.at >= cta.at * FPS) {
      enCta = { dice: senala.dice, es: senala.es };
      // Y **sin blanco y negro**: la tarjeta tapa el plano, asi que desaturar
      // no se veria — y aplicado a la tarjeta se llevaria por delante el oro
      // del numero, que es lo unico que hace el chiste. Un efecto que no se ve
      // es peor que no ponerlo: queda declarado y nadie sabe que no corre.
      return c;
    }
    if (senala.blanco_y_negro) {
      desatura.push({ at: c.at, duration: Math.min(c.duration, tope) });
    }
    return { ...c, corrige: { dice: senala.dice, es: senala.es } };
  });
  if (!hecha) {
    console.error(
      `  ojo: ${slug} declara senalar «${senala.dice}» y no aparece en los ` +
      `subtitulos. O el montaje ya no lleva esa frase, o cambio el texto.`,
    );
  }
  return { captions: out, desatura, enCta };
}

/**
 * **La correccion de cumplimiento, encima de lo que se dijo mal.**
 *
 * Jaime: *«el libreto dice la verdad, esta es una oportunidad para que el error
 * se manifieste; el subtitulo, cuando digo ministerio de comercio, dice la
 * informacion real palpitando»*. No se corrige el libreto ni se tapa el desliz —
 * sale la verdad encima, en oro, y palpita.
 *
 * **La correccion es sobre una palabra; la frase solo la situa.** Esto exigia
 * que `corrige_dice` cupiera entero dentro de UN caption, y el subtitulo parte
 * por tiempo, no por sentido: «un rector» sale con «un» al final de un trozo y
 * «rector» al principio del siguiente, asi que la correccion no se colocaba y el
 * render paraba. Se intenta la frase entera primero, que es lo mas preciso; si
 * no cabe en ningun trozo, se busca la palabra que de verdad cambia —la mas
 * larga, que es la que el ojo lee mal— y se corrige ahi.
 *
 * @returns `{captions, faltas}` — lo que no se pudo colocar se nombra.
 */
export function corregirLoDicho(slug, filas, captions) {
  const faltas = [];
  let out = captions;
  for (const row of filas) {
    let puesta = false;
    // **La que no se marca cambia la palabra y ya** (C-630): sin oro, sin
    // golpes. Por palabra entera, que «esa» no es la de «empresa».
    if (row.corrige_marca === "no") {
      const q = row.corrige_dice.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const re = new RegExp(`(?<!\\p{L})${q}(?!\\p{L})`, "iu");
      out = out.map((c) => {
        if (puesta || !re.test(c.text ?? "")) return c;
        puesta = true;
        return { ...c, text: c.text.replace(re, row.corrige_es) };
      });
      if (!puesta) faltas.push(`${slug}: no se pudo cambiar «${row.corrige_dice}» por`
                               + ` «${row.corrige_es}»: no aparece en ningun subtitulo`);
      continue;
    }
    const clave = row.corrige_dice
      .split(/\s+/)
      .reduce((a, b) => (b.length > a.length ? b : a), "");
    const cabe = (t, q) => t?.toLowerCase().includes(q.toLowerCase());
    const entera = out.some((c) => cabe(c.text, row.corrige_dice));
    out = out.map((c) => {
      if (puesta) return c;
      const encaja = entera
        ? cabe(c.text, row.corrige_dice)
        : clave.length > 3 && cabe(c.text, clave);
      if (!encaja) return c;
      puesta = true;
      // **Si ya la puso `marcaDeHumanidad`, solo se le enciende el palpiteo.**
      // Que la correccion exista por dos vias no es un conflicto: una la declara
      // la pieza a mano y la otra la deduce la composicion leyendo el libreto.
      // Duplicarla si seria un problema — dos capas diciendo lo mismo en el
      // mismo segundo es ruido, no enfasis (aprendizaje 38).
      return c.corrige
        ? { ...c, palpita: true }
        : { ...c, corrige: { dice: row.corrige_dice, es: row.corrige_es },
            palpita: true };
    });
    if (!puesta) {
      faltas.push(`${slug}: no se pudo colocar la correccion «${row.corrige_dice}`
                  + `» -> «${row.corrige_es}»: no aparece en ningun subtitulo`);
    }
  }
  return { captions: out, faltas };
}

/**
 * **Un remate necesita tiempo para leerse.**
 *
 * «POR SUPUESTO.» salio a cuerpo 128 y **no se vio**: su cue dura 1,20 s y la
 * entrada se lleva 0,33, asi que quedaban ocho decimas. Jaime lo dijo con esas
 * palabras — *«no se vio la tarjeta del de manera legal y siguiendo las
 * reglas»*.
 *
 * Cuando la cue que cierra la frase es corta, **se junta con la anterior** y el
 * remate hereda la suma de las dos. Y no hay que buscar por donde partir: la
 * frontera entre las dos cues es justo el sitio, porque ahi hubo una pausa real.
 */
const MIN_REMATE = 48;

/**
 * **El remate compuesto.** Cuatro condiciones, y las cuatro tienen un caso
 * detras:
 *
 * 1. **Cierra una idea** — la cue termina en punto. Es la frase que aterriza, y
 *    ademas quedan espaciadas solas sin necesidad de una cuota inventada.
 * 2. **No cuelga de la anterior.** La cue de antes no puede acabar en palabra de
 *    funcion. Es lo que distingue «POR SUPUESTO.» de «PIERDA LA MITAD EN
 *    IMPUESTOS», que dice lo contrario que la frase de la que sale (C-23).
 * 3. **Es la unica capa de texto del instante.** Con tablero, tarjeta, panel,
 *    rotulo o CTA en cuadro, el subtitulo se queda plano.
 * 4. **Cabe.** El remate va en Anton versales y por encima de 34 caracteres el
 *    cuerpo cae por debajo del minimo de subtitulo.
 *
 * Se intento agrupar por oracion entera en vez de por cue, para tener mas
 * contexto, y salio peor: las oraciones habladas rondan los 180 caracteres, asi
 * que casi ninguna cabia y el reel 1 se quedo con dos remates en 81 s. **La cue
 * es la unidad correcta; lo que faltaba era mirar la de al lado.**
 */
export function componer(captions, ocupado, ventanas, colgantes = COLGANTE) {
  const orden = captions.slice().sort((x, y) => x.at - y.at);
  const anterior = new Map();
  orden.forEach((c, i) => anterior.set(c, i ? orden[i - 1] : null));
  // Por mayoria, no por roce: una cue perdia su remate por solapar 0,2 s con el
  // final de un panel. Y por UNION, no por suma — ver `Tramos`.
  const tapan = new Tramos(ocupado);

  const libre = (c) => {
    if (c.realza || c.corrige) return false;
    if (!/[.!?]$/.test(c.text.trim())) return false;
    const prev = anterior.get(c);
    if (prev && colgantes.has(ultimaPalabra(prev.text))) return false;
    return !tapan.sepulta(c);
  };

  /** La unidad componible de una cue: ella sola, o con la anterior pegada. */
  const unidad = (c) => {
    const prev = anterior.get(c);
    const corto = c.duration < MIN_REMATE;
    if (corto && prev && !prev.realza && !prev.corrige &&
        !/[.!?]$/.test(prev.text.trim())) {
      /**
       * **Aqui NO se mira si la anterior cuelga**, y es deliberado: al juntar
       * dos cues la continuacion se la come el renglon de arriba, que va pequeno
       * y en caja mixta y se lee como lo que es —la frase siguiendo—. Lo que no
       * puede colgar es el remate, y de eso se encarga `partirFrase`.
       *
       * Costaba justo el caso que Jaime pidio: delante de «manera legal,
       * siguiendo las reglas» hay «...en impuestos de», que cuelga, asi que la
       * comprobacion tumbaba el remate entero por una palabra que iba a quedar
       * en el renglon de arriba.
       */
      const texto = `${prev.text.trim()} ${c.text.trim()}`.replace(/\s+/g, " ");
      const corte = prev.text.trim().split(/\s+/).filter(Boolean).length;
      const par = partirFrase(texto, corte, colgantes);
      if (par) {
        return {
          cues: [prev, c],
          at: prev.at,
          duration: prev.duration + c.duration,
          text: texto,
          compuesto: par,
        };
      }
    }
    if (corto) return null;
    const par = partirFrase(c.text, undefined, colgantes);
    return par
      ? { cues: [c], at: c.at, duration: c.duration, text: c.text, compuesto: par }
      : null;
  };

  const elegidas = [];
  for (const [a, b] of ventanas) {
    const dentro = orden.filter((c) => c.at >= a && c.at < b);
    /**
     * **Una etapa, un remate** — dos si la etapa pasa de 12 s, separados 5 s. Un
     * beat de 17,7 s hace mas trabajo que uno de 4 y aguanta dos golpes.
     *
     * Y la cifra se cuela delante: *«con mas colores»* es la mitad de lo que
     * pidio Jaime, y el oro es el unico color que el canon deja usar por
     * significado.
     */
    const cupo = b - a > 12 * FPS ? 2 : 1;
    const candidatas = dentro
      .map((c, i) => ({ c, i, oro: partirFrase(c.text, undefined, colgantes)?.tinte === "gold" }))
      .sort((x, y) => (x.oro === y.oro ? y.i - x.i : x.oro ? -1 : 1));
    const puestas = [];
    for (const { c } of candidatas) {
      if (puestas.length >= cupo) break;
      if (puestas.some((p) => Math.abs(p - c.at) < 5 * FPS)) continue;
      if (!libre(c)) continue;
      const u = unidad(c);
      if (!u) continue;
      elegidas.push(u);
      puestas.push(c.at);
    }
  }

  const cabeza = new Map();
  const dentroDeUnidad = new Set();
  for (const u of elegidas) {
    cabeza.set(u.cues[0], u);
    for (const c of u.cues) dentroDeUnidad.add(c);
  }
  const salida = [];
  for (const c of orden) {
    const u = cabeza.get(c);
    if (u) salida.push({ at: u.at, duration: u.duration, text: u.text,
                         compuesto: u.compuesto });
    else if (!dentroDeUnidad.has(c)) salida.push(c);
  }
  return { captions: salida, n: elegidas.length };
}
