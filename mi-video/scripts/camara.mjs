/**
 * **La cámara como algo que se pide, no como algo que toca.**
 *
 * Jaime, después de leer `docs/composicion.md`: *«dale herramientas al diseñador
 * para que pueda tocar todo eso, que no quede otra vez el mismo error de
 * declarar sin implementar, que ha sido la constante en este proyecto»*.
 *
 * Y tenía razón sobre lo que había. Los tipos de plano **existían en código**
 * desde el principio —`punch-ins.py` saca cinco encuadres distintos del mismo
 * 4K— y se repartían con `ENCUADRES[idx % len(ENCUADRES)]`: una rueda. Cinco
 * planos construidos, ninguno elegible. Igual la cortinilla: el componente
 * escrito, el hueco en el spec, `Reel.tsx` dibujándola — y `cortinillas: []`
 * fijo, así que la pieza no podía llevar una aunque la costura la pidiera.
 *
 * Aquí no se construye nada nuevo: se le da **el mando** de lo que ya se movía
 * solo.
 *
 * ## Y cada verbo dice quién lo hace
 *
 * `LO_HACE` son agujas —fichero y línea literal, como en `docs/correcciones.md`
 * y en los contratos—. `comprobar()` las abre. Un verbo que se ofrece y cuya
 * línea no existe **es el error que este fichero viene a cerrar**, así que sale
 * como fallo y no como nota al pie.
 *
 * `POR_CONSTRUIR` es lo contrario y pesa igual: un verbo que se puede pedir
 * sabiendo que cuesta código antes de verse. No se descarta, se agenda — pero
 * nunca se ofrece como si ya estuviera.
 *
 *     node scripts/camara.mjs              # el vocabulario, legible
 *     node scripts/camara.mjs --json       # para el contrato
 *     node scripts/camara.mjs --comprobar  # ¿lo ofrecido existe?
 */
import fs from "node:fs";
import path from "node:path";
// El tratamiento de la imagen —virado y costura animada— se declara y se
// resuelve en `imagen.mjs`; aqui solo se empalma al menu, que es uno solo.
import { ANIMADAS, DETRAS, POR_HACER, VIRADOS, bloqueDetras, bloqueVirado }
  from "./imagen.mjs";

/**
 * Los encuadres, **leídos de quien los recorta**.
 *
 * No es una lista paralela: es la de `punch-ins.py`. Escribirla aquí sería la
 * segunda copia de siempre —el día que se añada un encuadre, el diseñador
 * seguiría viendo cinco— y además una que prometería recortes que el cropper no
 * sabe hacer.
 */
export const encuadres = () => {
  const t = fs.readFileSync("scripts/punch-ins.py", "utf8");
  const bloque = t.match(/^ENCUADRES = \[([\s\S]*?)^\]/m);
  if (!bloque) return [];
  return [...bloque[1].matchAll(/\(\s*"([^"]+)"\s*,\s*([\d.]+)\)/g)].map(
    ([, nombre, frac]) => ({ nombre, cuadro: Number(frac) }),
  );
};

/**
 * El movimiento dentro de la escena.
 *
 * `punch-ins.py` ya calcula el recorte final con los ojos como punto fijo, así
 * que lo único que quedaba por decidir es **cuánto**. Y estaba clavado en 0,88
 * para todas las escenas de las siete piezas: un acercamiento lentísimo
 * idéntico en todas, que no es tener movimiento sino tener uno solo.
 *
 * `cuadro` es la fracción del recorte al final respecto al del principio: por
 * debajo de 1 el cuadro se cierra, por encima se abre.
 */
export const MOVIMIENTOS = {
  acercar: {
    que: "el cuadro se cierra despacio sobre la cara. Sube la tensión sin que se"
      + " note mientras pasa: se nota al comparar el final con el principio",
    cuadro: 0.88,
  },
  entrar: {
    que: "se cierra el doble de rápido. Para el remate y para el gancho, donde"
      + " el movimiento tiene que verse",
    cuadro: 0.76,
  },
  alejar: {
    que: "el cuadro se abre y deja sitio. Para cuando entra un panel al lado o"
      + " la idea se ensancha",
    cuadro: 1.12,
  },
  quieto: {
    que: "no se mueve. Es una decisión, no una ausencia: después de tres escenas"
      + " moviéndose, quedarse quieto es lo que dice que esto hay que leerlo",
    cuadro: 1.0,
  },
};

/**
 * Lo que media una costura entre dos beats.
 *
 * `corte` no es la ausencia de transición: es la más fuerte y la más honesta, y
 * sigue siendo el valor por defecto. Se nombra para poder **elegirlo**, que no
 * es lo mismo que que te toque.
 */
export const TRANSICIONES = {
  corte: {
    que: "corte seco. Lo tapa lo que ya haya —el tablero que se estira por"
      + " encima de la frontera, o la distorsión que puso la costura— y si no"
      + " hay nada, se ve el salto",
    placa: false,
  },
  // **Y el corte que no se tapa** (C-645). Jaime, reel-18, de un glitch en
  // mitad de «…hacerme rico, la verdad»: «ese glitch daña todo el mensaje y lo
  // dificulta». Con `corte` la costura dura se seguía tapando sola.
  seco: {
    que: "corte seco SIN distorsión en ninguna costura de la etapa, tampoco en"
      + " las de dentro: el salto se ve y la voz queda intacta. Para la etapa"
      + " cuya frase cruza la costura",
    placa: false,
  },
  glitch: {
    que: "la imagen se distorsiona unos frames sobre la propia costura. Tapa"
      + " el salto sin interrumpir: no hay placa, no hay corte a negro y la"
      + " cara sigue en cuadro. Es la transición discreta de esta pieza",
    placa: false,
  },
  // Y la animada, que es la tercera y la que faltaba. Ver `imagen.mjs`.
  ...ANIMADAS,
};

/**
 * Retiradas: se dicen, no se ofrecen.
 *
 * **Una transición que Jaime rechazó no puede volver por el menú.** La
 * cortinilla se probó en todas las costuras, quedó mal —*«en el segundo 7 se ve
 * raro; esos cortes de escena no vale la pena dejarlos como cortes de escena»*—
 * y se retiró. Después se reabrió «sólo donde se pida», el menú siguió
 * describiéndola como una virtud, y el diseñador la pidió: reel-01 salió con una
 * placa de 0,7 s en el segundo 61,7. Jaime, al verla: *«eso ya lo habíamos
 * depreciado, ¿por qué el diseñador volvió a traer esa cortina? Para eso está el
 * glitch, u otras transiciones más discretas y elegantes»*.
 *
 * La avería no fue del diseñador: **eligió de la carta que le dimos**. Un
 * mecanismo que sigue existiendo en el código y sigue anunciado en el menú no
 * está depreciado, está esperando a que alguien lo pida.
 *
 * Se listan aquí para que el que compone vea que existieron y por qué no están
 * — borrarlas del todo invita a reinventarlas dentro de un mes.
 */
export const RETIRADAS = {
  cortinilla: {
    que: "una placa con el nombre de la etapa llenando el cuadro 0,7 s",
    por_que: "Jaime: «eso ya lo habíamos depreciado… para eso está el glitch, u"
      + " otras transiciones más discretas y elegantes». Interrumpe la cara para"
      + " decir algo que el subtítulo ya dice",
    en_su_lugar: "glitch",
  },
};

/** Lo que todavía no existe, dicho como lo que es. */
export const POR_CONSTRUIR = {
  panoramica: {
    que: "el recorte viaja de lado dentro del 4K sin cortar: un travelling"
      + " gratis. Hoy el recorte final sólo cambia de tamaño, no de sitio",
    cuesta: "scripts/punch-ins.py — el rectángulo final se deriva del zoom;"
      + " haría falta un desplazamiento declarado del ancla",
  },
  segunda_camara: {
    que: "una escena grabada con dos cámaras a la vez, para cortar entre"
      + " ÁNGULOS en vez de entre encuadres del mismo plano",
    cuesta: "**ya casi.** El material entra: una grabación puede ser una carpeta"
      + " con los ángulos dentro (`rutas.angulos`) y `scripts/desfase.py` mide"
      + " por el sonido cuánto separa los relojes, con su confianza — medido,"
      + " no estimado. Falta lo último: poder decir en esta declaración **qué"
      + " ángulo lleva cada etapa**, y que el corte lo lea. Se abre el día que"
      + " haya una grabación a dos cámaras con la que comprobarlo",
  },
  // Las dos que piden ver dos tomas a la vez, con su coste. Ver `imagen.mjs`.
  ...POR_HACER,
};

/** Quién hace cada verbo. Fichero y línea literal: `comprobar()` las abre. */
export const LO_HACE = {
  encuadre: [
    ["scripts/plan-reel.mjs", "encuadre: cam.encuadre,"],
    ["scripts/punch-ins.py", 'pedido = e.get("encuadre")'],
  ],
  movimiento: [
    ["scripts/plan-reel.mjs", "zoom: movimientoDe(cam.movimiento),"],
    ["scripts/camara.mjs", "export const movimientoDe = (nombre) => {"],
  ],
  transicion: [
    ["scripts/reels-spec.mjs", "cortinillas: cortinillasDe(slug, reloj, marco),"],
    ["src/components/Cortinilla.tsx", "export const Cortinilla: React.FC<CortinillaProps> = ({"],
    ["scripts/reels/imagen.mjs", "export function filetesDe(reloj) {"],
    ["src/components/Filete.tsx", "export const Filete: React.FC<{"],
  ],
  virado: [
    ["scripts/plan-reel.mjs", "virado: cam.virado,"],
    ["scripts/reels/imagen.mjs", "export function viradosDe(reloj) {"],
    ["src/Ad.tsx", "const virado = virados.find("],
  ],
  // Quién lo declara, lo produce, lo coloca, lo dibuja y lo apila.
  detras: [
    ["scripts/plan-reel.mjs", "detras: cam.detras,"],
    ["scripts/dominio/sujeto.py", "def recortes_de_la_pieza(n):"],
    ["scripts/reels/imagen.mjs", "export function recortesDe(reloj, slug) {"],
    ["src/components/Detras.tsx", "export const Detras: React.FC<DetrasProps> = ({"],
    ["src/Ad.tsx", "<Recortes lista={recortes} filtro={filtro} />"],
  ],
};

/**
 * El movimiento como lo espera el plan. **Aquí se declara y aquí se resuelve**,
 * que es la única forma de que las dos mitades no puedan separarse.
 */
export const movimientoDe = (nombre) => {
  const m = MOVIMIENTOS[nombre] ?? MOVIMIENTOS.acercar;
  return m.cuadro === 1 ? null : { hasta: m.cuadro, desde_s: 0.3 };
};

/** Lo que el diseñador declaró para una etapa, ya como objeto y sin sorpresas. */
export const camaraDe = (crudo) => {
  let d = {};
  try {
    d = crudo ? JSON.parse(crudo) : {};
  } catch {
    d = {};
  }
  if (!d || typeof d !== "object") d = {};
  const enc = encuadres().map((e) => e.nombre);
  return {
    encuadre: enc.includes(d.encuadre) ? d.encuadre : null,
    movimiento: d.movimiento in MOVIMIENTOS ? d.movimiento : "acercar",
    transicion: d.transicion in TRANSICIONES ? d.transicion : "corte",
    // Sin virado el plano sale como se grabo, que es lo normal.
    virado: d.virado in VIRADOS ? d.virado : null,
    // Sin `detras` no hay recorte: la pasada de MediaPipe se paga donde se pide.
    detras: d.detras in DETRAS ? d.detras : null,
  };
};

/** El vocabulario entero, para el contrato. */
export const vocabulario = () => ({
  como_se_pide: "Un objeto `camara` por etapa: `{encuadre, movimiento,"
    + " transicion, virado, detras}`. Los cinco son opcionales; lo que no"
    + " declares sale como salía — encuadre por rueda, acercamiento lento, corte"
    + " seco, plano sin teñir y nada por detrás. Declarar es elegir, no rellenar.",
  encuadre: {
    que: "de qué habla el plano. El bruto es 4K y la salida 1080, así que"
      + " recortar no cuesta nitidez: los cinco son el mismo plano visto de más"
      + " cerca o de más lejos, y entre ellos no hay nada que casar.",
    valores: Object.fromEntries(encuadres().map((e) => [
      e.nombre, `ocupa el ${Math.round(e.cuadro * 100)}% del cuadro original`])),
    la_nitidez: "El bruto da exactamente 2x de margen, así que los dos"
      + " encuadres más cerrados gastan casi todo: `primerisimo` amplía un 9% y"
      + " deja poco sitio para acercarse dentro de la escena. No es una"
      + " prohibición —Jaime: «máximo un 10%, todavía es poco notable»— y la"
      + " máquina lo hace cumplir sola: si un plano se pasara, se abre y lo"
      + " dice. Pídelo cuando la etapa lo pida, no por variar.",
    si_no_dices: "se reparten en rueda, que es lo que llevaba haciéndose siempre",
  },
  movimiento: {
    que: "cómo se mueve el cuadro DENTRO de la escena, sin cortar",
    valores: Object.fromEntries(
      Object.entries(MOVIMIENTOS).map(([k, v]) => [k, v.que])),
    si_no_dices: "acercar",
  },
  transicion: {
    que: "qué media la costura con la etapa anterior",
    valores: Object.fromEntries(
      Object.entries(TRANSICIONES).map(([k, v]) => [k, v.que])),
    si_no_dices: "corte",
  },
  virado: bloqueVirado(),
  detras: bloqueDetras(),
  retiradas: Object.fromEntries(
    Object.entries(RETIRADAS).map(([k, v]) => [k, `${v.que} — RETIRADA:`
      + ` ${v.por_que}. En su lugar: ${v.en_su_lugar}`])),
  por_construir: Object.fromEntries(
    Object.entries(POR_CONSTRUIR).map(([k, v]) => [k, v.que])),
  si_pides_algo_por_construir: "Dilo en `por_que`. No se descarta: se agenda."
    + " Lo que no vale es componer suponiendo que ya está.",
});

/**
 * ¿Existe lo que se ofrece? Devuelve las agujas rotas.
 *
 * Es la guarda de este fichero y la razón de que exista: *«que no quede otra vez
 * el mismo error de declarar sin implementar»*. Un verbo en el menú del
 * diseñador cuya línea consumidora ya no está es una promesa muerta, y muere en
 * silencio — que es exactamente como murieron los cinco encuadres.
 */
export const comprobar = () => {
  const rotas = [];
  for (const [verbo, agujas] of Object.entries(LO_HACE)) {
    for (const [fichero, aguja] of agujas) {
      let hay = false;
      try {
        hay = fs.readFileSync(fichero, "utf8").includes(aguja);
      } catch {
        hay = false;
      }
      if (!hay) rotas.push({ verbo, fichero, aguja });
    }
  }
  return rotas;
};

const _directo =
  process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]));
if (_directo) {
  if (process.argv.includes("--comprobar")) {
    const rotas = comprobar();
    for (const r of rotas)
      console.log(`ROTA  ${r.verbo}: ${r.fichero} :: ${r.aguja}`);
    console.log(rotas.length
      ? `\n${rotas.length} verbo(s) ofrecidos y no implementados.`
      : `${Object.keys(LO_HACE).length} verbos, todos con su línea viva.`);
    process.exit(rotas.length ? 1 : 0);
  } else if (process.argv.includes("--json")) {
    console.log(JSON.stringify(vocabulario(), null, 1));
  } else {
    const v = vocabulario();
    for (const k of ["encuadre", "movimiento", "transicion", "virado", "detras"]) {
      console.log(`\n${k.toUpperCase()} — ${v[k].que}`);
      for (const [n, q] of Object.entries(v[k].valores))
        console.log(`  ${n.padEnd(14)} ${q}`);
    }
    console.log("\nPOR CONSTRUIR");
    for (const [n, q] of Object.entries(v.por_construir))
      console.log(`  ${n.padEnd(14)} ${q}`);
  }
}
