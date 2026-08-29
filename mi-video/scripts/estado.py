"""La base de datos de decisiones: qué segmento está bien y cuál no.

## Por qué existe

Idea de Jaime: *«abrir una base de datos que vaya registrando las partes que
están bien y las que están mal, con eso si te digo "este segmento no es
adecuado" sólo cambies ese segmento… como una semi aplicación»*.

Resuelve el problema que ya nos mordió tres veces y que está escrito como
aprendizaje 13: **al regenerar, un automatismo sustituye lo que ya se había
elegido de oído**. La apertura del reel 1, el arranque del 5, los cierres — cada
vez que se volvía a montar había que acordarse de re-imponerlos a mano.

Con esto deja de depender de que alguien se acuerde: **un beat aprobado no se
vuelve a elegir.** El montaje lo lee, lo respeta y sólo trabaja sobre lo que
está pendiente o rechazado.

## Los cuatro estados

| Estado | Qué significa | Qué hace el montaje |
|---|---|---|
| `aprobado` | Está bien. Jaime lo vio o lo aprobó por defecto | Lo usa tal cual. **No lo re-elige** |
| `recortar` | Sirve, pero hay que entrar o salir en otro punto | Lo usa con el recorte guardado |
| `rechazado` | No sirve. La etapa va con animación | No busca sustituto: va con tarjeta |
| `pendiente` | Todavía no se ha juzgado | Lo elige el paso 2 |

Un beat que no aparece en el fichero está `pendiente`.

## Uso

    python scripts/estado.py ver 1
    python scripts/estado.py aprobar 1 3
    python scripts/estado.py rechazar 1 7 "arranca con un intento abortado"
    python scripts/estado.py recortar 1 2 --entra 217.5 "el «y los que usan» sobra"
    python scripts/estado.py pendiente 1 5      # lo devuelve al paso 2
"""
import argparse
import json
import os
import sys

RUTA = os.path.join("ads", "estado.json")

CABECERA = [
    "Base de datos de decisiones por beat. La escribe `scripts/estado.py` y la",
    "lee `scripts/beats.py` antes de elegir nada.",
    "",
    "**Un beat `aprobado` no se vuelve a elegir.** Ése es todo el punto: cuando",
    "Jaime dice que un segmento no sirve, se marca ESE y se remonta — el resto",
    "no se toca. Antes cada regeneración sustituía lo ya decidido y había que",
    "re-imponerlo a mano (aprendizaje 13).",
    "",
    "Estados: `aprobado` · `recortar` · `rechazado` · `pendiente` (o ausente).",
]


def cargar():
    if not os.path.exists(RUTA):
        return {"_": CABECERA, "reels": {}}
    d = json.load(open(RUTA, encoding="utf-8"))
    d["_"] = CABECERA
    d.setdefault("reels", {})
    return d


def guardar(d):
    os.makedirs("ads", exist_ok=True)
    json.dump(d, open(RUTA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def de(reel, beat):
    """El estado de un beat, o `pendiente` si no está registrado."""
    d = cargar()
    return d["reels"].get(f"reel-{reel:02d}", {}).get(str(beat),
                                                      {"estado": "pendiente"})


def del_reel(reel):
    return cargar()["reels"].get(f"reel-{reel:02d}", {})


def marcar(reel, beat, estado, por_que="", **extra):
    d = cargar()
    slug = f"reel-{reel:02d}"
    d["reels"].setdefault(slug, {})
    if estado == "pendiente":
        d["reels"][slug].pop(str(beat), None)
    else:
        anterior = d["reels"][slug].get(str(beat), {})
        d["reels"][slug][str(beat)] = {
            **anterior, "estado": estado, "por_que": por_que,
            **{k: v for k, v in extra.items() if v is not None},
        }
    guardar(d)
    return d["reels"][slug].get(str(beat), {"estado": "pendiente"})


def _texto_de(reel, beat):
    """El texto que hay hoy en el EDL para ese beat, si lo hay."""
    f = f"ads/reel-{reel:02d}/edl-sell.json"
    if not os.path.exists(f):
        return None
    for u in json.load(open(f, encoding="utf-8")).get("detalle", []):
        if u.get("beat") == beat:
            return u
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("ver"); v.add_argument("reel", type=int)
    for nombre in ("aprobar", "rechazar", "pendiente"):
        q = sub.add_parser(nombre)
        q.add_argument("reel", type=int)
        q.add_argument("beat", type=int)
        q.add_argument("por_que", nargs="?", default="")
    q = sub.add_parser("recortar")
    q.add_argument("reel", type=int); q.add_argument("beat", type=int)
    q.add_argument("por_que", nargs="?", default="")
    q.add_argument("--entra", type=float); q.add_argument("--sale", type=float)

    a = ap.parse_args()

    if a.cmd == "ver":
        est = del_reel(a.reel)
        f = f"ads/reel-{a.reel:02d}/edl-sell.json"
        n = 0
        if os.path.exists(f):
            n = len(json.load(open(f, encoding="utf-8")).get("detalle", []))
        print(f"reel-{a.reel:02d} · {len(est)} beats registrados de {n} montados\n")
        for k in sorted(est, key=int):
            e = est[k]
            marca = {"aprobado": "OK ", "recortar": "REC", "rechazado": "NO "}
            extra = ""
            if e.get("entra_en"):
                extra += f" entra {e['entra_en']}"
            if e.get("sale_en"):
                extra += f" sale {e['sale_en']}"
            print(f"  {marca.get(e['estado'], '?  ')} beat {k:>2}{extra}"
                  f"  {e.get('por_que', '')[:64]}")
            u = _texto_de(a.reel, int(k))
            if u and u.get("texto"):
                print(f"        «{u['texto'][:70]}»")
        if not est:
            print("  (todos pendientes)")
        sys.exit(0)

    estado = {"aprobar": "aprobado", "rechazar": "rechazado",
              "recortar": "recortar", "pendiente": "pendiente"}[a.cmd]
    extra = {}
    if a.cmd == "recortar":
        extra = {"entra_en": a.entra, "sale_en": a.sale}
        if not extra["entra_en"] and not extra["sale_en"]:
            raise SystemExit("recortar necesita --entra o --sale")
    # Al aprobar se congelan los tiempos: es lo que impide que se re-elija.
    if estado == "aprobado":
        u = _texto_de(a.reel, a.beat)
        if u:
            extra.update({"desde": u["start"], "hasta": u["end"],
                          "texto": u.get("texto", "")})
    r = marcar(a.reel, a.beat, estado, a.por_que, **extra)
    print(f"reel-{a.reel:02d} beat {a.beat} → {r['estado']}"
          + (f"  ({a.por_que})" if a.por_que else ""))
