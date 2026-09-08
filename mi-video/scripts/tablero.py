"""Dónde va cada pieza, de un vistazo. Lee los estados, no la base.

Jaime, 7-9-2026: *«también vale la pena un registro de estado, con eso vamos
viendo en qué parte del proceso va»*.

## Por qué no es `donde.py`

`donde.py` es el parte completo —versión, corte, aprobación, audio, publicación,
lo que queda pendiente— y lo reconstruye de la base y de git. Cuesta lo que
cuesta y contesta a *«¿qué pasa con esta pieza?»*.

Esto contesta a otra cosa: *«¿por dónde va?»*. Son los siete `estado.json` y
nada más — sin base, sin git, sin ffmpeg. Se puede mirar cada minuto sin que
cueste, y ésa es la diferencia: un parte que se consulta una vez al día no sirve
para ver moverse la línea.

    python scripts/tablero.py            # las siete
    python scripts/tablero.py 3 5        # sólo esas
    python scripts/tablero.py --log 3    # el recorrido de una
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dominio import estado  # noqa: E402

#: El camino, en corto, para dibujar por dónde va sin escribir las 24.
HITOS = ["catalogado", "elegido", "cortado", "descrito", "disenado",
         "montado", "visto", "aprobado", "publicado"]


def _barra(etapa):
    """Una barra de nueve hitos con la pieza puesta donde está."""
    if not etapa:
        return "·" * len(HITOS)
    try:
        i = HITOS.index(etapa)
    except ValueError:
        # Una etapa intermedia: se coloca en el hito anterior que sí está.
        i = -1
        from dominio.fase import CICLO

        orden = [f for _, f, _ in CICLO]
        if etapa in orden:
            hasta = orden.index(etapa)
            for k, h in enumerate(HITOS):
                if h in orden and orden.index(h) <= hasta:
                    i = k
    return "#" * (i + 1) + "·" * (len(HITOS) - i - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*")
    ap.add_argument("--log", metavar="N", help="el recorrido de esa pieza")
    a = ap.parse_args()

    if a.log:
        d = estado.lee(f"reel-{int(a.log):02d}")
        print(f"reel-{int(a.log):02d} — {d.get('etapa') or 'sin etapa'}")
        for l in d.get("log", []):
            print(f"  {l.get('cuando','')}  {str(l.get('etapa') or ''):<14}"
                  f" {l.get('que','')}")
        return

    piezas = [f"reel-{int(r):02d}" for r in a.reels] or \
             [f"reel-{n:02d}" for n in range(1, 8)]
    print(f"{'pieza':<9} {'':<9}  {'etapa':<16} espera / abiertos")
    for s in piezas:
        d = estado.lee(s)
        etapa = d.get("etapa") or "?"
        esp = d.get("espera") or {}
        abiertos = d.get("abiertos") or []
        cola = ""
        if esp:
            cola = f"espera a «{esp.get('quien')}»"
        elif abiertos:
            # **Se dice cuantos y a donde van, no sus textos.** Un tablero que
            # imprime el tiquet entero deja de ser un tablero.
            donde = sorted({t.get("va_a") or "?" for t in abiertos})
            cola = (f"{len(abiertos)} tiquet(s) -> {', '.join(donde)}"
                    f"  [{', '.join('#' + str(t['id']) for t in abiertos)}]")
        print(f"{s:<9} {_barra(d.get('etapa')):<9}  {etapa:<16} {cola}")
    print("\n" + "  ".join(f"{k+1}.{h}" for k, h in enumerate(HITOS)))


if __name__ == "__main__":
    main()
