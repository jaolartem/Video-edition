"""La revisión del compositor: oír los bordes y cotejar lo que se dice.

Jaime, poniendo cada revisión en su oficio: *«tanto el diseñador como el
compositor tienen procesos simplificados de revisión. Por ejemplo el compositor
tiene que escuchar los bordes de las escenas para asegurarse de que no hay
escenas cortadas a la mitad, tiene que estar seguro de que los subtítulos dicen
lo que el vídeo dice, y debe estar seguro de que lo que se dice es coherente con
la intención y con el vídeo; y cuando es revisión o tiquet, tiene que asegurarse
de que los cambios no hayan afectado al resto»*.

El diseñador **mira** —cinco fotogramas por escena, `fotogramas.py`—. El
compositor **oye y coteja**, que es otra cosa, y es lo que arma esto.

## Las cuatro comprobaciones, y qué caza cada una

1. **Los bordes.** Un recorte de medio segundo a cada lado del corte. Es donde
   se ve si una frase quedó partida, si entra una palabra ya empezada o si se
   comió el final de la anterior. Es exactamente el defecto que él señaló —*«R3
   tiene frases que no inician donde deben sino que se comen la palabra»*— y que
   sólo se oye: por texto esos tramos estaban limpios.

2. **El subtítulo contra la voz.** Lo que está quemado en pantalla frente a lo
   que se oye. De aquí salió «una futura situación **gratuita**» donde la cinta
   dice «fortuita», y «bulletin» donde él dice «bootcamp».

3. **Lo dicho contra la intención.** El libreto de esa etapa al lado del texto
   que sobrevivió al corte. No para exigir que coincidan —*«no se toma el
   libreto literal, se toma la intención comunicativa»*— sino para ver si la
   idea sigue estando: así se vio que R5 nunca llegaba a nombrar al realtor.

4. **Qué más se movió.** Cuando esto viene de un tiquet, el resto de la pieza
   está aprobado. Se dice qué escenas cambiaron respecto al último montaje para
   que la revisión mire **ésas** y no la pieza entera, que es lo que él pidió:
   *«no puedo estar haciendo un rebuild cada vez que corrijo cosas puntuales»*.

    python scripts/escucha.py 3        # arma la revisión de reel-03
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: Cuánto se oye a cada lado del corte, en segundos. Medio segundo es una
#: palabra entera: lo justo para saber si entra empezada.
BORDE = 0.5

SALIDA = "work/escucha/{slug}"
CORTE = "public/{slug}.mp4"


def _cortes(slug):
    """Los segundos del montaje donde hay un empalme."""
    f = f"work/scenes/{slug}/plan-full.json"
    if not os.path.exists(f):
        return []
    with open(f, encoding="utf-8") as fh:
        plan = json.load(fh)["escenas"]
    fuera, t = [], 0.0
    for i, e in enumerate(plan, 1):
        t += e["origen_hasta"] - e["origen_desde"]
        if i < len(plan):
            fuera.append({"tras_escena": i, "en": round(t, 3)})
    return fuera


#: Cada cuanto se mide la envolvente del borde. 25 ms es medio fonema: mas fino
#: no dice nada nuevo y mas grueso se salta una consonante cortada.
PASO = 0.025

#: Por debajo de esto no hay voz. Medido sobre las siete piezas: los huecos
#: reales caen a -45 dB o menos y la voz mas floja se queda en -32.
SUELO = -38.0


def envolvente(wav, paso=PASO):
    """El borde **en algo que se pueda mirar**: dBFS cada 25 ms, y lo que dicen.

    Jaime, 7-9-2026, sobre que es de cada oficio: *«lo suyo es todo lo que les
    ayude a tomar mejores decisiones, como el tema del sonido»*. Y este paso
    existe justo para eso — *«el compositor tiene que escuchar los bordes»*.

    Pero el compositor **no oye**: lee texto e imagenes. Se le mandaban 33 rutas
    de wav y el de reel-05 lo dijo con todas las letras: *«no pude oir los 33
    wav; no hay juicio de bordes de corte en esta respuesta»*. Contestó sin esa
    mitad, y el pedido parecia completo.

    Nombrar un fichero que el oficio no puede abrir es igual que no mandarselo,
    con la diferencia de que parece que se lo mandaste. Asi que el wav se queda
    —para quien si pueda oirlo— y ademas viaja medido: donde hay voz, donde no,
    y si el corte cae dentro de una palabra o en el silencio de al lado.
    """
    import math
    import wave
    import contextlib
    import struct

    try:
        with contextlib.closing(wave.open(wav)) as f:
            sr, n = f.getframerate(), f.getnframes()
            d = struct.unpack("<%dh" % n, f.readframes(n))
    except Exception:                              # noqa: BLE001
        return None
    ancho = max(1, int(sr * paso))
    db = []
    for i in range(0, len(d) - ancho + 1, ancho):
        tr = d[i:i + ancho]
        rms = math.sqrt(sum(x * x for x in tr) / len(tr)) or 1
        db.append(round(20 * math.log10(rms / 32768), 1))
    if not db:
        return None
    # El corte esta en la mitad del recorte, que es como lo saca `bordes`.
    medio = len(db) // 2
    suena = [v > SUELO for v in db]
    def _corrido(desde, paso_):
        k, n_ = desde, 0
        while 0 <= k < len(suena) and not suena[k]:
            n_ += 1
            k += paso_
        return round(n_ * paso, 3)
    return {"paso_s": paso, "dbfs": db, "corte_en": medio,
            "voz_justo_antes": bool(medio and suena[medio - 1]),
            "voz_justo_despues": bool(medio < len(suena) and suena[medio]),
            "silencio_antes_s": _corrido(medio - 1, -1),
            "silencio_despues_s": _corrido(medio, 1)}


def bordes_medidos(slug):
    """Cada empalme con su envolvente, para el que dibuja.

    El mismo dato que ya recibe el compositor. Se calcula una vez —los wav ya
    estan en disco si el paso de escucha corrio— y si no estan, se dice y no se
    inventa.
    """
    import glob
    import os

    wavs = sorted(glob.glob(os.path.join("work", "escucha", slug, "*.wav")))
    if not wavs:
        return {"sin_medir": f"no hay recortes en work/escucha/{slug}:"
                             f" corre `python scripts/escucha.py {slug}`"}
    fuera = []
    for w in wavs:
        m = envolvente(w)
        if m:
            fuera.append({"corte": os.path.basename(w), **m})
    return fuera

def bordes(slug):
    """Deja un recorte de audio en cada empalme. Devuelve qué dejó."""
    mp4 = CORTE.format(slug=slug)
    if not os.path.exists(mp4):
        return [], f"no esta {mp4}"
    fuera = os.path.join(*SALIDA.format(slug=slug).split("/"))
    os.makedirs(fuera, exist_ok=True)
    hechos = []
    for c in _cortes(slug):
        wav = os.path.join(fuera, f"corte-{c['tras_escena']:02d}.wav")
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-ss", f"{max(0, c['en'] - BORDE):.3f}", "-i", mp4,
             "-t", f"{BORDE * 2:.3f}", "-vn", "-ac", "1", "-ar", "16000", wav],
            capture_output=True)
        if r.returncode == 0 and os.path.exists(wav):
            hechos.append({**c, "oye": wav.replace("\\", "/"),
                           "medido": envolvente(wav)})
    return hechos, None


def dice_vs_libreto(slug):
    """Etapa por etapa: qué se quería decir y qué quedó dicho."""
    import sqlite3

    import basedatos

    edl = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(edl):
        return []
    with open(edl, encoding="utf-8") as f:
        d = json.load(f)
    dicho = {}
    for det in d.get("detalle", []):
        b = det.get("beat") or det.get("etapa_orden")
        if b is not None and det.get("texto"):
            dicho.setdefault(b, det["texto"])
    cx = basedatos.abrir("ads/decisiones.db")
    cx.row_factory = sqlite3.Row
    v = cx.execute("select id from video where slug = ?", (slug,)).fetchone()
    libreto = {}
    if v:
        for r in cx.execute("select orden, texto from libreto where video_id = ?",
                            (v["id"],)):
            libreto[r["orden"]] = r["texto"]
    cx.close()
    return [{"etapa": b, "queria_decir": (libreto.get(b) or "")[:300],
             "quedo_dicho": (dicho.get(b) or "")[:300]}
            for b in sorted(set(dicho) | set(libreto))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    a = ap.parse_args()
    for n in (a.reels or range(1, 8)):
        slug = f"reel-{n:02d}"
        oir, mal = bordes(slug)
        if mal:
            print(f"  {slug}: {mal}")
            continue
        pares = dice_vs_libreto(slug)
        huecos = [p["etapa"] for p in pares if not p["quedo_dicho"]]
        kit = {"pieza": slug, "bordes": oir, "dice_vs_libreto": pares}
        d = os.path.join(*SALIDA.format(slug=slug).split("/"))
        with open(os.path.join(d, "revision.json"), "w", encoding="utf-8") as f:
            json.dump(kit, f, ensure_ascii=False, indent=1)
        print(f"  {slug}: {len(oir)} borde(s) para oir · {len(pares)} etapa(s)"
              f" cotejadas"
              + (f" · SIN VOZ en {huecos}" if huecos else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
