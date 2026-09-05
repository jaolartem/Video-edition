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
import { CONSTRUIDAS, revisarTablero } from "../formas.mjs";
import { enPantalla } from "./lectura.mjs";

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
 * El pie del tablero, **de la fuente comprobada y no de una cadena a mano**.
 *
 * `fuente` y `condicion` se escribían por pieza dentro del spec. Es la trampa
 * que `fuentes.py` vino a quitar —no escala a 16-50 anuncios y no se puede
 * auditar— y era el último tramo sin conectar: el paso ya guardaba el respaldo
 * en `dato`, y el tablero seguía imprimiendo el literal.
 *
 * Importa más de lo que parece por lo que decía cada uno. El literal era
 * *«$30,000 sobre $180,000 de utilidad»*, que es de donde sale la resta pero no
 * de donde sale la verdad. Comprobado contra la CRA la diferencia real es
 * 33.500 $ y —esto es lo que cambia el mensaje— **buena parte es diferimiento**.
 * Sin esa condición el espectador entiende «me ahorro 30.000 al año», y eso la
 * fuente no lo sostiene.
 *
 * **Y por eso admite `parcial`.** Sólo pintaba las cifras marcadas `si`, o sea
 * las que se sostienen sin matices — y las que más necesitan pie son justo las
 * otras: las que son ciertas **bajo una condición**. Una cifra así sin su
 * condición es peor que no ponerla, porque parece general. Regla de Jaime:
 * *«si esa parte no se sostiene, la aclaramos en pie de foto»*.
 *
 * Si no hay dato comprobado se deja lo que hubiera: una pieza sin verificar no
 * se queda muda de golpe.
 */
export const pieDe = (slug, beat, props) => {
  try {
    // **El pie es el de la cifra que SE ROTULA, no el de la mas larga.**
    //
    // Esto ordenaba `by length(d.cifra) desc`, o sea elegia la fila cuyo texto
    // de cifra ocupara mas caracteres. En reel-07 e3 eso saca «53.53%
    // (corroboracion independiente)» y el tablero rotula **32 %**: el pie salia
    // con la nota de metodo de PwC debajo de una cifra que no es la suya, que es
    // peor que no poner pie — parece respaldar lo que no respalda.
    //
    // Se busca la fila cuya cifra aparece en lo que el tablero pinta. Si no se
    // puede saber, manda la que MAS necesita el pie: una proyeccion
    // (`respalda = 'parcial'`) tiene condiciones que hay que decir; una cifra
    // publicada se sostiene sola. Eso es un criterio; la longitud no era ninguno.
    const pintado = JSON.stringify(props ?? {});
    const filas = db.prepare(
      "select f.rotulo, d.condiciones, d.cifra, d.respalda from dato d" +
      "  left join fuente f on f.id = d.fuente_id" +
      "  join video v on v.id = d.video_id" +
      " where v.slug = ? and d.etapa_orden = ?" +
      "   and d.respalda in ('si','parcial')",
    ).all(slug, beat);
    // **Y se comparan NORMALIZADAS.** La fila dice `53.53%` y el tablero puede
    // pintar «53,53 %» —coma decimal y espacio antes del signo, que es como se
    // escribe en español—: sin normalizar no casan, la busqueda falla en
    // silencio y el pie cae al `?? filas[0]`, o sea **el pie de OTRA cifra
    // debajo de esta**. Es peor que no poner pie: parece respaldar lo que no
    // respalda, que es justo lo que el comentario de arriba vino a arreglar por
    // la puerta de la longitud.
    const igual = (s) => s.replace(/\s+/g, "").replace(/,(\d)/g, ".$1");
    const plano_ = igual(pintado);
    const suya = filas.find((x) => {
      const n = String(x.cifra ?? "").match(/[\d.,]+\s*%?|\$[\d.,]+/);
      return n && plano_.includes(igual(n[0]));
    });
    const r = suya
      ?? filas.find((x) => x.respalda === "parcial")
      ?? filas[0];
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
          return JSON.parse(f.tablero)?.kind !== "tipo";
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
      return { beat: Number(f.etapa_orden), kind: t.kind, props: t.props };
    }).filter((b) => {
      for (const m of revisarTablero(b.kind, b.props))
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
  db.prepare(
    "select corrige_dice, corrige_es from escena_desc" +
    " where video_slug = ? and corrige_dice is not null",
  ).all(slug);
