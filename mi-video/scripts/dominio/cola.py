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
    " cambia sólo lo que no cumple. Todo se lee con Read, nunca troceado con"
    " Bash (C-662); Bash solo para `python scripts/consulta.py <verbo>` ante una"
    " duda concreta. No abras otros ficheros ni busques. Por pedido: leerlo, sus hojas de contacto (`hoja`) y"
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


def gasto(*_declarado) -> int:
    """Recoge de las transcripciones lo que gastaron de verdad los agentes (C-657).

    Antes apuntaba en `work/gasto.jsonl` la cifra que el agente devolvía al
    terminar, y la sumaba contra un tope de 30 min y 300 K por pieza. Las dos
    cosas fallaban: la cifra subestimaba unas 25× —un describir de reel-18
    apuntado en 75 K leyó 25,8 M de caché— y el tope no paraba nada. Jaime,
    23-10-2026: *«no quiero topes duros, quiero que las cosas se hagan bien,
    pero sí quiero monitorización»*. Lo que se le pase se ignora; se mide.
    Devuelve cuántos agentes quedaron en la tabla `gasto`.
    """
    import basedatos
    from dominio import gasto as _g

    return _g.recoger(basedatos.abrir(basedatos.BASE))


if __name__ == "__main__":
    if "--gasto" in sys.argv or "--parte" in sys.argv:
        # El parte es `monitor.py`: tiempo, vueltas, tiquets y agentes por pieza.
        print(f"cola: {gasto()} agentes recogidos; el parte: python scripts/monitor.py")
        raise SystemExit(0)
    args = [a for a in sys.argv[1:] if a != "--lote"]
    if "--lote" in sys.argv:
        for clave, encargo in lote(args).items():
            print(f"=== {clave}\n{encargo}\n")
    else:
        for linea in cola(args):
            print(linea)
