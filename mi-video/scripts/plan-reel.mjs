/**
 * Plan de escenas para el REEL ENTERO, no solo el gancho.
 *
 * Toma `segmentos` del EDL —que es la fuente de verdad del montaje— y lo parte
 * en escenas de ~3 s para que `punch-ins.py` les asigne encuadre. Dos reglas:
 *
 * - **Una escena nunca cruza un corte del EDL.** El corte ya cambia de plano;
 *   meter ademas un cambio de encuadre encima seria un salto doble.
 * - **Nada por debajo de `MINIMO`.** Un resto de 0,4 s lee como parpadeo; se
 *   funde con la escena anterior en vez de crear un plano nuevo.
 *
 * **El orden de `segmentos` es el de la línea de tiempo, no el del bruto.** El
 * reel 5 abre en frío con una frase del minuto 682: ordenar por tiempo de origen
 * la manda al medio de la pieza. Aquí se recorre tal cual viene.
 *
 * NO vuelve a montar. `build-reel.mjs` reejecuta `assemble.py` y eso pisaria las
 * correcciones hechas a mano sobre el EDL —la cifra del reel 2, la fecha, las
 * zonas—. Aqui el EDL entra como dato, no como algo a recalcular.
 *
 *   node scripts/plan-reel.mjs --reel 3
 */
import fs from "fs";
import { DatabaseSync } from "node:sqlite";
import { bruto } from "./rutas.mjs";
import { camaraDe, movimientoDe } from "./camara.mjs";
import { sql } from "./consulta.mjs";
import { conPausa, esDeclarado, fijosDe,
         pausasDe } from "./reels/declarado.mjs";

/**
 * Silencio interno que se quita. Por debajo de esto es respiración y se queda:
 * quitarla toda deja el habla pegada y suena a locutor de radio.
 *
 * **Bajado de 0,25 a 0,16 por indicación de Jaime**, viendo el primer render:
 * *«el vídeo tiene mucho tiempo entre frases y muchos silencios entre frases
 * pueden ser cortados; como son microsegundos, los cortes no se suelen notar»*.
 * Con 0,25 se conservaba toda pausa corta, y en una pieza de veinte trozos eso
 * son varios segundos de nada. Con 0,16 se respeta la respiración y se va el
 * hueco. Y no queda crudo: la mezcla pasa por Adobe Podcast, que suaviza el
 * empalme — *«Adobe Podcast va a suavizar los cortes»*.
 */
const AIRE = 0.16;
/** Margen que se deja a cada lado del habla para no comerse la consonante. */
const MARGEN = 0.05;

/**
 * Interseca un tramo del EDL con los tramos de habla medidos.
 *
 * **Esto faltaba y es el aprendizaje 3 del proyecto**, que estaba escrito y se
 * perdió al reescribir el montaje por beats: *«los tiempos del EDL están en la
 * línea del bruto, así que un enunciado que cruza aire muerto lo reintroduce al
 * renderizar»*. Costaba 6–13 s de silencio por reel, y es la mitad de por qué
 * el montaje se sentía «poco dinámico».
 *
 * Ahora importa más que antes: los candidatos son **intentos enteros de una sola
 * toma** —Jaime: *«puedes borrar silencios intermedios pero no puedes cambiar de
 * toma»*—, así que llevan pausas dentro por definición. Sin esta intersección,
 * elegir la frase entera y buena costaría tres segundos de aire.
 */
function conHabla(a, b, runs) {
  const trozos = [];
  for (const [ra, rb] of runs) {
    const x = Math.max(a, ra - MARGEN);
    const y = Math.min(b, rb + MARGEN);
    if (y - x <= 0.05) continue;
    const ult = trozos[trozos.length - 1];
    // Dos tramos separados por menos de AIRE se unen: esa pausa se respeta.
    if (ult && x - ult[1] < AIRE) ult[1] = y;
    else trozos.push([x, y]);
  }
  return trozos.length ? trozos : [[a, b]];
}

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i === -1 ? d : process.argv[i + 1];
};

/**
 * **Una escena por tramo, no una cada 3 s.**
 *
 * Jaime: *«los cortes de imagen son muy fuertes, pasan de un punto al otro; el
 * cambio debería ser continuo, progresivo, no ese cambio tan cortante»*. Y era
 * literal: la escena 9 iba a un recorte de 994 px y la 10 saltaba a 1744. Seis
 * recortes fijos pegados dentro de un mismo beat, cada frontera un salto.
 *
 * La regla de los 3 s sigue siendo el pulso del CORTE —y el corte cae donde
 * cambia la idea, que es la frontera del beat—. Dentro del beat no se corta: se
 * mueve. Por eso `CADA` es enorme por defecto: un tramo, una escena.
 */
const CADA = Number(arg("cada", "999"));
const MINIMO = 1.2;

const slug = `reel-${String(arg("reel")).padStart(2, "0")}`;
/** La toma del reel, para poder leer sus tramos de habla. */
const tomaDe = (sl) =>
  JSON.parse(fs.readFileSync("rutas.json", "utf8")).tomas[sl];
const edl = JSON.parse(fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"));

/**
 * **Los tramos de habla de LA CINTA DE CADA ESCENA, no los de la pieza.**
 *
 * Esto leia un solo fichero —el de la toma del reel— y se lo pasaba a
 * `conHabla` para TODOS los segmentos, incluidos los que el EDL declara de otra
 * cinta. Intersecar un tramo de una cinta con el mapa de silencios de otra no
 * da un error: da trozos, y los recorta donde la otra callaba.
 *
 * Es el gemelo del fallo que ya se arreglo para `fuente` —render-hook abria un
 * `-i` por escena y este productor no emitia de que cinta salia— y quedo a
 * medias: la escena decia su cinta y el recorte seguia preguntandole a la del
 * reel. Medido en reel-02 el 5-9-2026: el EDL declaraba 85,4 s y el corte salia
 * de 80,7 s. Los 4,7 s que faltaban eran las dos etapas de `20260825_224414`
 * —b8 y b10—, y ahi dentro iba «este bootcamp es para usted, si no no», el
 * cierre que Jaime aprobo y que llevaba tres entregas sin sonar.
 *
 * Sin fichero de cortes no se recorta: pasar el mapa de otra cinta es el fallo.
 *
 * **Y se pregunta DONDE SUENA, no que conservo el detector.** `work/cuts` trae
 * la pausa ya recortada dentro, asi que leerlo como «aqui suena» devuelve el
 * silencio al montaje — trece huecos de 0,55 a 0,77 s en reel-01, once segundos
 * de aire. El porque entero, con sus numeros, vive con el mecanismo:
 * `consulta.py :: voz`, que es quien sabe restar la holgura.
 */
const runsDe = ((cache) => (toma) => {
  const t = toma || edl.toma || tomaDe(slug);
  if (!cache.has(t)) {
    try {
      cache.set(t, JSON.parse(sql("voz", [t])));
    } catch {
      cache.set(t, null);
    }
  }
  return cache.get(t);
})(new Map());

/**
 * **Lo que el diseñador pidió de cámara, etapa por etapa.**
 *
 * `escena_desc.camara` es la fuente única — la misma columna donde vive el
 * tablero y por la misma razón. Vacía significa lo de siempre: encuadre por
 * rueda, acercamiento lento, corte seco, así que una pieza que nadie ha
 * compuesto sale exactamente igual que ayer.
 *
 * Los cinco encuadres llevaban desde el principio en `punch-ins.py` repartidos
 * con `ENCUADRES[idx % len]`. Construidos y no elegibles: aquí es donde la
 * elección entra en el plan.
 */
const camaraPorBeat = () => {
  const m = new Map();
  try {
    const db = new DatabaseSync("ads/decisiones.db", { readOnly: true });
    for (const f of db
      .prepare("select etapa_orden, camara, tablero from escena_desc" +
               " where video_slug = ?")
      .all(slug)) {
      const cam = camaraDe(f.camara);
      // **Un tablero que lo lleva DENTRO también pide el recorte.** El panel
      // declara `sujeto` —de qué lado va— y eso ya es la petición: exigir
      // además `camara.detras` sería la misma decisión en dos sitios, y el día
      // que no coincidan el recorte se produce de una etapa y se dibuja en
      // otra. Aquí sólo se marca el beat para que la pasada de MediaPipe lo
      // cubra; la capa que pasa POR DETRÁS no se emite (`reels/imagen.mjs`),
      // porque bajo un tablero a pleno no se ve. Un tablero ilegible no es
      // asunto de este paso: lo dice `base.mjs`.
      try {
        const t = JSON.parse(f.tablero ?? "null");
        if (!cam.detras && t?.props?.sujeto)
          cam.detras = "sujeto";
        // **Y el canto sale de la forma** (C-384): el `cuadro` es un retrato
        // de canto limpio; la pegatina, papel rasgado. Va aparte de `detras`
        // porque `reels/imagen.mjs` compara `detras === "sujeto"` para no
        // emitir la capa de detrás, y un valor nuevo ahí la colaría.
        if (t?.props?.sujeto_forma === "cuadro")
          cam.canto = "limpio";
      } catch { /* vacío a propósito: ver arriba */ }
      m.set(Number(f.etapa_orden), cam);
    }
    db.close();
  } catch {
    // Sin base no hay composición declarada, que es el estado de una pieza
    // recién cortada: se sigue con los valores de siempre.
  }
  return m;
};
const CAMARA = camaraPorBeat();

const escenas = [];
const PAUSAS = pausasDe(slug);
const declarado = esDeclarado(fijosDe(slug));
let montado = 0;
let aireQuitado = 0;
// Cada segmento del EDL se parte en los trozos que SÍ tienen voz.
/**
 * **Cada escena sabe de dónde viene.** Regla de Jaime: *«cada parte o cada
 * fragmento debe guardarse por separado, e identificarse por separado… de esa
 * manera el segmento queda relacionado a un vídeo, pero también a un frame, y
 * también a una intención comunicativa o libreto»*.
 *
 * Son las tres relaciones y van juntas: el **vídeo** (el reel), la **etapa del
 * frame** (qué función cumple en la estructura) y el **mensaje esperado** (qué
 * tenía que decir ahí el libreto). Sin ellas una escena es un rango anónimo
 * dentro de un JSON y no hay forma de decir «esta parte no sirve» sin contar
 * cortes con el dedo.
 *
 * La etapa sale del `detalle` del EDL **por el corte del que nace la escena**,
 * no por tiempo: el reparto puede ir fuera de orden (aprendizaje 35).
 */

const conVoz = edl.segmentos.flatMap(([a, b], iSeg) => {
  const d0 = (edl.detalle || [])[iSeg] || {};
  // La pausa declarada dice de QUE LADO se conserva el silencio, no sólo que
  // esta etapa lo tiene: el criterio vive en `declarado.mjs :: conPausa`.
  // **Un tramo declarado entra entero: no se le quita el silencio de dentro.**
  //
  // `conHabla` recorta el silencio interno y devuelve trozos, y cada trozo es
  // una escena, o sea un corte de plano. Eso vale cuando el segmento lo eligio
  // el automatismo y no cuando alguien declaro «esta frase va entera»: la
  // declaracion existia justo para quitar ese corte y el recorte la deshacia.
  // Es lo que `consulta.fijos` lleva escrito desde que existe —«un tramo
  // declarado no se vuelve a partir»— y lo que ningun sitio cumplia.
  //
  // Medido el 8-9-2026 sobre el plan: reel-01 declara 562,932-571,580 y salian
  // dos escenas con 0,937 s de hueco entre ellas — «semanales» solo entre dos
  // silencios, el tiquet #287 y el t282 antes que el. reel-03 declara
  // 340,251-342,320 y arrancaba 0,317 s tarde, que es el «es que» del t279.
  const t = conPausa(PAUSAS, d0.beat, a, b,
                     declarado(a, b)
                       ? [[a, b]]
                       : conHabla(a, b, runsDe(d0.toma) ?? [[a, b]]));
  aireQuitado += b - a - t.reduce((n, [x, y]) => n + (y - x), 0);
  const d = (edl.detalle || [])[iSeg] || {};
  /**
   * **Dentro de un tramo declarado, el empalme no cambia de plano.**
   *
   * Jaime lo describió como la operación que es: *«es literalmente cortar un
   * segmento y pegarlo al lado de donde va, y adelantar el otro segmento para
   * que empiece donde empezaba el anterior»*. Eso es quitar el silencio sin
   * cortar: `conHabla` ya hace lo primero y `render-hook` concatena, así que lo
   * único que delataba el empalme era el ENCUADRE — `punch-ins` le daba a cada
   * trozo un recorte distinto y el salto se veía.
   *
   * Con `hereda_encuadre` los trozos de un mismo tramo declarado comparten
   * recorte: el corte deja de existir para el ojo y la frase suena seguida.
   *
   * Las dos formas anteriores fallaban por lados opuestos, y las dos las oyó él:
   * partir en escenas dejaba «semanales» detrás de un cambio de plano; dejar el
   * tramo entero conservaba **1,10 s** de pausa y lo dejaba igual de suelto.
   */
  const junto = declarado(a, b);
  return t.map(([x, y], k) =>
    [x, y, d.beat ?? iSeg + 1, d.etapa || "", d.texto || "", d.toma,
     junto && k > 0]);
});

for (const [a, b, beat, etapa, dicho, toma, hereda] of conVoz) {
  const dur = b - a;
  /** Lo declarado para esta etapa; si no hay nada, los valores de siempre. */
  const cam = CAMARA.get(Number(beat)) ?? camaraDe(null);
  // Cuantas escenas caben; el resto se reparte para que ninguna quede corta.
  const n = Math.max(1, Math.round(dur / CADA));
  const paso = dur / n;
  for (let k = 0; k < n; k++) {
    const ini = a + paso * k;
    const fin = k === n - 1 ? b : a + paso * (k + 1);
    if (fin - ini < MINIMO && escenas.length) {
      // Se funde con la anterior en vez de crear un plano de parpadeo.
      const prev = escenas[escenas.length - 1];
      if (Math.abs(prev.origen_hasta - ini) < 1e-6 && prev.fuente === toma) {
        prev.origen_hasta = fin;
        prev.duracion = Number((fin - prev.origen_desde).toFixed(3));
        montado += fin - ini;
        continue;
      }
    }
    escenas.push({
      indice: escenas.length,
      // De qué sección de frame nace esta escena, y qué dijo ahí. Sin esto la
      // escena es un rango anónimo y no hay forma de decir «esta parte no
      // sirve» sin contar cortes con el dedo.
      beat,
      /**
       * **De que cinta sale esta escena.** `render-hook.mjs` lo lee
       * (`fuenteDe`) y abre un `-i` por escena: el consumidor lo soportaba y
       * este productor no lo emitia nunca, asi que las 23 escenas de reel-07
       * se cortaron de la cinta que pasa `montar.sh` —una sola— incluidas las
       * que el EDL declara de otra. Resultado: 26 s perdidos y audio de la
       * cinta equivocada sonando dos veces.
       *
       * Es la averia de la noche por cuarta puerta: el lector existia y el
       * escritor no se ejecutaba.
       */
      fuente: toma,
      etapa,
      dicho: dicho.slice(0, 160),
      montado_desde: Number(montado.toFixed(3)),
      origen_desde: Number(ini.toFixed(3)),
      origen_hasta: Number(fin.toFixed(3)),
      duracion: Number((fin - ini).toFixed(3)),
      modo: k === 0 ? "cut" : "chain",
      hereda_encuadre: Boolean(hereda) && k === 0,
      /**
       * **El encuadre que pidió quien compuso**, o `null` para que
       * `punch-ins.py` siga repartiendo por rueda.
       *
       * Va en TODAS las escenas del beat, no sólo en la primera: si un beat se
       * parte en tres y las tres piden lo mismo, las fronteras entre ellas
       * dejan de verse — que es lo que se quiere dentro de una etapa. La
       * variedad es entre etapas.
       *
       * `punch-ins.py` puede abrirlo si el sujeto no cabe. Ahí manda él: antes
       * un plano más abierto que una cara que se sale.
       */
      encuadre: cam.encuadre,
      /** La costura de ENTRADA del beat. Sólo la primera escena la tiene. */
      transicion: k === 0 ? cam.transicion : "corte",
      // **El virado va en TODAS las escenas del beat**, igual que el encuadre:
      // el tratamiento es de la etapa, no del trozo. Si sólo lo llevara la
      // primera, el plano volvería a su color a mitad de la etapa y eso no lo
      // pidió nadie. `null` = el plano sale como se grabó.
      virado: cam.virado,
      // **Y lo que pasa por detrás de él**, también en todas las escenas del
      // beat: el recorte del sujeto se produce por ETAPA, no por trozo, porque
      // una silueta que aparece y desaparece dentro de la misma etapa lee como
      // un fallo de máscara. `null` = nada detrás, que es como salía todo.
      detras: cam.detras,
      // Con qué canto se recorta lo de detrás. Lo lee `dominio/sujeto.py`.
      canto: cam.canto,
      /**
       * **El movimiento dentro de la escena.** `punch-ins.py` calcula el
       * recorte final con los OJOS como punto fijo (aprendizaje 27), así que
       * el acercamiento no deriva en diagonal aunque el recorte toque un borde.
       *
       * **Y cuánto lo elige quien compone.** Estaba clavado en 0,88 para las
       * escenas de las siete piezas: doce puntos de recorrido, la calibración
       * correcta para que no se note mientras pasa y sí al comparar principio
       * con final — pero la misma en el gancho, en la explicación y en el
       * cierre. Un movimiento único no es tener movimiento.
       *
       * `acercar` sigue siendo esos 0,88, así que lo no declarado sale igual.
       */
      zoom: movimientoDe(cam.movimiento),
    });
    montado += fin - ini;
  }
}

const plan = {
  source: bruto(slug),
  gancho_s: Number(montado.toFixed(3)),
  cambio_cada_s: CADA,
  escenas,
};
const out = `work/scenes/${slug}/plan-full.json`;
// **La carpeta se crea aquí.** Nunca se creaba: existía de corridas anteriores,
// así que el fallo sólo aparece arrancando de cero — y arrancar de cero es
// justo lo que hay que poder hacer. Un paso que depende de que alguien haya
// corrido otro antes no es un paso, es una suposición.
fs.mkdirSync(`work/scenes/${slug}`, { recursive: true });
fs.writeFileSync(out, JSON.stringify(plan, null, 1));
console.log(
  `${slug}: ${escenas.length} escenas · ${montado.toFixed(1)}s ` +
  `(quitados ${aireQuitado.toFixed(1)}s de silencio interno) → ${out}`,
);
