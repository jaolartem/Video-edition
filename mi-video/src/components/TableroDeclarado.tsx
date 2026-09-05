import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, layout, tracking, videoText } from "../brand/tokens";
import { limit } from "../brand/copy";

/**
 * Dibuja **lo que el diseñador declaró**, sea cual sea la forma que le puso.
 *
 * Regla de Jaime, dicha hasta que la entendí: *«lo que hace el diseñador no
 * llega a renderizarse»*, *«el punto es que lo que sale del diseñador sea lo que
 * renderice»*.
 *
 * ## Por qué hacía falta
 *
 * Al abrir el catálogo de formas —*«las limitaciones de código se acaban de
 * inmediato»*— los diseñadores montaron 38 tableros con 23 formas. `Ad.tsx`
 * sabía dibujar **cuatro**, así que 29 caían por el final del ternario y **no
 * salían en pantalla, sin decirlo**. El resultado es el que él vio: tres ciclos
 * de cambios duros y el mismo vídeo, porque lo único visible seguía siendo un
 * literal escrito a mano cinco ciclos antes.
 *
 * Esto no sustituye a construir cada forma: `Desproporcion` tiene que dibujar
 * dos bloques cuya ALTURA es la razón, y eso no sale de aquí. Lo que hace es que
 * **el trabajo del diseñador aparezca desde el primer render**, con su copy, su
 * jerarquía y su familia — y que cada forma se promueva a componente propio
 * cuando se gane el sitio, en vez de no existir mientras tanto.
 *
 * ## Cómo decide qué dibujar, sin interpretar
 *
 * No sabe qué es un `Filtro` ni un `PieLink`. Sabe lo que el canon fija:
 *
 * - **Un texto por línea, en orden de declaración.** El diseñador escribe los
 *   props en el orden en que se leen; respetarlo es respetar su composición.
 * - **La jerarquía sale de la longitud**, que es lo que el canon ya usa para
 *   sus roles: lo corto va grande en versales, lo largo va en cuerpo de lectura.
 * - **El oro es uno solo.** Lo dice `props.oro`, y si no lo dice se le da al
 *   primer texto corto. Si hay tres cosas en oro, dos sobran.
 * - **La familia decide el fondo**: `cargada` va sobre el plano, `tranquila`
 *   sobre placa lisa. No se inventa: viene declarada.
 *
 * Lo que **no** hace es rellenar huecos. Un tablero sin textos no dibuja nada y
 * eso se ve, que es mejor que dibujar una caja vacía con pinta de tablero.
  * @clase tablero
*/

/** Props que son estructura, no texto en pantalla. */
const NO_ES_TEXTO = new Set([
  // **`duracion` la mete el motor, no quien compone.** `armarTableros` la anade
  // a los props para saber cuanto dura el tablero, y esto la trataba como una
  // linea mas: el tablero del precio del reel-01 salia rotulando **«430»** en
  // versales, junto a $576 y $20. Un numero que nadie escribio, en el sitio
  // donde una cifra de mas es una cifra falsa.
  //
  // Lo encontro el paso de diseno la primera vez que corrio. Llevaba ahi desde
  // que `armarTableros` empezo a pasar la duracion.
  "duracion",
  // **Y las otras claves de motor, por la misma razon.** `duracion` la puso
  // aqui el «430» que salio rotulado en reel-01; estas tres son sus hermanas y
  // seguian fuera: `sfx`/`sound` los pone quien declara el movimiento que suena
  // —`sfx: "land"` se imprimia en versales como una linea mas—, `rotulo` es el
  // texto del gancho que lleva `BigTitle`, y `camara` la declaracion de plano.
  // Ninguna es copy, y las cuatro llegan por el mismo camino: alguien las
  // escribe para otro consumidor y esto las trata como si fueran una frase.
  "sfx", "rotulo", "camara", "motion",
  "familia", "zona", "cubre", "oro", "sound", "fondo", "filete", "source",
  "paso", "entrada", "giro", "placa", "cede_el_cuadro", "sin_pie", "anclas",
  // Los otros tres props de `Fondo`: `placa` ya estaba y sus companeras no,
  // asi que declarar como se recorta la placa —lo que separa el collage del
  // papel pintado— habria rotulado «cuna» en versales. Lo vio quien componia
  // reel-02 y prefirio dejarlo en `por_que` antes que arriesgarse.
  "recorte", "fuerza", "deriva",
  "ancla", "alinea", "a_la_vez", "no_rotular", "solo_si", "se_queda",
  "al_entrar_la_siguiente", "abajo_se_tacha", "sin_cifra_en_pantalla",
  "tachado", "corte", "eje", "saltos", "franja", "lastre", "suelo",
  "fondo_filetes", "filetes", "flecha", "universo", "capas", "escalones",
  "tramos", "marcas", "lineas", "palabras", "renglones", "condiciones_en_fila",
  "etiquetas", "figura",
]);

/** Lo que se dice al pie: fuente y condición, que son cumplimiento. */
const AL_PIE = new Set(["source", "fuente", "condicion", "condition", "legal"]);

type Linea = { texto: string; grande: boolean; oro: boolean };

/** Aplana un valor declarado a las líneas de texto que lleva dentro. */
const aLineas = (v: unknown, prof = 0): string[] => {
  if (prof > 2) return [];
  if (typeof v === "string") return v.trim() ? [v.trim()] : [];
  if (typeof v === "number") return [String(v)];
  if (Array.isArray(v)) return v.flatMap((x) => aLineas(x, prof + 1));
  if (v && typeof v === "object")
    return Object.entries(v as Record<string, unknown>)
      .filter(([k]) => !NO_ES_TEXTO.has(k))
      .flatMap(([, x]) => aLineas(x, prof + 1));
  return [];
};

export type TableroDeclaradoProps = {
  /** El `kind` que puso el diseñador. Se usa para el diagnóstico, no para dibujar. */
  kind: string;
  props: Record<string, unknown>;
};

export const TableroDeclarado: React.FC<TableroDeclaradoProps> = ({
  kind,
  props,
}) => {
  const frame = useCurrentFrame();

  const cuerpo: Linea[] = [];
  const pie: string[] = [];
  const quiereOro = String(props.oro ?? "").toLowerCase();

  for (const [k, v] of Object.entries(props)) {
    if (AL_PIE.has(k)) {
      pie.push(...aLineas(v));
      continue;
    }
    if (NO_ES_TEXTO.has(k) && !Array.isArray(v) && typeof v !== "object") continue;
    for (const t of aLineas(v)) {
      if (t.length > limit.legal) continue;
      cuerpo.push({
        // Corto y en versales = titular o cifra. Largo = lectura.
        grande: t.length <= limit.label,
        oro: false,
        texto: t,
      });
    }
  }

  // **Nada se dice dos veces, tampoco aquí.**
  //
  // Aplanar los props de una forma declarada repite texto en cuanto dos campos
  // comparten palabras: el `BeliefSwap` de reel-01 salió con «VENDER MÁS»
  // arriba y «VENDER MÁS» tres líneas más abajo, en el mismo tablero. Es la
  // regla del proyecto rompiéndose en el sitio que la viene a arreglar.
  //
  // Se compara sin tildes ni signos, porque «Vender más.» y «VENDER MAS» son la
  // misma línea para quien mira, y también se cae una línea que ya está
  // contenida en otra: si arriba dice «vender más» y abajo «si vende más le
  // queda más», la corta no añade nada y ocupa un renglón de los pocos que hay.
  const visto: string[] = [];
  const limpio = (s: string) =>
    s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ").trim();
  const unicas = cuerpo.filter((l) => {
    const c = limpio(l.texto);
    if (!c) return false;
    if (visto.some((v) => v === c || v.includes(c) || c.includes(v))) return false;
    visto.push(c);
    return true;
  });
  cuerpo.length = 0;
  cuerpo.push(...unicas);

  // **El oro es uno.** Lo declarado si coincide con alguna línea; si no, el
  // primer texto corto, que es el que hace de ancla.
  const iOro = (() => {
    if (quiereOro) {
      const i = cuerpo.findIndex((l) =>
        l.texto.toLowerCase().includes(quiereOro.slice(0, 14)));
      if (i >= 0) return i;
    }
    return cuerpo.findIndex((l) => l.grande);
  })();
  if (iOro >= 0) cuerpo[iOro].oro = true;

  if (!cuerpo.length) return null;

  const tranquila = String(props.familia ?? "tranquila") !== "cargada";

  /**
   * **`cubre` decide si el elemento ES el plano o lo acompaña, y lo dice el
   * diseñador.**
   *
   * Esto vivía en una vía aparte —`PANELES`, un literal escrito a mano— y por
   * eso llevaba cinco ciclos idéntico. No hacía falta pedirle nada nuevo al
   * diseñador: ya lo declaraba. `pleno` toma el cuadro; `panel` y `banda`
   * acompañan al plano sin taparle la cara, que es exactamente lo que el
   * literal codificaba a mano.
   *
   * Un camino en vez de dos: la misma declaración dibuja las dos cosas.
   */
  const cubre = String(props.cubre ?? "pleno");
  const acompana = cubre === "panel" || cubre === "banda";

  return (
    <AbsoluteFill
      style={{
        // Acompañando se va al tercio inferior y deja la cara libre; a pleno
        // toma el cuadro entero.
        justifyContent: acompana ? "flex-end" : "center",
        // **Y a pleno se reserva la banda del subtítulo.**
        //
        // Esto centraba en el alto útil entero, sin descontar los 200 px que
        // `layout.captionBand` guarda para el subtítulo: **cualquier tablero a
        // pleno con pie invadía 960-1160**, o sea escribía encima de lo que se
        // está oyendo. Es literalmente lo que Jaime vio en el primer render —
        // *«los tableros y paneles están sobrepuestos en todos lados»*— y la
        // reserva ya existía: `boardHeight` está en `lienzo.ts` justo para esto
        // y nadie la usaba aquí.
        //
        // Acompañando no hace falta: ya se va al tercio inferior con su propio
        // margen, que es lo que lo aparta de la cara.
        padding: `${layout.safe.top}px ${layout.safe.right}px ${
          acompana
            ? layout.safe.bottom + 120
            : layout.safe.bottom + layout.captionBand
        }px ${layout.safe.left}px`,
        // La familia decide el fondo, y viene declarada: `cargada` deja ver el
        // plano, `tranquila` va sobre placa lisa para que las cifras se lean.
        // Acompañando **nunca** hay placa: taparía el plano que acompaña.
        background: acompana || !tranquila ? "transparent" : color.richBlack,
      }}
    >
      {cuerpo.map((l, i) => {
        // Cada línea entra cuando la anterior ya se pudo leer: 0,75 s por
        // bloque, que es la regla del canon, no un número redondo.
        const entra = i * Math.round(0.75 * 30);
        const o = interpolate(frame, [entra, entra + 8], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const dx = interpolate(frame, [entra, entra + 10], [-24, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={`${l.texto}-${i}`}
            style={{
              opacity: o,
              transform: `translateX(${dx}px)`,
              marginBottom: l.grande ? 18 : 10,
              padding: l.oro ? "6px 16px" : 0,
              background: l.oro ? color.gold : "transparent",
              alignSelf: "flex-start",
              maxWidth: "100%",
            }}
          >
            <span
              style={{
                fontFamily: l.grande ? fontFamily.bloque : fontFamily.video,
                fontWeight: l.grande ? 400 : 800,
                fontSize: l.grande ? videoText.title : videoText.caption,
                letterSpacing: l.grande ? tracking.display : 0,
                textTransform: l.grande ? "uppercase" : "none",
                color: l.oro ? color.richBlack : color.lightNeutral,
                lineHeight: 1.05,
              }}
            >
              {l.texto}
            </span>
          </div>
        );
      })}

      {/* El pie lleva la fuente y la condición: cumplimiento, no adorno. */}
      {pie.length ? (
        <div style={{ marginTop: 24 }}>
          {pie.map((p) => (
            <div
              key={p}
              style={{
                fontFamily: fontFamily.video,
                fontWeight: 700,
                fontSize: 30,
                color: color.secondaryBlue,
                lineHeight: 1.25,
              }}
            >
              {p}
            </div>
          ))}
        </div>
      ) : null}

      {/* **Aquí NO va el nombre de la forma.**

          Estaba, y con buena intención —«para que se vea qué falta
          construir»—, pero esto se dibuja en la pieza que se publica: las
          entregas del 5 de septiembre llevaban escritas en pantalla las
          palabras FUSION, DESVIO, LISTANUMERADA, EVIDENCECARD y ANIDADO,
          porque diecinueve formas declaradas caen aquí. Cinco de las siete
          piezas salieron con un rótulo de diagnóstico encima.

          El dato es útil y no se pierde: que una forma declarada no tenga
          componente es un cable suelto, y lo dice `scripts/conectado.py`, que
          corre al empezar cualquier sesión. Un informe se lee cuando toca; un
          rótulo en el frame se publica. */}
    </AbsoluteFill>
  );
};
