/**
 * **Qué le falta a un panel para poder montarse.**
 *
 * Instrucción de lote de Jaime (5-9-2026): *«para los paneles, las animaciones
 * de bolitas y palitos y ultra sencillas se acaban, quitan más de lo que dan;
 * ahora sólo animaciones complejas que muestren luz o movimiento, ojalá con
 * animación 3D, y que estén en consonancia con la idea del tablero o del
 * panel»*.
 *
 * ## Por qué esto es un fichero y no un párrafo del prompt
 *
 * **Porque la regla ya estaba escrita y la pieza salió igual.** Estaba en
 * `docs/canon.md` con su nombre y en el contrato del diseñador, y los tres
 * paneles de reel-01 se entregaron siendo tres rótulos quietos —«VENDER MÁS»,
 * «ESTRUCTURA», «QUEDAR MÁS»— sobre el plano. Ninguna puerta preguntaba si un
 * panel llevaba algo además de letras, así que la instrucción **no se podía
 * incumplir y saberse**: es la avería de la casa, una regla declarada sin nadie
 * que la comprobara (C-254).
 *
 * Aquí vive lo que se exige; quién para la pieza es `puerta.mjs`. Es el mismo
 * reparto que `sePisa` — el spec arma, la puerta decide quién cede — y por eso
 * esto devuelve **el motivo**, no un booleano: un guarda que dice «no» sin decir
 * qué falta cuesta la vuelta entera.
 */
import fs from "node:fs";
import { FPS } from "./reloj.mjs";
import { evento, huecosDe } from "./material.mjs";

/**
 * Los volúmenes que existen, **leídos de la biblioteca**. Es la misma lista de
 * la que `src/components/Volumen.tsx` deriva su tipo, así que no puede
 * desviarse: pedir uno que no está se dice aquí, en vez de salir como un panel
 * mudo en el render.
 */
const REGISTRO = JSON.parse(
  fs.readFileSync("src/brand/volumenes.json", "utf8"),
);

export const VOLUMENES = Object.keys(REGISTRO.volumenes);

/**
 * **Y la biblioteca puede estar cerrada.** Jaime, 6-9-2026: *«hasta que no
 * tengamos una biblioteca de figuras decentes no las vamos a utilizar; graficos
 * y palabras, como tablero de clase»*.
 *
 * Sale del mismo JSON del que sale la lista, y por eso cerrar es una linea: si
 * la decision viviera aqui, `caja.py` seguiria ofreciendo los diez volumenes en
 * el pedido de diseno y la puerta los rechazaria despues — declarar sin poder
 * aplicar, otra vez, y esta vez al reves.
 */
export const CERRADA = REGISTRO.cerrada ?? null;

/** La caja del volumen, en fracciones del cuadro. Vive en `volumenes.json`. */
export const CAJA = REGISTRO.caja;

/**
 * **A qué lado hay hueco MIENTRAS el panel está puesto, y cuánto se ve.**
 *
 * `huecos` es lo que midió `scripts/dominio/hueco.py`. La escena que decide es
 * **sobre la que el panel está más tiempo** —no el tramo donde cae su primer
 * frame— y de ella se toma el lado con más sitio, que es la regla de la lámina
 * 3 del canon: *«el bloque cuelga de un margen o del otro según de qué lado
 * deja hueco su cuerpo… no hay nada elegido a mano»*.
 *
 * ## Por qué no vale el primer frame
 *
 * Porque **el primer frame de un panel cae en el corte**, y ahí un redondeo
 * decide de qué lado. El `at` de un panel de acompañamiento es
 * `enFrames(montado_desde)`, o sea el arranque de su beat redondeado a frame
 * entero: en reel-01 el beat 5 empieza en 58,847 s y su frame es el 1765, que
 * es 58,833 s — **14 ms ANTES del corte**. El tramo que contiene ese instante
 * es todavía el beat 4, y el beat 4 es un primer plano.
 *
 * Lo que salió por ahí, medido y visto en los fotogramas: el panel del
 * mecanismo vive 5 s enteros sobre el plano abierto del beat 5 —18,5% de ancho
 * libre— y la puerta lo paraba con el 9,6% del primer plano anterior, sobre el
 * que está catorce milésimas. Es la avería de siempre en su forma más barata:
 * una medida correcta preguntada en el instante equivocado.
 *
 * Y falla en los dos sentidos, que es lo que obliga a arreglarlo aquí y no con
 * un margen: en reel-05 el panel del beat 4 pasaba con el 27,4% de una escena
 * de medio segundo que ya había terminado, teniendo 12,6% donde de verdad se
 * dibuja.
 *
 * Devuelve `null` cuando no hay medida o el panel cae fuera de lo medido. Sin
 * medida no se adivina un lado: el lado adivinado es exactamente lo que puso
 * doce volúmenes sobre su cara.
 */
export function huecoDelPanel(p, huecos) {
  if (!huecos?.length) return null;
  const desde = p.at / FPS;
  const hasta = desde + (p.duration ?? 1) / FPS;
  const solape = (h) => Math.min(hasta, h.hasta) - Math.max(desde, h.desde);
  let tr = null;
  for (const h of huecos) if (!tr || solape(h) > solape(tr)) tr = h;
  if (!tr || solape(tr) <= 0) return null;
  const lado = tr.izq >= tr.der ? "izq" : "der";
  const libre = Math.max(tr.izq, tr.der);
  return { lado, libre, visible: Math.min(CAJA.ancho, libre - CAJA.margen) };
}

/**
 * **Cada panel, colocado donde su escena deja sitio.**
 *
 * El `lado` de la pieza sigue sirviendo para lo que siempre sirvió —los bloques
 * de texto, que caben en cualquier margen— y no para el volumen, que pide el
 * 30% del ancho. Lo que decide el volumen es cuánto hueco hay **en esa escena**.
 *
 * Cuando no está medido, el panel se queda sin `hueco` y `faltaDelPanel` lo
 * dice: antes que colocarlo a ojo, una falta declarada.
 */
export const colocaPaneles = (paneles, slug) => {
  const huecos = huecosDe(slug);
  return paneles.map((p) => {
    const c = p.casillas ? { ...p, casillas: p.casillas.map(deSuDueno) } : p;
    const h = huecoDelPanel(p, huecos);
    return h ? { ...c, lado: h.lado, hueco: h.libre } : c;
  });
};

/**
 * **Lo que una casilla derivada dice sale de su dueño, no de los props.**
 *
 * La tira de días de reel-04 e7 sella un bloque de oro con la fecha del evento,
 * y esa fecha vive en la escalera de `precio` —la lee `consulta.py evento`, la
 * misma que pone la fecha en la tarjeta de cierre—. Escribirla en el tablero
 * sería la segunda copia: el día que la escalera se mueva, la tira seguiría
 * diciendo la de antes y nadie se enteraría. El propio tablero lo dejó dicho
 * —*«no va escrita en props, se deriva de su dueño»*— y no había por dónde.
 *
 * Una casilla sin `dato` pasa tal cual. Una con `dato` que no se resuelve se
 * queda sin texto **y lo dice** `faltaDelPanel`: ausencia declarada antes que
 * una casilla vacía en pantalla.
 */
let _evento;
const DERIVADOS = { fecha: () => (_evento ??= evento())?.con_ano ?? null };

const deSuDueno = (c) => {
  const d = typeof c?.dato === "string" ? DERIVADOS[c.dato] : null;
  return d ? { ...c, texto: d() ?? undefined } : c;
};

/** Un panel que enseña un dígito enseña una cifra, y una cifra lleva pie. */
export const HAY_CIFRA = /\d/;

/**
 * El motivo por el que este panel no se monta, o `null` si está.
 *
 * **La banda queda fuera, y no es una excepción de conveniencia.**
 * `cubre: "banda"` es un rótulo de pie —fecha, condiciones— y no ilustra nada:
 * pedirle una animación compleja sería adorno, que es justo lo que la
 * instrucción viene a quitar. Lo que se exige es de los paneles, que son los que
 * explican.
 */
export function faltaDelPanel(p) {
  const dice = (p.bloques ?? []).map((b) => `«${b.texto}»`).join(", ");
  // **Una casilla derivada que no se resolvió sale vacía, y eso no se calla.**
  // El bloque de oro de la tira de días sin la fecha dentro es una casilla en
  // blanco: no se ve como un fallo, se ve como una decisión. Ver `deSuDueno`.
  const seca = (p.casillas ?? []).find((c) => c.dato && !c.texto);
  if (seca)
    return `pide la casilla derivada «${seca.dato}» y no se pudo resolver, así` +
      ` que saldría en blanco. La derivan \`DERIVADOS\` en` +
      ` \`scripts/reels/paneles.mjs\`; comprueba que su dueño conteste`;
  // **El pie se exige a los dos, panel y banda.** Lo que obliga no es de qué
  // clase sea la capa: es que esté enseñando una cifra. Jaime, sobre el pie:
  // *«pequeña no es descuidada»* — y una cifra sin de dónde sale es lo que el
  // playbook llama cumplimiento, no estilo.
  //
  // **Y un reparto enseña cifras aunque ningún rótulo lleve un dígito**: las
  // rotula la barra, con su cuerpo a 84 px, que es lo más grande de la lámina.
  // Sin esta mitad, pasar el «$54 / $46» de los bloques a la barra —que es lo
  // que pide la biblioteca cerrada— sacaba la cifra de esta puerta y la dejaba
  // en pantalla sin fuente.
  const conCifra = (p.bloques ?? []).some((b) => HAY_CIFRA.test(b.texto)) ||
    Boolean(p.reparto?.porciones?.length);
  if (conCifra && !p.fuente)
    return `enseña una cifra (${dice || "en el reparto"}) y no dice de dónde` +
      ` sale. El pie va` +
      ` FUERA de la zona segura, en una línea y en afirmativo —«basado en X` +
      ` datos bajo X condiciones»—, con la cifra y el tramo exactos. Declara` +
      ` \`source\` en su tablero`;
  // **Y una banda no lleva volumen: no basta con no exigírselo.**
  //
  // `cubre` no llega al render — `Reel.tsx` le pasa `volumen` a `SidePanel` sin
  // mirarlo —, así que una banda con `volumen` declarado sigue dibujando la
  // animación, y la dibuja donde nadie midió si cabe. Es la avería de la casa:
  // una clave que decide en un sitio y se aplica en otro.
  //
  // Salió al aplicar la decisión de Jaime del 6-9-2026 sobre los cuatro paneles
  // que nunca fueron volumen —reel-02 e5, reel-03 e1, reel-04 e9, reel-05 e7—:
  // cambiarles `cubre` los sacaba de esta puerta y les dejaba el volumen puesto.
  if (p.cubre === "banda" && p.volumen)
    return `es una \`banda\` —un rótulo de pie, no algo que ilustre— y aun así` +
      ` declara el volumen «${p.volumen}», que se dibujaría igual y sin que` +
      ` nadie mida si cabe. Retira \`volumen\` de su tablero, o decláralo` +
      ` \`panel\` y que pase por la medida del hueco`;
  if (p.cubre === "banda") return null;
  /**
   * **Con la biblioteca cerrada, la exigencia se invierte.**
   *
   * Hasta el 6-9-2026 esto paraba un panel de solo texto: era la aguja de la
   * instruccion del 5-9 —*«las animaciones de palitos y bolitas se acaban»*— y
   * empujaba al 3D. Ese mismo dia, viendo el 3D ya construido, Jaime lo retira:
   * *«hasta que no tengamos una biblioteca de figuras decentes no las vamos a
   * utilizar. Graficos y palabras, como tablero de clase»*.
   *
   * Dejar la exigencia puesta obligaria a declarar justo lo prohibido, y la
   * pieza no podria montarse ni haciendolo bien ni haciendolo mal. Lo que se
   * dice ahora es lo contrario: un `volumen` declarado es lo que para.
   *
   * **Y «solo texto» deja de ser una falta, no de ser un criterio.** Lo que la
   * instruccion del 5 protegia —que un panel no sea tres rotulos quietos— sigue
   * valiendo; lo que cambia es con que se cumple: con un grafico de datos o con
   * tipografia que entra, no con una figura dibujada.
   */
  if (CERRADA && p.volumen)
    return `declara el volumen «${p.volumen}» y la biblioteca esta CERRADA` +
      ` desde el ${CERRADA.desde}: «${CERRADA.jaime}». Lo que dibuja este panel` +
      ` tiene que ser ${CERRADA.que_entra}. Retira \`volumen\` de su tablero`;
  if (CERRADA) return null;
  if (!p.volumen)
    return `es SOLO TEXTO: ${dice}. Las animaciones de palitos y bolitas se` +
      ` acabaron —«quitan mas de lo que dan»—: un panel lleva luz o movimiento,` +
      ` y en consonancia con lo que dice. Declara \`volumen\` en su tablero con` +
      ` uno de: ${VOLUMENES.join(", ")} (ver src/brand/volumenes.json), o pide` +
      ` el que falte como encargo de codigo`;
  if (!VOLUMENES.includes(p.volumen))
    return `pide el volumen «${p.volumen}» y no existe. Los que hay:` +
      ` ${VOLUMENES.join(", ")}. Uno declarado y no construido sale como panel` +
      ` mudo, que es un fallo invisible`;
  // **Y que quepa donde va.** Un volumen que no cabe no se encoge hasta no
  // decir nada ni se dibuja sobre su cara: se declara. Medido con
  // `hueco.py` en las siete piezas, DOCE de trece volúmenes caían encima de él
  // —el de reel-05 e7 le cruzaba las gafas— porque el lado salía de una cuenta
  // sobre el recorte de la primera escena y nadie miraba cuánto sitio había.
  if (p.hueco === undefined)
    return `no tiene medido el hueco de su escena, así que su volumen se` +
      ` colocaría a ojo — que es como doce de trece acabaron sobre su cara.` +
      ` Corre \`python scripts/dominio/hueco.py\` para esa pieza`;
  if (p.hueco < CAJA.minimo + CAJA.margen)
    return `pide el volumen «${p.volumen}» y su cuerpo deja` +
      ` ${(p.hueco * 100).toFixed(0)}% de ancho libre en esa escena: se verían` +
      ` ${((p.hueco - CAJA.margen) * 100).toFixed(0)}% y el mínimo es` +
      ` ${(CAJA.minimo * 100).toFixed(0)}%. No es que sangre por el borde, es` +
      ` que no cabe. O el panel va en un beat con plano más abierto, o esa` +
      ` etapa es \`banda\``;
  return null;
}

/**
 * Los motivos por los que esta pieza no se monta, uno por panel. Lista vacía =
 * los paneles están. Lo llama `puerta.mjs`, que es quien para.
 */
export const faltasDePaneles = (r) =>
  (r.paneles ?? []).map((p) => {
    const falta = faltaDelPanel(p);
    return falta
      ? `${r.id}: el panel del beat ${p.beat ?? "?"} ` +
        `(${(p.at / FPS).toFixed(1)}s) ${falta}.`
      : null;
  }).filter(Boolean);
