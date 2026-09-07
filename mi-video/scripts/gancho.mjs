/**
 * **El gancho: el camino que es distinto, y por eso está aparte.**
 *
 * Regla de Jaime, y es literalmente el motivo de que este fichero exista:
 * *«dije tres pero son más, y definitivamente el gancho es uno de ellos porque
 * es diferente»*. Los otros cuatro caminos acompañan lo que él dice. Éste
 * **compite contra el pulgar**: no tiene que explicar, tiene que impedir que el
 * vídeo se vaya.
 *
 * ## La lámina que había, y por qué se cambió entera
 *
 * Jaime, 6-9-2026, con los siete puestos uno al lado del otro al segundo 1,6:
 * *«en todas hay que revisar el hook»*. El diagnóstico era de lote y estaba
 * medido: **los siete eran la misma lámina** —rótulo amarillo en dos líneas
 * abajo, subtítulo negro encima, plano medio—, con el rótulo en el tercio que la
 * interfaz de Meta tapa, **dos bloques de texto compitiendo en el primer
 * segundo**, todo quieto y nada jugando con él; y pictogramas de trazo sueltos
 * en tres de las siete.
 *
 * **Y el fallo no era que se parecieran.** *«No necesariamente tiene que ser
 * diferente»*: un tratamiento constante en el lote es un activo de marca. El
 * fallo era que **esa** lámina es mala. El sistema es uno y se aplica siete
 * veces; lo que cambia de pieza a pieza es lo que dice.
 *
 * ## Lo que este camino apila ahora
 *
 * Lo aprobado en `src/preview-gancho.tsx` —*«me gusta cómo se ve el hook»*—:
 * el rótulo **detrás de su cabeza** en el tercio de arriba, en dos líneas
 * escalonadas y sin rebote, su silueta recortada delante, y **sin subtítulo
 * compitiendo** en los primeros 2 s. La geometría y los tiempos viven en
 * `src/brand/gancho.json`, en un solo sitio, y quien comprueba que se cumplen es
 * `scripts/reels/portada.mjs`.
 *
 * **Y aquí ya no entra un pictograma.** La regla que lo pedía era «maximalismo =
 * densidad de entradas», y es justo la que producía los dos bloques peleándose y
 * las figuras sueltas. La que manda ahora la dio él: *«la composición disminuye
 * carga cognitiva y es coherente con el sistema visual»*, *«y estético»*. Una
 * cosa que leer en el primer segundo, no tres.
 */
import { frames, sonar } from "./capa.mjs";
import { rotuloDe } from "./escena.mjs";
import { CANON, colocar } from "./reels/rotulo.mjs";

/**
 * El gancho son 5 s y el primero es el que decide.
 *
 * **El número vive en `src/brand/gancho.json`** y no aquí: lo necesita también
 * el paso que recorta su silueta para esa ventana (`dominio/sujeto.py`), y
 * mientras estuvo escrito aquí ese recorte se hacía a mano con el número
 * tecleado en la línea de comandos.
 */
export const GANCHO_S = CANON.dura;
export const GANCHO_CLAVE_S = 1.0;

/**
 * La primera entrada, antes de esto. En frames.
 *
 * Doce frames son 0,4 s: lo que tarda el pulgar en decidir es ~1,3 s, así que
 * si la primera cosa que se mueve llega en el segundo 1, ya llegó tarde. El
 * plano puede estar quieto; la pantalla no.
 */
const PRIMERA_ENTRADA = 12;

/**
 * **La ventana quieta más larga de los tres segundos que deciden.**
 *
 * Jaime, 6-9-2026: *«con mucho movimiento, porque la idea es capturar la
 * atención esos tres segundos»*. Y el defecto que lo motiva estaba medido: lo
 * que había entraba en el frame 2 y en el 15, terminaba en el 28, **y de ahí a
 * los tres segundos no se movía nada**. Quieto no es lo contrario de rebotar.
 *
 * Se miden las ENTRADAS —cada palabra y el trazo del filete—, no el punch: el
 * punch está siempre, así que contarlo dejaría la comprobación vacía. La
 * ventana cierra en `armado`, que es donde el bloque queda montado.
 *
 * Vive aquí y no en la puerta porque es una indicación del camino, como «el
 * gancho no se mueve dentro de la toma» de dos líneas más abajo.
 */
function quietoEn(props) {
  const tramos = [
    ...(props.palabras ?? []).flat().map((f) => [f, f + CANON.entrada]),
    [props.regla ?? 0, (props.regla ?? 0) + (props.reglaDura ?? 0)],
    [CANON.armado, CANON.armado],
  ].sort((a, b) => a[0] - b[0]);
  let hasta = 0;
  for (const [de, a] of tramos) {
    if (de - hasta > CANON.quieto)
      return [
        `el gancho se queda quieto ${de - hasta} frames seguidos (del ${hasta}` +
          ` al ${de}) dentro de los tres segundos que deciden, y el tope son` +
          ` ${CANON.quieto}. Ahí ya no compite contra el pulgar: es una foto` +
          ` con texto.`,
      ];
    hasta = Math.max(hasta, a);
  }
  return [];
}

/**
 * **portada — el gancho.** Los primeros 5 s, *«de los que el primero es clave»*.
 *
 * Indicaciones, y todas se comprueban en `exige`: el rótulo detrás de su cabeza
 * y en el tercio de arriba, entrando escalonado y sin rebote; movimiento dentro
 * de la toma; el subtítulo en su forma grande, callado los primeros 2 s.
 */
export const portada = {
  nombre: "gancho",
  manda: "toma",
  porque:
    "compite contra el pulgar, no explica: la única que apila sobre la cara",
  capas(ctx) {
    const { at, duration, det, slug, lineas, desc } = ctx;
    // **El gancho dura 5 s, no lo que dure el segmento.** Si la toma que abre
    // dura 2 s, las capas siguen sobre la escena siguiente hasta cerrar los 5:
    // el gancho es una ventana de la pieza, no una propiedad del corte.
    const fin = at + frames(GANCHO_S);
    void duration;
    const out = [];

    // 1 · El plano se mueve dentro de sí mismo. No es un plano fijo con cosas
    //     encima: la toma empuja. Va primero porque no necesita entrada.
    //
    //     **Y se cierra a velocidad constante, que es lo que pidió Jaime**:
    //     *«el encuadre cerrándose despacio»*. Con la curva del sistema
    //     —`inOut`— el encuadre arranca parado y a los 15 frames aún no se ha
    //     movido; eso es medio segundo quieto justo donde el pulgar decide.
    //     Lineal es un travelling: nunca acelera, nunca frena y **nunca para**,
    //     así que los tres segundos tienen movimiento de fondo por debajo de
    //     todo lo que entra encima.
    out.push({
      tipo: "punch",
      at,
      duration: fin - at,
      props: { desde: 1.0, hasta: 1.08, curva: "lineal" },
    });

    // 2 · El rótulo, DETRÁS de su cabeza. Dos líneas escalonadas en el tercio
    //     de arriba y su silueta delante: el texto le pasa por detrás, que es
    //     lo único que este camino tiene que conseguir.
    //
    //     El recorte con alfa lo produce `scripts/text-behind.py` sobre este
    //     mismo corte. Si no está, `reels/portada.mjs` lo dice y para: caerse a
    //     la lámina de antes en silencio es cómo sobrevivió cuatro vueltas.
    const src = `recorte/${slug}-e${det.beat}.webm`;
    // Dónde cae el bloque y con qué cuerpo sale de `colocar`: el sitio lo manda
    // **su coronilla**, que midió la pasada del recorte y dejó en su ficha. Un
    // `arriba` fijo se comía la palabra en una pieza y flotaba en otra.
    // **Y de qué lado cae, y cuánto le tapa la cabeza, salen de lo mismo.**
    // Jaime, pidiendo variedad sobre los siete ya rehechos: *«el lado y la
    // altura los decide DÓNDE ESTÁ ÉL, no el gusto: el texto ocupa el hueco que
    // deja su cuerpo»*. La ficha del recorte trae las dos medidas.
    // **Y cuál de las líneas golpea lo dice quien compone.** El canon lo
    // declaraba —*«el oro va en la mitad que golpea»*— y el render lo clavaba
    // al último renglón: una pieza cuyo golpe está arriba lo habría dicho en
    // oro y pequeño a la vez. `null` es «la de siempre», la última.
    const { cuerpos, arriba, lado, gesto, oro, coronilla, anchos, palabras,
            regla, reglaDura } =
      colocar(lineas, src, rotuloDe(desc)?.oro ?? lineas.length - 1);
    out.push({
      tipo: "titular",
      at,
      duration: fin - at,
      props: {
        lineas,
        src,
        cuerpos,
        arriba,
        lado,
        gesto,
        oro,
        coronilla,
        anchos,
        // **Cada palabra entra en su frame, no cada línea.** Los tiempos los
        // resuelve `reels/rotulo.mjs :: ritmo` y viajan resueltos: el
        // componente dibuja lo que le llega y la puerta comprueba el mismo
        // número que se dibuja.
        palabras,
        regla,
        reglaDura,
        // Cada línea entra en su frame; se declaran para que la puerta pueda
        // comprobar el escalonado sin volver a calcularlo.
        entradas: lineas.map((_, i) => at + CANON.entradaEn + i * CANON.escalon),
      },
    });

    // **El sonido va en el frame del movimiento, y son movimientos distintos.**
    // La línea que acompaña aterriza con un clic seco (`mark`) y la que golpea
    // con el golpe grave (`land`) — el remate suena a remate—; el filete se
    // traza, así que suena el trazo. Antes había un `whoosh` solo: un barrido
    // sobre un texto que ni barre ni se desplaza es sonido sin movimiento que
    // lo justifique, que es la regla que este proyecto tiene escrita.
    for (let i = 0; i < lineas.length; i++)
      out.push(...sonar(i === oro ? "land" : "mark", at + palabras[i][0]));
    out.push(...sonar("draw", at + regla));

    // 3 · El subtítulo, en su forma grande, y desde el primer frame. Lo que le
    //     pasa en el gancho es que BAJA —`reels/portada.mjs ::
    //     bajarEnElGancho`—: el rótulo se queda el hueco de encima de su cabeza
    //     y el cc su franja, así que no se turnan, conviven.
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
    const t = capas.find((c) => c.tipo === "titular");
    if (!t) {
      faltas.push("el gancho no lleva rótulo detrás de su cabeza");
    } else {
      // **Una línea o dos lo decide la frase, no el sistema.** Esto exigía dos
      // siempre, y Jaime lo corrigió al pedir variedad: *«"NADA HA PASADO"
      // aguanta una sola línea enorme; "TRIMESTRE NORMAL / LA CUENTA MÁS ALTA"
      // pide dos»*. Lo que sigue sin poder pasar es ninguna y son tres: sin
      // rótulo no hay gancho, y tres renglones no se leen a velocidad de scroll.
      const n = (t.props.lineas ?? []).length;
      if (n < 1 || n > 2)
        faltas.push(
          `el rótulo del gancho tiene ${n} línea(s): son una o dos, y cuál de` +
            " las dos lo decide la frase",
        );
      const e = t.props.entradas ?? [];
      if (e.length > 1 && e[1] - e[0] < 1)
        faltas.push(
          "las dos líneas del gancho entran a la vez y tienen que entrar" +
            " escalonadas: un bloque que aparece de golpe no se lee en orden",
        );
      faltas.push(...quietoEn(t.props));
    }
    const entradas = capas.filter(
      (c) => c.tipo !== "sonido" && c.tipo !== "punch",
    );
    const primera = Math.min(...entradas.map((c) => c.at - ctx.at));
    if (!(primera <= PRIMERA_ENTRADA))
      faltas.push(
        `la primera entrada llega en el frame ${primera} y el primer segundo` +
          " es el que decide",
      );
    if (!capas.some((c) => c.tipo === "punch"))
      faltas.push("el gancho no se mueve dentro de la toma");
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
    return faltas;
  },
};
