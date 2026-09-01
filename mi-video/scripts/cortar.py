"""Corta cada fragmento a su propio fichero, y sólo el que cambió.

Es el peldaño `cortado` del embudo de Jaime: *«primero ponemos cada cosa en su
lugar, luego escogemos la mejor, luego la preparamos para que esté bien —pero ya
no todo el vídeo, esa parte específica— y luego renderizamos, pero sólo lo que
ya sabemos que está bien»*.

Y es la pieza que convierte el modelo en comportamiento. Hasta ahora el corte
iba escena→temporal→concatenado y la carpeta se borraba en cada pasada, así que
cambiar un segmento costaba rehacer la pieza entera. Con el fragmento como
fichero:

- **Corregir uno cuesta uno.** Los demás salen idénticos porque no se tocan.
- **Se salta lo que no cambió**, por la huella de `colocacion` — el peldaño caro
  toca sólo lo que cambió.
- **Deja de importar de qué cinta sale cada uno.** El corte abría un solo `-i` y
  por eso el material de otras grabaciones estaba frenado; aquí no hay dos
  fuentes en un corte, hay dos cortes.

    python scripts/cortar.py 3        # los fragmentos elegidos del reel 3
    python scripts/cortar.py 3 --todo # rehace tambien los que no cambiaron
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sqlite3
import basedatos
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(__file__))
import gpu  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402

BASE = os.path.join("ads", "decisiones.db")
RAIZ = os.path.join("work", "fragmentos")

# El codificador de AMD: medido 1,76x sobre libx264 en esta maquina (C-56).
ENCODE = ["-c:v", "h264_amf", "-quality", "balanced", "-b:v", "8M",
          "-c:a", "aac", "-b:a", "160k"]


def apodo(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "sin-nombre"


def huella(toma, a, b, filtro):
    crudo = json.dumps({"t": toma, "a": round(a, 3), "b": round(b, 3),
                        "f": filtro}, sort_keys=True)
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:16]


def filtro_de(slug, a, b):
    """El encuadre de la escena que cubre este fragmento, si lo hay.

    Se toma el de la PRIMERA escena que cae dentro: un fragmento se parte en
    varias escenas por encuadre, y para oírlo y aprobarlo basta una. El
    encuadre final es cosa del render de la pieza, no de este peldaño.
    """
    p = f"work/scenes/{slug}/plan-full.json"
    if not os.path.exists(p):
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    for e in json.load(open(p, encoding="utf-8")).get("escenas", []):
        if e.get("origen_desde", -1) >= a - 0.2 and e.get("origen_hasta", 0) <= b + 0.2:
            if e.get("filtro"):
                return e["filtro"]
    return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--todo", action="store_true",
                    help="rehace tambien los que no cambiaron")
    a = ap.parse_args()

    con = basedatos.abrir(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    fases = dict(con.execute("select nombre, id from fase").fetchall())
    ahora = datetime.datetime.now().isoformat(timespec="seconds")

    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        filas = con.execute("""
            select f.id, t.nombre, f.desde, f.hasta, e.orden, ec.nombre
              from eleccion el
              join etapa e on e.id = el.etapa_id
              join video v on v.id = e.video_id
              join fragmento f on f.id = el.fragmento_id
              join toma t on t.id = f.toma_id
              left join etapa_canonica ec
                     on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
             where v.slug = ? order by e.orden
        """, (slug,)).fetchall()
        if not filas:
            print(f"{slug}: sin elecciones — corre seleccionar.py primero")
            continue

        carpeta = os.path.join(RAIZ, slug)
        os.makedirs(carpeta, exist_ok=True)
        hechos = saltados = 0
        for (fid, toma, d, h, orden, etapa) in filas:
            nombre = f"{orden:02d}-{apodo(etapa)}"
            salida = os.path.join(carpeta, nombre + ".mp4")
            filtro = filtro_de(slug, d, h)
            hue = huella(toma, d, h, filtro)
            ya = con.execute("select fichero, por_que from paso where fragmento_id = ?",
                             (fid,)).fetchone()
            if (not a.todo and ya and ya[1] == hue and os.path.exists(salida)):
                saltados += 1
                continue
            src = f"{rutas.ORIGEN}/{toma}.mp4"
            # **Codificaba por la tarjeta y decodificaba en CPU.** El bruto es
            # 4K y eso era la mitad del coste: 9,0 s -> 4,7 s en un corte de
            # 12 s, **1,91x**.
            #
            # El `format=yuv420p` delante no es adorno, es la condicion. Con
            # `-hwaccel` los frames vuelven en NV12 y `crop`/`scale` los tratan
            # distinto: sin el, el corte salia con el 47,9% de los pixeles
            # cambiados —PSNR 42,9 dB, invisible pero real— y esto es el video
            # que se entrega. Con el, **el fichero sale con el mismo SHA-256**.
            # Comprobado ademas que el codificador si es determinista: CPU
            # contra CPU y tarjeta contra tarjeta dan cero diferencia.
            #
            # Y **no entra en `huella`** a proposito. La huella dice que corte
            # es, no como se decodifico; meterlo ahi invalidaria los 452
            # fragmentos y los volveria a cortar todos para producir los mismos
            # bytes. Eso es rehacer el lote por una tuerca.
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-y"] + gpu.decodifica()
                + ["-ss", str(d), "-i", src,
                   "-t", str(round(h - d, 3)),
                   "-vf", "format=yuv420p," + filtro, *ENCODE, salida],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0 or not os.path.exists(salida):
                registro.error("cortar", "no se pudo cortar el fragmento",
                               toma=toma,
                               detalle=f"{slug} {nombre}: {(r.stderr or '')[-160:]}")
                continue
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", salida], capture_output=True,
                text=True, encoding="utf-8", errors="replace").stdout.strip() or 0)
            # **Se comprueba que existe y cuanto dura**, no solo que ffmpeg
            # dijera que si: es la leccion de C-11, donde un fallo rapido se
            # midio como render rapido porque nadie miro el fichero.
            if abs(dur - (h - d)) > 0.5:
                registro.aviso("cortar", "el corte no dura lo pedido",
                               detalle=f"{slug} {nombre}: {dur:.2f}s de {h - d:.2f}s")
            con.execute(
                "insert into paso (fragmento_id, fase_id, fichero, duracion,"
                " por_que, fecha) values (?,?,?,?,?,?)"
                " on conflict(fragmento_id) do update set fase_id=excluded.fase_id,"
                " fichero=excluded.fichero, duracion=excluded.duracion,"
                " por_que=excluded.por_que, fecha=excluded.fecha",
                (fid, fases["cortado"], salida, round(dur, 3), hue, ahora))
            hechos += 1
        con.commit()
        print(f"{slug}: {hechos} cortados, {saltados} sin cambios -> {carpeta}")
    con.close()


if __name__ == "__main__":
    main()
