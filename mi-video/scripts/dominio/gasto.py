"""Lo que costó de verdad cada agente, leído de su transcripción. Ni estimado ni declarado.

Jaime, 23-10-2026: *«quiero monitorización de cada vídeo, análisis de gasto…
necesitamos ver la eficiencia»*. `work/gasto.jsonl` apuntaba la cifra que el
agente devolvía al terminar —el tamaño de su contexto en ese momento— y no lo
que se pagó por el camino. Medido el 23-10 sobre W40: el describir de reel-18 que
se apuntó como 75 K hizo 118 llamadas, 101 de ellas por Bash, y leyó 25,8 M de
caché. Los 33 agentes del lote, que el fichero contaba en 4,75 M, fueron unos
126 M de entrada. **Contar mal es peor que no contar**: decide sobre un número
falso.

Cada llamada del modelo deja su `usage` en la transcripción, y eso vale igual
para los dos caminos que contestan un pedido:

- **interno**: un subagente de una sesión (`<proyecto>/<sesión>/subagents/*.jsonl`);
- **bash**: el CLI que lanza `Oficio.llama` (`<proyecto>/<sesión>.jsonl`).

Un agente se atribuye a su pieza y su paso por la ruta del pedido que se le
encargó (`servicio/<paso>/<pieza>.pedido.json`), y a sus tiquets por los `#N`
del encargo. Una transcripción que no nombra ningún pedido no es de la línea —es
una sesión de trabajo como ésta— y no se cuenta.
"""
from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass, field

#: Dónde guarda Claude Code las transcripciones de este usuario.
PROYECTOS = os.path.join(os.path.expanduser("~"), ".claude", "projects")
#: Los proyectos que pueden contestar pedidos: el repo, sus worktrees y la línea.
PATRONES = ("F--Edicion-de-video*", "F--linea*")
_PEDIDO = re.compile(r"servicio[\\/]+([a-z_]+)[\\/]+(reel-\d+)\.(?:pedido|prompt)")
_TIQUET = re.compile(r"#(\d{2,5})\b")

#: Cuánto pesa cada clase de token frente a uno de entrada sin caché: escribir
#: caché 1,25×, leerla 0,1×, la salida 5×. Es la proporción del precio de lista
#: de los modelos Claude; da un número comparable entre agentes sin depender de
#: la tarifa del día.
PESO = {"entrada": 1.0, "cache_escritura": 1.25, "cache_lectura": 0.1, "salida": 5.0}


@dataclass
class Agente:
    """Un agente que contestó (o intentó contestar) un pedido de la línea."""

    id: str
    origen: str
    pieza: str
    paso: str
    tiquets: list = field(default_factory=list)
    inicio: str = ""
    fin: str = ""
    modelo: str = ""
    llamadas: int = 0
    bash: int = 0
    entrada: int = 0
    cache_escritura: int = 0
    cache_lectura: int = 0
    salida: int = 0
    fichero: str = ""

    @property
    def equivalente(self) -> int:
        """Tokens de entrada equivalentes: lo que se compara entre agentes."""
        return int(sum(getattr(self, k) * p for k, p in PESO.items()))

    @classmethod
    def de(cls, ruta: str) -> "Agente | None":
        """El agente de esa transcripción, o `None` si no contestaba un pedido."""
        vistos, a = set(), None
        try:
            lineas = open(ruta, encoding="utf-8", errors="replace")
        except OSError:
            return None
        with lineas:
            for x in lineas:
                try:
                    d = json.loads(x)
                except ValueError:
                    continue
                m = d.get("message") if isinstance(d.get("message"), dict) else {}
                if a is None:
                    if d.get("type") != "user":
                        continue
                    texto = json.dumps(m.get("content"), ensure_ascii=False)
                    p = _PEDIDO.search(texto)
                    if not p:
                        return None
                    a = cls(id=os.path.splitext(os.path.basename(ruta))[0],
                            origen="interno" if "subagents" in ruta else "bash",
                            paso=p.group(1), pieza=p.group(2), fichero=ruta,
                            tiquets=sorted({int(t) for t in _TIQUET.findall(texto)}),
                            inicio=d.get("timestamp", ""))
                if d.get("timestamp"):
                    a.fin = d["timestamp"]
                u, mid = m.get("usage"), m.get("id")
                if not u or not mid or mid in vistos:
                    continue
                # Una respuesta llega en varias líneas con el mismo `id` y el
                # mismo `usage`: se cuenta una vez, o se paga tres veces en el papel.
                vistos.add(mid)
                a.modelo = m.get("model") or a.modelo
                a.llamadas += 1
                a.entrada += u.get("input_tokens") or 0
                a.cache_escritura += u.get("cache_creation_input_tokens") or 0
                a.cache_lectura += u.get("cache_read_input_tokens") or 0
                a.salida += u.get("output_tokens") or 0
                a.bash += sum(1 for c in (m.get("content") or [])
                              if isinstance(c, dict) and c.get("type") == "tool_use"
                              and c.get("name") == "Bash")
        return a


def transcripciones(desde: float = 0.0):
    """Las transcripciones que pueden ser de un agente de la línea."""
    for patron in PATRONES:
        for raiz in glob.glob(os.path.join(PROYECTOS, patron)):
            for ruta in glob.glob(os.path.join(raiz, "*.jsonl")) + glob.glob(
                    os.path.join(raiz, "*", "subagents", "*.jsonl")):
                if os.path.getmtime(ruta) >= desde:
                    yield ruta


ESQUEMA = """create table if not exists gasto (
    id text primary key, origen text not null, pieza text not null,
    paso text not null, tiquets text, inicio text, fin text, modelo text,
    llamadas integer, bash integer, entrada integer, cache_escritura integer,
    cache_lectura integer, salida integer, equivalente integer, fichero text)"""


def recoger(cx, desde: float = 0.0) -> int:
    """Lee las transcripciones y guarda (o rehace) una fila por agente. Las que hay."""
    cx.execute(ESQUEMA)
    n = 0
    for ruta in transcripciones(desde):
        a = Agente.de(ruta)
        if a is None:
            continue
        cx.execute(
            "insert or replace into gasto values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (a.id, a.origen, a.pieza, a.paso, json.dumps(a.tiquets), a.inicio, a.fin,
             a.modelo, a.llamadas, a.bash, a.entrada, a.cache_escritura,
             a.cache_lectura, a.salida, a.equivalente, a.fichero))
        n += 1
    cx.commit()
    return n
