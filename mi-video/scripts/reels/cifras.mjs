/**
 * **Una cifra en pantalla, con el respaldo de esa cifra. No de otra.**
 *
 * Jaime, segunda noche seguida: *«otra vez se está renderizando lo que no está
 * actualizado»*. Y la variante cara de eso no es que falte un pie: es que salga
 * **el pie de otra cifra**, porque entonces la pieza afirma en pantalla algo
 * que la fuente no dice y no se ve como un fallo, se ve como una decisión.
 *
 * Medido antes de este fichero, en `reel-03 e3`: el tablero rotula **53,53 %**
 * y el pie que se le ponía empezaba por «Ninguna. Buscado en TaxTips, PwC,
 * ontario.ca…», que es el rótulo de la fuente 17 — la de OTRA cifra de la misma
 * etapa. La fila correcta existía; no casaba porque la base escribe `53.53%` y
 * el diseñador `53,53 %`, y la comparación era de texto crudo: ninguna casaba,
 * caía al desempate `respalda === 'parcial'` y se llevaba la primera que hubiera.
 *
 * ## Por qué está aquí y no repartido
 *
 * Porque el defecto se repitió tres veces en tres sitios que leían números con
 * criterios distintos: `pieDe` comparaba crudo, `fuentes.py` normalizaba con
 * `_normal`, y `verificar.py` sólo veía importes con separador de miles. Tres
 * lectores del mismo dato es la avería que el proyecto llama divergencia: no
 * fallan, **discrepan**, y las tres parecen correctas.
 *
 * Este fichero es el único dueño de cuatro preguntas:
 *
 * 1. **Qué es la misma cifra** — `normalizar`, la misma regla que `fuentes.py`,
 *    fijada por los casos de `cifras.json` y comprobada en los dos idiomas.
 * 2. **Qué se rotula de verdad** — `cifrasDe`, con los mismos campos que pinta
 *    `TableroDeclarado`, declarados en `cifras.json`.
 * 3. **Qué fila de `dato` la respalda** — `pieDe`, por token, no por contención.
 * 4. **Qué cifra sale sin respaldo** — `sinRespaldo`, que es lo que para la
 *    pieza en `puerta.mjs`.
 *
 * **La base se abre aquí en sólo lectura.** `base.mjs` es el dueño de las
 * consultas y ahí debería vivir `datos()`; está tomado por otro trabajo ahora
 * mismo, así que queda declarado como lo pendiente. La conexión es de lectura
 * para que no pueda ser otra cosa.
 */
import fs from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { enPantalla } from "./lectura.mjs";

const CAMPOS = JSON.parse(
  fs.readFileSync(new URL("./cifras.json", import.meta.url), "utf8"),
);

/** Props que son estructura, no texto en pantalla. Espejo de `TableroDeclarado`. */
const NO_ES_TEXTO = new Set(CAMPOS.no_es_texto);
/** Lo que se dice al pie: fuente y condición, que son cumplimiento. */
const AL_PIE = new Set(CAMPOS.al_pie);

/**
 * El tope de `limit.legal` en `src/brand/copy.ts`: por encima de esto
 * `TableroDeclarado` no pinta la línea, así que su cifra no está en pantalla.
 * Se repite aquí porque `copy.ts` es TypeScript y no se puede importar desde
 * node; `guardas.mjs` comprueba que los dos números siguen siendo el mismo.
 */
const LEGAL = 190;

/**
 * Lo que cuenta como cifra: dinero, porcentajes, años, plazos. Mismo criterio
 * —y misma expresión— que `CIFRA` en `fuentes.py`: una cantidad sin unidad no
 * se rotula ni se puede comprobar.
 */
export const CIFRA =
  /(\$\s?[\d.,]+|\d[\d.,]*\s?(?:%|mil|millones|dólares|dolares|años|anos|semanas|meses|puntos)|\b\d{2,}[.,]\d+\b)/gi;

/**
 * La misma cifra escrita de dos maneras es una cifra, no dos.
 *
 * Port literal de `_normal` en `scripts/fuentes.py`, con dos reglas más que el
 * lote obligó a añadir: el espacio del diseñador —`53,53 %` y `$ 20`— y las
 * mayúsculas de la unidad —`300.000 MIL`—. Los casos que lo fijan están en
 * `cifras.json` y los corren los dos idiomas.
 *
 * Lo que NO se toca es el valor: `25.000` y `25` son cifras distintas.
 */
export const normalizar = (c) => {
  let s = String(c ?? "").trim().replace(/\s+/g, " ").replace(/[.,;:)]+$/, "");
  if (!s) return "";
  // El separador de miles se escribe con punto o con coma según quien teclee.
  s = s.replace(/(?<=[0-9])\.(?=[0-9]{3})/g, ",");
  // Y el decimal: `53.53%` y `53,53%` son el mismo número, no dos rótulos.
  s = s.replace(/(?<=[0-9])\.(?=[0-9]{1,2}(?![0-9]))/g, ",");
  // El aire que mete el diseñador entre el signo y el número no es un número.
  s = s.replace(/\$\s+(?=[0-9])/g, "$").replace(/(?<=[0-9])\s+(?=%)/g, "");
  return s.toLowerCase();
};

/** Las cifras que lleva un texto, ya normalizadas. */
const enTexto = (t) =>
  [...String(t).matchAll(CIFRA)].map((m) => normalizar(m[0])).filter(Boolean);

/**
 * Aplana un valor declarado a las líneas de texto que lleva dentro. Copia
 * fiel de `aLineas` en `TableroDeclarado.tsx`: si esto se separa, el que
 * comprueba deja de mirar lo que el otro pinta.
 */
const aLineas = (v, prof = 0) => {
  if (prof > 2) return [];
  if (typeof v === "string") return v.trim() ? [v.trim()] : [];
  if (typeof v === "number") return [String(v)];
  if (Array.isArray(v)) return v.flatMap((x) => aLineas(x, prof + 1));
  if (v && typeof v === "object")
    return Object.entries(v)
      .filter(([k]) => !NO_ES_TEXTO.has(k))
      .flatMap(([, x]) => aLineas(x, prof + 1));
  return [];
};

/**
 * **Las cifras que ese tablero pone delante del espectador.**
 *
 * El pie no cuenta: lo que se comprueba es lo rotulado, y el pie es justo lo
 * que responde por ello. Contarlo haría que una cifra se respaldara a sí misma.
 */
export const cifrasDe = (props) => {
  const fuera = [];
  for (const [k, v] of Object.entries(props ?? {})) {
    if (AL_PIE.has(k)) continue;
    if (NO_ES_TEXTO.has(k) && !Array.isArray(v) && typeof v !== "object") continue;
    for (const t of aLineas(v)) {
      if (t.length > LEGAL) continue;
      fuera.push(...enTexto(t));
    }
  }
  return [...new Set(fuera)];
};

const db = new DatabaseSync("ads/decisiones.db", { readOnly: true });

/** Las filas de `dato` de una etapa, con su cifra ya normalizada. */
const datos = (slug, beat) =>
  db.prepare(
    "select f.rotulo, d.condiciones, d.cifra, d.respalda from dato d" +
    "  left join fuente f on f.id = d.fuente_id" +
    "  join video v on v.id = d.video_id" +
    " where v.slug = ? and d.etapa_orden = ?",
  ).all(slug, beat).map((r) => ({ ...r, tokens: enTexto(r.cifra ?? "") }));

/**
 * **Los importes de la escalera son de la casa.** Mismo criterio que `propias()`
 * en `fuentes.py`: pedirle a Jaime la fuente de su propio precio es pedirle que
 * demuestre lo que él fija. Se compara sólo el número, porque el panel del
 * reel-03 lo escribe «20 DÓLARES» y la tabla lo guarda como `20`.
 */
const DE_CASA = (() => {
  try {
    return new Set(db.prepare("select importe from precio").all()
      .map((f) => String(f.importe).replace(/\D/g, "")));
  } catch {
    return new Set();
  }
})();
const deCasa = (c) => DE_CASA.has(c.replace(/\D/g, ""));

/**
 * **La condición no se parte dentro de un importe.**
 *
 * `enPantalla` corta por frases con `[^.!?]+[.!?]*`, y el punto del separador
 * de miles cuenta como fin de frase: `reel-02 e3` salía rotulando «Caso
 * hipotetico. Ontario, ano fiscal 2026. Los $180.» — el importe mutilado y la
 * frase diciendo otra cosa que la condición. Se protege el punto que va entre
 * dígitos y se devuelve después, así que el corte sigue siendo por frase.
 *
 * El arreglo definitivo es la expresión `(?<!\d)[.!?](?!\d)` dentro de
 * `lectura.mjs`, que sirve para todos sus lectores; queda declarado.
 */
const PUNTO = "";
export const condicionEnPantalla = (t) =>
  enPantalla(String(t).replace(/(?<=\d)\.(?=\d)/g, PUNTO))
    .split(PUNTO).join(".");

/** Escribe `valor` en `destino` («a.b» admitido) sólo si el sitio está vacío. */
const colocar = (props, destino, valor) => {
  const [a, b] = destino.split(".");
  if (!b) {
    if (props[a]) return true;
    props[a] = valor;
    return true;
  }
  if (!props[a] || typeof props[a] !== "object") return false;
  if (props[a][b]) return true;
  props[a] = { ...props[a], [b]: valor };
  return true;
};

/**
 * **Dónde lee el pie cada camino de dibujo.**
 *
 * `pieDe` calculaba `fuente` y `condicion` para todos los tableros a pleno, y
 * tres de los cinco componentes no tienen esos props: los destructuran por
 * nombre, sin rest, así que el valor llegaba y **se evaporaba sin error**.
 * Medido: `Reel-R2 e3` es `acumulacion`, su props lleva `fuente: "EY — Ontario…"`
 * y en pantalla no aparece ninguna fuente.
 *
 * `null` significa que ese camino no tiene sitio donde ponerlo, y entonces es
 * una falta: no se manda un pie a un componente que no lo dibuja.
 *
 * Lo que no está aquí sale con `TableroDeclarado`, que pinta `AL_PIE` tal cual.
 */
const PIE_POR_KIND = {
  comparacion: { fuente: "fuente", condicion: "condicion" },
  acumulacion: { fuente: "resultado.source", condicion: "condicion" },
  twopaths: { fuente: "difference.source", condicion: "condition" },
  causal: { fuente: null, condicion: "limitation" },
};

/**
 * **El pie de la cifra que SE ROTULA, y lo declarado manda.**
 *
 * Dos reglas, y las dos costaron una entrega:
 *
 * 1. **Se casa por token normalizado**, no por contención de texto crudo. Sin
 *    esto ninguna fila casaba y ganaba el desempate, que traía la fuente de
 *    otra cifra de la misma etapa.
 * 2. **Si ninguna casa, no hay pie.** El desempate `respalda === 'parcial'`
 *    era peor que no poner nada: un pie que no es de la cifra parece respaldar
 *    lo que no respalda, y sale sin decirlo. Ahora sale como falta.
 *
 * Y la precedencia va al revés que antes: el spread de `pieDe` iba DESPUÉS de
 * `b.props`, así que la condición que el diseñador escribió para esa cifra
 * exacta se sobrescribía. En `reel-03 e3` escribió *«Tasa MARGINAL: se aplica
 * sólo al tramo que supera $253.414…»* —la del 53,53 %— y en `src/reels.json`
 * quedó la del 32 %. Es literalmente la producción gráfica del diseñador
 * reemplazada por otra en el último tramo.
 *
 * @returns `{props, faltas}` — los props con el pie puesto donde su componente
 *   lo lee, y lo que no se pudo resolver, dicho.
 */
export function pieDe(slug, b) {
  const faltas = [];
  const props = { ...b.props };
  const pintadas = cifrasDe(props);
  if (!pintadas.length) return { props, faltas };

  const filas = datos(slug, b.beat)
    .filter((r) => r.respalda === "si" || r.respalda === "parcial");
  const casan = filas.filter((r) => r.tokens.some((t) => pintadas.includes(t)));
  // Manda la que MÁS necesita el pie: una proyección (`parcial`) tiene
  // condiciones que hay que decir; una cifra publicada se sostiene sola.
  const r = casan.find((x) => x.respalda === "parcial") ?? casan[0];
  if (!r) {
    faltas.push(
      `${slug} e${b.beat}: rotula ${pintadas.map((c) => `«${c}»`).join(", ")} y ` +
      `ninguna fila de \`dato\` de esa etapa casa con lo rotulado ` +
      `(hay ${filas.length}). Se queda sin pie a propósito: un pie que no es ` +
      `de la cifra parece respaldar lo que no respalda.`,
    );
    return { props, faltas };
  }

  const sitio = PIE_POR_KIND[b.kind] ?? { fuente: "fuente", condicion: "condicion" };
  const pega = (campo, valor) => {
    if (!valor) return;
    const destino = sitio[campo];
    if (!destino) {
      faltas.push(
        `${slug} e${b.beat}: «${b.kind}» no dibuja ${campo}, y la cifra la ` +
        `necesita. El pie no se manda a un componente que no lo lee.`,
      );
      return;
    }
    // **Lo declarado gana, y una diferencia se dice.** Si el diseñador escribió
    // su propio pie, el de `dato` no lo sustituye en silencio.
    const [a, c] = destino.split(".");
    const ya = c ? props[a]?.[c] : props[a];
    if (ya && String(ya).trim() !== String(valor).trim()) {
      faltas.push(
        `${slug} e${b.beat}: el diseñador escribió ${campo} y \`dato\` dice ` +
        `otra cosa. Manda lo declarado; la de \`dato\` era «${String(valor).slice(0, 60)}…».`,
      );
      return;
    }
    if (!colocar(props, destino, valor)) {
      faltas.push(
        `${slug} e${b.beat}: «${b.kind}» lee ${campo} en \`${destino}\` y ese ` +
        `sitio no existe en lo declarado, así que la cifra sale sin ${campo}.`,
      );
    }
  };

  pega("fuente", r.rotulo ? String(r.rotulo) : "");
  if (r.condiciones) {
    const entera = String(r.condiciones);
    const cabe = condicionEnPantalla(entera);
    pega("condicion", cabe);
    // Lo que no cabe NO se tira: viaja en el spec para el copy del vídeo.
    if (cabe !== entera) props.condicion_completa = entera;
  }
  return { props, faltas };
}

/**
 * **Una cifra en pantalla sin fila en `dato` para la pieza.**
 *
 * El contrato de diseño lo daba por hecho —«Cumplimiento: una cifra en pantalla
 * sin fila en `dato` la para la puerta»— y no existía donde decía: la guarda 6a
 * de `verificar.py` leía la PROSA de la escena y no el JSON que pinta, su
 * expresión sólo veía importes con separador de miles —o sea ni $20, ni 2%, ni
 * 53,53 %— y además corre en la fase 10, DESPUÉS del render.
 *
 * Aquí se mira lo que de verdad se va a pintar, tableros y paneles, con los
 * props exactos. Medido al escribirlo: `reel-06 e9` pinta $20, $30 y $40 con
 * una sola fila declarada, y `reel-02 e6` rotula «$200» y «300 MIL» mientras
 * `dato` declara «$200.000–300.000 millones».
 *
 * @returns `[{beat, cifra}]` — lo que sale sin respaldo, para que la puerta lo
 *   diga con su sitio.
 */
export function sinRespaldo(slug, piezas) {
  const fuera = [];
  for (const b of piezas) {
    const declaradas = datos(slug, b.beat).flatMap((r) => r.tokens);
    for (const c of cifrasDe(b.props ?? b)) {
      if (declaradas.includes(c) || deCasa(c)) continue;
      fuera.push({ beat: b.beat, cifra: c });
    }
  }
  return fuera;
}
