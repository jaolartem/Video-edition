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


def cierra_los_fijados(slug: str) -> list:
    """Cierra los tiquets de `fijado` cuyos tramos declarados ya están en el corte.

    `fijar.py --aplicar` es código: mete en el EDL lo que se declaró, y no
    declara qué tiquets atiende (C-631). reel-18, 20-10: «reponer el cierre
    decidido… ya declarado con fijar, falta que entre en el corte» (#848) entró
    en el corte y siguió abierto, y `vencidas` paró la pieza en `afinado` en cada
    vuelta. Se mide lo que el tiquet pide: que cada tramo declarado de su etapa
    esté en el EDL. Sin declaración, o con un tramo que falte, se queda abierto.
    """
    import fijar

    from . import ticket as _t

    try:
        edl = json.load(open(os.path.join("ads", slug, "edl-sell.json"),
                             encoding="utf-8"))
    except (OSError, ValueError):
        return []
    en_corte = {(d.get("beat"), round(s[0], 2), round(s[1], 2))
                for s, d in zip(edl.get("segmentos", []), edl.get("detalle", []))}
    cerrados = []
    for t in _t.abiertos(slug):
        if (t.get("vuelve_a") or "") != "fijado" or t.get("beat") is None:
            continue
        suyos = [(f["beat"], round(f["desde"], 2), round(f["hasta"], 2))
                 for f in fijar.fijados(slug) if f["beat"] == int(t["beat"])]
        if not suyos or not set(suyos) <= en_corte:
            continue
        _t.contestar(int(t["id"]), f"medido: los {len(suyos)} tramo(s) declarados"
                     f" de e{t['beat']} están en el corte", "arreglado", "la linea",
                     t.get("cierra_con") or "")
        cerrados.append(int(t["id"]))
    return cerrados


#: `mi-video/`, para leer el spec que el render consumio.
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cierra_por_su_medida(slug: str) -> list:
    """Los que la linea cierra midiendo, cada uno con la suya. Los cerrados (C-611).

    Bordes por el empalme, cortes limpios, lo fijado y el texto. El de texto va
    el ultimo: si revienta, los demas ya quedaron cerrados.
    """
    return (cierra_los_suyos(slug) + cierra_cortes_limpios(slug)
            + cierra_los_fijados(slug) + cierra_por_texto(slug))


def cierra_por_texto(pieza: str) -> list:
    """Cierra los tiquets cuyo problema **ya no esta en la pieza**. Los cerrados.

    **Y vive aqui, con las otras medidas, y vuelve a correr** (C-611). Estaba en
    `ticket.py` como `cerrar_los_resueltos` y su unico llamador era la patrulla
    del despachador: al retirarla el 7-9 nadie la volvio a enganchar, y lo que
    `revisar` abre con `cierra_con = texto` no se cerraba nunca.

    **Por que existe.** Jaime, mirando el render: *«tampoco las correcciones ni
    los tickets»*. Y la pieza decia otra cosa: de las cinco cosas que habia
    senalado, cuatro ya no estaban — «eso, eso», la repeticion de «la mayoria de
    los emprendedores», la cola rota de la etapa 3—. Estaban arregladas y sus
    tickets seguian abiertos, asi que **la lista decia que no se habia hecho
    nada**.

    Un ticket que no se cierra solo obliga a alguien a repasar la pieza para
    saber si sigue vigente, y eso es justo lo que la lista tenia que ahorrar.

    Se cierra por lo que se puede medir: **el texto que el ticket cita entre
    comillas ya no esta en la pieza**. Lo que no cita nada se queda abierto —
    «el panel es figurativo», «el hook mas movido» no se comprueban contando, y
    cerrarlos por silencio seria peor que dejarlos.

    **Y «en la pieza» son las dos fuentes, no solo la voz.** Esto comparaba
    contra `Montaje.texto()`, que es lo HABLADO. El copy de los tableros no esta
    ahi —sale de `tarjeta`/`placa`, y lo que el render consumio esta en
    `src/reels.json`—, asi que un ticket como «el tablero dice «MISMA
    FACTURACION» y la voz ya no lo dice» daba todas las citas ausentes y se
    cerraba en la primera vuelta del despachador sin haber mirado el tablero. Se
    mira lo hablado **y** lo rotulado, que es donde puede estar lo que cito.
    """
    import re

    from .ticket import RECIBO, abiertos, contestar

    # **Sin lo hablado no se mide** (C-611): con el montaje ilegible, toda cita
    # que no estuviera en un tablero salia «ausente» y su tiquet se cerraba.
    hablado = _hablado(pieza)
    if not hablado.strip():
        return []
    dice = hablado + " " + _rotulado(pieza)
    cerrados = []
    for t in abiertos(pieza):
        citas = [c.strip() for c in re.findall(r"«([^»]{6,})»", t.get("dijo") or "")]
        # Se exige que TODAS las citas hayan desaparecido: un ticket que cita dos
        # cosas y solo pierde una sigue teniendo razon en la otra.
        # **Y solo los que se cierran con esta medida** (C-611): con otra,
        # `contestar` revienta (`CierreAjeno`); con un oficio, lo cierra el.
        if (t.get("cierra_con") != "texto" or (t.get("vuelve_a") or "") in RECIBO
                or not citas or any(c.lower() in dice for c in citas)):
            continue
        contestar(t["id"],
                  "cerrado midiendo: lo que citaba ya no esta en la pieza, ni"
                  " hablado ni rotulado ("
                  + "; ".join(f"«{c[:40]}»" for c in citas[:2]) + ")",
                  estado="arreglado", quien="la linea", medida="texto")
        cerrados.append(t["id"])
    return cerrados


def _hablado(pieza: str) -> str:
    """Todo lo que se oye en el montaje de hoy, en minusculas."""
    from .montaje import Montaje

    try:
        m = Montaje(pieza)
        return " ".join((m.texto(tr) or "") for tr, _ in m.tramos()).lower()
    # `SystemExit` tambien: sin transcript, `Montaje` sale asi, y desde la linea
    # se llevaba la vuelta entera del disparador (C-611).
    except (Exception, SystemExit):                # noqa: BLE001
        return ""


def _rotulado(pieza: str) -> str:
    """Todo lo que se lee en pantalla, **del spec que el render consumio**.

    De `src/reels.json` y no de la base: la base es lo que se pidio, el spec es
    lo que se dibujo. Es la misma distincion que ya hace `servicios/visto.py`.
    """
    try:
        n = int(str(pieza).split("-")[1])
        spec = json.load(open(os.path.join(_RAIZ, "src", "reels.json"),
                              encoding="utf-8"))
    except (OSError, ValueError, IndexError):
        return ""
    r = next((x for x in spec if x.get("id") == f"Reel-R{n}"), None)
    if not r:
        return ""
    fuera = []

    def _hojas(x):
        if isinstance(x, str):
            fuera.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                _hojas(v)
        elif isinstance(x, list):
            for v in x:
                _hojas(v)

    for cual in ("boards", "tarjetas", "paneles", "lineas", "cta"):
        _hojas(r.get(cual))
    return " ".join(fuera).lower()
