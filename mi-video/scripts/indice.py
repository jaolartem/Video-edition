"""El índice de FINALES: qué vídeo es cada uno y lo que dice.

Jaime, 20-10-2026: *«necesito que en I también quede un descriptor de qué video
es cada uno, con el script final, todo en un archivo md»*. Los ficheros se
llaman `reel-R20.mp4` y eso no dice nada a quien abre la carpeta para publicar.

Se escribe **de lo que hay en la carpeta**, no de lo que la línea cree haber
subido: una pieza copiada a mano también es una pieza que alguien va a abrir.
Y cada dato sale de su dueño —`video.porque` de la base, el EDL, los subtítulos
del render vía `Pieza.dicho`—, así que el índice no se edita: se regenera.

    python scripts/publicar.py --indice     # lo rehace sin subir nada
"""
import glob
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basedatos  # noqa: E402
from dominio.pieza import Pieza  # noqa: E402

NOMBRE = "INDICE.md"
#: Lo que se toma del guion como título: la primera frase, hasta este tope.
TITULO = 110


def _porque(slug):
    con = basedatos.abrir()
    con.row_factory = sqlite3.Row
    r = con.execute("select porque from video where slug = ?", (slug,)).fetchone()
    con.close()
    return (r["porque"] or "").strip() if r else ""


def _plan(slug):
    """Qué vídeo del plan es: la primera línea del `porque` de su frame.

    Jaime: *«lo importante es identificar qué video es cuál»*. Las piezas de un
    ciclo la declaran así en `ads/frames.json` —«Ciclo W40, video 3 · Lo gratis
    · larga · miércoles 21-10-2026, 7:00 p. m.»—, que es el nombre con el que
    él las planea. Las de antes de los ciclos no la tienen: cadena vacía.
    """
    try:
        r = json.load(open("ads/frames.json", encoding="utf-8"))["reels"].get(slug)
    except (OSError, KeyError, ValueError):
        return ""
    p = (r or {}).get("porque") or ""
    corrido = " ".join(p) if isinstance(p, list) else str(p)
    # La línea se parte a 80 columnas, así que se junta y se corta en la hora.
    m = re.match(r"(Ciclo .+? p\. m\.)", corrido.strip())
    return m.group(1) if m else ""


def _titulo(guion):
    """La primera frase de lo que se dice: es el gancho, y es como se reconoce."""
    corrido = " ".join(t for _, t in guion)
    m = re.match(r"(.+?[.?!])(\s|$)", corrido)
    frase = (m.group(1) if m else corrido).strip()
    return frase if len(frase) <= TITULO else frase[:TITULO].rsplit(" ", 1)[0] + "…"


def _verificacion(n):
    """El bloque de verificación de la pieza, como sección del índice."""
    import rutas

    try:
        texto = open(os.path.join(rutas.DESTINO, f"Reel-R{n}.verification.md"),
                     encoding="utf-8").read()
    except OSError:
        return ["### Verificación", "", "Sin verificación escrita para esta pieza.", ""]
    lineas = [ln for ln in texto.splitlines() if not ln.startswith("# ")]
    return ["### Verificación", ""] + [
        ("##" + ln) if ln.startswith("## ") else ln for ln in lineas] + [""]


def ficha(n):
    """La sección de una pieza, en markdown."""
    p = Pieza(n)
    edl = p.edl or {}
    etapas = {}
    for d in edl.get("detalle", []) + edl.get("sin_toma", []):
        etapas.setdefault(d.get("beat"), d.get("etapa"))
    dicho = p.dicho
    guion = [(b, t) for b, t in sorted((dicho or {}).items(),
                                       key=lambda x: (x[0] is None, x[0] or 0))]
    v = p.version or {}
    plan = _plan(p.slug)
    cab = f"## R{n} · {plan or _titulo(guion)}" if plan or guion else f"## R{n}"
    datos = [f"`reel-R{n}.mp4`"]
    if p.cintas:
        datos.append("bruto " + ", ".join(f"`{c}`" for c in sorted(p.cintas)))
    if v.get("duracion_s"):
        datos.append(f"{v['duracion_s']:.1f} s".replace(".", ","))
    datos += [x for x in (edl.get("pilar"), edl.get("estructura")) if x]
    if v.get("n"):
        datos.append(f"versión {v['n']}")
    out = [cab, "", " · ".join(datos), ""]
    if plan and guion:
        out += [f"Empieza: «{_titulo(guion)}»", ""]
    if _porque(p.slug):
        out += [f"**Qué es.** {_porque(p.slug)}", ""]
    out += ["### Guion final", ""]
    if dicho is None:
        out += ["El vídeo de esta carpeta salió de un montaje anterior al de hoy"
                " —la huella del render no es la del spec—, así que su guion no"
                " está en la línea. No se reconstruye.", ""]
    for b, t in guion:
        nombre = etapas.get(b) or "—"
        out += [f"**{b if b is not None else '·'} · {nombre}.** {t}", ""]
    # **Y su verificación, dentro** (C-623). Jaime: *«todos los documentos
    # deben estar en un solo documento»*: subía un `.verificacion.md` por
    # pieza al lado del vídeo. Es el bloque de `verificacion.mjs`, con sus
    # títulos bajados un nivel para que cuelguen de la pieza.
    out += _verificacion(n)
    pies = [(b.get("beat"), (b.get("props") or {}).get("pie"))
            for b in (p.pintado or {}).get("boards") or []]
    if any(pie for _, pie in pies):
        out += ["### Fuentes en pantalla", ""]
        out += [f"- Etapa {b}: {pie}" for b, pie in pies if pie] + [""]
    return "\n".join(out)


def escribir(raiz):
    """Rehace el índice de la carpeta con las piezas que tiene. Devuelve su ruta."""
    nums = sorted(int(m.group(1)) for f in glob.glob(os.path.join(raiz, "reel-R*.mp4"))
                  if (m := re.search(r"reel-R(\d+)\.mp4$", f)))
    partes = ["# FINALES · qué vídeo es cada uno", "",
              "Generado por `scripts/indice.py` al publicar. No se edita a mano:"
              " se rehace con `python scripts/publicar.py --indice`.", ""]
    partes += ["| Fichero | Qué vídeo es | Bruto |", "|---|---|---|"]
    for n in nums:
        slug = f"reel-{n:02d}"
        partes.append(f"| `reel-R{n}.mp4` | {_plan(slug) or '— (anterior a los ciclos)'}"
                      f" | {', '.join(sorted(Pieza(n).cintas)) or '—'} |")
    partes.append("")
    for n in nums:
        partes += ["---", "", ficha(n)]
    ruta = os.path.join(raiz, NOMBRE)
    open(ruta, "w", encoding="utf-8", newline="\n").write("\n".join(partes) + "\n")
    return ruta
