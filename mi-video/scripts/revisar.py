"""Cada fragmento **como se va a ver**, para poder aprobarlo.

Regla de Jaime: *«para aprobarlos necesito verlos renderizados»*. Y tiene razón
— el corte crudo no lleva subtítulos, ni tablero, ni rótulo, así que aprobarlo
sería aprobar otra cosa.

Lo que hace que esto sea barato: **la pieza ya está renderizada** con todo
encima, y `colocacion` sabe en qué segundo de la salida empieza y acaba cada
fragmento. Así que no hay que renderizar nada nuevo: se corta el render por
donde dice la tabla. El peldaño caro ya se pagó una vez.

Dos cuidados que no son obvios:

- **El montaje corre a 1,15×**, así que un tiempo del plan no es un tiempo del
  vídeo. Sin dividir, el desfase crece a lo largo de la pieza y el último
  fragmento sale de otro sitio (aprendizaje 47).
- **Se corta sin recodificar** y con `-ss` antes de `-i`: el fichero de revisión
  sale en segundos y con la misma imagen que la entrega, que es justo lo que hay
  que juzgar.

    python scripts/revisar.py 3          # los fragmentos del reel 3, como se ven
    python scripts/revisar.py            # los seis
"""
import argparse
import io
import os
import re
import sqlite3
import basedatos
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
import rutas  # noqa: E402

BASE = os.path.join("ads", "decisiones.db")
RAIZ = os.path.join("work", "revision")
# El montaje va acelerado; los tiempos del plan son de ANTES de acelerar.
# **1, no 1,15: no hay que acelerar nada.** Jaime, al ver las duraciones reales:
# *«ninguno hay que acelerar la verdad, todos estan por debajo de los 120 y en
# el rango de los 90s»*. A velocidad natural el lote va de 47,6 a 118,5 s, con
# cuatro de seis entre 72 y 89 — que es formato corto sin forzar nada.
#
# Y quita de la cadena la resintesis mas grande. `rubberband` no es un filtro:
# reconstruye la senal. Con la voz limpiada fuera eran **dos resintesis
# encadenadas**, y ahi es donde empezo a sonar a papilla.


# El apodo lo hace `dominio.texto`, que es el dueño de cómo se normaliza un
# texto en este proyecto. Estaba copiado aquí, en `publicar.py` y en
# `revisar.py`, las tres veces igual.
from dominio.texto import apodo  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    a = ap.parse_args()

    con = basedatos.abrir(BASE)
    for n in (a.reels or rutas.piezas()):
        slug, pieza = f"reel-{n:02d}", f"reel-R{n}"
        fuente = os.path.join(rutas.DESTINO, "entrega", f"{pieza}.mp4")
        if not os.path.exists(fuente):
            print(f"{slug}: sin entrega renderizada todavia")
            continue

        # Una fila por ETAPA, juntando las escenas que la componen: lo que se
        # aprueba es el segmento del frame, no cada punch-in por separado.
        filas = con.execute("""
            select e.orden, ec.nombre,
                   min(c.desde_s), max(c.desde_s + c.dura_s), count(*),
                   min(c.fragmento_id)
              from colocacion c
              join video v on v.id = c.video_id
              join etapa e on e.id = c.etapa_id
              left join etapa_canonica ec
                     on ec.estructura_id = e.estructura_id
                    and ec.orden = e.etapa_orden
             where v.slug = ? and c.tipo = 'toma'
             group by e.orden order by e.orden
        """, (slug,)).fetchall()
        if not filas:
            print(f"{slug}: sin colocaciones — corre colocar.py")
            continue

        carpeta = os.path.join(RAIZ, slug)
        os.makedirs(carpeta, exist_ok=True)
        # **De que segundo a que segundo va cada etapa**, en el video ENTREGADO
        # —ya dividido por la velocidad—, no en el plan. Si fueran los del plan
        # no servirian para buscar, que es justo para lo que se piden.
        indice = [f"# {pieza} - que hay en cada segundo", "",
                  "Segundos del video entregado. Para corregir algo, dime el"
                  " **numero de etapa**: se rehace esa sola y el resto sale"
                  " identico.", "",
                  "| # | etapa | desde | hasta | dura | de la cinta |",
                  "|---|---|---|---|---|---|"]
        hechos = 0
        # La cinta se busca aparte: SQLite no admite un agregado dentro de una
        # subconsulta correlacionada, y forzarlo es mas fragil que dos consultas.
        def cinta_de(fid):
            r = con.execute(
                "select t.nombre from fragmento f join toma t on t.id = f.toma_id"
                " where f.id = ?", (fid,)).fetchone()
            return r[0] if r else None

        for orden, etapa, a0, b0, escenas, fid in filas:
            cinta = cinta_de(fid)
            ini, dur = a0, b0 - a0
            salida = os.path.join(carpeta, f"{orden:02d}-{apodo(etapa)}.mp4")
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}",
                 "-i", fuente, "-t", f"{dur:.3f}", "-c", "copy", salida],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0 or not os.path.exists(salida):
                registro.error("revisar", "no se pudo recortar del render",
                               detalle=f"{slug} etapa {orden}: {(r.stderr or '')[-140:]}")
                continue
            hechos += 1
            propia = rutas.TOMAS.get(slug)
            marca = "" if cinta == propia else f"  ← {cinta}"
            indice.append(f"| {orden} | {etapa or ''} | **{ini:.1f}s** | "
                          f"{ini + dur:.1f}s | {dur:.1f}s | "
                          f"{'la suya' if cinta == propia else cinta} |")
            print(f"  {orden:2d}. {(etapa or '')[:30]:<30} "
                  f"{ini:6.1f}s - {ini + dur:6.1f}s  ({escenas} escenas){marca}")
        io.open(os.path.join(carpeta, f"{pieza}.segmentos.md"), "w",
                encoding="utf-8").write("\n".join(indice) + "\n")
        print(f"{slug}: {hechos} fragmentos listos para oir -> {carpeta}\n")
    con.close()


if __name__ == "__main__":
    main()
