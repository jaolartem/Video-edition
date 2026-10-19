"""Las dos puertas por las que entra trabajo a la línea.

Jaime, 7-9-2026, poniendo el modelo en una frase: *«el paso es automático, tú no
tocas nada, o no deberías tocar nada; el tiquet abierto abre una puerta y un
camino, y un video en bruto otra»*.

## Por qué hacía falta

El despachador ya existía y ya sabía repartir pedidos y recoger respuestas. Lo
que **no** hacía era enterarse de que había trabajo nuevo: recorría las piezas
que ya estaban en el camino y nada más. Así que un tiquet recién abierto se
quedaba quieto y un bruto nuevo en la carpeta de origen no despertaba a nadie —
y la única forma de que algo avanzara era que yo corriera `avanzar` a mano.

Eso es exactamente la avería que este proyecto persigue: **la decisión existe,
está escrita, y el paso siguiente no se entera.** Con la diferencia de que aquí
el paso siguiente no existía.

## Y no deciden nada

Las dos puertas **abren un camino, no lo recorren**. Miran si hay algo nuevo,
anotan la pieza en la fase que sabe atenderlo y se apartan. Quien decide sigue
siendo el paso al que llega.
"""
from __future__ import annotations

import os

from . import ticket
from .fase import anotar, antes_de
from .oficio import LA_FASE as DE_QUIEN

#: Lo que cuenta como un bruto. El resto de la carpeta de origen —proyectos,
#: audio suelto, capturas— no abre nada.
CINTAS = (".mp4", ".mov", ".mts", ".m4v")


def _fase_id(nombre):
    """El id de una fase por su nombre, o `None` si no existe."""
    from . import fase as _f

    con = _f._con()
    r = con.execute("select id from fase where nombre = ?", (nombre,)).fetchone()
    con.close()
    return r["id"] if r else None


def por_atender(pieza):
    """`(fase, ids)` de los abiertos que declaran paso y no han vuelto ya.

    **Una vuelta por ticket, no una por corrida.** Es el mismo tope que el
    repaso: devolver la pieza cada vez que el ticket sigue abierto es un bucle
    que parece trabajo. Aquí se manda una vez, se anota que se mandó, y si el
    ticket vuelve abierto lo que corresponde es pararla y decirlo — no volver a
    mandarla. Vivía en `ticket.py`; su único lector es esta puerta.

    **Y se atiende el que vuelve más atrás, no el primero de la lista** (C-410):
    reel-08, 12-9, tenía el #312 a «descrito» y el #314 a «revalidado»; se cogía
    el #312, la pieza no había llegado (C-407) y `vencidas` la retenía por el
    #314.
    """
    from .fase import camino

    abre = [t for t in ticket.abiertos(pieza)
            if (t.get("vuelve_a") or "") and not t.get("devuelto")]
    if not abre:
        return "", []
    ruta = [f["nombre"] for f in camino()]
    fase = min((t["vuelve_a"] for t in abre),
               key=lambda f: ruta.index(f) if f in ruta else len(ruta))
    return fase, [t["id"] for t in abre if t["vuelve_a"] == fase]


def del_tiquet_de(id_) -> None:
    """La puerta de la pieza de ese tiquet. **Reencaminar también es el evento.**

    Sólo se pasaba al abrir un tiquet: el #314 de reel-08 quedó reencaminado a
    «revalidado» y la pieza parada horas en «cosido» (12-9, C-411).
    """
    from .ticket import _con as _tc

    cx = _tc()
    r = cx.execute("select pieza from ticket where id = ?", (id_,)).fetchone()
    if r and r["pieza"]:
        for linea in del_tiquet([int(str(r["pieza"])[-2:])]):
            print(linea)


def _no_ha_llegado(n, vuelve) -> bool:
    """Cierto si la pieza está todavía antes de `vuelve` en el camino."""
    from .fase import camino
    from .pieza import Pieza

    ruta = [f["nombre"] for f in camino()]
    try:
        actual = (Pieza(int(n)).fase or {}).get("nombre")
    except Exception:                              # noqa: BLE001
        return False
    return (actual in ruta and vuelve in ruta
            and ruta.index(actual) < ruta.index(vuelve))


def _video_id(slug):
    from .ticket import _con as _tc

    cx = _tc()
    r = cx.execute("select id from video where slug = ?", (slug,)).fetchone()
    return r["id"] if r else None


def _aprobada(slug):
    """Si la version viva de esa pieza la aprobo **una persona**.

    Aprobar es lo unico que el motor no puede hacer solo, y por eso es tambien
    lo unico que puede cerrarle la puerta a la maquina.

    **Y se pregunta en un solo sitio.** Esto leia la tabla `aprobacion` —un
    veredicto por version— mientras `estado.json` publicaba el suyo contado por
    segmentos: dos respuestas a la misma pregunta, y nada que las mantuviera de
    acuerdo. Desde el 10-9-2026 la fuente es el marcador, que es lo que Jaime
    pidio: *«ahora la fuente de verdad es el Json, una sola fuente»*. La fila de
    `aprobacion` se queda como lo que de verdad es: **la firma** —quien, cuando
    y con que notas—, no la respuesta.
    """
    from . import segmento as _sg

    return _sg.aprobada(slug)

def del_tiquet(piezas):
    """**Un tiquet abierto manda su pieza al paso que sabe atenderlo.**

    `ticket.por_atender` ya contestaba a qué fase vuelve cada pieza y nadie se lo
    preguntaba salvo cuando alguien corría `avanzar` a mano. Aquí se le pregunta
    en cada vuelta.

    Y se manda **una vez por tiquet**, no una por vuelta: `devolver` lo anota, y
    `por_atender` deja de nombrarlo. Devolver la pieza mientras el tiquet siga
    abierto sería un bucle que parece trabajo — el mismo tope que ya se puso en
    el repaso.

    Devuelve las líneas que hay que decir en voz alta.
    """
    dicho = []
    for n in piezas:
        slug = f"reel-{int(n):02d}"
        fase, ids = por_atender(slug)
        if not fase or not ids:
            continue
        # **Lo aprobado no lo reabre una puerta.** Jaime, 7-9-2026, viendo que
        # reel-07 —firmada y subida a G:— habia vuelto a diseno: *«que hace r-07
        # ahi??»*. La habia mandado el #284, que lo levanto la maquina, no el.
        #
        # Aprobar es el unico paso que no tiene servicio porque no hay nada que
        # ejecutar: lo mueve una persona. Asi que una pieza aprobada vuelve
        # cuando el lo dice —con `avanzar --volver`, como hizo con reel-04— y no
        # porque una comprobacion interna encuentre algo. El tiquet no se cierra
        # ni se tira: se queda abierto y se dice, que es lo que hay que hacer
        # con algo que hay que mirar y no te toca decidir.
        if _aprobada(slug):
            dicho.append(f"  {slug}: APROBADA — {len(ids)} tiquet(s) de maquina"
                         f" piden «{fase}» y la puerta no la reabre."
                         f" Sube a Jaime: {', '.join('#' + str(i) for i in ids)}")
            continue
        # **Al punto desde el que ese paso vuelve a correr, no a su etiqueta.**
        # La etiqueta dice el paso YA HECHO; ver `fase.antes_de`.
        vuelve = antes_de(fase)
        # **Y la puerta sólo devuelve: no adelanta.** El 12-9 tres tiquets hacia
        # «revalidado» llevaron a reel-09, 10 y 11 de «depurado» a «recortado»,
        # y la redundancia —ya contestada— no se cargó nunca. Si la pieza aún no
        # ha llegado, el tiquet viaja en su pedido cuando llegue.
        if _no_ha_llegado(n, vuelve):
            continue
        destino, vid = _fase_id(vuelve), _video_id(slug)
        if destino is None or vid is None:
            dicho.append(f"  {slug}: {len(ids)} tiquet(s) piden «{fase}» y esa"
                         f" fase no existe en el camino — no se puede abrir")
            continue
        anotar(vid, destino,
               f"puerta del tiquet: {', '.join('#' + str(i) for i in ids)}")
        ticket.devolver(ids)
        dicho.append(f"  puerta del tiquet -> {slug} vuelve a «{vuelve}» para"
                     f" que corra «{fase}», por"
                     f" {', '.join('#' + str(i) for i in ids)}")
    return dicho


def _catalogadas():
    """Los nombres de cinta que la base ya conoce."""
    from .ticket import _con as _tc

    cx = _tc()
    return {r["nombre"] for r in cx.execute("select nombre from toma")}


def del_bruto(origen=None):
    """**Un vídeo nuevo en la carpeta de origen abre el camino de entrada.**

    Es la otra puerta, y hasta ahora no la miraba nadie: una cinta podía llevar
    horas en disco sin que la línea supiera que existía.

    **Señala, no cataloga.** Catalogar una cinta es caro —transcribirla son
    varias pasadas por tramo— y es una decisión: cuál de los brutos entra en qué
    pieza lo dice Jaime, no la fecha del fichero. Así que esto dice «hay una
    cinta que la base no conoce» y ahí se para, que es lo que un guarda tiene
    que hacer cuando lo que sigue exige entender.

    Y **no mira el tamaño ni la fecha**: mira si su nombre está en `toma`. Un
    fichero a medio copiar no engaña a esta comprobación porque tampoco está
    catalogado.
    """
    import rutas

    carpeta = origen or rutas.ORIGEN
    if not os.path.isdir(carpeta):
        return [f"  puerta del bruto: no existe la carpeta de origen"
                f" «{carpeta}»"]
    ya = _catalogadas()
    nuevas = sorted(
        f for f in os.listdir(carpeta)
        if f.lower().endswith(CINTAS) and os.path.splitext(f)[0] not in ya)
    if not nuevas:
        return []
    return [f"  puerta del bruto -> {len(nuevas)} cinta(s) que la base no"
            f" conoce: {', '.join(nuevas[:4])}"
            + (" …" if len(nuevas) > 4 else "")
            + f". Catalogar es decisión: `python scripts/catalogar.py`."]


def contestadas_tarde() -> list:
    """Respuestas escritas para un paso que la pieza ya dejo atras.

    Vivia en `avanzar.py` y se vino con la puerta, que es quien devuelve
    (C-579): el lanzador llego a 303 lineas.
    """
    import glob

    from .fase import camino, fase_de
    from .pieza import Pieza

    ruta = camino()
    orden = {f["nombre"]: k for k, f in enumerate(ruta)}
    fuera = []
    for f in sorted(glob.glob(os.path.join("work", "servicio", "*",
                                           "*.respuesta.json"))):
        paso = os.path.basename(os.path.dirname(f))
        slug = os.path.basename(f)[:-len(".respuesta.json")]
        fase = DE_QUIEN.get(paso)
        if not fase or fase not in orden:
            continue
        try:
            pieza = Pieza(int(slug[-2:]))
            actual = fase_de(pieza)
        except Exception:                          # noqa: BLE001
            continue
        if actual and orden.get(actual["nombre"], -1) > orden[fase]:
            fuera.append((paso, slug))
    return fuera


def devuelve_tarde(slug: str, paso: str) -> None:
    """Manda la pieza al punto desde el que ese paso se vuelve a correr.

    **Que no es su propia fase, y ahí estaba el fallo.** Una etiqueta dice el
    paso ya hecho: dejar la pieza en `descrito` es dejarla con la descripción
    por buena, así que lo siguiente que corre es `disenado` y la respuesta que
    la devolvió no la lee nadie. Medido el 8-9-2026: reel-03 y reel-05 entraron
    en `descrito` a las 19:45:56 y salieron a `disenado` **el mismo segundo**,
    con sus respuestas sin aplicar y sus tiquets abiertos.

    Se devuelve a la fase ANTERIOR, que es desde donde el paso vuelve a correr,
    y sale del camino declarado en vez de escribirse aquí: si mañana se mete un
    paso entre medias, esto sigue apuntando al sitio correcto.
    """
    fase = antes_de(DE_QUIEN.get(paso))
    # **Y una pieza aprobada no se devuelve.** Jaime, 7-9-2026, viendo el
    # tablero: *«por que esta el 4, el 6 y el 7... ya estan aprobados»*, y el
    # motivo: *«porque gastan tiempo valioso»*.
    #
    # Esto saco a reel-07 de `aprobado` a las 19:02 y dejo a reel-04 y reel-06
    # rebotando: llega una respuesta escrita para un paso que la pieza ya paso,
    # y el enrutador la manda atras. Para una pieza en vuelo eso es correcto —la
    # respuesta se pago y aplicarla tarde es mejor que tirarla—; para una
    # firmada es recomponer lo aprobado, y ademas en bucle, porque al volver a
    # avanzar la respuesta sigue ahi.
    #
    # El guarda de `puertas._aprobada` cubria la puerta del tiquet y no esto. Es
    # el mismo criterio en el otro camino: lo aprobado vuelve cuando Jaime lo
    # dice, no porque llegue una respuesta con retraso.
    try:
        if _aprobada(slug):
            _reg_aviso = __import__("registro")
            _reg_aviso.aviso(
                "avanzar", "respuesta tardia sobre una pieza aprobada",
                detalle=f"{slug}: llego «{paso}» y esta firmada; no se devuelve",
                eco=True)
            # **Y se archiva, no se deja en la cola** (C-491). Quedarse en el
            # buzón la dejaba viva para cuando Jaime reabriera la pieza: reel-13,
            # 14-9, volvió de «revisado» a «medido» por un visto del 13-9 que ya
            # no hablaba de nada. **Con su pedido**, que también es viejo: sin
            # respuesta, el pedido se contaba como trabajo abierto.
            __import__("servicio")._archivar(paso, slug, sufijo="tardia",
                                            solo_respuesta=False)
            return
    except Exception:                              # noqa: BLE001
        pass
    # **Y devolver no adelanta** (C-483), la misma regla que la puerta del
    # tiquet (`puertas._no_ha_llegado`). Si un tiquet mandó la pieza más atrás
    # que el paso de esta respuesta, llegará a él sola y la leerá entonces.
    # Moverla aquí la saltaba por encima del paso del tiquet, y el tiquet se
    # quedaba «ya devuelto» y sin atender: reel-16 #421 y reel-12 #449
    # (13-9), las dos paradas con «su paso ya quedo atras» y sin pedido.
    try:
        if _no_ha_llegado(int(slug[-2:]), fase):
            return
    except Exception:                              # noqa: BLE001
        pass
    a_donde, vid = _fase_id(fase), _video_id(slug)
    if a_donde is None or vid is None:
        return
    anotar(vid, a_donde,
           f"llego la respuesta de «{paso}» y la pieza ya habia pasado")
