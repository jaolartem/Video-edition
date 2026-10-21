/**
 * **Lo que el que monta lee de `ads/decisiones.db`.**
 *
 * La pregunta que ordena el proyecto es *«¿de dónde lo lee el que monta?»*, y
 * este fichero es la respuesta para todo lo que no está en un JSON del disco:
 * qué versión está aprobada, qué tablero describió el diseñador, con qué fuente
 * se respalda cada cifra y qué hay que corregir encima del subtítulo.
 *
 * Está separado por la misma razón que `material.mjs`: **mezclar la consulta con
 * la decisión es lo que hace que nadie sepa de dónde sale un dato**. Aquí no se
 * decide nada — se pregunta, y lo que vuelve se devuelve tal cual.
 *
 * La base **se abre una vez para todo el lote**. Son 54 filas y se abría dos
 * veces por corrida, una para las aprobaciones y otra para el resto.
 */
import { DatabaseSync } from "node:sqlite";
import { CONSTRUIDAS, canonico, revisarTablero, sinSujeto } from "../formas.mjs";
import { marcoDe, precioVigente } from "./material.mjs";
import { panelLargo } from "./tableros.mjs";

const db = new DatabaseSync("ads/decisiones.db");

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
export const aprobadas = (() => {
  try {
    return new Set(
      db.prepare(
        "select v.slug from aprobacion a" +
          " join version ve on ve.id = a.version_id" +
          " join video v on v.id = ve.video_id" +
          " where a.veredicto = 'aprobada'",
      ).all().map((r) => r.slug),
    );
  } catch {
    return new Set();
  }
})();

/**
 * **El pie del tablero NO vive aquí, y ésta es la lápida.**
 *
 * Aquí estaba `pieDe`, y era el que corría. `scripts/reels/cifras.mjs` —escrito
 * para ser el único dueño de las cuatro preguntas sobre una cifra— **no lo
 * importaba nadie**: su `pieDe` y su guarda `sinRespaldo` estaban completos y
 * muertos, y esta copia los suplantaba con criterios peores.
 *
 * Tres diferencias, y las tres se veían en el lote del 6 de septiembre:
 *
 * 1. **Casaba por contención de `JSON.stringify(props)`**, no por token
 *    normalizado. Un `53,53 %` del diseñador contra un `53.53%` de la base no
 *    casaban, y el pie caía al `?? filas[0]`: el de OTRA cifra.
 * 2. **Pisaba lo declarado.** El spread iba después de `b.props` en el spec, así
 *    que la condición que el diseñador escribió para esa cifra exacta se
 *    sustituía sin una línea de aviso. `reel-07 e3` declaraba la línea corta y
 *    buena y salió con el rótulo largo de `dato`.
 * 3. **Recortaba a 25 palabras con puntos suspensivos**, que es justo lo que
 *    Jaime prohibió: *«sin abreviar hasta que deje de decir nada»*.
 *
 * No se arregló aquí: se retiró. Dos lectores del mismo dato con criterios
 * distintos es la divergencia que este proyecto persigue, y el bueno ya estaba
 * escrito.
 */

/**
 * Sólo pasan los `kind` que `Ad.tsx` sabe dibujar con componente propio. El
 * resto sale con `TableroDeclarado`, que es una mejora pendiente y no un fallo.
 */
// **No es una lista suya: es la de quien despacha.** Habia aqui una copia
// escrita a mano y se quedo vieja el dia que se construyeron dos formas — el
// parte seguia diciendo «sale con TableroDeclarado» de dos tableros que ya se
// dibujaban con su componente. La segunda copia no dio error: dio un informe
// que mandaba a construir lo que ya estaba hecho.
const DIBUJA = CONSTRUIDAS;

// `canonico` vive en `formas.mjs`, con las formas que nombra (C-547).

/**
 * **El tablero sale de la DESCRIPCIÓN, no de un literal por pieza.**
 *
 * `TABLEROS[slug]` era un objeto escrito a mano, uno por reel: el
 * `if (slug === …)` que el proyecto prohíbe. La consecuencia no era estética:
 * **re-describir una etapa no cambiaba su tablero.** El paso que compone
 * escribía una descripción nueva en la base, el render seguía leyendo el
 * literal, y la pieza salía idéntica. Jaime, después de tres entregas iguales:
 * *«la decisión de componer está escuchando las indicaciones viejas»*.
 *
 * Ahora el tablero es un campo de `escena_desc`, escrito por quien compone y
 * leído por quien monta. Ése es el único orden en el que una corrección llega a
 * la pantalla.
 *
 * ## Dos guardas dentro, y las dos cazan lo que no avisa
 *
 * **`escena_desc.tablero` tiene DOS lectores, y sólo uno dibuja un tablero.** El
 * otro es `copyDeclarado()` en `caminos.mjs`: el gancho tipográfico declara ahí
 * la palabra que sale en pantalla porque `describir.mjs` lo exige por su nombre.
 * Sin la guarda esa fila entraba igual y salía como `board` en el segundo 0,0:
 * `Ad.tsx` no reconoce el `kind`, cae en `TwoPaths` por defecto y revienta. O
 * sea, declarar el gancho como pedía el paso anterior tumbaba el render entero.
 *
 * **Y el tablero se comprueba contra SU forma, aquí dentro.** Jaime: *«integra
 * todo al contrato, no debe ser por fuera del pipeline»*. `reel-04 e3` traía una
 * premisa de 54 caracteres contra un tope de 42 y `assertShort` **tumba el
 * render** —no advierte— con las seis piezas ya cortadas. Encontrarlo aquí
 * cuesta milisegundos; encontrarlo allí cuesta la corrida entera.
 *
 * @returns `{tableros, declarados, faltas}` — `declarados` es lo que el
 *   diseñador escribió y `tableros` lo que sobrevive a las dos guardas. Que la
 *   segunda cifra sea menor que la primera lo denuncia quien monta: **nadie
 *   comparaba las dos**, y por eso la base decía 38 tableros descritos y la
 *   pantalla mostraba 9 sin que ninguno de los dos lados pareciera equivocado.
 */
export function tablerosDe(slug) {
  const faltas = [];
  // **Se cuentan los comparables, y `tipo` no lo es.**
  //
  // Esto contaba TODOS los tableros declarados y abajo se filtran los de
  // `kind: "tipo"` —que existen y se dibujan, sólo que por el camino
  // tipográfico—. La resta acusaba entonces una falta que no existe: «declaró 3
  // y sólo llegan 2», y el paso terminaba en código 1.
  //
  // No saltaba porque hasta hoy nadie había diseñado un gancho: los rótulos
  // salían de un literal. La primera composición de un gancho en la historia
  // del proyecto lo disparó, que es justo cuando una guarda mal puesta hace más
  // daño — bloquea lo que viene a estrenar.
  //
  // La comparación sigue haciendo su trabajo, que es el de C-14x: denunciar que
  // la base diga 38 y la pantalla muestre 9. Sólo que ahora compara lo mismo
  // contra lo mismo.
  const declarados = (() => {
    try {
      return db.prepare(
        "select tablero from escena_desc where video_slug = ?" +
        " and tablero is not null and tablero <> ''",
      ).all(slug).filter((f) => {
        try {
          return canonico(JSON.parse(f.tablero)?.kind) !== "tipo";
        } catch {
          return true;
        }
      }).length;
    } catch {
      return 0;
    }
  })();
  let tableros;
  try {
    tableros = db.prepare(
      "select etapa_orden, tablero from escena_desc" +
      " where video_slug = ? and tablero is not null and tablero <> ''" +
      " order by etapa_orden",
    ).all(slug).map((f) => {
      const t = JSON.parse(f.tablero);
      return { beat: Number(f.etapa_orden), kind: canonico(t.kind), props: t.props };
    }).filter((b) => {
      for (const m of [...revisarTablero(b.kind, b.props), ...panelLargo(b.props)])
        faltas.push(`${slug} e${b.beat}: ${m}`);
      // **Y la regla de la cara, sólo donde la pieza la declara** (T-06): aquí
      // se sabe de qué pieza es el tablero, en `formas.mjs` no.
      if (marcoDe(slug)?.cara === "siempre")
        for (const m of sinSujeto(b.kind, b.props))
          faltas.push(`${slug} e${b.beat}: ${m}`);
      return true;
    }).filter((b) => {
      if (b.kind === "tipo") return false;
      if (!DIBUJA.has(b.kind))
        console.log(
          `    ${slug} e${b.beat}: «${b.kind}» sale con TableroDeclarado;` +
          ` construir su componente es una mejora, no un bloqueo.`,
        );
      return true;
    });
  } catch {
    tableros = [];
  }
  return { tableros, declarados, faltas };
}

/** La descripción de cada escena, por etapa: lo que el diseñador escribió. */
export const descDe = (slug) =>
  Object.fromEntries(
    db.prepare("select * from escena_desc where video_slug = ?")
      .all(slug)
      .map((r) => [r.etapa_orden, r]),
  );

/**
 * Las correcciones de cumplimiento que declaró el paso de composición: lo que
 * se dijo mal y lo que dice la verdad. Ver `corregirLoDicho` en
 * `subtitulos.mjs`, que es quien las coloca.
 */
export const correccionesDe = (slug) =>
  expandeCorrecciones(db.prepare(
    "select etapa_orden, corrige_dice, corrige_es, corrige_marca from escena_desc" +
    " where video_slug = ? and corrige_dice is not null",
  ).all(slug)).map((c) => ({ ...c, corrige_es: conPrecio(c.corrige_es) }));

/**
 * **Una fila por corrección, aunque la etapa guarde varias** (C-465). Con dos,
 * las columnas llevan dos listas JSON paralelas (`dominio/escena.py ::
 * columnas_de_corrige`); quien lee las necesita separadas.
 */
export const expandeCorrecciones = (filas) => filas.flatMap((f) => {
  const d = f.corrige_dice;
  if (typeof d !== "string" || !d.startsWith("[")) return [f];
  try {
    const dice = JSON.parse(d);
    const es = JSON.parse(f.corrige_es);
    // La marca va en paralelo si alguna no la lleva (C-630).
    const marca = f.corrige_marca ? JSON.parse(f.corrige_marca) : [];
    return dice.map((x, i) => ({ ...f, corrige_dice: x, corrige_es: es[i],
                                 corrige_marca: marca[i] ?? null }));
  } catch {
    return [f];
  }
});

/**
 * **`{precio}` es el importe de hoy, no un literal.** Jaime, 11-9-2026:
 * *«corrige el precio en pantalla»*. La voz de reel-04 y reel-07 dice «20
 * dólares»; escrito «30», la corrección mentiría el 16, cuando sube a 40.
 */
export const MARCA_PRECIO = "{precio}";
const conPrecio = (es) => {
  if (typeof es !== "string" || !es.includes(MARCA_PRECIO)) return es;
  const hoy = precioVigente()?.importe;
  return hoy == null ? es : es.replaceAll(MARCA_PRECIO, String(hoy));
};
