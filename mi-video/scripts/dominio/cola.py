"""**La cola de la sesión: quién espera y con qué encargo.** C-552, C-564.

Con `arrancar.sh --agentes` los oficios no los llama el CLI: los contesta la
sesión con sus propios agentes. Esto le dice qué hay pendiente y le da el
encargo ya escrito, para no componerlo a mano.

    python scripts/dominio/cola.py 18 19 20 21 22          # uno por pedido
    python scripts/dominio/cola.py --lote 18 19 20 21 22   # uno por buzón

**El lote es la forma normal** (C-564): un agente por buzón y ronda lee el
contrato y los comunes una vez para todas las piezas. Por pedido, las cinco
piezas eran cinco lecturas del mismo contrato y del mismo taller.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from dominio.oficio import DE, Oficio  # noqa: E402

#: El encargo de una ronda entera de un buzón.
LOTE = (
    "Tu turno, en lote: {n} pedido(s) del paso «{buzon}», todos con el mismo"
    " contrato. Lee UNA vez el contrato {contrato} y los ficheros de `_comun`"
    " que nombren los pedidos; después, por cada pedido, lee el pedido y"
    " escribe su respuesta, uno detrás de otro:\n{lista}\n"
    "Es una REVISION de lo que el código ya hizo, no una composición desde"
    " cero: si lo hecho cumple, contesta lo mínimo que el contrato admite y"
    " cambia sólo lo que no cumple. No abras otros ficheros, no busques, no"
    " ejecutes nada. Tope por pedido: leerlo, sus hojas de contacto (`hoja`) y"
    " como mucho dos fotogramas sueltos de la escena que te haga dudar, y una"
    " escritura; el contrato y los comunes, una vez. Si no basta, dilo en esa"
    " respuesta y sigue con la siguiente."
)


def _pendientes(piezas):
    import servicio

    quiere = {f"reel-{int(n):02d}" for n in (piezas or [])}
    for buzon, slug, ruta in servicio.pendientes():
        if DE.get(buzon) and (not quiere or slug in quiere):
            yield slug, Oficio(DE[buzon], buzon, ruta)


def cola(piezas=None):
    """Una línea por pedido: `oficio<TAB>buzon<TAB>pieza<TAB>encargo`."""
    for slug, o in _pendientes(piezas):
        yield f"{o.nombre}\t{o.buzon}\t{slug}\t{o.encargo(sesion=True)}"


def lote(piezas=None) -> dict:
    """`{"oficio<TAB>buzon": encargo}`: una ronda por buzón, para un agente."""
    por_buzon: dict = {}
    for _slug, o in _pendientes(piezas):
        por_buzon.setdefault(o.buzon, []).append(o)
    out = {}
    for buzon, ofs in por_buzon.items():
        lista = "\n".join(f"  - pedido {os.path.abspath(o.pedido)} -> respuesta"
                          f" {os.path.abspath(o.respuesta)}" for o in ofs)
        contrato = os.path.abspath(ofs[0].pedido).replace(".pedido.json", ".prompt.md")
        out[f"{ofs[0].nombre}\t{buzon}"] = LOTE.format(
            n=len(ofs), buzon=buzon, contrato=contrato, lista=lista)
    return out


#: El tope de una pieza, de punta a punta. Jaime, 18-10-2026: *«no puedes
#: demorarte mas de 30 minutos por video en todo el proceso»*, y el millon de
#: tokens de ese dia: *«es claro que no ha habido control»* (C-565).
TOPE_MIN, TOPE_TOKENS = 30, 300_000
PRESUPUESTO = os.path.join("work", "presupuesto.json")
#: **Cada agente, un apunte, y no se borra** (C-637). Jaime, 20-10-2026: *«cuando
#: puse un máximo de tiempo no era para que pararan, era para que se llevara el
#: registro y se entendiera qué causó la demora; necesitamos optimizar
#: procesos»*. El presupuesto sólo tenía un total por pieza y `arranca` lo ponía
#: a cero en cada reinicio de la línea: el día se perdía al meter una pieza.
APUNTES = os.path.join("work", "gasto.jsonl")


def _cuentas() -> dict:
    import json
    try:
        return json.load(open(PRESUPUESTO, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def arranca(piezas) -> None:
    """Abre la cuenta de las piezas que no la tenían. Lo llama `arrancar.sh`.

    **No pone a cero las que ya corren** (C-637): reiniciar la línea no es
    empezar la pieza, y ponerla a cero borraba lo que explica su demora.
    """
    import datetime
    import json
    c = _cuentas()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    for n in piezas:
        c.setdefault(f"reel-{int(n):02d}", {"desde": ahora, "tokens": 0, "agentes": 0})
    os.makedirs(os.path.dirname(PRESUPUESTO), exist_ok=True)
    json.dump(c, open(PRESUPUESTO, "w", encoding="utf-8"), indent=1)


def gasto(slug: str, tokens: int, paso: str = "", motivo: str = "") -> dict:
    """Suma lo que gasto un agente en esa pieza, lo apunta y dice si se paso del tope.

    `paso` es el oficio (disenar, describir, visto…) y `motivo` lo que lo
    disparó: un tiquet, un render nuevo, un arreglo de la máquina. Sin eso el
    total no dice qué causó la demora.
    """
    import datetime
    import json
    with open(APUNTES, "a", encoding="utf-8") as f:
        f.write(json.dumps({"cuando": datetime.datetime.now().isoformat(timespec="seconds"),
                            "pieza": slug, "paso": paso, "tokens": int(tokens),
                            "motivo": motivo}, ensure_ascii=False) + "\n")
    c = _cuentas()
    p = c.setdefault(slug, {"desde": None, "tokens": 0, "agentes": 0})
    p["tokens"] += int(tokens)
    p["agentes"] += 1
    json.dump(c, open(PRESUPUESTO, "w", encoding="utf-8"), indent=1)
    return parte().get(slug, {})


def por_paso(desde: str = "") -> dict:
    """`{(pieza, paso): [tokens, agentes]}` de los apuntes desde esa fecha."""
    import json
    out: dict = {}
    try:
        filas = [json.loads(x) for x in open(APUNTES, encoding="utf-8") if x.strip()]
    except OSError:
        return out
    for a in filas:
        if a["cuando"] >= desde:
            t = out.setdefault((a["pieza"], a.get("paso") or "?"), [0, 0])
            t[0] += a["tokens"]
            t[1] += 1
    return out


def parte() -> dict:
    """Minutos y tokens por pieza, y si va pasada (`pasada`)."""
    import datetime
    out = {}
    for slug, p in _cuentas().items():
        mins = None
        if p.get("desde"):
            mins = round((datetime.datetime.now() - datetime.datetime.fromisoformat(
                p["desde"])).total_seconds() / 60, 1)
        out[slug] = {**p, "minutos": mins,
                     "pasada": (mins or 0) > TOPE_MIN or p["tokens"] > TOPE_TOKENS}
    return out


if __name__ == "__main__":
    if "--arranca" in sys.argv:
        arranca([a for a in sys.argv[1:] if a != "--arranca"])
        raise SystemExit(0)
    if "--gasto" in sys.argv:
        i = sys.argv.index("--gasto")
        resto = sys.argv[i + 3:] + ["", ""]
        print(gasto(sys.argv[i + 1], int(sys.argv[i + 2]), resto[0], resto[1]))
        raise SystemExit(0)
    if "--parte" in sys.argv:
        for slug, p in sorted(parte().items()):
            print(f"{slug}: {p['minutos']} min, {p['tokens']} tokens, {p['agentes']}"
                  f" agente(s){'  ** PASADA **' if p['pasada'] else ''}")
        # Y en qué se fue, por paso (C-637).
        for (pieza, paso), (tk, n) in sorted(por_paso().items()):
            print(f"  {pieza} · {paso}: {tk} tokens en {n} agente(s)")
        raise SystemExit(0)
    args = [a for a in sys.argv[1:] if a != "--lote"]
    if "--lote" in sys.argv:
        for clave, encargo in lote(args).items():
            print(f"=== {clave}\n{encargo}\n")
    else:
        for linea in cola(args):
            print(linea)
