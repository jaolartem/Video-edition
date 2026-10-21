"""La versión de una pieza: **un corte concreto**, no un render concreto.

**Por qué es un sustantivo del dominio y no una función de `modelo.py`.** Lo dice
el propio ciclo que Jaime describe: *«de cada versión aprobada me das el audio
virgen»*. Si «la versión aprobada» no se puede nombrar, ese ciclo no se puede
ejecutar dos veces igual — y hasta hace poco no se podía: no existía la tabla, y
cuál WAV correspondía a qué corte era cosa de mirar fechas.

Vivía dentro de `modelo.py`, que es la herramienta que **migra** el esquema. Una
cosa es cambiar la forma de las tablas y otra es lo que significa una fila: dos
responsabilidades del tamaño y de la vida de cada una muy distintos.

## Lo único que hay que entender de aquí: la huella es del CORTE

Se calcula sobre los tramos y sus tomas, **no sobre el fichero**. Dos renders del
mismo montaje son la misma versión aunque el JSON se haya reescrito; un corte
distinto es otra versión aunque el fichero pese lo mismo. Es la misma lección que
la caducidad por contenido: comparar lo que significa, no lo que ocupa.

Por eso `registrar_version` es idempotente y un registro por fecha no lo sería:
renderizar dos veces lo mismo no crea dos versiones.

**Y son funciones, no una clase, a propósito.** La regla del proyecto es que un
dato del dominio no viaje desnudo —lista, `dict` o tupla—, y aquí no viaja nada:
lo que sale es la huella (una cadena que la base guarda tal cual) y el `id` de la
fila. Envolverlos en un objeto que nadie desempaqueta sería ceremonia. El día que
alguien necesite pasear una versión entera, la clase se declara aquí.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sqlite3
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402


def _con():
    c = basedatos.abrir()
    c.row_factory = sqlite3.Row
    return c


def _edl(slug):
    """El corte de una pieza, o `None` si todavía no lo hay."""
    p = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def huella_de(e):
    """La huella de un corte **que ya se tiene en la mano**.

    Existe porque la misma cuenta hacia falta sobre el corte VIVO —el fichero—
    y sobre un corte GUARDADO —la columna `version.edl`—, y la segunda se
    estaba haciendo aparte: `sellar.py` calculaba `sha1(edl + sha_del_mp4)` y
    lo guardaba en la misma columna `huella` que esta funcion llena con la del
    corte.

    **Dos escritores, una columna, dos significados.** El esquema dice, en un
    comentario encima de la columna, *«la huella es del CORTE, no del
    fichero»*, y lo que habia dentro era de la entrega: medido sobre las 95
    versiones de la base, **ninguna** coincidia con la huella de su corte. Con
    eso `donde.py` decia «CAMBIO» en las siete piezas **siempre**, hubiera
    cambiado el corte o no — un aviso que no puede ser nunca negativo no avisa
    de nada, y era el unico sitio donde mirar si lo que Jaime firmo seguia en
    pie.

    Lo que identifica una entrega distinta del mismo corte es el fichero, y eso
    ya tiene columna: `sha_entrega`.
    """
    if e is None:
        return None
    return hashlib.sha1(json.dumps(
        [[round(a, 3), round(b, 3), d.get("toma"), d.get("beat")]
         for (a, b), d in zip(e["segmentos"], e["detalle"])],
        ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def huella_edl(slug):
    """La huella del corte vivo de una pieza. Ver la cabecera de este fichero."""
    return huella_de(_edl(slug))


def registrar_version(slug, fichero=None, commit=None):
    """Apunta el corte actual como una versión. Idempotente por huella.

    Si el corte no cambió, devuelve la versión que ya había: renderizar dos
    veces lo mismo no crea dos versiones, que es lo que haría un registro por
    fecha.
    """
    h = huella_edl(slug)
    if not h:
        return None
    con = _con()
    v = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        con.close()
        return None
    ya = con.execute("select id, n from version where video_id = ? and huella = ?",
                     (v["id"], h)).fetchone()
    if ya:
        con.close()
        return ya["id"]
    n = (con.execute("select coalesce(max(n), 0) from version where video_id = ?",
                     (v["id"],)).fetchone()[0]) + 1
    e = _edl(slug)
    dur = e.get("duracion_montada_s") if e else None
    cur = con.execute(
        "insert into version (video_id, n, huella, duracion_s, fichero,"
        " commit_git, fecha) values (?,?,?,?,?,?,?)",
        (v["id"], n, h, dur, fichero, commit,
         datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    vid = cur.lastrowid
    con.close()
    return vid

def firmada(slug):
    """La versión que Jaime aprobó, o `None`. `(n, huella, edl)`."""
    con = _con()
    r = con.execute(
        "select ve.n, ve.huella, ve.edl from aprobacion a"
        " join version ve on ve.id = a.version_id"
        " join video vi on vi.id = ve.video_id"
        " where vi.slug = ? and a.veredicto = 'aprobada'"
        " order by ve.n desc limit 1", (slug,)).fetchone()
    con.close()
    return (r["n"], r["huella"], r["edl"]) if r else None


def restaurar(slug, n=None, quien=""):
    """Devuelve al EDL vivo el corte de esa versión. `(n, motivo)`.

    **Por qué se puede, y por qué hasta ahora se reconstruía.** `reconstruir.py`
    existe porque *«la tabla `version` guarda la huella y la duración, no los
    tramos»*, así que para volver a una entrega había que **transcribir el vídeo
    y buscar cada frase en la cinta** — una propuesta medida, no el corte. Desde
    C-205 la columna `edl` guarda el montaje entero: volver a una versión es
    copiar un JSON, y es exacto.

    Sin `n`, la versión que Jaime firmó. Y no se escribe nada sin comprobar que
    el corte guardado es el que la fila dice ser: un EDL que no case con su
    huella no es esa versión, y restaurar «algo parecido» encima de un corte
    bueno es peor que no restaurar.
    """
    v = None
    if n is None:
        f = firmada(slug)
        if not f:
            return None, "no hay ninguna versión aprobada"
        v = {"n": f[0], "huella": f[1], "edl": f[2]}
    else:
        con = _con()
        r = con.execute(
            "select ve.n, ve.huella, ve.edl from version ve"
            " join video vi on vi.id = ve.video_id"
            " where vi.slug = ? and ve.n = ?", (slug, n)).fetchone()
        con.close()
        if not r:
            return None, f"{slug} no tiene versión {n}"
        v = dict(r)
    if not v["edl"]:
        return None, (f"la versión {v['n']} es anterior a C-205: guarda su"
                      " huella y no sus tramos")
    try:
        e = json.loads(v["edl"])
    except ValueError:
        return None, f"el montaje guardado de la versión {v['n']} no se lee"
    h = huella_de(e)
    if h != v["huella"]:
        return None, (f"el montaje guardado da {h} y la fila dice"
                      f" {v['huella']}: no es esa versión")
    ruta = f"ads/{slug}/edl-sell.json"
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    if quien:
        _sella(slug, quien)
    elif n is None:
        # **Restaurar el corte firmado SIN decir quién lo firmó deja la pieza
        # rota y callada.** El corte vuelve bien, pero las etiquetas de etapa
        # siguen estampadas contra el corte de después, así que `aprobada()`
        # dice que no y la pieza se va a la línea sin que nadie sepa por qué.
        # Es literalmente el síntoma de C-506, y el arreglo de entonces dependía
        # de que el llamante se acordara de pasar `quien` — o sea que no era un
        # arreglo, era una costumbre. Pasó con reel-02: etapas 1 y 3 sin sello
        # durante semanas, y lo destapó la prueba de humo, no la línea.
        import registro

        registro.aviso("version", "corte firmado restaurado sin sellar",
                       toma=slug,
                       detalle="sin `quien`, las etiquetas de etapa no se"
                               " re-sellan y la pieza deja de contar como"
                               " aprobada: `python scripts/aprobar.py"
                               f" {str(slug)[-2:].lstrip('0')} --al-firmado`")
    return v["n"], None


def _sella(slug, quien):
    """Las etapas de este corte quedan firmadas por quien firmó la versión.

    **Por qué hace falta, y es la avería que destapó restaurar reel-02.** La
    firma vive en dos sitios que no se hablan: la tabla `aprobacion` dice que
    Jaime aprobó la versión 11, y la tabla `segmento` guarda una etiqueta por
    etapa **estampada contra la huella del corte que tenía cuando se puso**. Al
    devolver el corte de la v11, las etiquetas de las etapas 1 y 3 dejaron de
    casar y `segmento.aprobada` dijo que no — o sea que **restaurar el corte que
    él firmó hacía que la pieza dejara de contar como firmada**, y volvía a la
    línea.

    Y no eran dos opiniones igual de válidas: esas etiquetas se habían puesto
    contra el corte de 20 tramos, que es el que se le hizo **después** de su
    firma y que no aprobó nadie. La firma manda; la etiqueta es su registro por
    etapa, no una segunda decisión.

    Es la misma regla que `aprobar._cerrar_lo_abierto`: *«su firma es la
    respuesta»*. Aprobar viendo la pieza es aprobar sus etapas tal y como
    estaban.
    """
    from .segmento import Segmento

    for seg in Segmento.de(slug):
        seg.aprueba(quien)

#: Cuanto puede alejarse la entrega del corte declarado, en tanto por uno.
#:
#: **Medido, no elegido.** El 14-9-2026 se compararon las diecisiete piezas
#: contra su `duracion_montada_s`: once caian dentro de ±1,6% —las costuras y
#: las transiciones mueven decimas— y seis estaban a −4,6% o peor, hasta el
#: −14,7% de reel-13. Entre 1,6 y 4,6 no hay ninguna, asi que el 2% parte los
#: dos grupos sin rozar a ninguno. Si un dia una pieza sana cae en el 2%, se
#: sube el numero con la medida delante, no a ojo.
MARGEN = 0.02


def _dura(fichero):
    """Lo que dura un fichero segun ffprobe, o `None` si no se puede medir."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", fichero],
            capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def cuadra_con_el_json(slug, fichero, margen=MARGEN):
    """**Lo que se entrega tiene que durar lo que el corte dice que dura.**

    Jaime, 14-9-2026: *«solo hay una fuente de verdad, el Json, todo se
    contrasta con el Json»*, y el porque de que esto exista: *«porque los
    ficheros se modificaron sin criterio y sin tener en cuenta al Json»*.

    `duracion_montada_s` estaba escrita en el EDL y la leian seis ficheros del
    dominio, **todos del lado de construir el corte**. Del lado de sacarlo no la
    miraba nadie —ni `verificar.py`, ni `cadena.py`, ni `montar.sh`, ni
    `musica.sh`—, asi que ningun paso llegaba a preguntar «¿lo que acabo de
    escribir dura lo que el JSON dice?». Por eso reel-13 se entrego con 51,90 s
    de un corte de 60,83 sin que fallara nada: se escribio el fichero fuera de
    su fase y no habia quien lo desmintiera.

    Devuelve `None` cuando **cuadra o no se puede medir**, y el aviso cuando no.
    No medir no es aprobar: se dice, igual que hace la separacion de la cama con
    un stem de otro corte (C-243), porque un numero falso es peor que ninguno.
    """
    e = _edl(slug)
    dice = (e or {}).get("duracion_montada_s")
    if not dice:
        return None
    # **Y se contrasta en el reloj de la entrega, no en el del corte.**
    #
    # `duracion_montada_s` mide el corte a 1x. Cuando la voz limpia entra, la
    # entrega sale a `VELOCIDAD` —decision de Jaime oyendo el lote, *«la
    # velocidad vamos a aumentarla a 1.15»*—, asi que restarle el corte sin
    # dividir acusa de -14,4% a una pieza que esta a -1,6%: eso le paso a
    # reel-13 el 14-9-2026 y paro la linea con la pieza bien hecha.
    #
    # Medido el mismo dia sobre las diecisiete: las cuatro que habian pasado
    # por `acelerar` —reel-02, -06, -12, -13— salian entre -9,6% y -14,4%, y
    # las trece que no, dentro de +-1,6%. O sea que el desvio no era de las
    # piezas: era de comparar dos relojes. Dividir solo las aceleradas deja a
    # las diecisiete dentro del margen. C-495.
    #
    # Quien sabe si esta acelerada es la pieza, que es de quien es el dato; y
    # `VELOCIDAD` se importa de `beats`, su dueno. Los dos imports van aqui
    # dentro porque `beats` come del dominio: al reves es un ciclo.
    from beats import velocidad as _vel
    from dominio.pieza import Pieza

    acelerada = Pieza(int(slug.rsplit("-", 1)[1])).acelerada
    VELOCIDAD = _vel(slug)
    # **Y las pausas que su ritmo conserva**, que están en el corte a 1x y no en
    # el JSON: las declara el plan (C-621). En el general son cero.
    from dominio.ritmo import alarga as _alarga

    debe = dice / VELOCIDAD if acelerada else dice
    debe += _alarga(slug) / VELOCIDAD if acelerada else _alarga(slug)
    hay = _dura(fichero)
    if hay is None:
        return (f"{slug}: NO SE PUDO MEDIR {fichero} — el JSON dice"
                f" {dice:.2f}s y no hay con que contrastarlo")
    # **Y la cola declarada entra en la tolerancia, no en el objetivo.**
    #
    # `musica.sh` le anade `cama.cola_s` —0,6 s— al mezclar y lo dice en voz
    # alta. Es parte del fichero que esto mide, pero **no todas las entregas la
    # llevan**: las que no pasaron por la mezcla con musica salen sin ella. Por
    # eso se ensancha el margen en vez de mover `debe`: sumarsela a todas hacia
    # fallar a reel-09, que estaba sana y sin cola, justo al arreglar reel-10.
    #
    # Y el porcentaje solo no basta porque la cola es FIJA: 0,6 s son el 0,9%
    # de una pieza de 70 s y el 1,8% de una de 34. Medido el 16-9: reel-10
    # recien mezclada daba +2,4% —fuera— con las largas del mismo lote pasando
    # con la misma cola dentro. Lo que se colaba no era el margen: era que un
    # tope relativo no cubre algo que se suma en segundos.
    #
    # Sigue cogiendo lo que vino a coger: reel-12, -13 y -14 estan entre -10,5%
    # y -15,3%, o sea entre siete y nueve segundos, muy lejos de una cola.
    # **Y lo que la pieza baila tambien cuenta.** Las pausas de `compas.json`
    # congelan frames a proposito para que la costura caiga en el beat: son
    # parte del fichero, declaradas y medidas, no un descuadre.
    import cama as _cama
    import compas as _compas

    debe += _compas.total(slug)
    d = hay - debe
    # **Y un fotograma por escena** (C-634): el corte redondea cada escena a
    # fotograma entero, así que diez escenas suman hasta 0,33 s que no están en
    # el JSON. En una pieza de 19 s eso es más que el 2 %: reel-21 aprobada se
    # quedó fuera por 14 ms (+1,00 s contra 0,99 de margen).
    from dominio.pieza import FPS

    try:
        escenas = len(json.load(open(os.path.join(
            "work", "scenes", slug, "plan-full.json"), encoding="utf-8"))["escenas"])
    except (OSError, ValueError, KeyError):
        escenas = 0
    if abs(d) <= debe * margen + _cama.cola(slug) + escenas / FPS:
        return None
    reloj = (f" (el corte declara {dice:.2f}s a 1x y esta sale a {VELOCIDAD}x)"
             if acelerada else "")
    return (f"{slug}: la entrega dura {hay:.2f}s y deberia durar {debe:.2f}s"
            f"{reloj} ({d:+.2f}s, {d / debe * 100:+.1f}%). Manda el JSON: o el"
            f" fichero se escribio fuera de su paso, o el corte cambio y nadie"
            f" lo volvio a sacar.")
