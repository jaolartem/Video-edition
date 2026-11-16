import fs from "fs";
import path from "path";

/**
 * **El encuadre que Jaime aprobó, para la escena que no ha cambiado** (C-730).
 *
 * reel-23, 16-11-2026: Jaime aprobó la hoja guía y pidió un cambio en e14. El
 * compositor declaró `medio` para las escenas de e14 y la rueda de
 * `punch-ins.py` —que sólo avanza en las escenas sin declarar— se corrió tres
 * puestos. e15 a e19, ya aprobadas, cambiaron de plano solas: «pecho» pasó a
 * «completo» y «primerísimo» a «medio». Jaime: *«las escenas aprobadas no se
 * cancelan, quedan aprobadas; sólo cambian las que necesitan cambio»*.
 *
 * `guia.py` guarda el spec de cada aprobación en
 * `work/still/guia/<pieza>/aprobados/`. Una escena sin encuadre declarado que
 * ocupa los mismos fotogramas que en la última aprobada —empieza y dura lo
 * mismo, ±1 fotograma— hereda el encuadre que se aprobó. Si el corte cambió,
 * la escena ya es otra y vuelve a la rueda.
 */
export const encuadreAprobado = (slug, fps = 30) => {
  const dir = path.join("work", "still", "guia", slug, "aprobados");
  const ultimo = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => f.endsWith(".json"))
      .map((f) => path.join(dir, f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0]
    : null;
  const escenas = ultimo ? JSON.parse(fs.readFileSync(ultimo, "utf8")).escenas ?? [] : [];
  return (desde, dura) => {
    const a = Math.round(desde * fps);
    const b = Math.round((desde + dura) * fps);
    const e = escenas.find((x) => Math.abs(x.a - a) <= 1 && Math.abs(x.b - b) <= 1);
    return e?.encuadre ?? null;
  };
};
