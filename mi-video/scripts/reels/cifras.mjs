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

const CAMPOS = JSON.parse(
  fs.readFileSync(new URL("./cifras.json", import.meta.url), "utf8"),
);

/**
 * La geometría del pie, declarada una vez y leída por los dos lados: aquí para
 * saber si la línea cabe, y en `src/components/PieTablero.tsx` para dibujarla.
 * Ver `src/brand/pie.json`.
 */
const PIE = JSON.parse(
  fs.readFileSync(new URL("../../src/brand/pie.json", import.meta.url), "utf8"),
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
    // Lo de motor no se aplana, tampoco si es un objeto (C-427).
    if (NO_ES_TEXTO.has(k) && !Array.isArray(v)) continue;
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

/** El texto de un prop, limpio, o cadena vacía. */
const txt = (v) => (typeof v === "string" ? v.trim() : "");

/**
 * **Un destino, no uno por forma.** Aquí vivía `PIE_POR_KIND` —`fuente` en
 * `comparacion`, `resultado.source` en `acumulacion`, `limitation` en `causal`—
 * y existía sólo porque cada componente dibujaba su propio pie: cinco
 * dibujantes, cinco destinos, y tres de ellos sin ninguno, así que el valor
 * llegaba y se evaporaba sin error. Desde que el pie va fuera de la zona segura
 * lo dibuja `dibujaTablero` para las 24 leyendo este prop. Uno no diverge.
 */
const DESTINO = "pie";

/**
 * La línea del pie, junta. **No se redacta aquí**: redactarla en afirmativo
 * exige entender la frase, y eso lo hace quien compone y lo deja escrito en
 * `escena_desc.tablero.props.pie`. Aquí se junta lo declarado y se dice cuándo
 * no cabe. El separador es el punto medio del canon.
 */
const unaLinea = (partes) =>
  partes.map(txt).filter(Boolean).join(" · ").replace(/\s+/g, " ").trim();

/**
 * **El pie de la cifra que SE ROTULA, y lo declarado manda.**
 *
 * Tres reglas, y las tres costaron una entrega:
 *
 * 1. **Se casa por token normalizado**, no por contención de texto crudo. Sin
 *    esto ninguna fila casaba y ganaba el desempate, que traía la fuente de
 *    otra cifra de la misma etapa.
 * 2. **Si ninguna casa, no hay pie.** El desempate `respalda === 'parcial'`
 *    era peor que no poner nada: un pie que no es de la cifra parece respaldar
 *    lo que no respalda, y sale sin decirlo. Ahora sale como falta.
 * 3. **Lo declarado gana, y `dato` sólo rellena lo que falta.** Ésta es la que
 *    estuvo rota hasta hoy: el que corría de verdad era `base.mjs :: pieDe`,
 *    cuyo spread iba DESPUÉS de `b.props`, así que **pisaba sin avisar la
 *    condición que el diseñador escribió para esa cifra exacta**. Medido en las
 *    seis piezas: `reel-07 e3` declaraba la línea buena —*«53,53%: TAXTIPS.CA Y
 *    PWC, ONTARIO 2026 · 32%: PROYECCIÓN, SIN CIFRA PUBLICADA»*— y en
 *    `src/reels.json` quedó el rótulo largo de `dato`; `reel-01 e3` declaraba
 *    *«CCPC con ingreso activo bajo el límite…»* y salió *«Es un supuesto de la
 *    pieza, no un dato medido… —una…»*, o sea la redacción defensiva que Jaime
 *    prohibió, además cortada por la mitad.
 *
 * ## Y no se abrevia en silencio
 *
 * `enPantalla` recortaba la condición a 25 palabras y le pegaba puntos
 * suspensivos. Jaime pidió lo contrario: *«la cifra y el tramo exactos, sin
 * abreviar hasta que deje de decir nada»*. Lo que no cabe **sale como falta** y
 * se reescribe más corto, que es decisión de redacción y no recorte de máquina;
 * el texto entero viaja igual en `condicion_completa` para el copy del vídeo.
 *
 * Las faltas se **empujan**, como en `armarTableros`: devolverlas obligaba a
 * desestructurar en el sitio de llamada, que es donde una falta se olvida.
 *
 * @returns los props con `pie` puesto.
 */
export function pieDe(slug, b, faltas) {
  const props = { ...b.props };

  // Lo que escribió el diseñador. `pie` es la línea ya redactada y gana entera;
  // si no la hay, se junta con lo que declaró por campos.
  const fuente = txt(props.fuente) || txt(props.source);
  const condicion =
    txt(props.condicion) || txt(props.condition) || txt(props.limitation);

  const pintadas = cifrasDe(props);
  const filas = datos(slug, b.beat)
    .filter((f) => f.respalda === "si" || f.respalda === "parcial");
  let r = null;
  if (pintadas.length) {
    const casan = filas.filter((f) => f.tokens.some((t) => pintadas.includes(t)));
    // Manda la que MÁS necesita el pie: una proyección (`parcial`) tiene
    // condiciones que hay que decir; una cifra publicada se sostiene sola.
    r = casan.find((x) => x.respalda === "parcial") ?? casan[0] ?? null;
    if (!r && !fuente) {
      faltas.push(
        `${slug} e${b.beat}: rotula ${pintadas.map((c) => `«${c}»`).join(", ")} y ` +
        `ninguna fila de \`dato\` de esa etapa casa con lo rotulado ` +
        `(hay ${filas.length}). Se queda sin pie a propósito: un pie que no es ` +
        `de la cifra parece respaldar lo que no respalda.`,
      );
    }
  } else if (filas.length === 1) {
    /**
     * **Un tablero sin cifra también puede afirmar algo, y entonces lleva pie.**
     *
     * `reel-04 e3` no rotula ningún número —«DEUDAS PERSONALES · DIVORCIO ·
     * TARJETAS»— y aun así afirma que el banco pide empresa incorporada: eso es
     * una fuente que hay que decir. Sólo se toma cuando la etapa declara **una**
     * fila: con dos no hay forma de saber cuál respalda qué, y un pie que no es
     * de lo que afirma parece respaldar lo que no respalda.
     */
    r = filas[0];
  } else if (filas.length > 1 && !fuente && !txt(props[DESTINO])) {
    faltas.push(
      `${slug} e${b.beat}: no rotula ninguna cifra y la etapa declara ` +
      `${filas.length} filas de \`dato\`, así que no hay forma de saber cuál ` +
      `respalda el tablero. Sale sin pie: el que corría antes cogía una de las ` +
      `${filas.length} y la enseñaba como si fuera la del tablero. Se escribe ` +
      `la línea en \`escena_desc.tablero.props.pie\`.`,
    );
  }

  const deDato = { rotulo: txt(r?.rotulo), condiciones: txt(r?.condiciones) };
  const linea = txt(props[DESTINO]) ||
    unaLinea([fuente || deDato.rotulo, condicion || deDato.condiciones]);
  if (!linea) return props;

  // Lo que no cabe NO se tira: viaja en el spec para el copy del vídeo.
  const entera = unaLinea([fuente || deDato.rotulo, condicion || deDato.condiciones]);
  if (entera && entera !== linea) props.condicion_completa = entera;

  props[DESTINO] = linea;
  if (linea.length > PIE.max_caracteres) {
    faltas.push(
      `${slug} e${b.beat}: el pie mide ${linea.length} caracteres y en una ` +
      `línea caben ${PIE.max_caracteres} (${PIE.suelo} px, el cuerpo por debajo ` +
      `del cual no se lee ni parando la pieza). Se reescribe en afirmativo y ` +
      `más corto en \`escena_desc.tablero.props.pie\` — «basado en X datos bajo ` +
      `X condiciones», con la cifra y el tramo exactos. Abreviarlo aquí sería ` +
      `dejarlo diciendo nada.`,
    );
  }
  return props;
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
