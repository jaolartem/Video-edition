/**
 * Emite `src/reels.json`: lo que Remotion superpone sobre cada reel montado.
 *
 * Este fichero es **el camino de fases, no el almacén**. Lee lo que hay, pide a
 * cada servicio su capa, arma la pieza, la escribe y deja que la puerta diga si
 * se renderiza. Ninguna regla vive aquí: viven en `scripts/reels/`, un fichero
 * por responsabilidad, y aquí sólo se llaman en orden.
 *
 * | Módulo | De qué responde |
 * |---|---|
 * | `reloj.mjs` | de un tiempo del plan a un frame de la pieza |
 * | `tramos.mjs` | cuánto tapa un conjunto de capas, por unión |
 * | `lectura.mjs` | cuánto dura lo que hay que leer |
 * | `texto.mjs` | normalizar una frase y saber por dónde se parte |
 * | `material.mjs` | lo que hay en el disco |
 * | `base.mjs` | lo que hay en `ads/decisiones.db` |
 * | `copy.mjs` | lo que todavía está escrito a mano, junto y contado |
 * | `capas.mjs` · `tableros.mjs` | qué se pone encima del plano, y cuándo |
 * | `subtitulos.mjs` | qué se pone encima del subtítulo |
 * | `cta.mjs` | la tarjeta de cierre |
 * | `escenas.mjs` | que ninguna escena vaya a cara pelada |
 * | `puerta.mjs` | qué se renderiza y qué no, y por qué |
 *
 * El orden en el que se llaman **no es libre**, y por eso está aquí y no
 * repartido: el CTA necesita la duración del corte, los tableros necesitan las
 * tarjetas para no pisarse, y el subtítulo compuesto necesita saber qué hay ya
 * en pantalla. Cada dependencia está dicha donde se usa.
 *
 *   node scripts/reels-spec.mjs
 */
import fs from "fs";
import { createHash } from "node:crypto";
import { faltasDeclaradas, rotuloDe } from "./caminos.mjs";
import { lecturaCorta } from "./reels/lectura.mjs";
import { FPS, Reloj } from "./reels/reloj.mjs";
// Las tres importaciones de `material.mjs` que había aquí eran una.
import { FRAMES, caraDe, duracionDelCorte, edlDe, marcoDe, planDe, subsDe }
  from "./reels/material.mjs";
import { correccionesDe, descDe, pieDe, tablerosDe }
  from "./reels/base.mjs";
import { CONTRASTE, precioSinEscala, LINEAS, SOSTIENE, entraRotulo, literalesDe }
  from "./reels/copy.mjs";
import { acotarAlCta, ctaDe, faltasDelCierre } from "./reels/cta.mjs";
import { caminosDe, contrasteDe, cortinillasDe, cortinillasSinSitio,
  faltaMezcla, glitchesDe, repartirPorCubre, tarjetasDe }
  from "./reels/capas.mjs";
import { armarPaneles, armarTableros, empujaTablero, sePisa }
  from "./reels/tableros.mjs";
import { imagenDe } from "./reels/imagen.mjs";
import { componer, corregirLoDicho, ideasFuerza, marcaDeHumanidad }
  from "./reels/subtitulos.mjs";
import { porEscena, rellenar } from "./reels/escenas.mjs";
import { revisar } from "./reels/puerta.mjs";

/**
 * Lo que un camino exige y no se cumple. **No se acumula en silencio**: se
 * imprime al final y el paso sale con código 1, que es lo que convierte una
 * indicación escrita en una indicación que se cumple.
 */
const faltas = [];

// **Las piezas salen de lo declarado, no de `LINEAS`.** Una que no estuviera en
// ese literal no existia para el render: reel-07 llevaba dias invisible aqui.
const spec = Object.keys(FRAMES.reels).map((slug) => {
  // **El rotulo lo declara el diseno; `LINEAS` es el respaldo.** Del literal
  // salia «No es por / ser inmigrante», que refuta la creencia antes de plantarla.
  // El DECLARADO y el que se usa son dos cosas: si se pasa el resuelto a
  // `literalesDe`, una pieza que cae al literal parece haberlo declarado.
  const rotuloDeclarado = rotuloDe(descDe(slug)?.[1]);
  const lineas = rotuloDeclarado ?? LINEAS[slug] ?? [];
  const marco = marcoDe(slug);
  const edl = edlDe(slug);
  const plan = planDe(slug);
  const reloj = new Reloj(plan);
  const duracion = duracionDelCorte(slug);

  reloj.cuadraCon(slug, duracion);

  const captions = subsDe(slug);
  if (!captions.length) {
    console.error(`  ojo: ${slug} sin subtitulos — falta correr subtitular.py`);
  }
  const entra = entraRotulo(captions, lineas);

  const cartas = tarjetasDe(slug, { marco, edl, reloj });

  const { tableros: deLaBase, declarados, faltas: fBase } = tablerosDe(slug);
  faltas.push(...fBase);

  /**
   * **Lo que sale de un literal escrito a mano se dice, cada vez.**
   *
   * Jaime, cerrando el diagnóstico de las cinco entregas idénticas: *«estaba
   * conectada a un "arreglo" hecho a mano por fuera del pipeline»*. Un parche
   * declarado es deuda; un parche callado es la fuente de verdad de facto. Lo
   * que queda escrito a mano vive junto en `copy.mjs` y se cuenta aquí.
   */
  const literales = literalesDe(slug, rotuloDeclarado);
  if (literales.length) {
    faltas.push(
      `${slug}: ${literales.map(([q, n]) => `${n} ${q}`).join(", ")} salen de ` +
      `un literal de \`reels-spec.mjs\`, no del diseñador — re-describir la ` +
      `pieza no los cambia.`,
    );
  }
  /**
   * **Lo que el diseñador declaró tiene que llegar a la pantalla, y se cuenta.**
   *
   * El fallo pudo durar tres ciclos por una razón concreta: **nadie comparaba
   * las dos cifras**. La base decía 38 tableros descritos y la pantalla mostraba
   * 9, y como cada lado informaba de lo suyo, los dos parecían correctos.
   */
  if (declarados > deLaBase.length) {
    faltas.push(
      `${slug}: el diseñador declaró ${declarados} tablero(s) y sólo ` +
      `${deLaBase.length} llegan al render. Lo que no llega no se ve y no ` +
      `avisa: es la diferencia entre corregir y entregar.`,
    );
  }

  faltas.push(...faltaMezcla(slug, deLaBase));
  const { pleno, panel } = repartirPorCubre(deLaBase);
  const tableros = armarTableros(
    // El pie sale de la fuente comprobada, no de una cadena a mano. Va antes
    // del horario porque la condición cuenta para el tiempo de lectura.
    pleno.map((b) => ({ ...b, props: { ...b.props, ...pieDe(slug, b.beat, b.props) } })),
    { slug, reloj, duracion, empuja: empujaTablero(cartas), captions },
  );

  // El CTA se calcula ahora y no antes porque su sitio sale de la duración del
  // corte; y los tableros se acotan a él porque lo que se pinta por debajo de
  // la tarjeta no lo ve nadie.
  const cta = ctaDe(slug, marco, duracion);
  acotarAlCta(tableros, cta);

  const marca = marcaDeHumanidad(
    slug, marco.senala, ideasFuerza(slug, reloj, marco.beats, captions), cta,
  );
  const corregidas = corregirLoDicho(slug, correccionesDe(slug), marca.captions);
  marca.captions = corregidas.captions;
  faltas.push(...corregidas.faltas);
  // Si el desliz cae dentro del CTA, lo señala la fila de precio de la tarjeta.
  // Y entonces el precio SÍ se imprime: no caduca, porque lo que se enseña es
  // el número que el propio libreto calcula, no la oferta vigente.
  if (marca.enCta && cta) cta.corrige = marca.enCta;

  const { capas: caminos, faltas: fCaminos } =
    caminosDe({ slug, plan, edl, desc: descDe(slug) });
  faltas.push(...fCaminos);

  // El virado del plano y la costura animada: lo que el diseñador pidió sobre
  // la IMAGEN, con su horario. Ver `scripts/reels/imagen.mjs`.
  const imagen = imagenDe(reloj);

  const pieza = {
    id: `Reel-R${slug.slice(-1)}`,
    video: `${slug}.mp4`,
    // Los efectos suenan siempre: la puerta de aprobacion se quito.
    sonido: true,
    // Las capas por camino: el gancho, los tableros, los cercanos y las
    // metáforas, cada uno con lo suyo. Ver `scripts/caminos.mjs`.
    caminos,
    // El EDL entero viaja con la pieza: la puerta esta en el SEGMENTO, y para
    // mirarla hace falta el detalle por etapa, no solo lo que se oye.
    edl: { detalle: edl.detalle ?? [], sin_toma: edl.sin_toma ?? [] },
    duracion: Number(duracion.toFixed(3)),
    lineas,
    /**
     * **El rótulo entra cuando lo dice el gancho, no cuando cae la palabra.**
     *
     * `entra` se calculaba anclando el rótulo a la palabra que subraya, y eso
     * dejaba el título de reel-01 entrando en el frame 106 —3,5 s— dentro de un
     * gancho que dura 5. Es justo la decisión suelta que Jaime señaló: la regla
     * estaba escrita («el gancho son 5 segundos, de los que el primero es
     * clave») y el render la ignoraba.
     *
     * Si hay camino de portada, manda el camino. Si no lo hay, se queda el
     * anclaje por palabra, que para una pieza sin gancho declarado es correcto.
     */
    entra: caminos.find((c) => c.tipo === "rotulo")?.at ?? entra,
    sostiene: SOSTIENE,
    cta,
    captions: marca.captions,
    desatura: marca.desatura,
    cortes: reloj.cortes,
    /**
     * Lado libre del cuadro: el contrario a donde está el sujeto. Sale del ancla
     * que midió `punch-ins.py` sobre la toma, no se elige a ojo.
     */
    lado: (() => {
      const e = plan.escenas[0];
      const cx = e.crop ? (e.crop.x + e.crop.w / 2) / 2160 : 0.5;
      return cx < 0.5 ? "der" : "izq";
    })(),
    /**
     * **Una sola fuente, y es `escena_desc`.** Jaime: *«unifica fuentes de
     * verdad, no pueden ser dos»*.
     *
     * `PANELES` era la segunda: un literal escrito a mano en este fichero que
     * llevaba cinco ciclos idéntico. Y no era inofensivo — de sus diez entradas,
     * **ocho caían en beats que el diseñador ya había descrito**, así que se
     * dibujaba encima de su trabajo. Su contenido se migró a `escena_desc`, y
     * ahí ya lo mueve él.
     */
    paneles: armarPaneles(panel, reloj, tableros, captions),
    // **Las que se piden, no todas.** Se probaron en TODAS las costuras y
    // quedaron mal —Jaime: «en el segundo 7 se ve raro; esos cortes de escena
    // no vale la pena dejarlos como cortes de escena»—: partian el rotulo por
    // la mitad, y para tapar un corte metian dos.
    //
    // La conclusion que se aplico fue `cortinillas: []` fijo, y con eso se
    // perdio la pieza entera: componente escrito, hueco aqui, `Reel.tsx`
    // dibujandolo, y ninguna forma de pedir una. Ahora sale de
    // `escena_desc.camara.transicion`, asi que sigue sin haber ninguna mientras
    // nadie la pida — y quien compone puede pedirla en la costura que la
    // necesita, que es lo que no existia.
    //
    // Lo que cubre las costuras por defecto sigue siendo el propio TABLERO, que
    // se estira `SOLAPE` frames por encima de la frontera: un L-cut, y lo que
    // la tapa ademas explica algo.
    cortinillas: cortinillasDe(slug, reloj, marco),
    // Y el virado y los filetes, que se piden por etapa y salen del plan.
    ...imagen,
    // Una costura con filete pedido ya está resuelta: el glitch encima serían
    // dos efectos en el mismo frame, que es ruido y no transición.
    glitch: glitchesDe(edl, reloj, [...tableros, ...cartas, ...imagen.filetes]),
    tarjetas: cartas,
    boards: tableros,
    cara: caraDe(slug),
  };

  // **Y se comprueba que cada tablero DE TIEMPO A LEERSE.** Jaime: *«todo
  // tablero tiene que tener tiempo suficiente de lectura»*. La regla llevaba
  // escrita en el contrato del disenador desde el principio —0,75 s por bloque
  // mas medio segundo— y no la miraba nadie.
  faltas.push(...lecturaCorta(tableros).map((f) => `${slug}: ${f}`));

  /**
   * **El subtítulo se compone al final**, cuando ya se sabe qué hay en pantalla.
   *
   * La condición es «ser la única capa de texto del instante», y eso no se puede
   * saber antes de tener tableros, tarjetas y paneles calculados. El panel
   * cuenta **todo el rato que está en cuadro**, no sólo mientras escribe: es un
   * objeto de texto grande y permanente, y un remate en Anton a cuerpo 128 al
   * mismo tiempo son dos capas gritando.
   *
   * **Y el rótulo, que es el vecino más cercano.** `BigTitle` vive en 0,62-0,76
   * de altura y la banda de subtítulo cierra en y=1160: treinta píxeles. Un
   * remate a dos bloques además del rótulo son tres objetos de texto apilados
   * ocupando el 29% del cuadro, y justo en el gancho —que es donde no hay
   * tablero ni tarjeta ni panel, así que la regla dispara—. Medido, chocaba en
   * dos de las seis.
   *
   * La ventana de cada beat sale del plan igual que la de un panel o un tablero,
   * así que el subtítulo compuesto cae donde cae el argumento y no cada N
   * segundos.
   */
  const ventanas = marco.beats.map((_, i) => [
    reloj.anclaDe(i + 1),
    reloj.anclaDe(i + 2),
  ]);
  const comp = componer(pieza.captions, [
    ...pieza.boards,
    ...pieza.tarjetas,
    ...pieza.paneles,
    // El CTA se pinta encima: componer ahi seria trabajar para nadie.
    ...(pieza.cta ? [{ at: pieza.cta.at * FPS, duration: pieza.cta.dur * FPS }] : []),
    { at: pieza.entra, duration: 9 + pieza.sostiene + 9 },
  ], ventanas);
  pieza.captions = comp.captions;
  // Las ventanas de beat viajan en el spec: sin ellas no se puede comprobar
  // desde fuera que cada beat lleve su tratamiento.
  pieza.ventanas = ventanas;
  pieza.escenas = porEscena(pieza, reloj);
  /**
   * **Bajo el contraste, el subtítulo no se compone.** Las dos cifras ya están
   * arriba y grandes; un remate que repita una de ellas es la misma información
   * en dos capas —«SE QUEDA CON 67.» debajo de un «$67»—, que es el aprendizaje
   * 38 otra vez. El subtítulo sigue, plano, que es lo que Jaime pidió:
   * *«manteniendo los subtítulos»*.
   */
  const contraste = contrasteDe(pieza.id, CONTRASTE[slug], pieza.captions);
  faltas.push(...[precioSinEscala(slug, pieza.captions)].filter(Boolean));
  if (sePisa(contraste, pieza.tableros ?? [])) {
    faltas.push(`${slug}: el contraste se pisaba con un tablero y se retira`);
    pieza.contraste = null;
  } else if (contraste) {
    for (const c of pieza.captions) {
      if (c.compuesto && c.at < contraste.at + contraste.duration &&
          c.at + c.duration > contraste.at) {
        delete c.compuesto;
      }
    }
    pieza.escenas = porEscena(pieza, reloj);
  }
  /**
   * **El contraste se calcula antes de quitar remates y se publica después.**
   *
   * Aquí `pieza.contraste` se asignaba al final, o sea DESPUÉS del bloque que
   * lee `pieza.contraste` para quitar los remates de debajo: la condición miraba
   * un campo que en ese punto siempre era `undefined`, así que la regla estaba
   * escrita y no corría nunca. Con el reel 2 sin remates compuestos hoy no se
   * notaba, y el día que tuviera uno habría salido «SE QUEDA CON 67.» debajo de
   * un «$67». Es la familia de C-14: una regla que no se puede cumplir por el
   * orden en que está escrita.
   *
   * Se separa en dos: el cálculo va arriba, donde hace falta, y la publicación
   * se queda aquí, para que la escena rellenada cuente ya sin el remate quitado.
   */
  pieza.rellenadas = rellenar(pieza);
  if (pieza.rellenadas) pieza.escenas = porEscena(pieza, reloj);
  if (contraste) pieza.contraste = contraste;
  pieza.compuestos = comp.n;
  return pieza;
});
// **Cada pieza lleva la huella de lo que se compuso.**
//
// Jaime, despues de tres dias viendo el mismo video: *«con una que no cuadre es
// suficiente para saber que eso no es lo que se mando a render»*. Tiene razon, y
// la consecuencia es que no hay que catalogar diferencias: hay que poder
// comparar lo dibujado con lo compuesto, de una sola vez.
//
// Hasta ahora la frescura se DEDUCIA comparando fechas de ficheros y de filas: si
// el EDL es mas nuevo que el mp4, si `escena_desc.fecha` cambio. Eso adivina, y
// se equivoca en las dos direcciones — no vio el bundle cacheado, y rehizo
// renders que estaban bien.
//
// La huella no adivina: es el sha1 de lo que el render va a dibujar. Si el
// fichero renderizado no lleva esta misma huella, lo que hay en disco NO es lo
// que se compuso. No hay tercera posibilidad.
for (const p of spec) {
  const {huella: _v, ...sinHuella} = p;
  p.huella = createHash("sha1").update(JSON.stringify(sinHuella)).digest("hex").slice(0, 12);
}

fs.writeFileSync("src/reels.json", JSON.stringify(spec, null, 1) + "\n");
// **Las comprobaciones van DESPUES de escribir el spec.** Estaban antes, asi
// que cuando una paraba el montaje `src/reels.json` se quedaba con el estado
// anterior y no habia forma de mirar por que fallo: los numeros que uno lee no
// son los que la hicieron saltar. Un artefacto que no existe cuando la
// comprobacion falla es un artefacto que no sirve para diagnosticar.
revisar(spec); faltasDelCierre(spec, faltas); // el cierre que falta tambien bloquea

/**
 * **El spec se reescribe al final, con lo que dijeron las comprobaciones.**
 *
 * Se escribe antes para que un fallo de comprobación no deje al montaje sin spec
 * (C-49), pero entonces la marca `bloqueado` —que sale de las comprobaciones— no
 * llegaba al fichero. Se escribe dos veces a propósito: la primera para no
 * perder el trabajo, la segunda para no perder el veredicto.
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
 * pieza peor, no una pieza inválida, y pararlo todo por eso deja seis vídeos sin
 * hacer por una descripción corta. Lo que sí hace es dejar de ser invisible.
 *
 * Lo declarado que no llega a producirse —el sonido que no suena, la figura que
 * no se traza— lo redacta `faltasDeclaradas()` en `escena.mjs`, que es donde se
 * acumula. Estaba escrito aquí dos veces, una por accidente: dos redacciones
 * del mismo aviso son dos sitios donde el día que cambie el formato queda uno
 * mal, que es el error que este fichero ya cometió con `donde()`.
 */
faltas.push(...faltasDeclaradas());
// Y la cortinilla pedida que no se pudo poner. Sale como falta y no como
// silencio por lo de siempre: una transicion que se declara y no aparece deja
// a quien compuso creyendo que la costura esta tapada.
faltas.push(...cortinillasSinSitio.map((c) => `cortinilla sin sitio — ${c}`));
if (faltas.length) {
  console.log(`\nFALTAS DE CAMINO — ${faltas.length}:`);
  for (const f of faltas) console.log(`  · ${f}`);
} else {
  console.log("\ncaminos: todas las indicaciones se cumplen");
}
