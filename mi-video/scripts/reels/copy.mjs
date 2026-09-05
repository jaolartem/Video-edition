/**
 * **Lo que sigue escrito a mano**, y por eso está junto y se cuenta.
 *
 * Jaime, cerrando el diagnóstico de las cinco entregas idénticas: *«estaba
 * conectada a un "arreglo" hecho a mano por fuera del pipeline»*. Eso eran los
 * literales por pieza repartidos dentro del spec: el diseñador no los escribe,
 * no los puede tocar, y llevaban cinco ciclos idénticos mientras todo lo demás
 * cambiaba.
 *
 * No se pueden quitar hoy sin dejar esas piezas sin nada. Lo que sí se puede es
 * que **dejen de ser invisibles**: viven todos aquí, `literalesDe()` los nombra
 * en cada corrida, y quien mire este fichero ve de un vistazo cuánto del vídeo
 * todavía no sale de la base.
 *
 * ## Los dos que ya no están
 *
 * - **`TABLEROS`** — 219 líneas de tableros por pieza que **nada dibujaba**. Se
 *   declaraba como «respaldo para una pieza sin describir» y ese respaldo no
 *   existía: los tableros salen de `escena_desc` y sólo de ahí. Lo único que
 *   hacía era disparar una falta que decía *«el tablero se monta desde el
 *   literal»*, o sea afirmar algo que no pasaba.
 * - **`PANELES`** — 115 líneas de paneles por pieza, migradas ya a `escena_desc`
 *   y sin ningún lector. Seguían contándose en la falta de literales, así que
 *   el montaje informaba de *«5 paneles salen de un literal»* de una pieza cuyos
 *   paneles salían enteros del diseñador. Un aviso que señala un problema ya
 *   resuelto gasta la misma atención que uno de verdad.
 */
import { FPS } from "./reloj.mjs";
import { pal, raiz } from "./texto.mjs";
import { FRAMES, precioVigente } from "./material.mjs";

/** El rótulo del gancho, línea a línea. */
export const LINEAS = {
  "reel-01": ["No es", "mala suerte"],
  "reel-02": ["Trabaja más.", "Le queda menos"],
  "reel-03": ["Su contador", "no es estratega"],
  "reel-04": ["No es por", "ser inmigrante"],
  "reel-05": ["Empieza el año", "con lastre"],
  "reel-06": ["Nadie le mandó", "una carta"],
};

/** Frames que se sostiene el rótulo dentro del cuadro. 54 = 1,8 s. */
export const SOSTIENE = 54;
/** Ventana de apertura donde vive el rótulo del gancho, en segundos. */
const APERTURA = 20;

/**
 * Cuándo entra el rótulo: **cuando EMPIEZA a decirse la frase**, no cuando
 * termina.
 *
 * Entraba en el frame 0 y decía lo que la voz iba a decir cinco segundos
 * después: para cuando llegaba la frase, el remate ya estaba gastado. Ahora
 * entra EN la palabra, así que subraya en vez de anunciar.
 *
 * La PRIMERA aparición, no la última: si la frase vuelve más adelante —en el
 * reel 6 vuelve— el rótulo llegaría tardísimo. Y si no suena en la apertura,
 * entra al principio: es un gancho y su sitio son los primeros segundos.
 */
export function entraRotulo(captions, lineas) {
  const clave = new Set(
    lineas.flatMap(pal).filter((w) => w.length > 3).map(raiz),
  );
  let entra = null;
  for (const c of captions) {
    if (entra === null && pal(c.text).some((p) => clave.has(raiz(p)))) {
      entra = c.at;
    }
  }
  return entra === null || entra / FPS > APERTURA ? 0 : entra;
}

/**
 * Promesa de cada pieza en la tarjeta final. Sale del libreto, no se inventa.
 *
 * **Tope duro de 42 caracteres**: `CtaCard` la pasa por `assertShort(…, "title")`
 * y eso no avisa, **falla el render**. Es la regla del proyecto funcionando —
 * con 16-50 anuncios, una tarjeta con exceso de texto que sólo advierte se
 * replica cincuenta veces.
 *
 * Y son promesas **educativas**, nunca de resultado: el playbook prohíbe
 * garantizar un resultado individual.
 */
export const PROMESA = {
  "reel-01": "Cómo mover la plata sin perder la mitad.",
  "reel-02": "Qué preguntarle a su contador.",
  "reel-03": "Sepa qué pedirle a su contador.",
  "reel-04": "Por qué el banco dice no, y qué cambiar.",
  "reel-05": "Qué activa el castigo y cómo evitarlo.",
  "reel-06": "Dónde está su brecha y qué hacer con ella.",
  // Condensada de su propio cierre en el libreto —«para que más plata le
  // llegue al bolsillo, de manera legal»—, no escrita aquí de cero.
  "reel-07": "Que más plata le llegue al bolsillo.",
};
for (const [k, v] of Object.entries(PROMESA)) {
  if (v.length > 42) throw new Error(`promesa de ${k}: ${v.length} car (max 42)`);
}

const PRECIO_HOY = precioVigente();

/**
 * **Las dos cuentas del CTA.**
 *
 * Corrección de Jaime, y desarma lo que había: *«el precio del bootcamp es 20,
 * 30 o 40 dólares; el precio de NO conocerlos es de 576»*. La tarjeta ponía los
 * 576 en la fila de precio, así que decía que el bootcamp costaba 576 — el
 * número correcto en la fila equivocada, que es peor que no ponerlo.
 *
 * Son dos cifras de naturaleza distinta y la pieza vive de compararlas: lo que
 * cuesta no saberlo, cada semana, contra lo que cuesta aprenderlo, una vez. Por
 * eso van en dos filas enfrentadas y **la pregunta no se escribe**: la hace la
 * voz —*«revise qué cuenta le sale mejor»*— y la tarjeta sólo enseña las dos
 * cuentas para que la pregunta tenga a qué referirse.
 *
 * **El precio se deriva de la escalera, no se escribe.** Ver la tabla `precio` y
 * `consulta.precio_vigente`: un literal no caduca, y por eso «$20 hasta el 28
 * ago» seguía en pantalla en septiembre (C-28, reabierta). Con el cierre
 * declarado dice lo que es —una escalera, y en qué tramo está— y sigue siendo
 * cierto cuando suba. Es la urgencia real que pide el playbook: una fecha del
 * brief, no un «cupos limitados».
 */
export const CUENTA = {
  "reel-01": {
    cuesta: "$576 cada semana",
    vale: PRECIO_HOY?.vale ?? null,
    // **Sin `nota`.** Decia "luego $30 y $40" y `vale` ya lo trae: la tarjeta
    // pegaba las dos y salia «HASTA EL 4 SEP · LUEGO $30 Y $40 · LUEGO $30 Y
    // $40», en pantalla y en la entrega. `nota` se escribio cuando `vale` era
    // solo «$20»; al derivarse de la escalera de precios crecio y se comio lo
    // que decia la nota, que quedo como segunda copia del mismo dato.
  },
};

/**
 * **El precio, cuando la pieza no lleva las dos cuentas.**
 *
 * Va **siempre con su fecha de cierre**, que es lo que lo hace publicable: un
 * «$20» a secas deja de ser cierto el día que sube y la pieza sigue colgada
 * (C-28). Y aquí carga además la urgencia, porque el reel 3 no la dice en voz —
 * la única toma que la tenía colgaba del precio sin antecedente.
 */
/**
 * **El escalón va en pantalla en TODAS, y sale de la tabla `precio`.**
 *
 * Esto era un literal con una sola pieza dentro —`"reel-03"`— así que las demás
 * salían sin precio o, peor, diciéndolo en voz sin decir que sube: reel-03,
 * reel-05 y reel-06 dicen «20 dólares» y se callan el escalón, y el día 5 las
 * tres mienten sin que nadie toque nada. reel-02 no lo decía en absoluto.
 *
 * Jaime, el 1 de septiembre: *«rotula el escalón en pantalla en las cuatro»*. Y
 * el mecanismo ya estaba hecho: `precioVigente()` devuelve el escalón entero con
 * su fecha de cierre. Lo único que faltaba era dárselo a todas en vez de a una.
 *
 * Las que llevan las dos cuentas (`CUENTA`) no lo repiten: ahí el precio ya está
 * enfrentado a lo que cuesta no saberlo, y ponerlo dos veces lo desarma.
 */
export const PRECIO = Object.fromEntries(
  Object.keys(FRAMES.reels)
    .filter((slug) => !CUENTA[slug])
    .map((slug) => [slug, PRECIO_HOY?.vale ?? null]),
);

/**
 * **La comparación como texto fuerza.**
 *
 * Jaime: *«para la comparación no quiero un tablero, quiero el texto fuerza
 * comparando como animación»*. Se declara que dos cifras se enfrentan y con qué
 * palabra se ancla cada una; **el instante lo pone el subtítulo**, no una
 * constante: cada cifra aterriza cuando la voz la dice.
 *
 * Y las dos se quedan hasta el final del tramo, porque una comparación existe
 * cuando los dos números están a la vez en pantalla.
 */
export const CONTRASTE = {
  "reel-02": {
    izq: { etiqueta: "El electricista", cifra: "$44", ancla: "44", de100: 44,
           placa: "c1-extraction-vertical" },
    der: { etiqueta: "El del yate", cifra: "$67", ancla: "67", de100: 67,
           placa: "r2-horizontes" },
    pie: "Misma facturación · $180,000",
  },
};

/**
 * Tarjetas: los beats que **no tienen toma utilizable**.
 *
 * *«A cada estructura le escogemos el mejor, y si no entra bien hacemos un
 * gráfico, así sea sólo palabras.»* Un beat del libreto no se cae por falta de
 * plano: se dibuja.
 *
 * El copy es decisión humana y por eso vive escrito aquí. Lo que NO se escribe a
 * mano es **cuándo entra**: eso se deriva del plan. Y lo declarado a mano gana:
 * si una pieza trae su tarjeta escrita aquí, ésa se queda; la del paso 2 rellena
 * lo que falte.
 */
export const TARJETAS = {
  "reel-01": [{
    beat: 5,
    props: {
      framework: "Information Gap",
      beat: [5, 8],
      bloques: [
        { texto: "No es un producto" },
        { texto: "No es un puesto" },
        { texto: "Es el mapa" },
      ],
      remate: ["De la empresa", "a su bolsillo."],
      pie: "Legal y cumpliendo las normas.",
    },
  }],
  "reel-05": [{
    beat: 2,
    props: {
      framework: "Transformation Story",
      beat: [2, 11],
      bloques: [
        { texto: "Un realtor" },
        { texto: "Un médico" },
        { texto: "Uno de retail" },
      ],
      remate: ["Mismo trimestre.", "Mismo susto."],
      pie: "Los tres pagaron más que nunca.",
    },
  }],
};

/**
 * **Lo que sale de un literal escrito a mano se dice, cada vez.**
 *
 * Un parche declarado es deuda; un parche callado es la fuente de verdad de
 * facto. Sólo se nombra lo que **de verdad llega a la pantalla desde aquí**:
 * contar literales que ya nadie lee convierte la falta en ruido.
 */
/**
 * **Y se cuenta el que SE USA, no el que existe.**
 *
 * Esto miraba si el literal estaba escrito, no si alguien lo leia. Con cinco de
 * las siete piezas declarando ya su rotulo en `escena_desc` —y `rotuloDe`
 * ganandole al literal, como debe— el montaje seguia avisando de «1 rotulo del
 * gancho sale de un literal» en las seis. Veintiuna faltas de treinta eran eso.
 *
 * Es la misma averia que este fichero documenta arriba para `TABLEROS` y
 * `PANELES`, palabra por palabra: *«un aviso que senala un problema ya resuelto
 * gasta la misma atencion que uno de verdad»*. Escrita en el docstring y no en
 * la funcion.
 */
export const literalesDe = (slug, declarado) => {
  // `declarado` lo pasa quien monta: alli ya se resolvio el rotulo y aqui no se
  // puede preguntar sin un ciclo de imports —`escena.mjs` importa de este
  // fichero—. Se recibe en vez de deducirse.
  return [
    ["rotulo del gancho", !declarado && (LINEAS[slug] ?? []).length ? 1 : 0],
    ["tarjetas", (TARJETAS[slug] ?? []).length],
  ].filter(([, n]) => n > 0);
};


/**
 * **Un precio dicho sin la escala en pantalla no sale.**
 *
 * Jaime: *«prefiero o dejarlo con el 20 o cambiarlo, pero dejar en pantalla la
 * escala de precios»*. Con la escala puesta, que la voz diga «20 dolares» deja
 * de caducar: la pantalla dice hasta cuando vale y a cuanto sube. Sin ella, la
 * pieza miente sola el dia que el escalon cambia — y no avisa nadie, porque una
 * frase correcta el lunes sigue siendo gramatical el viernes.
 *
 * Por eso se comprueba aqui y no se confia en que alguien se acuerde: es la
 * unica forma de que no vuelva. Lo que se mira es lo que el espectador tiene
 * delante — la voz por un lado, `PRECIO` o `CUENTA` por el otro.
 */
export const precioSinEscala = (slug, captions) => {
  const dice = (captions ?? []).some(
    (c) => /(20|30|40|veinte|treinta|cuarenta)\s+(d[oó]lares|dolares)/i
      .test(String(c.text ?? "")),
  );
  if (!dice) return null;
  if (PRECIO[slug] || CUENTA[slug]) return null;
  return `${slug}: la voz dice un precio y la escala no sale en pantalla —` +
    ` el dia que suba, la pieza miente sola`;
};
