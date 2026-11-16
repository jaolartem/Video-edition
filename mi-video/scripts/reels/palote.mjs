/**
 * **Lo que el palote sabe hacer, dicho antes de guardarlo** (C-724).
 *
 * reel-23, 16-11-2026: el diseñador escribió `accion: "celebra"` y `lado:
 * "der"`; la puerta lo dejó pasar porque sólo miraba props que faltan y topes
 * de texto, y `src/components/Palote.tsx` —que tira el render ante una acción
 * que no conoce— tumbó los fotogramas 10 a 14 de la hoja guía. La guía no
 * salía y la línea repetía `montado` entero.
 *
 * La lista es la `ACCIONES` del componente, copiada a propósito: el humo
 * (`humo_del_corte._el_palote_es_recurso`) mide que las dos digan lo mismo.
 */
export const ACCIONES_PALOTE = ["millonario", "musculo", "mecanico", "investigar",
  "curriculum", "guion", "aplicacion", "senalar", "pensar", "aprobar", "celebrar",
  "encoger", "saludar", "caminar"];
const LADOS = ["arriba", "abajo", "izquierda", "derecha"];
const TEXTO_AL = ["frente", "encima"];

const fuera = (campo, v, validos) => (v === undefined || v === null || validos.includes(v) ? []
  : [`«Palote».\`${campo}\` = «${v}» no existe; hay: ${validos.join(", ")}. Esto NO avisa,`
     + " falla el render"]);

export function faltasDePalote(props) {
  const p = props ?? {};
  return [...fuera("accion", p.accion, ACCIONES_PALOTE), ...fuera("lado", p.lado, LADOS),
    ...fuera("textoAl", p.textoAl, TEXTO_AL),
    ...(Array.isArray(p.acciones) ? p.acciones : [])
      .flatMap((a) => fuera("acciones[].accion", a?.accion, ACCIONES_PALOTE))];
}
