/**
 * Emite `src/reels.json`: lo que Remotion superpone sobre cada reel montado.
 *
 * Tres capas, y ninguna es decorativa:
 *
 * - **Subtítulos.** El playbook exige que el argumento funcione sin audio y esa
 *   carga la llevan ellos. Salen de las palabras del transcript mapeadas a la
 *   línea de tiempo del EDL — no de tiempos aproximados a mano.
 * - **Rótulo del gancho**, con la misma regla que en `ganchos-spec.mjs`: cede en
 *   un corte posterior a su frase, o no cede.
 * - **Tarjeta de CTA** al final, con fecha y precio. Un SELL lleva exactamente
 *   un CTA; el resto de pilares, cero.
 *
 *   node scripts/reels-spec.mjs
 */
import fs from "fs";
import { execFileSync } from "child_process";
import { DatabaseSync } from "node:sqlite";
import { construir, revisarPieza, sonidosMudos } from "./caminos.mjs";

const FPS = 30;
/**
 * El montaje corre acelerado — Jaime: *«ponlo a 1.1× o a 1.2×»*—, así que
 * **los tiempos del EDL no son los del vídeo**. Todo lo que se derive del EDL
 * y tenga que caer sobre la línea de tiempo se divide por esto.
 *
 * Sin ello la comprobación de coherencia gritaba en los seis reels: comparaba
 * 60,8 s de EDL contra 53,3 s de corte y concluía «el corte está viejo». Una
 * alarma que suena siempre deja de leerse, y entonces ya no sirve para el aviso
 * que sí valga. Tiene que coincidir con `VELOCIDAD` de `render-hook.mjs`.
 */
const VELOCIDAD = 1;
/** Duración de la cortinilla, en frames. Igual que `DURACION` en el componente. */
/**
 * Cuánto se estira un tablero por encima de la costura que sigue.
 *
 * 0,8 s: el beat siguiente arranca por debajo mientras el tablero todavía está,
 * así que al volver al plano no hay corte que ver. Es la forma clásica de
 * esconder una costura —cortar a otra cosa y volver tarde— y aquí esa otra cosa
 * además explica.
 */
const SOLAPE = 24;
/**
 * Cuanto metraje con Jaime en cuadro basta por si solo.
 *
 * Jaime, calibrando: *«mas del 60% del video, o en esos tres puntos»*. Si su
 * cara ocupa mas de esto, la pieza cumple sin mirar donde caen los tableros —
 * porque entonces la pieza **es** el, y un tablero largo en un sitio no lo hace
 * desaparecer. Por debajo, se exige el reparto en los tres tercios.
 */
const MINIMO_CARA = 0.60;
/**
 * Cuánto dura la distorsión que tapa una costura. 5 frames, 0,17 s.
 *
 * Muy corta a propósito: lo que tapa dura un frame, y un efecto más largo deja
 * de esconder el corte para pasar a ser el corte.
 */
const DUR_GLITCH = 5;
const TOMA = {
  "reel-01": "20260825_135637", "reel-02": "20260825_144010",
  "reel-03": "20260825_224414", "reel-04": "20260825_225808",
  "reel-05": "20260825_151758", "reel-06": "20260825_231706",
};
const LINEAS = {
  "reel-01": ["No es", "mala suerte"],
  "reel-02": ["Trabaja más.", "Le queda menos"],
  "reel-03": ["Su contador", "no es estratega"],
  "reel-04": ["No es por", "ser inmigrante"],
  "reel-05": ["Empieza el año", "con lastre"],
  "reel-06": ["Nadie le mandó", "una carta"],
};
/**
 * Promesa de cada pieza en la tarjeta final. Sale del libreto, no se inventa.
 *
 * **Tope duro de 42 caracteres**: `CtaCard` la pasa por `assertShort(…, "title")`
 * y eso no avisa, **falla el render**. Es la regla del proyecto funcionando —
 * con 16-50 anuncios, una tarjeta con exceso de texto que solo advierte se
 * replica cincuenta veces.
 *
 * Y son promesas **educativas**, nunca de resultado: el playbook prohíbe
 * garantizar un resultado individual.
 */
const PROMESA = {
  "reel-01": "Cómo mover la plata sin perder la mitad.",
  "reel-02": "Qué preguntarle a su contador.",
  "reel-03": "Sepa qué pedirle a su contador.",
  "reel-04": "Por qué el banco dice no, y qué cambiar.",
  "reel-05": "Qué activa el castigo y cómo evitarlo.",
  "reel-06": "Dónde está su brecha y qué hacer con ella.",
};
for (const [k, v] of Object.entries(PROMESA)) {
  if (v.length > 42) throw new Error(`promesa de ${k}: ${v.length} car (max 42)`);
}

/**
 * **Las dos cuentas del CTA.**
 *
 * Correccion de Jaime, y desarma lo que habia: *«el precio del bootcamp es 20,
 * 30 o 40 dolares; el precio de NO conocerlos es de 576»*. La tarjeta ponia los
 * 576 en la fila de precio, asi que decia que el bootcamp costaba 576 — el
 * numero correcto en la fila equivocada, que es peor que no ponerlo.
 *
 * Son dos cifras de naturaleza distinta y la pieza vive de compararlas: lo que
 * cuesta no saberlo, cada semana, contra lo que cuesta aprenderlo, una vez. Por
 * eso van en dos filas enfrentadas y **la pregunta no se escribe**: la hace la
 * voz —*«revise que cuenta le sale mejor»*— y la tarjeta solo ensena las dos
 * cuentas para que la pregunta tenga a que referirse. Escribirla ademas seria
 * la misma frase en dos capas.
 *
 * El precio del bootcamp SI entra aqui, al contrario que la regla general: no
 * es un dato que envejezca en silencio, es una escalera que sube y **esa es la
 * urgencia real** que pide el playbook. Lo que no entra es un «cupos
 * limitados» generico.
 */
/**
 * **El escalon de precio vigente hoy, preguntado a quien lo sabe.**
 *
 * La escalera vive en la tabla `precio` y el rotulo lo redacta
 * `consulta.precio_vigente` — aqui NO se vuelve a implementar. Dos formas de
 * redactar el mismo rotulo son dos rotulos en cuanto alguien toque una.
 *
 * `null` cuando ya cerro la inscripcion, y entonces **no se imprime precio**:
 * una tarifa cerrada en pantalla es peor que ninguna.
 */
const PRECIO_HOY = (() => {
  try {
    return JSON.parse(
      execFileSync("python", ["scripts/consulta.py", "precio_vigente", "[]"],
                   { encoding: "utf8" }),
    );
  } catch {
    return null;
  }
})();

const CUENTA = {
  "reel-01": {
    cuesta: "$576 cada semana",
    // **La fecha es lo que lo hace justo.** Jaime quito el precio de la tarjeta
    // porque *«es a 20 hasta el 28, es decir hasta manana, y no se ve tan
    // justo»*: un «$20» a secas se lee como el precio del bootcamp y deja de
    // ser cierto pasado manana. Con el cierre declarado dice lo que es —una
    // escalera, y en que tramo esta— y sigue siendo cierto cuando suba.
    //
    // Es la urgencia real que pide el playbook: una fecha del brief, no un
    // «cupos limitados». Los tramos de $30 y $40 van sin fecha porque no la
    // hay cerrada, y **inventarla seria fabricar un detalle de la oferta**.
    // **El precio se deriva de la escalera, no se escribe.** Ver la tabla
    // `precio` y `consulta.precio_vigente`: un literal no caduca, y por eso
    // «$20 hasta el 28 ago» seguia en pantalla en septiembre (C-28, reabierta).
    vale: PRECIO_HOY?.vale ?? null,
    nota: "luego $30 y $40",
  },
};

/**
 * **La comparacion como texto fuerza.**
 *
 * Jaime: *«para la comparacion no quiero un tablero, quiero el texto fuerza
 * comparando como animacion»*. Se declara que dos cifras se enfrentan y con que
 * palabra se ancla cada una; **el instante lo pone el subtitulo**, no una
 * constante: cada cifra aterriza cuando la voz la dice.
 *
 * Y las dos se quedan hasta el final del tramo, porque una comparacion existe
 * cuando los dos numeros estan a la vez en pantalla.
 */
const CONTRASTE = {
  "reel-02": {
    izq: { etiqueta: "El electricista", cifra: "$44", ancla: "44", de100: 44,
           placa: "c1-extraction-vertical" },
    der: { etiqueta: "El del yate", cifra: "$67", ancla: "67", de100: 67,
           placa: "r2-horizontes" },
    pie: "Misma facturación · $180,000",
  },
};

/**
 * **El precio, cuando la pieza no lleva las dos cuentas.**
 *
 * Va **siempre con su fecha de cierre**, que es lo que lo hace publicable: un
 * «$20» a secas deja de ser cierto el dia que sube y la pieza sigue colgada
 * (C-28). Y aqui carga ademas la urgencia, porque el reel 3 no la dice en voz —
 * la unica toma que la tenia colgaba del precio sin antecedente.
 */
const PRECIO = {
  "reel-03": PRECIO_HOY?.vale ?? null,
};

/** Frames que se sostiene el rotulo dentro del cuadro. 54 = 1,8 s. */
const SOSTIENE = 54;
/** Ventana de apertura donde vive el rotulo del gancho, en segundos. */
const APERTURA = 20;
const REMATE = 0.5;
/** Tope de la tarjeta: el subtítulo sigue debajo, así que no puede taparlo. */
/**
 * Cuánto dura la tarjeta de CTA.
 *
 * 5,5 s y no 4: Jaime pidió que el último tablero entre **desde el 1:10**, y
 * con 4 s entraba en 71,2 y se montaba entero en el primer medio segundo. Con
 * 5,5 entra en 69,7 y reparte su horario sobre toda su vida.
 */
const CTA_S = 5.5;

/**
 * **El tratamiento de cada ESCENA, no de cada beat.**
 *
 * Jaime: *«en la tabla de los videos siempre quede relacionado por escena: si
 * es tablero, si tiene animaciones graficas o si tiene texto animado o CC
 * animado. Siempre debe tener una de las tres y no siento que se este
 * cumpliendo»*.
 *
 * Por beat no bastaba: un beat de 17 s son tres o cuatro escenas y con un panel
 * al principio el beat contaba como tratado mientras las otras dos iban a plano
 * seco. La escena es la unidad que el espectador ve cambiar, asi que es la
 * unidad que hay que auditar.
 *
 * Las tres, y su orden de prelacion cuando coinciden: **tablero** (reemplaza la
 * escena), **animacion** (panel detras del hablante) y **texto** (idea fuerza,
 * remate compuesto o marca de humanidad). Una escena con ninguna sale marcada.
 */
const porEscena = (r, slug) => {
  const f = `work/scenes/${slug}/plan-full.json`;
  if (!fs.existsSync(f)) return [];
  const plan = JSON.parse(fs.readFileSync(f, "utf8"));
  const texto = r.captions.filter((c) => c.realza || c.corrige || c.compuesto);
  let t = 0;
  return plan.escenas.map((e, i) => {
    const a = Math.round((t / VELOCIDAD) * FPS);
    t += e.duracion;
    const b = Math.round((t / VELOCIDAD) * FPS);
    const pisa = (x) => x.at < b && x.at + x.duration > a;
    const trato = r.boards.some(pisa) || r.tarjetas.some(pisa)
      ? "tablero"
      : r.paneles.some(pisa)
        ? "animacion"
        : texto.some(pisa)
          ? "texto"
          : r.cta && r.cta.at * FPS < b && (r.cta.at + r.cta.dur) * FPS > a
            ? "cta"
            : "—";
    return { n: i + 1, a, b, trato, encuadre: e.encuadre };
  });
};

/**
 * **Lo que la pieza tiene que decir, comprobado contra lo que de verdad dice.**
 *
 * Jaime, del reel 2: *«el guion deja de lado los puntos comparativos; eso debe
 * quedar claro en el proceso, no es solo el guion, es la intencion
 * comunicativa: si es comparar, entonces las comparaciones deben ser claras»*.
 *
 * El paso 2 ya filtra por esto al elegir la frase de cada etapa, pero elegir no
 * es llegar: entre la eleccion y el montaje hay un recorte de silencios, una
 * interseccion con los tramos de habla y una transcripcion nueva. **Esto se
 * comprueba al final, sobre los subtitulos del montaje**, que son literalmente
 * lo que se oye.
 *
 * Y falla el build. Una comparacion sin sus dos cifras no es una comparacion
 * floja: es otra pieza.
 */
// Suelo de encaje de un segmento en su etapa: por debajo, lo grabado no cabe
// dentro de lo que el guion espera ahi. Es el mismo umbral con que
// `seleccionar.py` admite una candidata, y por eso significa lo mismo en los
// dos sitios.
const ENCAJE = 0.14;
// Y cuanto de lo ALCANZABLE hay que cubrir. Es el mismo criterio relativo con
// que `beats.py` deja competir a una candidata: lo que importa no es el valor
// absoluto, es la distancia al mejor posible.
const RELATIVO = 0.5;

const DICE = (t) =>
  sinTildes(String(t).toLowerCase()).replace(/(?<=\d)[.,](?=\d)/g, "");

const sinTildes = (t) =>
  t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const pal = (t) => sinTildes(t).match(/[a-z]+/g) ?? [];
/**
 * Raiz de cinco letras para emparejar el rotulo con lo que se dice.
 *
 * El rotulo del reel 2 dice «Trabaja mas» y en la toma suena «trabajÓ fines de
 * semana»: distinta persona, misma palabra. Comparando la forma exacta no
 * casaba, asi que el primer emparejamiento caia en «se queda con 44» —por el
 * «queda» del rotulo, que ahi no significa lo mismo— y el rotulo se quedaba
 * puesto 18,5 s.
 *
 * Cinco letras separan «trabaj-» de «trabalenguas» sin exigir conjugacion.
 */
const raiz = (w) => w.slice(0, 5);



/**
 * Tableros: el plano de las explicaciones.
 *
 * Jaime lo pidio literal —«si puedes poner animaciones en las partes que se
 * expliquen cosas asi yo no me vea, es importante»— y resuelve de paso lo otro
 * que dijo, que los cambios de escena se ven raros. Un punch-in cada tres
 * segundos desde una camara fija **es un jump cut**, y los jump cuts son
 * visibles por diseño. La forma clasica de tapar un corte es cortar a otra cosa:
 * b-roll. Aqui el b-roll es el tablero, y ademas explica.
 *
 * El audio sigue corriendo por debajo, asi que la transicion es un L-cut: la voz
 * cruza el corte y la costura no se oye.
 *
 * `ancla` es la palabra sobre la que entra. Se busca en los subtitulos del
 * montaje, asi que el tablero aparece cuando la cifra se dice — no en un
 * segundo fijo que se desincroniza al primer reajuste.
 *
 * **Cumplimiento:** `difference` exige cifra Y fuente juntas, y `condition` es
 * obligatoria. La fuente es la que hay de verdad: el calculo del propio Jaime, o
 * la norma cuando la cifra sale de la norma. No se inventa una autoridad.
 */
/**
 * Cuánto tiene que durar el hueco de un tablero, en frames.
 *
 * **Un componente con horario propio necesita su tiempo.** Los tableros se
 * construyen por tiempo de lectura —cada nodo espera a que el anterior se haya
 * podido leer—, así que un número redondo puesto desde fuera los deja a medio
 * construir: con 5,5 s el `TwoPaths` mostraba sólo la cabecera y el pie, y en
 * el render parecía un tablero vacío cuando lo que estaba era corto de tiempo.
 *
 * Esto replica la cadena de `duracionDe` de cada componente. Es duplicación y
 * se sabe: el spec es Node y los componentes son TSX, y no hay import directo.
 * **Si cambias el horario de un componente, cambia también aquí** — la señal de
 * que se te olvidó es un tablero que aparece incompleto.
 */
const lectura = (t) => Math.max(36, Math.ceil((String(t).trim().split(/\s+/).length / 2.8) * FPS));
/**
 * **La condicion que cabe en pantalla, no la ficha entera.**
 *
 * Jaime, viendo el reel-01 bloqueado: *«lo que hace falta es simplificar el
 * tablero y animarlo mas, reducir la carga cognitiva; para eso son los
 * tableros»*. Y antes: *«ponemos pies de foto con la info complementaria que no
 * cabe en el video»*.
 *
 * El tablero dura lo que cuesta leerlo, y eso esta bien — es lo que impide que
 * un dato pase sin poder leerse. Pero la condicion de la etapa 3 del reel-01
 * llevaba **100 palabras**: una nota de metodo —CCPC, capital gravable, personal
 * services business— escrita para dejar constancia, no para leerse en pantalla.
 * A 2,8 palabras por segundo son 39 s, y el tablero salia de 40,9 s sobre una
 * pieza de 101,5 s. Con eso Jaime se quedaba en 59,7% de cara —el suelo es 60—
 * y sin un segundo limpio en el tercio central, asi que la pieza no se
 * renderizaba **y el motivo que se imprimia era el equivocado**: decia que
 * Jaime no aparecia en mitad, cuando la causa era la letra pequena.
 *
 * Se corta por frases enteras, nunca a mitad de una: una condicion partida dice
 * otra cosa que la condicion. Lo que no entra viaja como `condicion_completa`
 * para el copy, que es donde Jaime dijo que va.
 */
const CONDICION_PALABRAS = 25;
const enPantalla = (t) => {
  const limpio = String(t).trim().replace(/\s+/g, " ");
  if (limpio.split(" ").length <= CONDICION_PALABRAS) return limpio;
  const frases = limpio.match(/[^.!?]+[.!?]*/g) ?? [limpio];
  let salida = "";
  for (const f of frases) {
    const cand = (salida + f).trim();
    if (salida && cand.split(" ").length > CONDICION_PALABRAS) break;
    salida = cand;
  }
  // Si la primera frase ya se pasa, se corta por palabra y se dice que sigue.
  if (!salida) {
    salida = limpio.split(" ").slice(0, CONDICION_PALABRAS).join(" ") + "…";
  }
  return salida;
};
const duracionTarjeta = (p) => {
  // `Tarjeta` encadena: un bloque cada 8 frames, luego el remate, luego el pie.
  const escalon = 8;
  return p.bloques.length * escalon + 6 + p.remate.length * 4 + 4 +
    lectura(p.remate.join(" ")) + (p.pie ? lectura(p.pie) : 0) + 20;
};
/**
 * **Sin tope de 3 s.** Jaime: *«si los tableros duran más de 3 segundos no hay
 * problema, siempre que sean dinámicos y expliquen conceptos»*. La regla de los
 * 3 s es el pulso del CORTE, no del tablero — y un tablero que se construye por
 * tiempo de lectura no está quieto: cada nodo entra cuando el anterior ya se
 * pudo leer. Lo que no se permite es un tablero estático largo.
 *
 * Se le suma un margen para que el último elemento respire antes de irse: con
 * la duración justa, el remate aparecía y desaparecía en el mismo suspiro.
 */
const RESPIRO = 20;
const duracionTablero = (kind, p) => {
  const entrada = 8;
  if (kind === "acumulacion") {
    const tramos = p.tramos.reduce((n, tr) => n + Math.max(entrada + 4, lectura(tr.etiqueta)), 0);
    return entrada * 3 + tramos + lectura(p.condicion) + RESPIRO + 24;
  }
  if (kind === "comparacion") {
    return entrada * 2 + Math.max(20, lectura(p.izquierda.cifra)) +
      Math.max(20, lectura(p.derecha.cifra)) + lectura(p.condicion) +
      RESPIRO + 24;
  }
  // `TwoPaths` y `CausalChain` no publican su horario; 8,5 s es lo medido.
  return Math.round(8.5 * FPS);
};

const TABLEROS = {
  // R1 · Information Gap · el coste de no entenderlo.
  "reel-01": [{
    beat: 3,
    kind: "comparacion",
    props: {
      premisa: "Misma facturación · $180,000",
      // **Cifra en las DOS columnas.** La derecha decía «SE QUEDAN» y Jaime lo
      // señaló: «la comparación no es suficientemente clara». No se puede
      // comparar un número con una frase — el ojo no tiene contra qué medirlo.
      // **La cifra la manda la voz, no el tablero.** La etapa cambio a la toma
      // que entrega —Jaime: *«prima la emocion en la entrega de un mensaje»*—
      // y esa dice «entre 25 mil y 30 mil». Dejar el tablero en 30.000 dejaria
      // la pantalla diciendo una cosa y la voz otra, que es lo unico que la
      // regla de la entrega NO mueve.
      //
      // Y la horquilla no debilita: comprobado contra la CRA, la diferencia
      // sobre 180.000 $ es 33.500 $, asi que 25-30 es conservador por los dos
      // lados. Una cifra redonda suena mas segura y se defiende peor.
      izquierda: {
        titulo: "Sin estructura",
        cifra: "−$25-30K",
        pie: "En impuesto, cada año.",
      },
      derecha: {
        titulo: "Con estructura",
        cifra: "+$25-30K",
        // **Aqui decia «$16,70 de cada $100 facturado» y el numero no era el
        // problema: era lo que la columna dejaba entender.** Enfrentada a un
        // «se van en impuesto, cada ano», un «+$30,000» se lee como ahorro
        // definitivo, y la fuente no sostiene eso.
        //
        // Comprobado contra la CRA: sobre 180.000 $ el impuesto personal en
        // Ontario 2026 es ~55.500 $ y el corporativo al 12,2% es 21.960 $. La
        // diferencia de ESE ano es real —33.500 $, o sea decir 30.000 se queda
        // corto— pero **es diferimiento**: el dinero se queda en la sociedad y
        // paga al salir, porque la integracion iguala la carga al repartir
        // dividendos.
        //
        // La columna izquierda si puede decir «cada ano»: sin estructura eso se
        // paga todos los anos. La derecha no, y por eso solo cambia esta.
        //
        // Y no debilita la pieza: «queda en la empresa» es una promesa mas
        // concreta que «se ahorra», y ademas es la que se puede defender.
        pie: "Quedan en la empresa. Impuesto al sacarlos.",
      },
      // **El dato ancla, por cada $100.** Es como lo pide el canon —«por cada
      // $100 que saca»— y sale de las cifras del propio libreto: 30.000 sobre
      // 180.000 son 16,70 de cada 100. Nada inventado.
      // **La invitación cierra el tablero**, con las palabras de Jaime. Al
      // final de la pieza sobraba —repetía el CTA— y aquí cae bien: se acaba de
      // ver la diferencia y se le devuelve la decisión al espectador.
      remate: "Decida usted qué cuenta le sale mejor",
      fuente: "Cálculo de Jaime Olarte · $30,000 sobre $180,000 de utilidad",
      condicion:
        "Cambia según la utilidad, la provincia y si necesita la caja hoy. Consúltelo con su contador.",
    },
  }],
  // R2 · Two Paths / Default Loss. Este SÍ lleva `TwoPaths`: es el componente
  // de su estructura y es el único reel del lote que la ejecuta.
  "reel-02": [{
    /**
     * **El tablero se queda.** Jaime, aclarando: *«el tablero estaba bien, yo me
     * refiero a la parte anterior, donde se dice el valor retenido por cada 100
     * dolares vendido»*.
     *
     * Son dos cosas distintas y las dos hacen falta: el **contraste animado**
     * (ver `CONTRASTE`) pone las dos cifras encima del plano **cuando la voz las
     * dice**, en los beats 1 y 2, sin quitarle el cuadro; y este tablero, en el
     * beat 3, es donde la comparacion se lee entera con su gap y su fuente. El
     * primero acompana lo que se esta diciendo; el segundo lo cierra.
     *
     * La anatomia es la lamina aprobada -02_Polarizing_Thesis/slide-02-: cinta
     * con la condicion comun, dos columnas con la buena en oro, cinta de remate
     * con el gap y la fuente al pie.
     */
    beat: 3,
    kind: "comparacion",
    props: {
      premisa: "Misma facturación · $180,000",
      izquierda: {
        titulo: "El electricista",
        cifra: "$44",
        pie: "De cada $100 que recibe.",
      },
      derecha: {
        titulo: "El del yate",
        cifra: "$67",
        pie: "Vendiendo exactamente lo mismo.",
      },
      remate: "Gap en cinco años · $189,000",
      fuente: "Cálculo de Jaime Olarte · $21 por cada $100 facturado",
      condicion:
        "Depende de cómo se remunere y de la provincia. No es automático.",
    },
  }, {
    beat: 7,
    kind: "comparacion",
    props: {
      premisa: "Búsquelo en Google",
      izquierda: {
        titulo: "En inglés",
        cifra: "Seminarios",
        pie: "El CRA los publica y los explica.",
      },
      derecha: {
        titulo: "En español",
        cifra: "Uno",
        pie: "Y no está en ninguna plataforma.",
      },
      remate: "La brecha no es de esfuerzo",
      fuente: "Búsqueda pública · CRA, seminarios sobre el T2",
      condicion:
        "Lo que hay disponible cambia con el tiempo. Compruébelo usted mismo antes de darlo por cierto.",
    },
  }],
  // R3 · Polarizing Thesis. La demostración carga el argumento: el 53,53 → 32
  // va en pantalla o el reel es sólo actitud.
  "reel-03": [{
    beat: 3,
    kind: "comparacion",
    props: {
      premisa: "Mismo dueño, misma facturación",
      izquierda: {
        titulo: "Todo por nómina",
        cifra: "53,53%",
        pie: "Marginal, sacándolo como salario.",
      },
      derecha: {
        titulo: "Salario y dividendo",
        cifra: "32%",
        pie: "Con la mezcla calculada.",
      },
      remate: "No es magia. Está en la ley.",
      fuente: "Tasas marginales de Ontario · Income Tax Act",
      condicion:
        "La mezcla correcta depende del caso y exige contador y abogado. No es automático ni aplica a todos.",
    },
  }],
  // R5 · Transformation Story. Dos beats sin toma, y son la consecuencia: la
  // plata quieta y el umbral que cruza.
  "reel-05": [{
    beat: 6,
    kind: "acumulacion",
    props: {
      title: "La plata que se quedó quieta",
      concepto: "Ingreso pasivo",
      horizonte: "Un año fiscal",
      tramos: [
        { etiqueta: "Trimestre normal", alto: 0.3 },
        { etiqueta: "Se queda dentro", alto: 0.28 },
        { etiqueta: "Cruza el umbral", alto: 0.3 },
      ],
      umbral: { etiqueta: "Umbral", en: 0.6 },
      resultado: {
        figure: "$14,300 de más",
        source: "Caso relatado por Jaime Olarte",
      },
      condicion:
        "El umbral depende del ingreso pasivo acumulado y de la provincia. Confírmelo con su contador antes de decidir nada.",
    },
  }],
  // R6 · Impact–Threat–Efficacy. Beat 6: la exposición acumulada a diez años.
  "reel-06": [{
    beat: 6,
    kind: "acumulacion",
    props: {
      title: "La pérdida silenciosa",
      concepto: "Sin estructura",
      horizonte: "Diez años",
      tramos: [
        { etiqueta: "Un año", alto: 0.18 },
        { etiqueta: "Cinco años", alto: 0.3 },
        { etiqueta: "Diez años", alto: 0.42 },
      ],
      resultado: {
        figure: "$250,000–$300,000",
        source: "Cálculo de Jaime Olarte · utilidad de $180,000",
      },
      condicion:
        "No aplica a todos los negocios ni a toda la utilidad, y depende de la provincia. Consúltelo.",
    },
  }],
  // R7 · Polarizing Thesis · el beat que carga el argumento.
  //
  // **La cinta no tiene ni una cifra en 160 s**, y Polarizing Thesis pone
  // «cálculo o evidencia» en la tercera etapa: sin este tablero la pieza es
  // actitud entera. La cifra la aprobó Jaime —*«sí, puede ser lo que
  // propones»*— y son las mismas fuentes que ya sostienen reel-03, no copias:
  // una cifra con dos fichas distintas es una cifra sin ficha.
  //
  // **Tres bloques, no ocho.** Criterio suyo, y está en `docs/canon.md`: *«el
  // tablero es un mecanismo de reducir carga cognitiva, esa es su función:
  // facilitar la decisión»*. La premisa fija lo que NO cambia —la facturación—
  // para que lo único que se lea distinto sean las dos cifras.
  //
  // **Y el 32% se rotula PROYECCIÓN.** No lo publica ninguna fuente: sale de la
  // mezcla salario/dividendos y depende del caso. Rotularlo como dato medido
  // sería exactamente lo que el piso prohíbe.
  "reel-07": [{
    beat: 3,
    kind: "comparacion",
    props: {
      premisa: "Misma facturación · dos estructuras",
      izquierda: {
        titulo: "Todo salario",
        cifra: "53,53%",
        pie: "Tasa marginal en Ontario.",
      },
      derecha: {
        titulo: "Salario + dividendos",
        cifra: "32%",
        pie: "PROYECCIÓN. Exige sociedad incorporada.",
      },
      remate: "La misma plata, dos resultados distintos",
      sound: true,
    },
  }],
};

/**
 * Tarjetas: los beats que **no tienen toma utilizable**.
 *
 * *«A cada estructura le escogemos el mejor, y si no entra bien hacemos un
 * gráfico, así sea sólo palabras.»* Un beat del libreto no se cae por falta de
 * plano: se dibuja.
 *
 * El copy es decisión humana y por eso vive escrito aquí. Lo que NO se escribe
 * a mano es **cuándo entra**: eso se deriva del EDL (ver `anclarBeat`).
 */
/**
 * **Las tarjetas del paso 2, si el paso 2 corrio.**
 *
 * El copy de las etapas que se quedan sin toma lo escribe la IA con su prompt
 * fijo, dentro de los topes de caracteres, y sale en
 * `work/asignacion/reel-NN.json`. Estaba escrito ahi y **no lo leia nadie**: las
 * tarjetas se declaraban a mano aqui, asi que una etapa que el paso 2 mandaba a
 * tarjeta se quedaba sin nada. Es el mismo eslabon roto de C-43, un tramo mas
 * abajo.
 *
 * Lo declarado a mano gana: si una pieza trae su tarjeta escrita en `TARJETAS`,
 * esa se queda. La del paso 2 rellena lo que falte.
 */
const delPaso2 = (slug, estructura) => {
  const f = `work/asignacion/${slug}.json`;
  if (!fs.existsSync(f)) return [];
  const d = JSON.parse(fs.readFileSync(f, "utf8"));
  const total = FRAMES.reels[slug].beats.length;
  const beats = FRAMES.reels[slug].beats;
  return (d.tarjetas ?? [])
    /**
     * **Una etapa declarada `omitir` no lleva tarjeta.**
     *
     * Una tarjeta no trae audio propio: se pinta encima de lo que suena. Con
     * una sola pasa desapercibida, pero con dos o tres seguidas tapan las
     * apariciones de Jaime y el montaje se para -en el reel 3 se comian sus dos
     * ultimas-. Cuando una etapa no tiene toma **y no vale la pena regrabarla**,
     * lo honesto es sacarla de la pieza y decirlo en el frame, no darle una
     * tarjeta que le quita el sitio a otra cosa.
     */
    .filter((t) => !beats[t.etapa_n - 1]?.omitir)
    .map((t) => ({
    beat: t.etapa_n,
    props: {
      framework: estructura,
      beat: [t.etapa_n, total],
      bloques: t.bloques.map((texto) => ({ texto })),
      remate: t.remate,
      pie: t.pie,
    },
  }));
};

const TARJETAS = {
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
 * En qué frame entra la tarjeta de un beat **sin toma**.
 *
 * Los tableros se anclan a una palabra del subtítulo, pero eso aquí no sirve:
 * un beat sin toma no tiene audio, así que no hay palabra a la que agarrarse.
 * Lo que sí hay es el orden — `segmentos` va en el orden de la estructura— así
 * que la tarjeta entra **justo donde empieza el beat siguiente**, que es el
 * sitio que el beat ausente habría ocupado.
 *
 * Se deriva del EDL y no se escribe a mano: al cambiar un corte, la tarjeta se
 * mueve sola. Escrito a mano se desfasa al primer reajuste y no avisa.
 */
/**
 * Cuánto dura la escena de un beat, en frames de la línea final.
 *
 * El tablero **reemplaza esa escena entera**, así que su duración no se calcula
 * por tiempo de lectura: se toma de lo que dura el beat. Jaime: *«en esos cortes
 * el tablero reemplaza la escena, y el tablero es un instrumento pedagógico»*.
 */
function duracionBeat(plan, beat) {
  const suyas = (plan.escenas ?? []).filter((e) => Number(e.beat) === beat);
  if (!suyas.length) return null;
  const t = suyas.reduce((n, e) => n + e.duracion, 0);
  return Math.round((t / VELOCIDAD) * FPS);
}

/** La placa asignada a un beat en `ads/fondos.json`, o `undefined`. */
function placaDe(slug, beat) {
  const placas = JSON.parse(fs.readFileSync("ads/fondos.json", "utf8")).placas;
  return Object.keys(placas).find((k) =>
    (placas[k].sirve ?? []).includes(`${slug}:${beat}`),
  );
}

/**
 * Donde cae un beat **en la linea que se renderiza**, que es el plan.
 *
 * Esto sumaba los segmentos del EDL, y el EDL no es la pieza: `plan-reel`
 * quita el aire de cada corte antes de repartirlo en escenas —regla de Jaime,
 * *«lo de los silencios tambien puede ser aritmetico»*— asi que la imagen corre
 * sobre una linea mas corta que el EDL. En reel-01 la diferencia son 6,83 s.
 *
 * El efecto no es un desfase constante sino uno que **crece**: 0 en el beat 2,
 * 2,08 s en el 4, 4,93 s en el 6, y 6,77 s en el 8 — o sea el cierre se
 * colocaba en el segundo 119,77 de un video que dura 119,32 y se caia fuera.
 * Por el camino, cada tablero entraba cuando el audio ya estaba en otra frase:
 * Jaime lo describio como *«la entrada del tablero sigue hablando de los 500
 * antes de entrar a dar el remate»*, y como glitches y perdida de continuidad.
 *
 * Dos listas describiendo la misma pieza es el aprendizaje 33 otra vez. La que
 * manda es la que se renderiza.
 */
function anclarBeat(plan, beat) {
  const es = plan.escenas ?? [];
  for (const e of es) {
    // Su propio hueco si el beat tiene escena; el del siguiente si no la tiene.
    if (Number(e.beat) >= beat) {
      return Math.round((e.montado_desde / VELOCIDAD) * FPS);
    }
  }
  const u = es[es.length - 1];
  return u ? Math.round(((u.montado_desde + u.duracion) / VELOCIDAD) * FPS) : 0;
}

/**
 * Paneles laterales: se animan EN EL HUECO del plano abierto, sin cortar.
 *
 * Idea de Jaime — «se manda una vez al plano más lejano y en el espacio
 * disponible se anima». El cambio de escena deja de verse porque no hay corte:
 * cambia lo que ocupa el cuadro. Fotomontaje constructivista literal, geometría
 * compuesta CON la fotografía.
 */
/**
 * Paneles laterales: **la entrada del tablero que los desarrolla**.
 *
 * Idea original de Jaime — animar en el hueco del plano abierto, sin cortar. Y
 * su corrección, que es la que ordena esto: *«al segundo 7 pones la estructura,
 * pero si pones eso es porque ahí vas a desarrollar una animación; la siguiente
 * toma es con animación toda completa, luego la siguiente no se siente cortada a
 * las malas»*.
 *
 * Es decir: **un gráfico que aparece es una promesa.** Anunciar un dato y
 * volver al plano sin desarrollarlo deja la promesa colgando, y doce segundos
 * después el tablero llega como si empezara de cero.
 *
 * De ahí la secuencia, que es una sola unidad de tres tiempos:
 *
 *   1. **Anuncia** — el panel entra en el hueco del plano, sin cortar.
 *   2. **Desarrolla** — el tablero toma el cuadro entero y explica.
 *   3. **Devuelve** — al volver, el corte no se siente porque lo que terminó
 *      fue una unidad completa, no un plano interrumpido.
 *
 * Por eso el panel **no se ancla a una palabra**: se ancla a su tablero, y entra
 * `ADELANTO` frames antes. Anclado a una palabra caía donde cayera y la promesa
 * quedaba suelta.
 */
const PANELES = {
  "reel-01": [
    // La estructura que el sistema espera: concepto abstracto, va con imagen.
    { beat: 2, bloques: [
      { texto: "Canadá espera", placa: "c5-convergence" },
      { texto: "una estructura", fuerte: true },
      { texto: "Los que la usan, ganan más", placa: "c3-routes-vertical" },
    ] },
    // Anuncia el tablero del beat 3.
    { beat: 3, bloques: [
      { texto: "Misma facturación", placa: "c7-orbit" },
      { texto: "$30,000", fuerte: true },
      { texto: "al año", placa: "c9-bridge" },
    ] },
    // **Animación detrás del hablante**, sin tablero que anunciar. Jaime:
    // *«desde el segundo 54 hasta entrados al 70 pueden haber animaciones
    // detrás mío, gráficos e imágenes que ejemplifican lo que digo; esto ayuda
    // a mantener la dopamina y la atención»*. Dura el beat entero.
    // El mecanismo: la plata saliendo de la empresa sin perder la mitad. Son
    // 17,7 s de plano sostenido, que es justo donde la atención se cae.
    { beat: 5, bloques: [
      { texto: "De la empresa", placa: "r1-mecanismo" },
      { texto: "a su bolsillo", fuerte: true },
      { texto: "Legal, siguiendo las reglas", placa: "c9-bridge" },
    ] },
    /**
     * **El tramo del asesor.** Jaime: *«buena parte de "su asesor" no tenia ni
     * subs animados ni animaciones por detras, valdria la pena poner algunas»*.
     * Son doce segundos de plano sostenido y era el unico beat del reel sin
     * tratamiento.
     *
     * Y dice el mecanismo **sin reirse de nadie**: el playbook prohibe por
     * nombre ridiculizar a quien transmitio la creencia, asi que el panel
     * separa dos cosas —el ahorro personal y la estructura— en vez de senalar
     * al asesor. La broma de esta pieza es la del precio, y va una por minuto.
     */
    { beat: 4, bloques: [
      { texto: "Le explicaron el ahorro", placa: "c7-orbit" },
      { texto: "No la estructura", fuerte: true },
      { texto: "No es lo mismo", placa: "c9-bridge" },
    ] },
    { beat: 6, bloques: [
      { texto: "21 de septiembre", fuerte: true },
      { texto: "En vivo, en español", placa: "c4-coordination-vertical" },
      { texto: "Dueños en Ontario", placa: "c3-routes-vertical" },
    ] },
  ],
  /**
   * **Reel 2.** No tenia ninguno, y la regla de Jaime es que *«cada video debe
   * tener animaciones por detras del hablante para ejemplificar cada punto»*.
   *
   * Dos, y con horarios distintos a proposito:
   *
   * - **Beat 3 anuncia** el tablero de las dos trayectorias. Un grafico que
   *   aparece es una promesa, asi que entra justo antes y le entrega el cuadro.
   *   No repite el tablero: pone la cifra y deja que el tablero la desarrolle.
   * - **Beat 5 acompana.** Ahi no hay tablero que anunciar, hay algo que
   *   sostener: es la demolicion de la objecion —*«no importa si usted es
   *   blanco, negro, azul o canadiense de quinta generacion»*— y el panel dice
   *   el mecanismo mientras el sigue en cuadro.
   *
   * El beat 6 se queda **sin panel a proposito**: lleva la marca de humanidad
   * («comercio» que se lee FINANZAS) y la regla es un beat, un tratamiento. Dos
   * capas subrayando en el mismo segundo no es enfasis, es ruido.
   */
  "reel-02": [
    { beat: 3, bloques: [
      { texto: "De cada $100", placa: "c7-orbit" },
      { texto: "$21 de diferencia", fuerte: true },
      { texto: "Vendiendo lo mismo", placa: "r2-horizontes" },
    ] },
    { beat: 5, bloques: [
      { texto: "No es de dónde viene", placa: "c3-routes-vertical" },
      { texto: "Es la estructura", fuerte: true },
      { texto: "Nadie se la explicó", placa: "c1-extraction-vertical" },
    ] },
  ],
  /**
   * **Reel 3.** Dos, con los dos horarios del sistema.
   *
   * - **Beat 2 acompana.** Es el mecanismo causal -el contador registra, no
   *   disena- y ahi no hay tablero que anunciar: hay algo que sostener
   *   mientras el sigue en cuadro.
   * - **Beat 3 anuncia** el tablero del calculo. Pone la condicion comun y las
   *   dos vias, y deja las cifras para el tablero: si el panel las diera, el
   *   tablero llegaria a repetir.
   *
   * Y ninguno se rie del contador: *Polarizing Thesis* carga el argumento con
   * la demostracion, no con la actitud, y el playbook prohibe por nombre
   * ridiculizar a quien transmitio la creencia. «Registra» y «disena» son dos
   * oficios, no un bueno y un malo.
   */
  "reel-03": [
    { beat: 2, bloques: [
      { texto: "El contador registra", placa: "c4-coordination-vertical" },
      { texto: "No diseña", fuerte: true },
      { texto: "Son dos oficios", placa: "c5-convergence" },
    ] },
    { beat: 3, bloques: [
      { texto: "Misma facturación", placa: "c1-extraction-vertical" },
      { texto: "Dos formas de sacarla", fuerte: true },
      { texto: "La ley permite las dos", placa: "c2-fragmentation-vertical" },
    ] },
  ],
  "reel-04": [{ beat: 3, bloques: [
    { texto: "El banco ve" },
    { texto: "Sus deudas", fuerte: true },
    { texto: "Nada del negocio" },
  ] }],
  "reel-05": [{ beat: 6, bloques: [
    { texto: "La plata quieta" },
    { texto: "cruzó el umbral", fuerte: true },
    { texto: "y cobró de más" },
  ] }],
};

/**
 * Cuánto entra el panel antes que su tablero.
 *
 * **Se calcula por bloque, no es fijo.** Con 1,6 s los tres letreros entraban
 * encima unos de otros y no daba tiempo a leer ninguno — Jaime: *«los números
 * que salen en el segundo 17 se pierden porque el tablero aparece muy rápido;
 * cada letrero se debe ver»*.
 *
 * 0,75 s por bloque más medio segundo de respiro antes de que el tablero tome
 * el cuadro.
 */
const ADELANTO = (bloques) => Math.round((bloques.length * 0.75 + 0.5) * FPS);

/**
 * **La marca de humanidad**, declarada en `ads/frames.json` bajo `senala`.
 *
 * Dos capas de una sola marca, no dos marcas:
 *
 * - **El subtitulo dice lo que ES**, no lo que se oye. Jaime: *«no pones lo
 *   mismo que yo digo sino lo que esta bien y lo amplias, de manera que la
 *   contradiccion se note y sea una especie de burla»*. Se oye «550», se lee
 *   **$576**.
 * - **El plano se va a blanco y negro** mientras dura, si la marca lo pide.
 *
 * **Y es CORTA a proposito.** El tope sale del propio `senala` y ronda 1,6 s,
 * porque el desliz suele no cambiar nada — Jaime, sobre esa cifra: *«esos
 * dolares no cambian absolutamente nada del mensaje»*. Una marca larga sobre un
 * desliz trivial hace que parezca grave: el espectador concluye que la cifra
 * estaba mal y la broma trabaja contra el argumento. El chiste vive de que sea
 * breve.
 *
 * Tasa: **una o dos por minuto**, y en piezas de 80-90 s eso es UNA. Por eso
 * `senala` es un objeto y no una lista.
 */
const FRAMES = JSON.parse(fs.readFileSync("ads/frames.json", "utf8"));

/**
 * **Las ideas fuerza.** La frase clave de un beat crece en el subtítulo cuando
 * se dice.
 *
 * Es el tratamiento de los beats que **afirman, provocan o prometen**: ahí la
 * fuerza está en la voz y el texto sólo marca dónde cae el golpe. Frente a un
 * tablero es más barato —no roba el plano— y frente a nada, sostiene la
 * atención en el tramo en que sólo hay una cara hablando.
 *
 * Se busca dentro de la ventana del beat, no en toda la pieza: la misma frase
 * puede repetirse y sólo debe realzarse donde ese beat la dice.
 */
/**
 * De un corte del EDL a **donde acaba en la pieza montada**, en segundos.
 *
 * Hace falta porque son dos lineas distintas: `plan-reel` quita el aire de cada
 * corte antes de repartirlo en escenas, asi que el reloj del EDL corre por
 * delante del de la imagen —6,83 s de mas al final de reel-01—. Todo lo que se
 * coloca por tiempo tiene que traducirse, o entra tarde y creciendo.
 *
 * Se traduce por CONTENIDO, no por indice: las escenas del plan llevan de que
 * trozo de cinta nacen, asi que el final del corte `i` es el final montado de
 * su ultima escena.
 */
function finMontado(plan, edl, i) {
  const [a, b] = edl.segmentos[i];
  let fin = null;
  for (const e of plan.escenas ?? []) {
    if (e.origen_desde >= a - 0.05 && e.origen_hasta <= b + 0.05) {
      fin = e.montado_desde + e.duracion;
    }
  }
  return fin;
}

function ideasFuerza(slug, edl, plan, captions) {
  const marco = FRAMES.reels[slug];
  const ventanas = [];
  const det = edl.detalle ?? [];
  /**
   * **La ventana es la del plan.** Esto acumulaba las duraciones del EDL y las
   * cruzaba con `captions`, que salen de transcribir el video ya montado: dos
   * relojes distintos, asi que el realce caia sobre la frase de al lado. Aqui
   * se toma el hueco real del beat en la pieza.
   */
  const porBeat = new Map();
  for (const e of plan.escenas ?? []) {
    const b = Number(e.beat);
    const v = porBeat.get(b);
    if (v) v.hasta = Math.max(v.hasta, e.montado_desde + e.duracion);
    else porBeat.set(b, { desde: e.montado_desde,
                          hasta: e.montado_desde + e.duracion });
  }
  for (const [b, v] of porBeat) {
    const frase = marco.beats[b - 1]?.idea_fuerza;
    if (!frase) continue;
    ventanas.push({
      desde: Math.round((v.desde / VELOCIDAD) * FPS),
      hasta: Math.round((v.hasta / VELOCIDAD) * FPS),
      frase,
    });
  }
  void det;
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
 * ## Y no siempre la lleva el subtitulo
 *
 * En el reel 1 el «550» se dice en 73,7 y el CTA entra en 69,7 — la tarjeta
 * tapa la cara y los subtitulos, asi que el chiste se emitia debajo de ella y
 * no lo veia nadie. No es un fallo de posicion: **el precio se dice DENTRO del
 * CTA porque el precio ES el CTA**, y la tarjeta ya tiene su fila de precio.
 *
 * Asi que cuando la frase marcada cae en la ventana del CTA, la correccion se
 * pinta en la fila de precio de la tarjeta —tachado lo dicho, ampliado lo
 * cierto— y el subtitulo no la duplica. Dos capas diciendo el mismo chiste en
 * el mismo segundo no es enfasis, es ruido (aprendizaje 38).
 *
 * @returns `captions` con la marca puesta donde toque, `desatura` con las
 *   ventanas de blanco y negro, y `enCta` si se la queda la tarjeta.
 */
function marcaDeHumanidad(slug, captions, cta) {
  const m = FRAMES.reels[slug]?.senala;
  if (!m) return { captions, desatura: [], enCta: null };
  const tope = Math.round((m.maximo_s ?? 1.6) * FPS);
  // **Solo la PRIMERA aparicion.** Si la palabra vuelve, la broma se repite y
  // deja de serlo — y la tasa se dispara sin que nadie lo haya decidido.
  let hecha = false;
  let enCta = null;
  const desatura = [];
  const out = captions.map((c) => {
    if (hecha || !c.text.toLowerCase().includes(m.dice.toLowerCase())) return c;
    hecha = true;
    // Dentro del CTA la lleva la tarjeta, no el subtitulo.
    if (cta && c.at >= cta.at * FPS) {
      enCta = { dice: m.dice, es: m.es };
      // Y **sin blanco y negro**: la tarjeta tapa el plano, asi que desaturar
      // no se veria — y aplicado a la tarjeta se llevaria por delante el oro
      // del numero, que es lo unico que hace el chiste. Un efecto que no se ve
      // es peor que no ponerlo: queda declarado y nadie sabe que no corre.
      return c;
    }
    if (m.blanco_y_negro) {
      desatura.push({ at: c.at, duration: Math.min(c.duration, tope) });
    }
    return { ...c, corrige: { dice: m.dice, es: m.es } };
  });
  if (!hecha) {
    console.error(
      `  ojo: ${slug} declara senalar «${m.dice}» y no aparece en los ` +
      `subtitulos. O el montaje ya no lleva esa frase, o cambio el texto.`,
    );
  }
  return { captions: out, desatura, enCta };
}

/** Frame en que entra un tablero: la primera vez que se dice su ancla. */
/**
 * **El subtitulo compuesto**: dos renglones, dos fuentes, dos superficies.
 *
 * Peticion de Jaime: *«el cc tambien puede ser grande, o compuesto —una frase
 * luego otra abajo— con dos fuentes y con mas colores. De esa manera los
 * animamos»*. Ver `Compuesta` en `CaptionBand.tsx` para la parte grafica.
 *
 * Aqui vive la decision de **cual** se compone, y se deriva; no se escribe a
 * mano por pieza. Tres condiciones, y las tres tienen motivo:
 *
 * 1. **Cierra una idea.** Solo se compone la cue que termina en punto. Es la
 *    frase que aterriza, y ademas quedan espaciadas solas —una cada tres o
 *    cuatro segundos— sin necesidad de una cuota inventada. Componer todas
 *    seria gritar toda la pieza; alternar por turnos seria arbitrario.
 * 2. **Es la unica capa de texto del instante.** Con un tablero, una tarjeta o
 *    un panel escribiendo, el subtitulo se queda plano: dos capas subrayando
 *    lo mismo en el mismo segundo no es enfasis, es ruido.
 * 3. **Cabe.** El remate va en Anton versales; por encima de 34 caracteres el
 *    cuerpo cae por debajo del minimo de subtitulo y deja de ser un remate.
 *
 * Y **no se compone lo que ya lleva tratamiento**: la correccion que se burla y
 * la idea fuerza tienen su propia animacion dentro del renglon.
 */
const CONJUNCION = new Set([
  "y", "o", "ni", "pero", "porque", "que", "para", "sin", "con", "cuando",
  "si", "aunque", "mientras", "como", "donde", "hasta", "desde", "sino",
]);

/** Oro **solo donde hay algo que mirar**: una cifra o una fecha. El resto,
 *  navy. El oro decorativo esta prohibido por nombre. */
const CIFRA = /\d|\$|(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)/i;

function partirFrase(texto, preferido) {
  const t = texto.trim();
  const w = t.split(/\s+/).filter(Boolean);
  // Por encima de 62 caracteres no hay reparto que quepa en dos renglones.
  if (t.length > 62) return null;

  const medio = w.length / 2;
  const dentro = (i) => i >= 1 && i <= w.length - 1;

  const arma = (i, tinte) => {
    const arriba = w.slice(0, i).join(" ");
    const abajo = w.slice(i).join(" ");
    // **No se parte detras de una palabra de funcion**: ahi la frase cuelga y
    // el renglon de abajo -que va grande y en versales- deja de ser un remate
    // para ser un fragmento. Misma regla que decide que cue se compone.
    if (COLGANTE.has(ultimaPalabra(arriba))) return null;
    // El remate tiene que ser un remate: ni una palabra suelta ni un parrafo.
    if (abajo.length < 5 || abajo.length > 34) return null;
    // Y el de arriba tampoco puede ser un parrafo: por encima de 40 caracteres
    // envuelve a tres renglones y el bloque sube hasta la cara.
    if (arriba.length < 4 || arriba.length > 40) return null;
    return { arriba, abajo, tinte };
  };

  if (w.length >= 3) {
    /**
     * **La juntura preferida: donde acababa una cue y empezaba la otra.**
     *
     * Cuando dos cues se juntan para dar tiempo al remate, el sitio por el que
     * partir ya lo eligio whisper al trocear: ahi hubo una pausa. Es la misma
     * razon por la que una frontera de tramo de habla se considera limpia por
     * definicion (aprendizaje 19).
     */
    if (dentro(preferido ?? -1)) {
      const par = arma(preferido, CIFRA.test(w.slice(preferido).join(" ")) ? "gold" : "navy");
      if (par) return par;
    }
    /**
     * **Si hay una cifra, la cifra manda donde se parte.**
     *
     * El canon reserva el oro a lo que el espectador debe mirar, y en una frase
     * hablada eso es el numero. Partiendo justo antes, la cifra encabeza el
     * renglon de abajo y se lleva la superficie dorada: el subtitulo se compone
     * **alrededor del dato**, que es lo que hacen las laminas del canon.
     */
    const cifra = w.findIndex((x) => /\d/.test(x));
    if (dentro(cifra)) {
      const oro = arma(cifra, "gold");
      if (oro) return oro;
    }
    const comas = w.map((x, i) => (x.endsWith(",") ? i + 1 : -1)).filter(dentro);
    const conj = w
      .map((x, i) => (CONJUNCION.has(x.toLowerCase().replace(/[^a-zñáéíóú]/gi, "")) ? i : -1))
      .filter(dentro);
    /**
     * Se prueban **todas** las junturas, de la mas centrada hacia fuera, y vale
     * la primera que da dos mitades legibles. Quedarse solo con la mas centrada
     * costaba remates por un caracter.
     */
    const cand = (comas.length ? comas : conj.length ? conj : [Math.round(medio)])
      .slice()
      .sort((x, y) => Math.abs(x - medio) - Math.abs(y - medio));
    for (const corte of cand) {
      const par = arma(corte, CIFRA.test(w.slice(corte).join(" ")) ? "gold" : "navy");
      if (par) return par;
    }
  }

  /**
   * **La otra forma: grande, de un solo renglon.**
   *
   * Jaime da las dos: *«el cc tambien puede ser GRANDE, O compuesto una frase
   * luego otra abajo»*. Una frase corta no se puede partir sin dejar
   * fragmentos, pero entera en Anton versales ocupa el ancho de la banda y **es**
   * el golpe: «POR SUPUESTO.» son dos palabras y a cuerpo 128 cierran el beat.
   *
   * Va **despues** del reparto y no antes: si la frase admite dos renglones, dos
   * renglones dicen mas. Y no depende del numero de palabras -eso bloqueaba las
   * de dos, que son justo las que mejor funcionan aqui.
   */
  return t.length >= 10 && t.length <= 30
    ? { arriba: "", abajo: t, tinte: CIFRA.test(t) ? "gold" : "navy" }
    : null;
}

/**
 * **Palabras que dejan la frase colgando.**
 *
 * Es el filtro que separa un remate de un fragmento, y sale de mirar los dos
 * casos reales. «PIERDA LA MITAD EN IMPUESTOS» era un fragmento peligroso -dice
 * lo contrario que la frase: la completa es *«sin que se pierda la mitad en
 * impuestos»*- y «POR SUPUESTO.» es un remate perfectamente bueno. La diferencia
 * no esta en el trozo: esta en **como acaba lo que va justo antes**.
 *
 * Delante del fragmento malo hay «sin que se»; delante del bueno, «reglas». Una
 * preposicion, un articulo, una conjuncion o un cliticos **abren una dependencia
 * que la palabra siguiente tiene que cerrar**, asi que cortar ahi parte una
 * unidad sintactica. Detras de un sustantivo o de un verbo pleno, no.
 *
 * Es una lista cerrada y por eso es fiable: el espanol tiene muchas palabras de
 * contenido y muy pocas de funcion.
 */
const COLGANTE = new Set(
  JSON.parse(fs.readFileSync("scripts/colgantes.json", "utf8")).palabras,
);

const ultimaPalabra = (t) =>
  sinTildes(String(t).trim().toLowerCase()).replace(/[^a-z]+$/, "").split(/\s+/).pop() ?? "";

/**
 * **El remate compuesto.** Ver `Compuesta` en `CaptionBand.tsx` para la parte
 * grafica; aqui vive la decision de cual se compone, y se deriva.
 *
 * Cuatro condiciones, y las cuatro tienen un caso detras:
 *
 * 1. **Cierra una idea** — la cue termina en punto. Es la frase que aterriza, y
 *    ademas quedan espaciadas solas sin necesidad de una cuota inventada.
 * 2. **No cuelga de la anterior.** La cue de antes no puede acabar en palabra de
 *    funcion. Es lo que distingue «POR SUPUESTO.» de «PIERDA LA MITAD EN
 *    IMPUESTOS», que dice lo contrario que la frase de la que sale (C-23).
 * 3. **Es la unica capa de texto del instante.** Con tablero, tarjeta, panel,
 *    rotulo o CTA en cuadro, el subtitulo se queda plano: dos capas subrayando
 *    lo mismo no es enfasis, es ruido.
 * 4. **Cabe.** El remate va en Anton versales y por encima de 34 caracteres el
 *    cuerpo cae por debajo del minimo de subtitulo.
 *
 * Se intento agrupar por oracion entera en vez de por cue, para tener mas
 * contexto, y salio peor: las oraciones habladas rondan los 180 caracteres, asi
 * que casi ninguna cabia y el reel 1 se quedo con dos remates en 81 s. **La cue
 * es la unidad correcta; lo que faltaba era mirar la de al lado.**
 */
function componer(captions, ocupado, ventanas) {
  const orden = captions.slice().sort((x, y) => x.at - y.at);
  const anterior = new Map();
  orden.forEach((c, i) => anterior.set(c, i ? orden[i - 1] : null));

  const libre = (c) => {
    if (c.realza || c.corrige) return false;
    if (!/[.!?]$/.test(c.text.trim())) return false;
    const prev = anterior.get(c);
    if (prev && COLGANTE.has(ultimaPalabra(prev.text))) return false;
    // Por mayoria, no por roce: una cue perdia su remate por solapar 0,2 s con
    // el final de un panel.
    const tapado = ocupado.reduce(
      (n, b) =>
        n + Math.max(0, Math.min(c.at + c.duration, b.at + b.duration) - Math.max(c.at, b.at)),
      0,
    );
    return tapado <= c.duration / 2;
  };

  /**
   * **Un remate necesita tiempo para leerse.**
   *
   * «POR SUPUESTO.» salio a cuerpo 128 y **no se vio**: su cue dura 1,20 s y la
   * entrada se lleva 0,33, asi que quedaban ocho decimas. Jaime lo dijo con esas
   * palabras — *«no se vio la tarjeta del de manera legal y siguiendo las
   * reglas»*.
   *
   * Cuando la cue que cierra la frase es corta, **se junta con la anterior** y
   * el remate hereda la suma de las dos. Y no hay que buscar por donde partir:
   * la frontera entre las dos cues es justo el sitio, porque ahi hubo una pausa
   * real. De «manera legal, siguiendo las reglas» + «por supuesto.» sale
   * exactamente lo que Jaime echaba en falta, y con 4,0 s en pantalla en vez de
   * 1,2.
   */
  const MIN_REMATE = 48;

  /** La unidad componible de una cue: ella sola, o con la anterior pegada. */
  const unidad = (c) => {
    const prev = anterior.get(c);
    const corto = c.duration < MIN_REMATE;
    if (
      corto &&
      prev &&
      !prev.realza &&
      !prev.corrige &&
      !/[.!?]$/.test(prev.text.trim())
    ) {
      /**
       * **Aqui NO se mira si la anterior cuelga**, y es deliberado: al juntar
       * dos cues la continuacion se la come el renglon de arriba, que va
       * pequeno y en caja mixta y se lee como lo que es —la frase siguiendo—.
       * Lo que no puede colgar es el remate, y de eso se encarga `arma()`.
       *
       * Costaba justo el caso que Jaime pidio: delante de «manera legal,
       * siguiendo las reglas» hay «...en impuestos de», que cuelga, asi que la
       * comprobacion tumbaba el remate entero por una palabra que iba a quedar
       * en el renglon de arriba.
       */
      const texto = `${prev.text.trim()} ${c.text.trim()}`.replace(/\s+/g, " ");
      const corte = prev.text.trim().split(/\s+/).filter(Boolean).length;
      const par = partirFrase(texto, corte);
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
    const par = partirFrase(c.text);
    return par
      ? { cues: [c], at: c.at, duration: c.duration, text: c.text, compuesto: par }
      : null;
  };

  const elegidas = [];
  for (const [a, b] of ventanas) {
    const dentro = orden.filter((c) => c.at >= a && c.at < b);
    /**
     * **Una etapa, un remate** — dos si la etapa pasa de 12 s, separados 5 s.
     * Un beat de 17,7 s hace mas trabajo que uno de 4 y aguanta dos golpes.
     *
     * Y la cifra se cuela delante: *«con mas colores»* es la mitad de lo que
     * pidio Jaime, y el oro es el unico color que el canon deja usar por
     * significado.
     */
    const cupo = b - a > 12 * FPS ? 2 : 1;
    const candidatas = dentro
      .map((c, i) => ({ c, i, oro: partirFrase(c.text)?.tinte === "gold" }))
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
    if (u) salida.push({ at: u.at, duration: u.duration, text: u.text, compuesto: u.compuesto });
    else if (!dentroDeUnidad.has(c)) salida.push(c);
  }
  return { captions: salida, n: elegidas.length };
}

function anclarTablero(captions, ancla) {
  for (const c of captions) {
    if (pal(c.text).includes(ancla) || c.text.includes(ancla)) return c.at;
  }
  return null;
}

/**
 * La base de decisiones, para leer la descripción de cada escena.
 *
 * Se abre una vez para todo el lote: son 54 filas y abrir por pieza es abrir
 * seis veces lo mismo.
 */
const db = new DatabaseSync("ads/decisiones.db");

/**
 * Lo que un camino exige y no se cumple. **No se acumula en silencio**: se
 * imprime al final y el paso sale con código 1, que es lo que convierte una
 * indicación escrita en una indicación que se cumple.
 */
const faltas = [];

/**
 * **La pieza para aprobar va sin música y sin efectos.**
 *
 * Jaime: *«los vídeos para aprobación van sin música y sin audio adicional, no
 * los necesitamos, y será más fácil con el audio final y definitivo, menos
 * retrabajo»*.
 *
 * Masterizar música sobre un corte que todavía puede cambiar es pagarlo dos
 * veces, y para juzgar si el mensaje llega el acompañamiento estorba más que
 * ayuda.
 *
 * Lo decide **el estado de la versión**, no una bandera que alguien recuerde
 * poner: mientras no esté aprobada sale sólo la voz, y en cuanto lo está la
 * misma línea la monta con música y efectos.
 */
const aprobadas = (() => {
  try {
    const db = new DatabaseSync("ads/decisiones.db");
    return new Set(
      db
        .prepare(
          "select v.slug from aprobacion a" +
            " join version ve on ve.id = a.version_id" +
            " join video v on v.id = ve.video_id" +
            " where a.veredicto = 'aprobada'",
        )
        .all()
        .map((r) => r.slug),
    );
  } catch {
    return new Set();
  }
})();

const spec = Object.entries(LINEAS).map(([slug, lineas]) => {
  const edl = JSON.parse(fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"));
  const words = JSON.parse(
    fs.readFileSync(`work/transcripts/${TOMA[slug]}.json`, "utf8"),
  ).segmentos;

  const plan = JSON.parse(
    fs.readFileSync(`work/scenes/${slug}/plan-full.json`, "utf8"),
  );
  // Duracion prevista por el PLAN. Sirve de referencia, no de verdad.
  /**
   * Lo previsto sale del PLAN, no del EDL.
   *
   * El EDL es la intención; el plan ya descontó el silencio interno que
   * `conHabla()` quita al cortar, y eso son décimas que el EDL no conoce. Con
   * nueve escenas la tolerancia por redondeo bajó a 0,3 s y el aviso saltaba
   * por una diferencia que no es un desfase: es el aire quitado.
   *
   * Es el mismo patrón de C-05 — comparar dos magnitudes que no son la misma
   * cosa — y la tercera vez que aparece. El plan es lo que se cortó.
   */
  const previsto =
    plan.escenas.reduce((t, e) => t + e.duracion, 0) / VELOCIDAD;

  /**
   * **La duracion sale del video cortado, no del EDL.**
   *
   * Eran dos fuentes para el mismo dato y se separaban en cuanto el EDL cambiaba
   * despues de cortar. La composicion pedia entonces frames que no existen, y
   * Remotion **no dice eso**: se queda esperando a que la pagina pinte un frame
   * imposible y aborta con un timeout de 33 s a mitad del render. Costo un lote
   * entero entender que el error no era de rendimiento.
   *
   * El video es la verdad —es lo que se va a ver— y el EDL, la intencion. Si
   * discrepan se avisa, pero se renderiza contra lo que hay.
   */
  const mp4 = `public/${slug}.mp4`;
  if (!fs.existsSync(mp4)) {
    throw new Error(`falta ${mp4}: hay que cortar antes de generar el spec`);
  }
  const duracion = Number(
    execFileSync("ffprobe", [
      "-v", "error", "-show_entries", "format=duration",
      "-of", "csv=p=0", mp4,
    ]).toString().trim(),
  );
  /**
   * Aviso de corte viejo, **descontando la deriva normal**.
   *
   * Cada escena se codifica a frame entero, asi que cada una puede sumar hasta
   * 1/30 s. Con treinta escenas eso es un segundo de diferencia que NO significa
   * nada: el corte esta bien, solo redondea. Avisar de eso hacia saltar la
   * alarma en piezas correctas — y una alarma que suena siempre deja de leerse.
   *
   * Lo que si importa es que el corte se quede **corto**: ahi la composicion
   * pide frames que no existen y el render muere en un timeout.
   */
  const deriva = plan.escenas.length / 30;
  if (duracion + 0.1 < previsto - deriva) {
    console.error(
      `  ojo: ${slug} el corte (${duracion.toFixed(2)}s) es MAS CORTO que el ` +
      `EDL (${previsto.toFixed(2)}s): el corte esta viejo y el render fallara`,
    );
  } else if (duracion > previsto + deriva + 0.5) {
    console.error(
      `  ojo: ${slug} el corte (${duracion.toFixed(2)}s) sobra sobre el EDL ` +
      `(${previsto.toFixed(2)}s) mas de lo que explica el redondeo`,
    );
  }

  // Subtitulos: salen de `work/subs/todos.json`, que produce `subtitular.py`
  // transcribiendo el reel YA MONTADO.
  //
  // Antes se derivaban del transcript del bruto mapeado a la linea de tiempo, y
  // eso heredaba sus fallos: palabras estiradas que cruzan silencios eliminados
  // y tramos donde al transcript le faltan palabras. En el reel 6 se comia media
  // frase de apertura. Lo montado no tiene ese problema — es lo que se oye.
  const subs = fs.existsSync("work/subs/todos.json")
    ? JSON.parse(fs.readFileSync("work/subs/todos.json", "utf8"))
    : {};
  const captions = subs[slug] ?? [];
  if (!captions.length) {
    console.error(`  ojo: ${slug} sin subtitulos — falta correr subtitular.py`);
  }

  // Cuando se termina de decir la frase del rotulo.
  const clave = new Set(
    lineas.flatMap(pal).filter((w) => w.length > 3).map(raiz),
  );
  // Cuando EMPIEZA a decirse la frase, no cuando termina.
  //
  // El rotulo entraba en el frame 0 y decia lo que la voz iba a decir cinco
  // segundos despues: para cuando llegaba la frase, el remate ya estaba
  // gastado. Ahora entra EN la palabra, asi que subraya en vez de anunciar.
  //
  // La PRIMERA aparicion, no la ultima: si la frase vuelve mas adelante —en el
  // reel 6 vuelve— el rotulo llegaria tardisimo.
  let entra = null;
  for (const c of captions) {
    if (entra === null && pal(c.text).some((p) => clave.has(raiz(p)))) {
      entra = c.at;
    }
  }
  // Si la frase no suena en la apertura, el rotulo entra al principio: es un
  // gancho y su sitio son los primeros segundos.
  if (entra === null || entra / FPS > APERTURA) entra = 0;


  /**
   * **Sólo donde el beat NO tiene toma.** La tarjeta es lo que sustituye a un
   * plano que no existe; si el beat tiene audio, ponerla encima es taparlo.
   *
   * Faltaba esta comprobación y se veía en el reel 1: el beat 5 llevaba tarjeta
   * de cuando no tenía toma, y al corregirlo —ahora sí la tiene— la tarjeta
   * siguió puesta, tapando el plano y de paso la costura, que se quedó sin su
   * glitch porque el spec la daba por cubierta.
   */
  const conToma = new Set(
    (edl.detalle ?? []).filter((u) => u.texto).map((u) => u.beat),
  );
  // Lo declarado a mano manda; el paso 2 rellena las etapas que falten.
  const aMano = TARJETAS[slug] ?? [];
  const cartas = [
    ...aMano,
    ...delPaso2(slug, FRAMES.reels[slug].estructura).filter(
      (t) => !aMano.some((m) => m.beat === t.beat),
    ),
  ]
    .filter((t) => !conToma.has(t.beat))
    .map((t) => ({
      at: anclarBeat(plan, t.beat),
      /**
       * **La tarjeta no se come el beat sobre el que cae.**
       *
       * Jaime: *«no quitar partes ni poner partes»*. Una etapa sin audio no se
       * saca de la pieza —eso es quitar una parte— pero su tarjeta tampoco
       * puede tapar entera la etapa siguiente: en el reel 3 los 9 s de la
       * demolicion se comian los tres beats finales y la pieza acababa sin
       * Jaime en cuadro.
       *
       * Se acota a **la mitad** del beat en el que aterriza. Si con eso baja de
       * lo que tarda en leerse, se dice por consola: una tarjeta que no da
       * tiempo a leer no esta en la pieza aunque este en el frame, y eso es una
       * decision de material, no de montaje.
       */
      duration: (() => {
        const quiere = duracionTarjeta(t.props);
        const a0 = anclarBeat(plan, t.beat);
        const a1 = anclarBeat(plan, t.beat + 2);
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
    /**
     * **Las tarjetas hacen cola, no se apilan.**
     *
     * Varios beats seguidos sin material se anclan todos donde empieza el
     * primero que si lo tiene, asi que salian los tres en el mismo frame,
     * pintados uno encima de otro: solo se veia el ultimo y las otras dos
     * etapas no existian. En el reel 3 pasaba con los beats 4, 5 y 6.
     *
     * Van en el orden del argumento, cada una cuando acaba la anterior. Es la
     * misma correccion que C-48 hizo entre tarjeta y tablero, ahora entre
     * tarjetas.
     */
    .sort((x, y) => x.at - y.at || x.props.beat[0] - y.props.beat[0])
    .map((t, i, todas) => {
      const previa = todas[i - 1];
      return previa && previa.at + previa.duration > t.at
        ? { ...t, at: previa.at + previa.duration }
        : t;
    });
  /**
   * **Una tarjeta y un tablero no pueden empezar en el mismo frame.**
   *
   * Un beat sin material se ancla donde empieza el siguiente -no tiene sitio
   * propio- y si ese siguiente lleva tablero, los dos ocupan el cuadro entero
   * a la vez: se pintan uno encima del otro y la tarjeta no existe. En el reel
   * 2 la del beat 2 y el tablero del beat 3 salian los dos en 6,9 s.
   *
   * La tarjeta va primero -es el beat anterior- y el tablero entra cuando ella
   * termina, que ademas es el orden del argumento.
   */
  const empujaTablero = (at) =>
    cartas.reduce(
      (t, c) => (c.at <= t && t < c.at + c.duration ? c.at + c.duration : t),
      at,
    );

  /**
   * El pie del tablero, **de la fuente comprobada y no de una cadena a mano**.
   *
   * `TABLEROS` trae `fuente` y `condicion` escritas aqui, una por pieza. Es la
   * trampa que `fuentes.py` vino a quitar —no escala a 16-50 anuncios y no se
   * puede auditar— y era el ultimo tramo sin conectar: el paso ya guardaba el
   * respaldo en `dato`, y el tablero seguia imprimiendo el literal.
   *
   * Importa mas de lo que parece por lo que decia cada uno. El literal era
   * *«$30,000 sobre $180,000 de utilidad»*, que es de donde sale la resta pero
   * no de donde sale la verdad. Comprobado contra la CRA, la diferencia real es
   * 33.500 $ y —esto es lo que cambia el mensaje— **buena parte es
   * diferimiento**: mientras el dinero se queda en la sociedad se paga menos, y
   * al repartirlo como dividendo la integracion iguala la carga. Sin esa
   * condicion el espectador entiende «me ahorro 30.000 al ano», y eso la fuente
   * no lo sostiene.
   *
   * Si no hay dato comprobado se deja lo que hubiera: una pieza sin verificar
   * no se queda muda de golpe.
   */
  /**
   * **El pie lleva la fuente Y la condicion, y por eso admite `parcial`.**
   *
   * Solo pintaba las cifras marcadas `si`, o sea las que se sostienen sin
   * matices — y las que mas necesitan pie son justo las otras: las que son
   * ciertas **bajo una condicion**. Una cifra asi sin su condicion es peor que
   * no ponerla, porque parece general.
   *
   * Regla de Jaime, y es la misma que ya aplico a los redondeos: *«si esa parte
   * no se sostiene, la aclaramos en pie de foto»*. No se cambia la toma ni se
   * quita el numero: se dice al pie que hace falta para que sea verdad.
   */
  const pieDe = (beat) => {
    try {
      const r = db.prepare(
        "select f.rotulo, d.condiciones from dato d" +
        "  left join fuente f on f.id = d.fuente_id" +
        "  join video v on v.id = d.video_id" +
        " where v.slug = ? and d.etapa_orden = ?" +
        "   and d.respalda in ('si','parcial')" +
        " order by length(d.cifra) desc limit 1",
      ).get(slug, beat);
      if (!r) return {};
      const out = {};
      if (r.rotulo) out.fuente = String(r.rotulo);
      if (r.condiciones) {
        const entera = String(r.condiciones);
        out.condicion = enPantalla(entera);
        // Lo que no cabe NO se tira: viaja en el spec para el copy del video.
        if (out.condicion !== entera) out.condicion_completa = entera;
      }
      return out;
    } catch {
      return {};
    }
  };

  const tableros = (TABLEROS[slug] ?? [])
      .map((b) => {
        b = { ...b, props: { ...b.props, ...pieDe(b.beat) } };
        // **Por beat, no por palabra.** Anclar a una palabra del subtítulo no
        // puede funcionar en un beat sin toma: no hay audio, así que no hay
        // palabra. Y en los que sí la tienen, la palabra puede no aparecer en
        // el montaje final — de seis tableros anclaban dos. El orden del EDL
        // siempre está.
        const at = empujaTablero(anclarBeat(plan, b.beat));
        return at === null
          ? null
          : (() => {
            // La escena entera, o el horario mínimo si el beat no tiene toma.
            // La escena entera MÁS el solape que tapa la costura siguiente.
            // La escena entera MAS el solape que tapa la costura siguiente,
            // **sin pasarse del final de la composicion**: si se pasa, Remotion
            // recorta el `<Sequence>` en silencio y el tablero desaparece a
            // media construccion sin que nadie se entere.
            const fin = Math.round(duracion * FPS);
            // **Un tablero sustituye SU escena, no el final de la pieza.**
            //
            // Cuando `duracionBeat` no encontraba el beat caía en el horario
            // propio del componente, y el `Math.min` sólo lo recortaba contra
            // el final de la composición: el tablero se estiraba hasta ahí. En
            // reel-06 ocupaba de 56,4 a 86,2 s —treinta segundos, con el CTA
            // debajo— y la comprobación de presencia bloqueaba la pieza
            // diciendo que Jaime no aparecía al final. Tenía razón: no aparecía
            // porque había un tablero encima.
            //
            // El tope duro es el arranque del CTA: la tarjeta lleva su propio
            // cuadro y un tablero por debajo no lo ve nadie.
            // **El tablero dura lo que cuesta leerlo, no lo que dura el beat.**
            //
            // Esto tomaba la duracion del beat y solo caia en el tiempo de
            // lectura cuando el beat no existia. Mientras la voz decia la
            // comparacion entera daba igual; en cuanto la etapa 3 del reel-01
            // paso a la toma corta —9,4 s de voz, 6,5 s de escena— el tablero
            // se quedo en 6,5 s **para ocho bloques**: premisa, dos columnas
            // con su cifra y su pie, remate y fuente. A 0,75 s por bloque mas
            // medio segundo de respiro son doce, asi que la mitad de la tabla
            // pasaba sin poder leerse.
            //
            // Jaime: *«el primer tablero esta sin sonido, prefiero borrarlo,
            // pero realmente prefiero que explique lo que tiene que
            // explicar»*. Y el canon ya lo decia: la duracion la decide la
            // lectura, y **un dato que no da tiempo a leer no esta en la pieza
            // aunque este en el frame**.
            //
            // Se toma el mayor de los dos. El tope duro sigue siendo el CTA.
            const dur = Math.min(
              Math.max(duracionBeat(plan, b.beat) ?? 0,
                       duracionTablero(b.kind, b.props)) + SOLAPE,
              fin - at,
            );
            return {
              at,
              duration: dur,
              kind: b.kind,
              // La placa del beat, si la hay: **los fondos son para usarse**.
              // El collage asoma alrededor y los bloques opacos sostienen las
              // cifras, que es como lo hace el canon.
              // Los ficheros de `public/sfx/` ya existen, asi que el sonido
              // de los movimientos se enciende. Niveles bajos: la voz manda.
              props: {
                ...b.props,
                sound: true,
                placa: placaDe(slug, b.beat),
                duracion: dur,
              },
            };
          })();
      })
      .filter(Boolean)
      /**
       * **Un tablero sin sitio no se emite.** Al empujarlo detras de las
       * tarjetas puede quedar despues del final de la pieza, y entonces su
       * duracion sale cero o negativa: Remotion aborta con «durationInFrames
       * must be positive», que no dice nada del tablero. Es C-14 por el otro
       * lado -alli se pasaba del final, aqui empieza despues.
       */
      .filter((b) => {
        if (b.duration > 0) return true;
        console.log(
          `    ojo: un tablero queda fuera de la pieza (empieza en ` +
          `${(b.at / FPS).toFixed(1)}s de ${duracion.toFixed(1)}s) y no se emite.`,
        );
        return false;
      });
  /**
   * **La tarjeta dura lo que tarda en leerse, no 5,5 s fijos.**
   *
   * Jaime: *«todo el panel final pasa muy rapido, conviene bajarle la velocidad
   * a esa parte»*. Era literal: `CtaCard` reparte kicker, promesa y filas sobre
   * su propia duracion, asi que con 5,5 s y cuatro filas cada dato entraba y se
   * iba antes de leerse.
   *
   * Se deriva de lo que lleva dentro -medio segundo de entrada, segundo y medio
   * para la promesa, 1,2 s por fila y un segundo de sostener al final-, que es
   * la misma regla que gobierna paneles y tableros: **la duracion la decide la
   * lectura**. Con cuatro filas salen 7,8 s en vez de 5,5.
   *
   * El primer intento fue darle el beat de registro entero, y lo tumbo el
   * detector de mudos: en el reel 5 eso tapaba 15 s de subtitulo. La tarjeta
   * ilustra el cierre, no lo sustituye.
   */
  const filasCta = 2 + (CUENTA[slug] ? 2 : 0);
  const CTA_DUR = Math.min(
    15,
    Math.max(CTA_S, 0.5 + 1.5 + filasCta * 1.2 + 1),
  );
  const cta = {
    at: Number((duracion - CTA_DUR).toFixed(3)),
    dur: Number(CTA_DUR.toFixed(3)),
    cuenta: CUENTA[slug],
    precio: PRECIO[slug],
    promesa: PROMESA[slug],
    fecha: "21 de septiembre",
    // El CTA es el último frame de la pieza: no puede ser un plano negro
    // quieto. Lleva placa recortada y reparte su horario sobre su duración.
    duracion: Math.round(CTA_DUR * FPS),
    placa: placaDe(slug, FRAMES.reels[slug].beats.length),
    // Sin precio: sube pronto y decirlo caduca la pieza. Ver `CtaCard`.
  };
  // **Ningun tablero pasa del arranque del CTA.** Ver el comentario de arriba:
  // en reel-06 uno se estiraba treinta segundos y se comia el final. Se acota
  // aqui y no donde se construyen porque `cta` se calcula despues.
  for (const b of tableros) {
    const topeCta = Math.round(cta.at * FPS);
    if (b.at + b.duration > topeCta) {
      b.duration = Math.max(Math.round(2.5 * FPS), topeCta - b.at);
      b.props = { ...b.props, duracion: b.duration };
    }
  }

  const marca = marcaDeHumanidad(slug, ideasFuerza(slug, edl, plan, captions), cta);
  /**
   * **La correccion de cumplimiento, encima de lo que se dijo mal.**
   *
   * Jaime: *«el libreto dice la verdad, esta es una oportunidad para que el
   * error se manifieste; el subtitulo, cuando digo ministerio de comercio, dice
   * la informacion real palpitando»*. No se corrige el libreto ni se tapa el
   * desliz — sale la verdad encima, en oro, y palpita.
   *
   * Sale del paso de composicion, que es quien lee el libreto contra lo dicho.
   * Se pone en la PRIMERA cue que contenga lo dicho mal: repetirla no es
   * enfasis, es ruido.
   */
  for (const row of db
    .prepare("select corrige_dice, corrige_es from escena_desc" +
             " where video_slug = ? and corrige_dice is not null")
    .all(slug)) {
    let puesta = false;
    // **La correccion es sobre una palabra; la frase solo la situa.**
    //
    // Esto exigia que `corrige_dice` cupiera entero dentro de UN caption, y el
    // subtitulo parte por tiempo, no por sentido: «un rector» sale con «un» al
    // final de un trozo y «rector» al principio del siguiente, asi que la
    // correccion no se colocaba y el render paraba. Pasaba con las tres del
    // lote —«un rector», «El Serrea»— teniendo el texto delante.
    //
    // Se intenta la frase entera primero, que es lo mas preciso; si no cabe en
    // ningun trozo, se busca la palabra que de verdad cambia —la mas larga, que
    // es la que el ojo lee mal— y se corrige ahi.
    const clave = row.corrige_dice
      .split(/\s+/)
      .reduce((a, b) => (b.length > a.length ? b : a), "");
    const cabe = (t, q) => t?.toLowerCase().includes(q.toLowerCase());
    const entera = marca.captions.some((c) => cabe(c.text, row.corrige_dice));
    marca.captions = marca.captions.map((c) => {
      if (puesta) return c;
      const encaja = entera
        ? cabe(c.text, row.corrige_dice)
        : clave.length > 3 && cabe(c.text, clave);
      if (!encaja) return c;
      puesta = true;
      // **Si ya la puso `marcaDeHumanidad`, solo se le enciende el palpiteo.**
      // Que la correccion exista por dos vias no es un conflicto: una la
      // declara la pieza a mano y la otra la deduce la composicion leyendo el
      // libreto. Duplicarla si seria un problema — dos capas diciendo lo mismo
      // en el mismo segundo es ruido, no enfasis (aprendizaje 38).
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
  // Si el desliz cae dentro del CTA, lo señala la fila de precio de la tarjeta.
  // Y entonces el precio SÍ se imprime: no caduca, porque lo que se enseña es
  // el número que el propio libreto calcula, no la oferta vigente.
  if (marca.enCta) cta.corrige = marca.enCta;

  /**
   * **Las capas de cada segmento salen de su camino, no de un literal.**
   *
   * Esto es lo que Jaime pidió: *«creo que el renderizado también debe ser por
   * código, tres caminos y cada camino con sus propias indicaciones; hay muchas
   * decisiones sueltas que simplemente no se están cumpliendo»*. `trato.py`
   * decidía el tratamiento de cada segmento desde hacía días y **el render no
   * lo leía**: por eso la portada salía como un plano con subtítulo.
   *
   * El lado libre se calcula por escena y no una vez por pieza: el sujeto no
   * está en el mismo sitio en todos los encuadres, y una figura en el lado
   * ocupado tapa justo lo que el camino `cercano` protege.
   */
  const caminos = (() => {
    const desc = Object.fromEntries(
      db
        .prepare("select * from escena_desc where video_slug = ?")
        .all(slug)
        .map((r) => [r.etapa_orden, r]),
    );
    /**
     * **La unidad es el beat, no el corte.** `depurar.py` parte una etapa en
     * varios trozos al quitar el aire, y todos heredan el mismo `detalle` — con
     * el mismo `trato`. Recorriendo segmentos, la portada de reel-05 emitia sus
     * capas dos veces y la figura de una metafora entraba una vez por trozo.
     *
     * La descripcion de escena tambien es por etapa, asi que el beat es la
     * unidad correcta en los dos lados: se toma el frame donde empieza su primer
     * trozo y la duracion de todos los suyos juntos.
     */
    /**
     * **Y el reloj es el del plan, no el del EDL.** Esto acumulaba la duracion
     * de los segmentos del EDL, que incluye el aire que `plan-reel` quita antes
     * de renderizar: la imagen corre sobre una linea 6,83 s mas corta. El
     * desfase no es constante, crece —0 en el beat 2, 4,93 s en el 6, 6,77 s en
     * el 8— asi que cada tablero entra mas tarde que la frase que ilustra y el
     * cierre se sale del video. Es lo que Jaime describio como *«la entrada del
     * tablero sigue hablando de los 500 antes de entrar a dar el remate»*.
     *
     * El `det` sigue viniendo del EDL, que es donde vive lo que dice y como se
     * trata la etapa; lo unico que cambia de sitio es **cuando**.
     */
    const detPorBeat = new Map();
    for (let i = 0; i < edl.segmentos.length; i++) {
      const det = edl.detalle[i] ?? {};
      if (!detPorBeat.has(det.beat)) detPorBeat.set(det.beat, { det, i });
    }
    const porBeat = new Map();
    for (const e of plan.escenas ?? []) {
      const beat = Number(e.beat);
      const dur = Math.round((e.duracion / VELOCIDAD) * FPS);
      const previo = porBeat.get(beat);
      if (previo) {
        previo.duration += dur;
        continue;
      }
      const d = detPorBeat.get(beat) ?? { det: {}, i: 0 };
      porBeat.set(beat, {
        at: Math.round((e.montado_desde / VELOCIDAD) * FPS),
        duration: dur,
        det: d.det,
        i: d.i,
      });
    }
    const out = [];
    for (const { at, duration, det, i } of porBeat.values()) {      const e = plan.escenas[i] ?? plan.escenas[0];
      const cx = e?.crop ? (e.crop.x + e.crop.w / 2) / 2160 : 0.5;
      const r = construir({
        at,
        duration,
        desc: desc[det.beat],
        det,
        lado: cx < 0.5 ? "der" : "izq",
      });
      out.push(...r.capas);
      for (const f of r.faltas) faltas.push(`${slug}: ${f}`);
    }
    for (const f of revisarPieza(out)) faltas.push(`${slug}: ${f}`);
    return out;
  })();

  const pieza = {
    id: `Reel-R${slug.slice(-1)}`,
    video: `${slug}.mp4`,
    // Sin aprobar, sin audio adicional: ver `aprobadas` arriba.
    sonido: aprobadas.has(slug),
    // Las capas por camino: el gancho, los tableros, los cercanos y las
    // metáforas, cada uno con lo suyo. Ver `scripts/caminos.mjs`.
    caminos,
    // El EDL entero viaja con la pieza: la puerta esta en el SEGMENTO, y para
    // mirarla hace falta el detalle por etapa, no solo lo que se oye.
    edl: { detalle: edl.detalle ?? [], sin_toma: edl.sin_toma ?? [] },
    duracion: Number(duracion.toFixed(3)),
    lineas,
    /**
     * **El rotulo entra cuando lo dice el gancho, no cuando cae la palabra.**
     *
     * `entra` se calculaba anclando el rotulo a la palabra que subraya, y eso
     * dejaba el titulo de reel-01 entrando en el frame 106 —3,5 s— dentro de un
     * gancho que dura 5. En reel-04 igual, 104. Es justo la decision suelta que
     * Jaime senalo: la regla estaba escrita («el gancho son 5 segundos, de los
     * que el primero es clave») y el render la ignoraba.
     *
     * Si hay camino de portada, manda el camino. Si no lo hay, se queda el
     * anclaje por palabra, que para una pieza sin gancho declarado es correcto.
     */
    entra: caminos.find((c) => c.tipo === "rotulo")?.at ?? entra,
    sostiene: SOSTIENE,
    cta,
    captions: marca.captions,
    desatura: marca.desatura,
    // Frames donde cambia el encuadre: ahi cruza la barra que tapa el corte.
    // Salen del plan, asi que no pueden desincronizarse del montaje.
    cortes: (() => {
      const out = [];
      let t = 0;
      for (const e of plan.escenas.slice(0, -1)) {
        t += e.duracion;
        out.push(Math.round(t * FPS));
      }
      return out;
    })(),
    /**
     * Lado libre del cuadro: el contrario a donde esta el sujeto.
     *
     * Sale del ancla que midio `punch-ins.py` sobre la toma, no se elige a ojo.
     * Con el sujeto a la izquierda del centro, el hueco esta a la derecha.
     */
    lado: (() => {
      const e = plan.escenas[0];
      const cx = e.crop ? (e.crop.x + e.crop.w / 2) / 2160 : 0.5;
      return cx < 0.5 ? "der" : "izq";
    })(),
    /**
     * Los paneles tienen **dos usos**, y la diferencia la marca si su beat
     * lleva tablero:
     *
     * - **Con tablero: anuncia.** Entra justo antes y le entrega el cuadro. Un
     *   gráfico que aparece es una promesa, y el tablero la cumple.
     * - **Sin tablero: acompaña.** Es la animación detrás del hablante que
     *   ejemplifica lo que dice, y **dura el beat entero** — no hay nada que
     *   anunciar, hay algo que sostener.
     */
    paneles: (PANELES[slug] ?? [])
      .map((b) => {
        const inicio = anclarBeat(plan, b.beat);
        const suyo = tableros.find((t) => t.at === inicio);
        if (suyo) {
          const dur = ADELANTO(b.bloques);
          const at = suyo.at - dur;
          return at < 0 ? null : { at, duration: dur, bloques: b.bloques };
        }
        /**
         * **El panel de acompanamiento tampoco dura el beat entero.**
         *
         * Duraba 17,7 s en el beat 5 del reel 1, y sus tres bloques entran en
         * el primer segundo: lo que quedaban eran dieciseis segundos de tres
         * rotulos quietos. La regla ya estaba escrita para el tablero -no hay
         * problema si dura mas de 3 s, siempre que sea dinamico- y vale igual
         * aqui: **lo que no se permite es un elemento estatico largo**.
         *
         * Se queda lo que tarda en escribirse mas tres segundos de sostener, y
         * despues devuelve el cuadro. Eso libera el resto del beat para que lo
         * lleve el subtitulo compuesto, que es lo que Jaime pidio para ese
         * tramo: *«del 45 al 65 no hay cc»*.
         */
        const dur = duracionBeat(plan, b.beat);
        const tope = ADELANTO(b.bloques) + 3 * FPS;
        return dur
          ? { at: inicio, duration: Math.min(dur, tope), bloques: b.bloques }
          : null;
      })
      .filter(Boolean)
      // **Un panel cede cuando entra el siguiente.** El de acompañamiento dura
      // el beat entero, y el que anuncia un tablero entra antes de que ese beat
      // acabe: sin esto se pisaban tres segundos.
      .sort((x, y) => x.at - y.at)
      .map((x, i, todos) => {
        const sig = todos[i + 1];
        return sig && x.at + x.duration > sig.at
          ? { ...x, duration: sig.at - x.at }
          : x;
      })
      /**
       * **Un panel que cede del todo no se emite.** Cuando dos empiezan en el
       * mismo frame -el de acompanamiento de un beat y el que anuncia el tablero
       * del siguiente- el recorte deja al primero en cero, y Remotion aborta con
       * «durationInFrames must be positive», que no dice nada del panel.
       */
      .filter((x) => {
        if (x.duration > 0) return true;
        console.log(
          `    ojo: un panel cede del todo en ${(x.at / FPS).toFixed(1)}s ` +
          `(otro entra en el mismo frame) y no se emite.`,
        );
        return false;
      }),
    /**
     * **Sin cortinillas.** Se probaron y se quitaron.
     *
     * Eran placas de 0,7 s en cada costura, y Jaime: *«en el segundo 7 se ve
     * raro; esos cortes de escena no vale la pena dejarlos como cortes de
     * escena»*. Dos motivos, y el primero es un defecto claro:
     *
     * - **Partían el rótulo por la mitad.** El gancho estaba en pantalla, la
     *   cortinilla lo tapaba 0,7 s y volvía — y al desvanecerse dejaba fantasma
     *   encima del propio rótulo.
     * - **No valían el corte.** Un flash que aparece y se va no desarrolla
     *   nada: es el «comodity para cambiar escenas». Y para tapar un corte
     *   estaba metiendo dos.
     *
     * Lo que cubre las costuras ahora es **el propio tablero**, que se estira
     * `SOLAPE` frames por encima de la frontera: cuando la escena vuelve al
     * plano, el beat siguiente ya empezó por debajo. Es un L-cut — la costura no
     * se ve ni se oye — y lo que la tapa además explica algo.
     */
    cortinillas: [],
    /**
     * **Un glitch en cada costura que no tape ya un tablero.**
     *
     * Jaime: *«hay cortes muy fuertes todavía… el corte es abrupto; lo ideal es
     * que no se note. Se puede poner una transición discreta, un efecto glitch
     * que distorsione la imagen y el sonido como un TV antiguo cambiando de
     * canal, durante poco tiempo, con el respectivo ruido»*.
     *
     * Va **centrado en la costura** —mitad antes, mitad después— para que el
     * corte caiga dentro de la distorsión y no en su borde. Y dura `DUR_GLITCH`
     * frames: lo justo para sustituir el salto sin convertirse en el efecto.
     */
    glitch: (() => {
      /**
       * **Sólo donde la costura salta, no en todas.**
       *
       * Iba en cada costura, y una máscara que se pone siempre deja de ser
       * máscara: se convierte en el efecto, y entonces el corte limpio y el
       * malo se ven igual de raros. Jaime lo había acotado —*«el glitch para
       * cambios de escena o en cortes de escena que quedan mal»*— y después dio
       * el orden completo: *«busca los mejores cortes posibles, y si no,
       * utiliza la transición del glitch, con ésa se disimula»*.
       *
       * `costuras.py` mueve lo que se puede mover **sin perder voz** y deja en
       * `costuras_duras` lo que no tuvo arreglo. Eso, y sólo eso, se disimula.
       */
      const duras = new Set(edl.costuras_duras ?? []);
      const out = [];
      const det = edl.detalle ?? [];
      /**
       * **Y se coloca donde esta la costura en la pieza, no en el EDL.**
       * Esto acumulaba las duraciones del EDL, que lleva el aire que la imagen
       * ya no tiene: el glitch entraba hasta 6,8 s tarde, o sea **en mitad de
       * una frase en vez de encima del salto que venia a tapar**. Un efecto que
       * disimula un corte se convierte en un defecto en cuanto se despega de
       * el, y es lo que Jaime vio: *«veo muchos glitches, se pierde bastante
       * continuidad»*.
       */
      for (let i = 0; i < edl.segmentos.length - 1; i++) {
        if (!duras.has(i)) continue;
        const fin = finMontado(plan, edl, i);
        if (fin === null) continue;
        const at = Math.round((fin / VELOCIDAD) * FPS) - Math.round(DUR_GLITCH / 2);
        if (at < 0) continue;
        // Donde ya hay tablero o tarjeta el plano cambió: no hay salto que tapar.
        const cubierto = [...tableros, ...cartas].some(
          (b) => at < b.at + b.duration && at + DUR_GLITCH > b.at,
        );
        if (!cubierto) out.push({ at, duration: DUR_GLITCH });
      }
      return out;
    })(),
    tarjetas: cartas,
    boards: tableros,
  };
  /**
   * **El subtitulo se compone al final**, cuando ya se sabe que hay en pantalla.
   *
   * La condicion es «ser la unica capa de texto del instante», y eso no se
   * puede saber antes de tener tableros, tarjetas y paneles calculados. El
   * panel cuenta **todo el rato que esta en
   * cuadro**, no solo mientras escribe: es un objeto de texto grande y
   * permanente, y un remate en Anton a cuerpo 128 al mismo tiempo son dos capas
   * gritando. Por eso el panel se acota arriba: cede el cuadro, y entonces el
   * subtitulo puede subir la voz sin pisarlo.
   */
  const enCuadro = pieza.paneles;
  /**
   * **Una etapa, un remate.** La ventana de cada beat sale del EDL igual que
   * la de un panel o un tablero, asi que el subtitulo compuesto cae donde cae
   * el argumento y no cada N segundos.
   */
  const ventanas = FRAMES.reels[slug].beats.map((_, i) => [
    anclarBeat(plan, i + 1),
    anclarBeat(plan, i + 2),
  ]);
  const comp = componer(pieza.captions, [
    ...pieza.boards,
    ...pieza.tarjetas,
    ...enCuadro,
    // El CTA se pinta encima: componer ahi seria trabajar para nadie.
    { at: pieza.cta.at * FPS, duration: pieza.cta.dur * FPS },
    /**
     * **Y el rotulo, que es el vecino mas cercano.**
     *
     * `BigTitle` vive en 0,62-0,76 de altura (y=1190..1459) y la banda de
     * subtitulo cierra en y=1160: treinta pixeles. Un remate a dos bloques
     * ademas del rotulo son tres objetos de texto apilados ocupando el 29% del
     * cuadro, y justo en el gancho —que es donde no hay tablero ni tarjeta ni
     * panel, asi que la regla dispara—. Medido, chocaba en dos de las seis.
     *
     * Es el aprendizaje 38 generalizado: la capa permanente cede el volumen,
     * no el sitio.
     */
    { at: pieza.entra, duration: 9 + pieza.sostiene + 9 },
  ], ventanas);
  pieza.captions = comp.captions;
  // Las ventanas de beat viajan en el spec: sin ellas no se puede comprobar
  // desde fuera que cada beat lleve su tratamiento.
  pieza.ventanas = ventanas;
  // El tratamiento de cada escena, para poder auditarlo desde fuera.
  pieza.escenas = porEscena(pieza, slug);
  /**
   * **Ninguna escena a cara pelada.** Regla de Jaime: *«lo que quiero es que
   * siempre haya animaciones, que no sea mi cara y ya»*.
   *
   * El reparto por beat no lo garantizaba: un beat de 17 s son tres o cuatro
   * escenas y con un panel al principio el beat contaba como tratado mientras
   * las otras iban a plano seco. La escena es lo que el espectador ve cambiar,
   * asi que es la unidad que hay que llenar.
   *
   * Se llena con **la capa mas barata que no inventa nada**: el subtitulo de esa
   * escena, compuesto. El texto es lo que Jaime dice, asi que no hay copy nuevo
   * que aprobar, y es una de las tres formas que el pidio -«texto animado o CC
   * animado». Si la escena no tiene ningun subtitulo que admita reparto, se
   * queda seca y **se dice cual**: forzar una animacion sobre una frase que no
   * la aguanta es justo lo que el canon prohibe.
   */
  const rellena = () => {
    let puestas = 0;
    for (const e of pieza.escenas) {
      if (e.trato !== "—") continue;
      const dentro = pieza.captions
        .filter((c) => c.at < e.b && c.at + c.duration > e.a)
        .sort((x, y) => y.at - x.at);
      for (const c of dentro) {
        if (c.realza || c.corrige || c.compuesto) break;
        const par = partirFrase(c.text);
        if (!par) continue;
        c.compuesto = par;
        puestas += 1;
        break;
      }
    }
    if (puestas) pieza.escenas = porEscena(pieza, slug);
    return puestas;
  };
  /**
   * **Bajo el contraste, el subtitulo no se compone.** Las dos cifras ya estan
   * arriba y grandes; un remate que repita una de ellas es la misma informacion
   * en dos capas —«SE QUEDA CON 67.» debajo de un «$67»—, que es el aprendizaje
   * 38 otra vez. El subtitulo sigue, plano, que es lo que Jaime pidio:
   * *«manteniendo los subtitulos»*.
   */
  if (pieza.contraste) {
    const { at, duration } = pieza.contraste;
    for (const c of pieza.captions) {
      if (c.compuesto && c.at < at + duration && c.at + c.duration > at) {
        delete c.compuesto;
      }
    }
    pieza.escenas = porEscena(pieza, slug);
  }
  pieza.rellenadas = rellena();
  /**
   * El contraste se ancla al subtitulo: la cifra entra **cuando se dice**. Si
   * una de las dos no se llega a decir, no se emite — media comparacion es
   * peor que ninguna.
   */
  const c = CONTRASTE[slug];
  if (c) {
    const cuando = (t) =>
      pieza.captions.find((x) => DICE(x.text).includes(DICE(t)))?.at ?? null;
    const a1 = cuando(c.izq.ancla);
    const a2_ = cuando(c.der.ancla);
    if (a1 === null || a2_ === null) {
      console.log(
        `    ojo: ${pieza.id} declara contraste ${c.izq.cifra}/${c.der.cifra} y ` +
        `el montaje no dice ${a1 === null ? c.izq.ancla : c.der.ancla}.`,
      );
    } else {
      pieza.contraste = {
        at: Math.min(a1, a2_),
        duration: Math.max(a1, a2_) + 5 * FPS - Math.min(a1, a2_),
        props: {
          izq: { ...c.izq, ancla: undefined, at: a1 - Math.min(a1, a2_) },
          der: { ...c.der, ancla: undefined, at: a2_ - Math.min(a1, a2_) },
          pie: c.pie,
        },
      };
    }
  }
  pieza.compuestos = comp.n;
  return pieza;
});

/**
 * **Beats sin ningun tratamiento.**
 *
 * Jaime, sobre los doce segundos del asesor en el reel 1: *«buena parte no
 * tenia ni subs animados ni animaciones por detras, valdria la pena poner
 * algunas»*. Y era el unico beat de la pieza sin nada encima — cosa que nadie
 * podia ver sin ir beat por beat a mano.
 *
 * El reparto dice que cada beat lleva uno: tablero si compara o cuantifica,
 * animacion si explica un mecanismo, idea fuerza si afirma, marca si hay
 * desliz. **Un beat sin ninguno es un beat que se cayo del reparto**, no una
 * decision.
 *
 * Se avisa y no se falla: un beat puede ir a plano seco a proposito -el
 * arranque en frio del reel 5 lo hace- y forzar un tratamiento por cuota seria
 * justo lo que el canon prohibe, movimiento que no se gana su sitio.
 */
const sinTrato = (r) => {
  const capas = [...r.boards, ...r.tarjetas, ...r.paneles];
  const marcados = r.captions.filter((c) => c.realza || c.corrige || c.compuesto);
  return (r.ventanas ?? []).flatMap(([a, b], i) => {
    const hay =
      capas.some((x) => x.at < b && x.at + x.duration > a) ||
      marcados.some((c) => c.at < b && c.at + c.duration > a);
    return hay || b - a < 2 * FPS
      ? []
      : [`${i + 1} (${(a / FPS).toFixed(1)}-${(b / FPS).toFixed(1)}s)`];
  });
};

fs.writeFileSync("src/reels.json", JSON.stringify(spec, null, 1) + "\n");
// **Las comprobaciones van DESPUES de escribir el spec.** Estaban antes, asi
// que cuando una paraba el montaje `src/reels.json` se quedaba con el estado
// anterior y no habia forma de mirar por que fallo: los numeros que uno lee no
// son los que la hicieron saltar. Un artefacto que no existe cuando la
// comprobacion falla es un artefacto que no sirve para diagnosticar.
/**
 * **Jaime aparece mínimo tres veces**: al comienzo, hacia la mitad y al final o
 * justo antes. Regla suya, y es un suelo: más está bien, menos no.
 *
 * Es lo que impide que la pieza se convierta en una sucesión de tableros con
 * una voz en off. Se comprueba por tercios contra lo que tapan los tableros y
 * las tarjetas, y **falla el build** en vez de avisar: con 16-50 anuncios, un
 * aviso que se ignora se replica cincuenta veces.
 */
/**
 * **Una pieza rota no para el lote.** `reels-spec` genera las seis siempre
 * -necesita el spec entero- pero **sólo falla por las que se están montando**.
 *
 * Sin esto, el reel 3 —que se quedó sin material y está esperando decisión— no
 * dejaba renderizar el 1 ni el 2, que estaban bien. Y el trabajo es de uno en
 * uno por instrucción de Jaime, así que bloquear el lote por una pieza en
 * revisión es exactamente lo contrario de lo que hace falta.
 *
 * Las demás siguen comprobándose: se avisa con la misma frase, sin parar.
 */
const PEDIDOS = (process.env.REELS_PEDIDOS ?? "")
  .split(/[^0-9]+/)
  .filter(Boolean)
  .map((n) => `Reel-R${Number(n)}`);
const bloquea = (r) => !PEDIDOS.length || PEDIDOS.includes(r.id);
/**
 * **Marca la pieza como no renderizable y sigue.** Antes lanzaba, y una pieza
 * incompleta paraba el lote entero: el reel 1 sin su etapa 8 impedia renderizar
 * los otros cinco, que estaban bien.
 *
 * Eso contradice el embudo — *«renderizamos, pero solo lo que ya sabemos que
 * esta bien»*—: lo que hay que impedir es gastar el peldaño caro en lo que no
 * esta, no impedir gastarlo en lo que si. La pieza queda con sus motivos y
 * `montar.sh` no la renderiza.
 */
const para = (r, msg) => {
  if (bloquea(r)) {
    (r.bloqueado ??= []).push(msg);
    console.log(`    NO RENDERIZA · ${msg}`);
    return;
  }
  console.log(`    (en revisión, no bloquea) ${msg}`);
};

for (const r of spec) {
  const fin = Math.round(r.duracion * FPS);
  const tapa = [...r.boards, ...r.tarjetas];
  const libres = [0, 1, 2].filter((i) => {
    const a = (fin * i) / 3;
    const b = (fin * (i + 1)) / 3;
    /**
     * Cuánto de este tercio queda con Jaime en cuadro.
     *
     * **Por union, no por suma.** Sumando, dos capas que se pisan cuentan dos
     * veces: en el reel 2 la tarjeta del beat 2 (6,9-14,3) y el tablero del
     * beat 3 (6,9-28,6) daban 24,5 s de tapado en un tercio de 24, asi que el
     * hueco salia negativo y la comprobacion paraba el montaje **teniendo Jaime
     * 6,9 s de plano limpio**. Es la familia de los aprendizajes 19 y 28: un
     * detector que cuenta de mas grita por casos que no existen.
     */
    const tramos = tapa
      .map((t) => [Math.max(a, t.at), Math.min(b, t.at + t.duration)])
      .filter(([x, y]) => y > x)
      .sort((p, q) => p[0] - q[0]);
    let cubierto = 0;
    let hasta = a;
    for (const [x, y] of tramos) {
      cubierto += Math.max(0, y - Math.max(x, hasta));
      hasta = Math.max(hasta, y);
    }
    return b - a - cubierto > FPS; // al menos un segundo de plano real
  });
  /**
   * **Dos formas de cumplir, y basta con una.** Jaime, calibrando la regla:
   * *«más del 60% del vídeo, o en esos tres puntos»*.
   *
   * - **Por proporción:** si está en cuadro más del `MINIMO_CARA` del metraje,
   *   ya está — da igual dónde caigan los tableros, porque su cara es la pieza.
   * - **Por reparto:** si sale menos, entonces tiene que aparecer al menos una
   *   vez en cada tercio, para que no desaparezca durante medio vídeo.
   *
   * Y es **un suelo, no una cuota**: *«pero si yo aparezco en mayor proporción
   * no hay problema»*. Aparecer más nunca bloquea. Importa decirlo porque la
   * tentación al leer «mínimo tres veces» es recortar cara para hacer sitio a
   * los tableros, y es al revés — el tablero entra donde hace falta y si sobra
   * plano suyo, mejor.
   */
  const enCuadroTotal = (() => {
    const tramos = tapa
      .map((b) => [b.at, b.at + b.duration])
      .sort((x, y) => x[0] - y[0]);
    let cubierto = 0;
    let hasta = 0;
    for (const [x, y] of tramos) {
      cubierto += Math.max(0, y - Math.max(x, hasta));
      hasta = Math.max(hasta, y);
    }
    return fin > 0 ? (fin - cubierto) / fin : 1;
  })();
  /**
   * **Un tablero que se come un tercio de la pieza es un tablero, no la pieza.**
   *
   * Jaime, y queda como criterio de edicion: *«el tablero es un mecanismo de
   * reducir carga cognitiva, esa es su funcion: facilitar la decision»*, y
   * *«lo que hace falta es simplificar el tablero y animarlo mas»*.
   *
   * Va **antes** de la comprobacion de presencia a proposito. En reel-01 el
   * tablero de la etapa 3 duraba 40,9 s sobre 101,5 —el 40% del anuncio— y lo
   * unico que se leia era «Jaime no aparece en mitad»: el motivo correcto,
   * pero la causa equivocada. Nadie iba a mover la cara; habia que simplificar
   * el tablero. Un diagnostico que apunta al sitio equivocado cuesta la vuelta
   * entera.
   *
   * El tope es un tercio porque es exactamente lo que la regla de presencia
   * necesita para poder cumplirse por reparto.
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
  if (enCuadroTotal <= MINIMO_CARA && libres.length < 3) {
    const donde = ["comienzo", "mitad", "final"].filter((_, i) => !libres.includes(i));
    para(r,
      `${r.id}: Jaime no aparece en ${donde.join(" ni ")}. La regla es minimo ` +
      `tres veces —comienzo, mitad y final—; hay que mover o acortar un tablero.`,
    );
  }
}

/**
 * **El tramo mas largo sin una palabra en pantalla.**
 *
 * Sale de repetir aqui el mismo filtro que aplica `Reel.tsx`, porque el defecto
 * que caza es exactamente ese: una capa que tapa el subtitulo mas de lo que
 * cree. Los paneles callaban la banda entera y en el reel 1 eso costo **20 de
 * los 36 subtitulos** -43,6 s de una pieza de 75,2 s- sin un solo aviso.
 *
 * El subtitulo es capa portante: el playbook exige que el argumento funcione
 * sin audio, y **el 85% del video social se ve sin sonido**. Un hueco largo no
 * es un detalle de acabado, es la pieza rota. Por eso se imprime **siempre** el
 * numero -para que se vea aunque nadie lo busque- y por encima de `MUDO_MAX`
 * **falla el build**, que es lo que impide que vuelva.
 */
const MUDO_MAX = 10 * FPS;
const mudo = (r) => {
  // La tarjeta de CTA se pinta ENCIMA del subtitulo y lleva su propio texto:
  // para esta cuenta tapa igual que una tarjeta. Sin esto el numero saldria
  // optimista justo donde la pieza se juega el registro.
  const tapan = [
    ...r.tarjetas,
    ...r.cortinillas,
    ...(r.cta ? [{ at: r.cta.at * FPS, duration: r.cta.dur * FPS }] : []),
  ];
  const vis = r.captions
    .filter(
      (c) =>
        tapan.reduce(
          (n, b) =>
            n +
            Math.max(
              0,
              Math.min(c.at + c.duration, b.at + b.duration) - Math.max(c.at, b.at),
            ),
          0,
        ) <= c.duration / 2,
    )
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

for (const r of spec) {
  const m = mudo(r);
  console.log(
    `${r.id}  ${r.duracion.toFixed(1)}s  ${m.visibles}/${r.captions.length} cc (${r.compuestos} compuestos)  mudo max ${(m.dur / FPS).toFixed(1)}s  ` +
    `rotulo entra en ${(r.entra / FPS).toFixed(1)}s  ` +
    `${r.paneles.length} panel(es) · ${r.boards.length} tablero(s)${r.boards.length ? " en " + r.boards.map((b) => (b.at / FPS).toFixed(1) + "s").join(",") : ""}  ` +
    `CTA en ${r.cta.at.toFixed(1)}s`,
  );
  const exige = FRAMES.reels[`reel-0${r.id.slice(-1)}`]?.debe_decir ?? [];
  const dicho = DICE(r.captions.map((c) => c.text).join(" "));
  // Mismo criterio que en `beats.py`: el termino admite alternativas con `|`,
  // porque lo que se comprueba es la intencion comunicativa y no la letra.
  const faltan = exige.filter(
    (t) => !String(t).split("|").some((x) => dicho.includes(DICE(x))),
  );
  /**
   * **La cifra es secundaria respecto al segmento.**
   *
   * Correccion de Jaime, y cambia donde esta la puerta: *«no creo que las
   * cifras sean el parametro para medir; lo que tenemos que encontrar son los
   * segmentos especificos de lo grabado que caben dentro de los segmentos
   * esperados por el guion. Aca hay falsos positivos»*.
   *
   * El ejemplo esta medido: «estructura. 30.000 dolares no de ventas de
   * estructura» **contiene el 30** y es un tropiezo de cuatro segundos con
   * cobertura -0,07. La cifra decia que si y la seccion estaba mal — falso
   * positivo del criterio. Y al reves: una etapa puede cumplir su funcion sin
   * que la cifra sobreviva al recorte, y eso no la invalida.
   *
   * Asi que la cifra pasa a **aviso por segmento** y la puerta se baja a donde
   * esta la unidad de analisis: cada etapa con su encaje. Lo que para el build
   * es una etapa OBLIGATORIA sin fragmento o que no encaja — no que falte un
   * numero en la pieza.
   */
  if (faltan.length) {
    console.log(
      `    aviso: no suena ${faltan.map((x) => `«${x}»`).join(", ")}.` +
      ` Es un dato declarado, no el criterio: lo que decide es si cada segmento` +
      ` encaja en su etapa.`,
    );
  }
  const det = (r.edl?.detalle ?? []);
  /**
   * **Un segmento encaja si hace su trabajo, no si repite el libreto.**
   *
   * La cobertura sola mide literalidad: comparada contra un parrafo largo,
   * decir solo lo esencial puntua bajo aunque la etapa quede cumplida. En el
   * reel 2 la etapa 2 dice «por cada 100 dolares se quedan con 67» —que es
   * exactamente lo que el libreto pide ahi— y sacaba 0,10 porque el parrafo
   * ademas habla de la mansion, el yate y Muskoka.
   *
   * Asi que se mira contra **lo alcanzable en esa etapa** (`cubre_max`), y
   * ademas se acepta el segmento que trae el dato que la etapa declara. Falla
   * solo el que ni dice el dato ni se acerca a lo que otro habria cubierto:
   * eso ya no es «poco literal», es que no cumple.
   */
  const encaja = (u) =>
    u.dice ||
    (u.cobertura ?? 0) >= Math.max(ENCAJE, RELATIVO * (u.cubre_max ?? 0));
  const flojas = det.filter((u) => !encaja(u));
  /**
   * **Un tablero SÍ ejecuta la etapa.** La puerta contaba como «sin material»
   * cualquier etapa sin fragmento, y ahí caían dos cosas distintas: la que no
   * tiene nada en la cinta, y la que se mandó a tablero **a propósito** porque
   * la toma leía plano. La segunda está resuelta —lleva su copy, que es la
   * propia lectura y por eso es exacta— y bloquearla contradice la regla que la
   * creó: *«no es aceptado leer; para leer prefiero el tablero»*.
   */
  const huecos = (r.edl?.sin_toma ?? [])
    .filter((u) => u.obligatorio && !u.copy);
  if (det.length) {
    console.log(
      `    encaje por segmento: ` +
      det.map((u) => `${u.beat}:${(u.cobertura ?? 0).toFixed(2)}`).join(" ") +
      /**
       * **Parecerse poco al libreto no es un defecto.** Jaime separo tres
       * cosas: *«una cosa el libreto o el mensaje esperado, otra el mensaje
       * entregado, otra la intencion comunicativa; se respeta la ultima, y
       * desde que el mensaje se mantenga coherente buscamos que se ajuste»*.
       *
       * La cobertura mide el parecido con el **mensaje esperado**, que es la
       * preferencia, no el criterio. Lo que decide si una etapa esta rota es
       * `integridad`, que lo juzga el paso de composicion leyendo la pieza
       * seguida. Asi que esto se dice como dato y no como alarma: llamarlo
       * «flojo» hacia perseguir el parecido y no el sentido.
       */
      (flojas.length
        ? `  · mas lejos del libreto: ${flojas.map((u) => u.beat).join(",")}`
        + ` (no es defecto: lo que decide es la integridad)`
        : ""),
    );
  }
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

/**
 * **El spec se reescribe al final, con lo que dijeron las comprobaciones.**
 *
 * Se escribe antes para que un fallo de comprobacion no deje al montaje sin
 * spec (C-49), pero entonces la marca `bloqueado` —que sale de las
 * comprobaciones— no llegaba al fichero. Se escribe dos veces a proposito: la
 * primera para no perder el trabajo, la segunda para no perder el veredicto.
 */
fs.writeFileSync("src/reels.json", JSON.stringify(spec, null, 1) + "\n");
const parados = spec.filter((r) => r.bloqueado?.length);
if (parados.length) {
  console.log(
    `\nNO SE RENDERIZAN ${parados.length} de ${spec.length}: ` +
      parados.map((r) => r.id).join(", ") +
      ` — el resto sigue, que es lo que dice el embudo.`,
  );
}

/**
 * **Y las faltas de camino, que antes no las veía nadie.**
 *
 * Se imprimen al final —después de escribir el spec, para no dejar el montaje
 * sin fichero— y **no paran el lote**: una escena sin figura dibujable es una
 * pieza peor, no una pieza inválida, y pararlo todo por eso deja seis vídeos
 * sin hacer por una descripción corta. Lo que sí hace es dejar de ser
 * invisible, que era el problema: *«hay muchas decisiones sueltas que
 * simplemente no se están cumpliendo»*.
 */
/**
 * **Un sonido descrito que no suena entra aqui, no se calla.**
 *
 * `sonidoDe` reconoce la descripcion de la escena por expresiones —«golpe
 * seco», «se traza», «barrido»—; lo que no encaja con ninguna se montaba mudo
 * sin decir nada, con la descripcion escrita y correcta. Jaime, oyendo el
 * reel-01: *«el tablero sin sonido»*, y la regla que lo ordena: *«el sonido del
 * tablero deben ser las acciones animadas del tablero»*.
 *
 * No se inventa el sonido —eso romperia la ley de que el sonido sigue al
 * movimiento— pero se dice que etapa lo describio y que escribio, que es lo
 * que permite arreglarlo en la descripcion, que es de donde sale.
 */
for (const s of sonidosMudos) {
  faltas.push(
    `${s.donde}: describe un sonido que no suena — «${s.dice}». Ninguna ` +
    `expresion de SONIDOS lo reconoce, asi que la capa se monta muda.`,
  );
}
if (faltas.length) {
  console.log(`\nFALTAS DE CAMINO — ${faltas.length}:`);
  for (const f of faltas) console.log(`  · ${f}`);
} else {
  console.log("\ncaminos: todas las indicaciones se cumplen");
}
