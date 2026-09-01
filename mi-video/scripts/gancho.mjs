/**
 * **El gancho: el camino que es distinto, y por eso está aparte.**
 *
 * Regla de Jaime, y es literalmente el motivo de que este fichero exista:
 * *«dije tres pero son más, y definitivamente el gancho es uno de ellos porque
 * es diferente»*. Los otros cuatro caminos acompañan lo que él dice. Éste
 * **compite contra el pulgar**: no tiene que explicar, tiene que impedir que el
 * vídeo se vaya. Por eso es el único que apila capas sobre la cara, el único
 * con más de una entrada por segundo y el único donde el subtítulo va en su
 * forma grande.
 *
 * Vivía dentro de `caminos.mjs` ocupando un tercio del fichero, y con él dentro
 * ninguna de las dos cosas cabía en la cabeza: los cuatro caminos de reposo son
 * quince líneas cada uno y éste es una composición entera con su propia ventana
 * de tiempo, sus propias constantes y sus propias exigencias.
 *
 * ## Coherente es la palabra que hace el trabajo
 *
 * *«Maximalismo coherente: romper el patrón y generar curiosidad.»* Apila, pero
 * apila con la paleta, la tipografía y las prohibiciones del canon. Nada de
 * rebote ni confeti — el maximalismo aquí es **densidad de entradas**, no
 * blandura.
 */
import { frames, reparte, sonar } from "./capa.mjs";
import { copyDeclarado, donde, esTipografico, figuraDe, sonidoDe } from "./escena.mjs";

/** El gancho son 5 s y el primero es el que decide. Igual que en `trato.py`. */
export const GANCHO_S = 5.0;
export const GANCHO_CLAVE_S = 1.0;

/**
 * La primera entrada, antes de esto. En frames.
 *
 * Doce frames son 0,4 s: lo que tarda el pulgar en decidir es ~1,3 s, así que
 * si la primera cosa que se mueve llega en el segundo 1, ya llegó tarde. El
 * plano puede estar quieto; la pantalla no.
 */
const PRIMERA_ENTRADA = 12;

/** Entradas mínimas dentro del gancho. Menos de esto no es maximalismo. */
const ENTRADAS_MIN = 3;

/**
 * **portada — el gancho.** Los primeros 5 s, *«de los que el primero es clave»*.
 *
 * Indicaciones, y todas se comprueban en `exige`: cara y máxima expresividad,
 * mucho movimiento dentro de la toma, ganchos visuales múltiples, sonidos que
 * acompañan al título y a los subtítulos animados.
 */
export const portada = {
  nombre: "gancho",
  manda: "toma",
  porque:
    "compite contra el pulgar, no explica: la única que apila sobre la cara",
  capas(ctx) {
    const { at, duration, desc, det, lado } = ctx;
    // **El gancho dura 5 s, no lo que dure el segmento.** Si la toma que abre
    // dura 2 s, las capas siguen sobre la escena siguiente hasta cerrar los 5:
    // el gancho es una ventana de la pieza, no una propiedad del corte.
    const fin = at + frames(GANCHO_S);
    void duration;
    const clave = at + frames(GANCHO_CLAVE_S);
    const tipo = esTipografico(desc?.grafico);
    const fig = tipo ? null : figuraDe(desc);
    const motion = sonidoDe(desc?.sonido, donde(desc), desc);
    const out = [];

    // 1 · El plano se mueve dentro de sí mismo. No es un plano fijo con cosas
    //     encima: la toma empuja. Va primero porque no necesita entrada.
    out.push({
      tipo: "punch",
      at,
      duration: fin - at,
      props: { desde: 1.0, hasta: 1.08 },
    });

    // 2 · El rótulo entra con movimiento —por bloques desde el lado libre—,
    //     no con un fundido. Un fundido no rompe ningún patrón.
    const tR = at + PRIMERA_ENTRADA;
    out.push({
      tipo: "rotulo",
      at: tR,
      duration: fin - tR,
      props: { lado, entrada: "bloque" },
    });
    out.push(...sonar("whoosh", tR));

    // 3 · La figura de la escena, entrando desde fuera del cuadro. Sólo si la
    //     descripción la nombra: el catálogo de `FIGURAS` no adivina.
    if (fig) {
      const [t1, t2] = reparte(2, clave, fin - frames(0.6));
      out.push({
        tipo: "figura",
        at: t1,
        duration: fin - t1,
        props: { figura: fig, oro: true, lado, dura: fin - t1 },
      });
      out.push(...sonar("draw", t1));
      // 4 · Y el elemento geométrico que entra y sale — el segundo gancho
      //     visual, con el sonido que la escena describió para él.
      out.push({
        tipo: "remate",
        at: t2,
        duration: fin - t2,
        props: { lado, tinte: "gold" },
      });
      out.push(...sonar(motion ?? "land", t2));
    }

    // 3bis · El gancho tipografico. Mismo trabajo que la figura —segundo y
    //     tercer gancho visual dentro de los 5 s— pero con el material que la
    //     escena pidio: tipo, en versales, entrando por bloques.
    //     Y **con su propio texto**: el que la escena declaró en versales. Sin
    //     él la capa no entra — repetir el rótulo es peor que una capa menos,
    //     y `exige` lo cuenta para que lo resuelva quien describe.
    const literal = tipo ? copyDeclarado(desc) : null;
    if (tipo && literal) {
      const [t1, t2] = reparte(2, clave, fin - frames(0.6));
      out.push({
        tipo: "bloque",
        at: t1,
        duration: fin - t1,
        props: { lado, tinte: "gold", entrada: "corte", texto: literal },
      });
      out.push(...sonar("mark", t1));
      out.push({
        tipo: "remate",
        at: t2,
        duration: fin - t2,
        props: { lado, tinte: "navy", texto: literal },
      });
      out.push(...sonar(motion ?? "land", t2));
    }

    // 5 · El subtítulo, en su forma grande. En el gancho el subtítulo no
    //     acompaña: es una de las capas que enganchan.
    out.push({
      tipo: "subtitulo",
      at,
      duration: fin - at,
      props: { forma: "grande", suena: "type" },
    });

    return out.map((c) => ({ ...c, camino: "portada", beat: det.beat }));
  },
  exige(capas, ctx) {
    const faltas = [];
    const entradas = capas.filter(
      (c) => c.tipo !== "sonido" && c.tipo !== "punch",
    );
    if (entradas.length < ENTRADAS_MIN)
      faltas.push(
        `el gancho lleva ${entradas.length} entradas y necesita ${ENTRADAS_MIN}:` +
          " «ganchos visuales múltiples»",
      );
    const primera = Math.min(...entradas.map((c) => c.at - ctx.at));
    if (!(primera <= PRIMERA_ENTRADA))
      faltas.push(
        `la primera entrada llega en el frame ${primera} y el primer segundo` +
          " es el que decide",
      );
    if (!capas.some((c) => c.tipo === "punch"))
      faltas.push("el gancho no se mueve dentro de la toma");
    // **El gancho tipográfico sin copy declarado no entra, y se cuenta.**
    // La escena pide tipo —su `grafico` habla de versales— y nadie escribió
    // qué dice. Antes eso se rellenaba con la primera línea del rótulo y el
    // gancho se repetía a sí mismo; ahora falta una capa y **se dice**, que
    // es lo que lo manda a quien compone la escena. Es editorial: no sale de
    // aquí.
    if (esTipografico(ctx.desc?.grafico) && !copyDeclarado(ctx.desc))
      faltas.push(
        "el gancho pide tipo y la escena no declara qué dice:" +
          " escríbelo en `escena_desc.tablero`, que es de donde lo lee el" +
          " render. Deducirlo de la prosa seria codigo decidiendo el copy.",
      );
    if (
      !capas.some((c) => c.tipo === "subtitulo" && c.props.forma === "grande")
    )
      faltas.push("el subtítulo del gancho no va en su forma grande");
    // Cada movimiento suena. Se comprueba que no haya entrada muda salvo el
    // subtítulo, que trae su sonido dentro.
    for (const c of entradas) {
      if (c.tipo === "subtitulo") continue;
      if (
        !capas.some((s) => s.tipo === "sonido" && Math.abs(s.at - c.at) <= 2)
      )
        faltas.push(`la capa «${c.tipo}» del gancho entra sin sonido`);
    }
    if (!figuraDe(ctx.desc) && !esTipografico(ctx.desc?.grafico))
      faltas.push(
        "la escena del gancho no describe ni figura dibujable ni composición" +
          ` de tipo: «${ctx.desc?.grafico ?? "sin descripción"}»`,
      );
    return faltas;
  },
};
