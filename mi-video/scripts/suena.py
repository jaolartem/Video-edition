"""Cómo SUENA la pieza entregada. Es mi oído, y no es leer el transcript.

Regla de Jaime, y corrige lo que yo estaba haciendo: *«no se escucha con
subtítulos, el sonido no es escrito»*. Yo había contestado «reel-04 dice esto»
mirando el texto y la cobertura de subtítulos, que es exactamente lo que no
contesta *cómo suena*. Y la otra suya, que es la que da el método: *«tú no
tienes oídos, pero puedes analizar qué está pasando cuando algo se dice»*.

Así que esto mide **la onda del fichero entregado**, no el corte ni el texto:

    sonoridad      LUFS integrados. Las plataformas normalizan a ~−14: una pieza
                   a −9 la bajan ellas, y el nivel deja de ser del montaje
    pico_real      dBTP. Por encima de −1 los códecs con pérdida distorsionan
    saturadas      muestras pegadas a 0 dB. Vienen del rodaje y no se arreglan
                   bajando el volumen: la onda ya está recortada
    aire           el silencio más largo. Un hueco de 6 s en formato corto es
                   el sitio por donde se va el espectador

Y lo que sólo se ve **entre** dos trozos, que es lo que delata un corte:

    costuras       cuánto salta la voz al cruzar cada unión, en semitonos y en
                   palabras por segundo. Dos tomas pueden puntuar de maravilla
                   por separado y sonar a pegote cuando una acaba grave y
                   despacio y la siguiente arranca aguda y disparada

Los umbrales no son míos: `beats.SALTO_TONO` y `beats.SALTO_RITMO` son los que
el proyecto ya usaba para decir cuándo una costura se oye.

Nada de esto decide. Informa, y lo que informa se guarda en `medicion` —que
llevaba seis tipos declarados y cero filas—, porque un número que se pierde al
cerrar la terminal se vuelve a medir o, peor, se supone.

    python scripts/suena.py            # las seis
    python scripts/suena.py 4          # sólo el reel 4
    python scripts/suena.py --guardar  # además lo apunta en `medicion`
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import basedatos
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beats  # noqa: E402
import rutas  # noqa: E402
import transcribir  # noqa: E402

BASE = "ads/decisiones.db"

#: Lo que las plataformas esperan. No es una preferencia: es a lo que normalizan.
OBJETIVO_LUFS = -14.0
PICO_MAX = -1.0
#: Un hueco más largo que esto en formato corto es por donde se va el espectador.
AIRE_MAX = 4.0


def _ffmpeg(args):
    return subprocess.run(["ffmpeg", "-v", "info", *args, "-f", "null", "-"],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stderr


def onda(mp4):
    """Sonoridad, pico y saturación del fichero, medidos sobre la onda."""
    out = {}
    t = _ffmpeg(["-i", mp4, "-af", "ebur128=peak=true"])
    for clave, patron in (("sonoridad", r"I:\s*(-?[\d.]+) LUFS"),
                          ("pico_real", r"Peak:\s*(-?[\d.]+) dBFS")):
        m = re.findall(patron, t)
        if m:
            out[clave] = float(m[-1])
    t = _ffmpeg(["-i", mp4, "-af", "astats=metadata=1:reset=0"])
    m = re.findall(r"Number of samples exceeding 0dB:\s*(\d+)", t)
    if not m:
        m = re.findall(r"Flat factor:\s*([\d.]+)", t)
        out["saturadas"] = None
    else:
        out["saturadas"] = sum(int(x) for x in m)
    return out


def aire(mp4, umbral=-40, minimo=0.6):
    """Los silencios del fichero. Devuelve el más largo y cuántos hay."""
    t = _ffmpeg(["-i", mp4, "-af", f"silencedetect=noise={umbral}dB:d={minimo}"])
    duras = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", t)]
    return {"huecos": len(duras),
            "aire_max": round(max(duras), 2) if duras else 0.0,
            "aire_total": round(sum(duras), 1)}


def costuras(slug):
    """Cuánto se oye cada unión. Una fila por costura del montaje.

    Se mide **sobre las cintas**, no sobre el mp4: en el fichero entregado las
    dos mitades ya están pegadas y no hay forma de separar qué venía de dónde.
    La costura es una propiedad del corte, y el corte está en el EDL.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    segs, det = edl["segmentos"], edl["detalle"]
    cache = {}

    def palabras(toma):
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
        return cache[toma]

    out = []
    for i in range(len(segs) - 1):
        ta = det[i].get("toma")
        tb = det[i + 1].get("toma")
        if not ta or not tb:
            continue
        try:
            s = beats.salto(ta, segs[i][1], tb, segs[i + 1][0],
                            palabras(ta), palabras_b=palabras(tb))
        except Exception:                          # noqa: BLE001
            continue
        tono = float(s.get("tono") or 0)
        ritmo = float(s.get("ritmo") or 0)
        # **Se oye o no se oye, y la vara es UNA.** Esto usaba
        # `beats.SALTO_TONO` (2,0) y `beats.SALTO_RITMO` (1,5) mientras el paso
        # que cose usaba 2,5 y 3,0, así que el informe denunciaba uniones que el
        # cosido daba por limpias — dos respuestas a la misma pregunta, que es
        # la avería de esta semana en su forma más pura.
        #
        # Manda la del paso que **actúa**: sus umbrales están medidos contra las
        # piezas reales, y una alarma que nadie va a atender es ruido que tapa
        # las que sí. Ver `dominio/costura.py`.
        from dominio.costura import RITMO_OK, TONO_OK

        if tono > TONO_OK or ritmo > RITMO_OK:
            out.append({"en": round(sum(b - a for a, b in segs[:i + 1]), 1),
                        "beat": det[i].get("beat"),
                        "a_beat": det[i + 1].get("beat"),
                        "tono": round(tono, 1), "ritmo": round(ritmo, 2),
                        "cambia_de_cinta": ta != tb})
    return out


def medir(n):
    """Mide **lo que se entrega**, no el render crudo.

    Se apuntaba a `out/reels/`, que es la salida de Remotion antes de nivelar, y
    por eso el primer parte decia «-10,0 LUFS» de una pieza que ya estaba a -14:
    estaba midiendo otro fichero. Lo que se publica es `out/entrega/`, asi que es
    lo unico que tiene sentido medir; el crudo queda de respaldo por si la fase
    de nivelado todavia no ha corrido.
    """
    slug = f"reel-{n:02d}"
    mp4 = rutas.salida("entrega", f"reel-R{n}.mp4")
    if not os.path.exists(mp4):
        mp4 = rutas.salida("reels", f"reel-R{n}.mp4")
    if not os.path.exists(mp4):
        return None
    d = {"slug": slug, "fichero": mp4}
    d.update(onda(mp4))
    d.update(aire(mp4))
    d["costuras"] = costuras(slug)
    return d


def guardar(d):
    """Lo apunta en `medicion`, que existía con seis tipos y ninguna fila."""
    con = basedatos.abrir(BASE)
    con.row_factory = sqlite3.Row
    tipos = {r["nombre"]: r["id"] for r in con.execute("select * from tipo_medicion")}
    # **La medida cuelga de la VERSION, no del video**, y es lo correcto: un
    # numero de sonoridad sin decir de que corte sale no dice nada, porque el
    # siguiente montaje lo cambia. `medicion.version_id` es NOT NULL justo por
    # eso; yo lo intente guardar contra `video_id` y la base me paro.
    ver = con.execute(
        "select ve.id from version ve join video vi on vi.id = ve.video_id"
        " where vi.slug = ? order by ve.n desc limit 1", (d["slug"],)).fetchone()
    if not ver:
        con.close()
        return 0
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    n = 0
    for nombre, clave in (("sonoridad", "sonoridad"), ("pico_real", "pico_real"),
                          ("muestras_saturadas", "saturadas"),
                          ("aire_quitado", "aire_total")):
        if tipos.get(nombre) is None or d.get(clave) is None:
            continue
        con.execute(
            # **Se sustituye, no se acumula.** La clave es
            # `(version_id, tipo_id)`, asi que un `insert` a secas revienta la
            # segunda vez que se mide la MISMA version — y medir dos veces la
            # misma pieza no es un error del usuario: es lo que pasa cuando la
            # linea vuelve atras y repite el paso, que es su forma normal de
            # trabajar.
            #
            # Y sustituir es lo correcto ademas de lo comodo: la medida de una
            # version es una, la del fichero que hay ahora. Guardar dos
            # obligaria a decidir cual vale, y esa pregunta no deberia existir.
            "insert into medicion (version_id, tipo_id, valor, fecha)"
            " values (?,?,?,?)"
            " on conflict(version_id, tipo_id) do update set"
            " valor=excluded.valor, fecha=excluded.fecha",
            (ver["id"], tipos[nombre], d[clave], ahora))
        n += 1
    con.commit()
    con.close()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--guardar", action="store_true")
    a = ap.parse_args()
    for n in (a.reels or rutas.piezas()):
        d = medir(n)
        if not d:
            print(f"reel-{n:02d}: sin render")
            continue
        mal = []
        if d.get("sonoridad") is not None and abs(d["sonoridad"] - OBJETIVO_LUFS) > 1.5:
            mal.append(f"sonoridad {d['sonoridad']:.1f} LUFS (las plataformas"
                       f" normalizan a {OBJETIVO_LUFS:.0f}: se la bajan ellas)")
        if d.get("pico_real") is not None and d["pico_real"] > PICO_MAX:
            mal.append(f"pico {d['pico_real']:.1f} dBTP: por encima de"
                       f" {PICO_MAX:.0f} los codecs distorsionan")
        if d["aire_max"] > AIRE_MAX:
            mal.append(f"un hueco de {d['aire_max']:.1f}s de aire")
        if d["costuras"]:
            mal.append(f"{len(d['costuras'])} costura(s) que se oyen")
        print(f"\n{d['slug']}  {d.get('sonoridad', '?')} LUFS · pico"
              f" {d.get('pico_real', '?')} dBTP · aire max {d['aire_max']}s"
              f" ({d['huecos']} huecos)")
        for m in mal:
            print(f"    · {m}")
        for c in d["costuras"][:6]:
            print(f"      {c['en']:>6.1f}s  b{c['beat']}->b{c['a_beat']}"
                  f"  tono {c['tono']} st  ritmo {c['ritmo']} pal/s"
                  + ("  (cambia de cinta)" if c["cambia_de_cinta"] else ""))
        if not mal:
            print("    suena limpio")
        if a.guardar:
            print(f"    ({guardar(d)} medida(s) apuntadas)")


if __name__ == "__main__":
    main()
