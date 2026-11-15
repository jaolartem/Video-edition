"""El guion de Jaime, transcrito a la declaración de la pieza. Sin interpretar.

    python scripts/guion.py <guion.md> reel-23 --aprobado "Jaime, 13-11-2026"

**Por qué existe.** El 14-11-2026 la sesión declaró `reel-23` a mano: metió el
AUDIO del guion como libreto, sacó de la columna VIDEO sólo unos rótulos y dejó
que los oficios improvisaran el resto. Salieron tableros negros donde el guion
decía «usted a cámara» (C-683). Jaime: *«ahí estaba el guion, ahí estaba todo;
¿por qué improvisan?»*.

Así que la declaración no la redacta nadie: la copia esto, mecánicamente.

- Un bloque es `### N · Título`, con su `**VIDEO:**` y su `**AUDIO:**` (las
  líneas `>` de debajo).
- Cada `//` del AUDIO cierra un beat: es la unidad que el propio guion marca.
- Cada beat lleva el VIDEO entero de su bloque, como `video`. Lo que dice cada
  frase del bloque lo entiende el compositor, que es comprensión; que el VIDEO
  llegue, no lo decide nadie.
- `--aprobado` es obligatorio: **una pieza entra desde un guion aprobado**. Si no
  hay guion, se construye como propuesta y Jaime lo aprueba antes de esto.
- Volver a declarar con un VIDEO distinto abre un tiquet a `descrito` por cada
  etapa que cambió (C-695): el cambio del guion es de Jaime y la máquina lo
  lleva a quien compone, no se queda en el JSON.

Lo demás de la pieza (formato, pilar, mecanismo…) se conserva si ya estaba, o se
pasa la primera vez con sus opciones. Escribe `ads/frames.json` de la línea en la
que corre; la base se entera en la siguiente vuelta (`avanzar` migra).
"""
import argparse
import json
import os
import re
import sys

FRAMES = os.path.join("ads", "frames.json")
_BLOQUE = re.compile(r"^###\s+\d+\s*[·.\-]\s*(.+?)\s*$")
_LIMPIA = re.compile(r"\*\*|(?<!\*)\*(?!\*)")


def bloques(texto: str) -> list[dict]:
    """`[{titulo, video, audio}]` en el orden del guion. Hasta la primera `## `."""
    out, actual, modo = [], None, None
    for linea in texto.splitlines():
        if linea.startswith("## ") and out:
            break
        m = _BLOQUE.match(linea)
        if m:
            actual = {"titulo": m.group(1).strip(), "video": "", "audio": []}
            out.append(actual)
            modo = None
            continue
        if actual is None:
            continue
        if linea.startswith("**VIDEO:**"):
            actual["video"] = _LIMPIA.sub("", linea[len("**VIDEO:**"):]).strip()
            modo = "video"
        elif linea.startswith("**AUDIO:**"):
            modo = "audio"
        elif modo == "audio" and linea.startswith(">"):
            actual["audio"].append(linea.lstrip(">").strip())
    return out


def beats(bls: list[dict]) -> list[dict]:
    """Un beat por unidad cerrada con `//`, con el VIDEO de su bloque."""
    out = []
    for b in bls:
        crudo = " ".join(x for x in b["audio"] if x)
        unidades = [_LIMPIA.sub("", u).strip() for u in crudo.split("//")]
        unidades = [re.sub(r"\s+", " ", u) for u in unidades if u]
        base = b["titulo"].lower()
        for k, u in enumerate(unidades, 1):
            out.append({"etapa": base if k == 1 else f"{base} ({k})",
                        "texto": u, "video": b["video"]})
    return out


def declarar(ruta_guion, slug, aprobado, estructura=None, extra=None):
    """Escribe la pieza `slug` en `frames.json`. Devuelve cuántos beats."""
    with open(ruta_guion, encoding="utf-8") as f:
        bs = beats(bloques(f.read()))
    if not bs:
        raise SystemExit(f"{ruta_guion}: no hay bloques `### N · Título` con AUDIO")
    texto = open(FRAMES, encoding="utf-8").read()
    d = json.loads(texto)
    pieza = d["reels"].get(slug) or {}
    est = estructura or pieza.get("estructura")
    if not est:
        raise SystemExit(f"{slug} es nueva: di su estructura con --estructura")
    d["estructuras"].setdefault(est, [b["etapa"] for b in bs if "(" not in b["etapa"]])
    pieza.update({k: v for k, v in (extra or {}).items() if v is not None})
    pieza.update({
        "estructura": est,
        "guion": {"fichero": os.path.basename(ruta_guion), "aprobado": aprobado},
        "beats": [{"etapa": b["etapa"], "video": b["video"]} for b in bs],
        "libreto": [b["texto"] for b in bs],
    })
    antes = (d["reels"].get(slug) or {}).get("beats") or []
    d["reels"][slug] = pieza
    with open(FRAMES, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1)
                + ("\n" if texto.endswith("\n") else ""))
    _devuelve_al_compositor(slug, antes, pieza["beats"])
    return len(bs)


def _devuelve_al_compositor(slug, antes, ahora) -> list:
    """**Un VIDEO que cambia en el guion vuelve a su compositor** (C-695).

    La columna VIDEO es la edición decidida (C-683) y el que compone la lee del
    pedido; pero lo ya compuesto no se enteraba de que cambió. reel-23,
    15-11-2026: Jaime quitó la cartela del bloque 1 y la pieza siguió adelante
    con la descripción vieja de la apertura. Cada etapa cuyo VIDEO cambió abre
    su tiquet a `descrito` con el texto nuevo; la primera declaración no abre
    ninguno, porque no hay nada compuesto que devolver.
    """
    cambian = [i for i, (a, b) in enumerate(zip(antes, ahora), 1)
               if (a.get("video") or "") != (b.get("video") or "")]
    if not antes or not cambian:
        return []
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dominio import ticket
    ids = [ticket.abrir(slug, f"Guion: cambió el VIDEO de la etapa {i} —"
                        f" «{ahora[i - 1]['video']}». Lo compuesto para esa etapa"
                        " se revisa contra esto.", tipo="objecion",
                        vuelve_a="descrito", etapa=i) for i in cambian]
    print(f"{slug}: VIDEO distinto en {len(ids)} etapa(s) -> tiquet(s) a descrito"
          f" {', '.join('#' + str(x) for x in ids)}")
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("guion")
    ap.add_argument("slug")
    ap.add_argument("--aprobado", required=True,
                    help="quién y cuándo aprobó el guion: sin esto no entra")
    ap.add_argument("--ver", action="store_true", help="enseña los beats y no escribe")
    ap.add_argument("--estructura")
    ap.add_argument("--formato")
    ap.add_argument("--pilar")
    a = ap.parse_args()
    if a.ver:
        with open(a.guion, encoding="utf-8") as f:
            for i, b in enumerate(beats(bloques(f.read())), 1):
                print(f"{i:2d} {b['etapa']:24} {b['texto'][:70]}")
        return
    n = declarar(a.guion, a.slug, a.aprobado, a.estructura,
                 {"formato": a.formato, "pilar": a.pilar})
    print(f"{a.slug}: {n} beats desde {a.guion}, aprobado por {a.aprobado}")


if __name__ == "__main__":
    sys.exit(main())
