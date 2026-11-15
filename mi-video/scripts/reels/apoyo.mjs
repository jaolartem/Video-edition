/**
 * **La biblioteca de apoyo, con un solo dueño en JS.** Los clips propios que
 * van bajo la voz —Alfred en pantalla, el guion escrito, la captura de Gemini—
 * viven en `src/brand/apoyo.json` y en ningún otro sitio (C-673); aquí se leen
 * para el catálogo del diseñador y para la puerta que para antes del render lo
 * que no se puede dibujar. Lo dibuja `src/components/Apoyo.tsx`.
 */
import fs from "fs";

export const CLIPS = (() => {
  try {
    return JSON.parse(fs.readFileSync("src/brand/apoyo.json", "utf8")).clips ?? {};
  } catch {
    return {};
  }
})();

/** Las tres formas que `Apoyo.tsx` dibuja. `amplia` es la de C-696. */
export const FORMAS_APOYO = ["completo", "panel", "amplia"];

/** Lo que hace que un `Apoyo` no se pueda dibujar, dicho antes del render. */
export function faltasDeApoyo(props) {
  if (!props?.clip) return [];
  const c = CLIPS[props.clip];
  if (!c) return [`«Apoyo» pide el clip \`${props.clip}\`, que no está en src/brand/apoyo.json`];
  if (!fs.existsSync(`public/${c.fichero}`)) return [`«Apoyo» \`${props.clip}\`: falta public/${c.fichero}`];
  // Otra palabra caería a `completo` sin avisar, y «amplia» mal escrita es una
  // ampliación que nunca ocurre.
  if (props.forma !== undefined && !FORMAS_APOYO.includes(props.forma))
    return [`«Apoyo» forma \`${props.forma}\`: es ${FORMAS_APOYO.join(", ")} (C-696)`];
  return [];
}
