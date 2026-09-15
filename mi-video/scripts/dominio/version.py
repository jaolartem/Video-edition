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


def huella_edl(slug):
    """La huella del corte de una pieza. Ver la cabecera de este fichero."""
    e = _edl(slug)
    if e is None:
        return None
    return hashlib.sha1(json.dumps(
        [[round(a, 3), round(b, 3), d.get("toma"), d.get("beat")]
         for (a, b), d in zip(e["segmentos"], e["detalle"])],
        ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


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
    from beats import VELOCIDAD
    from dominio.pieza import Pieza

    acelerada = Pieza(int(slug.rsplit("-", 1)[1])).acelerada
    debe = dice / VELOCIDAD if acelerada else dice
    hay = _dura(fichero)
    if hay is None:
        return (f"{slug}: NO SE PUDO MEDIR {fichero} — el JSON dice"
                f" {dice:.2f}s y no hay con que contrastarlo")
    d = hay - debe
    if abs(d) <= debe * margen:
        return None
    reloj = (f" (el corte declara {dice:.2f}s a 1x y esta sale a {VELOCIDAD}x)"
             if acelerada else "")
    return (f"{slug}: la entrega dura {hay:.2f}s y deberia durar {debe:.2f}s"
            f"{reloj} ({d:+.2f}s, {d / debe * 100:+.1f}%). Manda el JSON: o el"
            f" fichero se escribio fuera de su paso, o el corte cambio y nadie"
            f" lo volvio a sacar.")
