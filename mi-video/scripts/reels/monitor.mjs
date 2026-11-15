/**
 * **Dónde está el monitor dentro del plano, para que una pantalla se amplíe
 * desde él** (C-696).
 *
 * Jaime, 15-11-2026, sobre la apertura de reel-23: *«la lógica era que cuando
 * mirara al computador, la pantalla se compartiera, como que se ampliara la
 * pantalla, y ahí empieza a rodar el vídeo»*. El tablero `Apoyo` con `forma:
 * "amplia"` arranca con el clip metido en el monitor que se ve en el plano y
 * crece hasta el cuadro entero. Dónde está ese monitor no lo sabe el diseñador
 * ni se adivina: **lo declara la cinta**, en `rutas.json` → `monitores`, como
 * fracciones de su cuadro, medidas una vez sobre un fotograma. Aquí se lleva al
 * cuadro de la pieza pasando por el recorte de la escena (`escena.crop`), que
 * es el mismo que aplica `cortar.py`.
 *
 * El recorrido lento de la escena (`escena.recorrido`) no se sigue: el clip
 * sale del monitor en sus primeros fotogramas y ya no vuelve a él.
 */
import { lienzoDePieza } from "../lienzo.mjs";
import { rutas } from "../rutas.mjs";
import { sujetoDe } from "./material.mjs";

export const AMPLIA = "amplia";

/** El monitor de `escena`, en píxeles del cuadro de la pieza, o `{ falta }`. */
export function monitorDe(escena, lienzo) {
  const m = rutas.monitores?.[escena.fuente];
  if (!m)
    return { falta: `la cinta ${escena.fuente} no declara dónde está el monitor`
      + " (rutas.json → monitores): sin eso la pantalla no sabe de dónde ampliarse" };
  const [W, H] = m.cuadro ?? [];
  const c = escena.crop;
  if (!(W > 0 && H > 0) || !c?.w || !c?.h)
    return { falta: `monitor de ${escena.fuente}: falta \`cuadro\` o la escena no trae recorte` };
  const kx = lienzo.width / c.w;
  const ky = lienzo.height / c.h;
  const r = {
    x: Math.round((m.x * W - c.x) * kx),
    y: Math.round((m.y * H - c.y) * ky),
    w: Math.round(m.w * W * kx),
    h: Math.round(m.h * H * ky),
  };
  const dentro = r.x >= -4 && r.y >= -4 && r.x + r.w <= lienzo.width + 4
    && r.y + r.h <= lienzo.height + 4;
  if (!dentro)
    return { falta: `el monitor queda fuera del encuadre «${escena.encuadre}» de la`
      + ` escena ${escena.indice + 1}: la pantalla no puede ampliarse desde lo que no se ve` };
  return r;
}

/**
 * Pone `props.monitor` a cada `Apoyo` con `forma: "amplia"`, desde la escena
 * sobre la que cae, **y su recorte**: el clip se pinta encima del plano, y sin
 * el recorte con alfa delante tapa lo que está delante del monitor —Jaime,
 * 15-11-2026: *«la imagen de la pantalla tapa mi brazo»*—. El recorte es el de
 * su etapa, el mismo que usan los tableros con él dentro (`sujetoDe`), desde el
 * fotograma en que el tablero arranca dentro de ella. Lo que no se puede
 * resolver se dice en `faltas`, y el render no sale.
 */
export function ampliaDesdeElMonitor(tableros, reloj, slug, faltas) {
  const amplias = tableros.filter((t) => t.kind === "Apoyo" && t.props?.forma === AMPLIA);
  if (!amplias.length) return tableros;
  const lienzo = lienzoDePieza(slug);
  const huecos = reloj.limites();
  for (const t of amplias) {
    const h = huecos.find((x) => t.at >= x.a && t.at < x.b);
    const r = h ? monitorDe(h.escena, lienzo) : { falta: "no cae sobre ninguna escena" };
    const sujeto = sujetoDe(slug, t.beat);
    if (!r.falta && !sujeto)
      r.falta = `sin recorte en public/recorte/${slug}-e${t.beat}.webm, el clip le taparía`
        + " el brazo: falta la pasada de scripts/dominio/sujeto.py sobre este corte";
    if (r.falta) {
      faltas.push(`${slug} e${t.beat}: Apoyo «amplia» — ${r.falta}`);
      continue;
    }
    t.props = { ...t.props, monitor: r, sujeto_src: sujeto,
                sujeto_trim: Math.max(0, Math.round(t.at - reloj.anclaDe(t.beat))) };
  }
  return tableros;
}
