"""Como viaja un pedido: el mismo JSON, con renglones donde ayudan. C-550.

Lo usa `servicio.pedir`, que es el unico que escribe pedidos. Vive aparte
porque `servicio.py` ya estaba en el techo, y porque la forma del pedido es una
regla propia: cuanto cuesta leerlo.
"""
import hashlib
import json

#: Lo que cabe en una linea va en una linea. C-550.
ANCHO = 160


def _volcar(x, nivel=0):
    """El pedido en JSON, **con renglones donde ayudan y no donde sobran**.

    Con `indent=1` cada numero de una lista ocupaba su linea: el pedido de
    revalidar eran 4.222 lineas y quien contesta lo leia en tres o cuatro
    tandas, un turno entero de agente por tanda. Lo que cabe en `ANCHO`
    caracteres va junto; lo demas se abre. Es el mismo JSON (C-550).
    """
    plano = json.dumps(x, ensure_ascii=False)
    if len(plano) <= ANCHO or not isinstance(x, (dict, list)) or not x:
        return plano
    pad, dentro = " " * nivel, " " * (nivel + 1)
    if isinstance(x, dict):
        filas = [f"{dentro}{json.dumps(k, ensure_ascii=False)}: "
                 f"{_volcar(v, nivel + 1)}" for k, v in x.items()]
        return "{\n" + ",\n".join(filas) + f"\n{pad}}}"
    filas = [f"{dentro}{_volcar(v, nivel + 1)}" for v in x]
    return "[\n" + ",\n".join(filas) + f"\n{pad}]"


def _en_renglones(ins):
    """Cada instruccion de Jaime en una linea: `#id [paso] (xN) lo que dijo`.

    Viajaban como fichas de nueve campos —1.300 lineas en cada pedido— cuando
    lo que se obedece es lo que dijo. Se queda entero; se van la fecha, el
    ambito, el estado y la nota de como se atendio, que es historia (C-550).
    """
    if not isinstance(ins, list):
        return ins
    return [f"#{i.get('id')}" + (f" [{i['paso']}]" if i.get("paso") else "")
            + (f" (x{i['veces']})" if (i.get("veces") or 1) > 1 else "")
            + f" {i.get('dijo', '')}" if isinstance(i, dict) else i
            for i in ins]


def _referencia(slug, prompt):
    """Donde esta el contrato, con su huella: el texto va en `.prompt.md`.

    Dentro del JSON era una sola linea de 23 a 59 KB que la lectura cortaba a
    mitad (C-445); quien contesta la lee del fichero. La huella hace que un
    contrato nuevo siga siendo una pregunta nueva (C-550).
    """
    sha = hashlib.sha256(str(prompt).encode("utf-8")).hexdigest()[:12]
    return f"en {slug}.prompt.md, junto a este pedido (sha {sha})"
