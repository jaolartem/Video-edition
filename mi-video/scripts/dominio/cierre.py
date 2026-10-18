"""**El cierre de un tiquet por la medida que el propio tiquet declara.**

Un tiquet de tipo `suena` declara `cierra_con = bordes`: la única medida que
puede cerrarlo sola es mirar el empalme del que habla. Y hasta ahora **no había
quien lo midiera**, así que un `suena` no lo podía cerrar nadie: su paso es
`cosido`, que es código, y un paso de código no declara qué tiquets atiende —eso
sólo lo hace un oficio en su respuesta—. La pieza volvía a coser, avanzaba, y la
corrección seguía abierta con su paso ya detrás: `vencidas` la paraba para
siempre.

Medido el 8-9-2026: el #282 y el #287 de reel-01 —«el semanales se escucha
aislado»— pasaron por ahí tres veces, y las tres la pieza salió con el defecto
dentro y el tiquet abierto o cerrado en falso.

## Qué se mide, y por qué basta

El defecto que nombra un `suena` es un empalme donde no debería haberlo: el corte
parte una frase y deja la palabra entre dos silencios. Así que la pregunta es
aritmética sobre el plan —**¿queda un empalme en ese segundo?**— y no hace falta
volver a decodificar el audio: el plan dice dónde empieza cada escena en el
montaje, y una frontera entre dos escenas es exactamente un empalme.

Si en el segundo que el tiquet señala ya no hay frontera, el corte que lo causaba
no existe. Eso es lo que cierra, y nada más: si sigue habiendo empalme ahí, el
tiquet se queda abierto, que es el lado seguro.
"""
from __future__ import annotations

import json
import os

#: Cuánto se admite de desajuste entre el segundo que él dijo y la frontera
#: medida. Él mira el vídeo y dice «del 83 al 85»; el empalme está en un punto.
HOLGURA = 0.6


def _al_dia(slug: str) -> None:
    """Rehace el plan si está caducado, porque medir sobre el viejo no vale.

    El plan se rehace al montar, y con un tiquet abierto la pieza no llega ahí:
    `vencidas` la para antes. O sea que la evidencia que cierra el tiquet vivía
    detrás del propio tiquet. Quien dice si está al día es `cadena`, que es su
    dueño, y rehacerlo cuesta un `plan-reel.mjs` — ni render ni corte.
    """
    import subprocess
    import sys

    raiz = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(raiz, "scripts"))
    try:
        import cadena

        if not cadena.hay_que("plan", int(slug[-2:]))[0]:
            return
    except Exception:                              # noqa: BLE001
        return
    subprocess.run(["node", "scripts/plan-reel.mjs", "--reel", str(int(slug[-2:]))],
                   cwd=raiz, capture_output=True, check=False, timeout=600)


def empalmes(slug: str) -> list:
    """Los segundos del montaje donde una escena da paso a la siguiente."""
    _al_dia(slug)
    ruta = os.path.join("work", "scenes", slug, "plan-full.json")
    try:
        escenas = json.load(open(ruta, encoding="utf-8"))["escenas"]
    except (OSError, ValueError, KeyError):
        return []
    return [round(float(e["montado_desde"]), 3) for e in escenas[1:]
            if e.get("montado_desde") is not None]


def hay_empalme(slug: str, segundo, holgura: float = HOLGURA) -> bool:
    """¿Queda una frontera de escena en ese segundo del montaje?"""
    if segundo is None:
        return True
    return any(abs(x - float(segundo)) <= holgura for x in empalmes(slug))


def cierra_los_suyos(slug: str, fase: str = "cosido") -> list:
    """Cierra los tiquets de esa fase cuyo empalme ya no existe. Los cerrados.

    No cierra el que no puede medir —sin segundo no hay dónde mirar— ni el que
    todavía tiene su empalme: los dos se quedan abiertos, dicho y sin arreglar,
    que es lo que hay que hacer con algo que sigue estando.
    """
    from . import ticket as _t

    cerrados = []
    for t in _t.abiertos(slug):
        if (t.get("vuelve_a") or "") != fase or t.get("segundo") is None:
            continue
        if hay_empalme(slug, t["segundo"]):
            continue
        try:
            _t.contestar(
                int(t["id"]),
                f"medido sobre el plan de hoy: en el segundo {t['segundo']} ya"
                f" no hay empalme, asi que el corte que partia la frase no"
                f" existe. Cerrado por la medida que el tiquet declara.",
                "arreglado", "la linea", "bordes")
            cerrados.append(int(t["id"]))
        except Exception as e:                     # noqa: BLE001
            print(f"  el tiquet #{t['id']} no se pudo cerrar:"
                  f" {type(e).__name__}: {e}", flush=True)
    return cerrados


#: La marca de los tiquets que abre la puerta por un corte sobre la voz. La
#: escribe `servicios/verificar.py :: SOBRE_LA_VOZ`; aqui se cierran.
SOBRE_LA_VOZ = "corte sobre la voz:"


def cierra_cortes_limpios(slug: str) -> list:
    """Cierra los «corte sobre la voz» cuyo borde ya calla. Los cerrados.

    **El empalme no sirve aqui** (C-560): un corte arreglado sigue siendo una
    frontera de escena, asi que `hay_empalme` lo daria por abierto siempre, y
    el tiquet trababa la pieza con `vencidas` en cuanto pasaba su paso —reel-22,
    #632, 18-10—. Lo que el tiquet nombra es un borde en la cinta; se mira si
    ese borde, o el que lo sustituye a menos de medio segundo, ya no suena.
    """
    import re

    from . import ticket as _t
    from .bordes import VOZ
    from .senal import Senal

    try:
        edl = json.load(open(os.path.join("ads", slug, "edl-sell.json"),
                             encoding="utf-8"))
    except (OSError, ValueError):
        return []
    fines = [(b, d.get("toma")) for (_a, b, *_r), d
             in zip(edl.get("segmentos", []), edl.get("detalle", []))]
    cerrados = []
    for t in _t.abiertos(slug):
        dijo = t.get("dijo") or ""
        m = re.search(r"corte de ([\d.]+)s", dijo)
        if not dijo.startswith(SOBRE_LA_VOZ) or not m:
            continue
        seg = float(m.group(1))
        cerca = [(abs(b - seg), b, toma) for b, toma in fines if abs(b - seg) <= 0.5]
        if cerca:
            _d, b, toma = min(cerca)
            try:
                if not toma or Senal(toma).suena(b) > VOZ:
                    continue
            except Exception:                      # noqa: BLE001
                continue
            como = f"el borde esta ahora en {b:.3f} y alli ya no suena la voz"
        else:
            como = "ese corte ya no existe en el montaje"
        try:
            _t.contestar(int(t["id"]), f"medido sobre el EDL de hoy: {como}.",
                         "arreglado", "la linea", "bordes")
            cerrados.append(int(t["id"]))
        except Exception as e:                     # noqa: BLE001
            print(f"  el tiquet #{t['id']} no se pudo cerrar: {e}", flush=True)
    return cerrados
