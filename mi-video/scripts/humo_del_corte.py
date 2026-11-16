"""La prueba de humo **de la pieza**: su corte, su firma y su salida.

`humo.py` mide la línea —el marcador, los buzones, las guardas, el motor— y
esto mide el otro sustantivo: **el montaje de una pieza**. Estaban juntas
porque se corren juntas, y con eso `humo.py` pasó del techo de 300 líneas. La
frontera ya estaba: ninguna de las de aquí mira una fase, y ninguna de las de
allá abre un EDL.

Las corre `humo.main()`, que sigue siendo el único sitio desde el que se mide.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: La pieza sobre la que se mide. La misma que usa `humo.py`, preguntada y no
#: copiada: dos piezas distintas serían dos pruebas distintas con un nombre.
from humo import PIEZA  # noqa: E402


def _lo_firmado_se_puede_volver_a_poner(h):
    """El corte que Jaime firmó está guardado y casa con su huella.

    Es lo que hace que «volver a lo aprobado» sea copiar un JSON en vez de
    reconstruirlo del vídeo. Y que la pieza siga contando como firmada después:
    la etiqueta de cada etapa se estampa contra su corte, así que devolver el
    corte firmado sin volver a sellarlas dejaba a reel-02 fuera de «aprobada»
    —restaurar lo que él aprobó la sacaba de aprobada—. C-506.
    """
    import json as _json

    from dominio import segmento as _sg
    from dominio import version as _v

    firmadas = [s for s in (f"reel-{n:02d}" for n in range(1, 18))
                if _v.firmada(s)]
    h.mide("C-506", bool(firmadas),
           f"{len(firmadas)} pieza(s) con firma de Jaime en la base")
    sanas = []
    for slug in firmadas:
        n, huella, edl = _v.firmada(slug)
        try:
            sanas.append(_v.huella_de(_json.loads(edl)) == huella)
        except (ValueError, TypeError):
            sanas.append(False)
    h.mide("C-506", all(sanas),
           "y el montaje guardado de cada una casa con su huella")
    h.mide("C-506", all(_sg.aprobada(s) for s in firmadas),
           "y todas siguen contando como aprobadas con el corte que tienen")
def _el_corte_nace_derivado(h):
    """Escribir el EDL vuelve a poner lo que ya se había decidido.

    `seleccion.edl.escribir` rehace el corte desde el reparto, así que borra los
    tramos declarados y los recortes ya aplicados. De ahí salían dos fases cuya
    única razón era reponerlos. Ahora la reposición es parte de escribir, y se
    comprueba de la única forma que vale: **derivar dos veces no cambia nada**.
    C-507.
    """
    import inspect
    import shutil

    import modelo
    from dominio.seleccion import edl as _edl

    h.mide("C-507", "derivar(slug)" in inspect.getsource(_edl.escribir),
           "escribir termina derivando, no dejando el corte crudo")
    ruta = os.path.join("ads", PIEZA, "edl-sell.json")
    if not os.path.exists(ruta):
        h.mide("C-507", False, f"no hay EDL de {PIEZA} que derivar")
        return
    copia = ruta + ".humo"
    shutil.copy2(ruta, copia)
    try:
        # **Derivar DOS veces, que es lo que dice arriba y lo que se puede
        # exigir.** Comparaba una sola derivación contra el corte vivo, o sea
        # `derivar(x) == x`, y eso es más fuerte de lo que el mecanismo promete:
        # un corte **restaurado** es el que Jaime firmó, no uno derivado, así
        # que la primera derivación lo mueve con razón — es la reposición
        # haciendo su trabajo. Lo que tiene que ser cierto es que sea un punto
        # fijo: de la segunda en adelante, nada se mueve.
        #
        # Medido en reel-03: vivo `b8f238bf975e`, primera derivación
        # `aef13cdc0125`, y la segunda y la tercera igual que la primera.
        _edl.derivar(PIEZA)
        antes = modelo.huella_edl(PIEZA)
        _edl.derivar(PIEZA)
        h.mide("C-507", modelo.huella_edl(PIEZA) == antes,
               f"y derivar sobre lo ya derivado no mueve el corte ({antes})")
    finally:
        shutil.move(copia, ruta)


def _cada_corte_lleva_lo_decidido(h):
    """El JSON del pedido va publicado ahora y con lo decidido de cada corte. C-714.

    reel-23, 15-11-2026: el pedido de `describir` de las 23:32 llevó el JSON de
    las 20:36 —sólo se publicaba al cambiar de fase— y sus 18 cortes sin un
    solo elemento decidido. Jaime: *«¿y por qué no se usó?»*.
    """
    import time

    import servicio
    from dominio import segmento as sg

    hace = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 60))
    m = servicio._marcador(PIEZA)
    con = [s["etapa"] for s in m["segmentos"] if {"trato", "plano", "tablero"} & set(s)]
    h.mide("C-714", (m.get("publicado") or "") >= hace,
           f"el pedido lleva el JSON publicado ahora ({m.get('publicado')})")
    h.mide("C-714", bool(con) or not sg.decididas(PIEZA),
           f"y lo decidido de {len(con)} de {len(m['segmentos'])} cortes")


def _lo_publicado_queda_escrito(h):
    """La tabla `publicacion` se llena cuando algo sale. C-511.

    Estuvo declarada desde el principio con **cero filas**: nadie la escribía y
    `donde.py` la leía, así que preguntaba «¿se publicó?» a un sitio que no
    podía contestar nunca.
    """
    import inspect

    import basedatos
    import publicar

    cx = basedatos.abrir("ads/decisiones.db")
    n = cx.execute("select count(*) from publicacion").fetchone()[0]
    cx.close()
    h.mide("C-511", n > 0, f"{n} publicacion(es) escritas en la base")
    h.mide("C-511", "anotar(" in inspect.getsource(publicar.main),
           "y publicar la anota, no solo copia el fichero")


def _un_tablero_sin_encargo_caduca(h):
    """Un tablero puesto sin `grafico` vuelve al diseño cuando el `grafico` llega.

    reel-23 e12, 16-11-2026: un `Apoyo` compuesto sin encargo guardaba
    `encargo: null`, y `null` se leía como fila de antes. El compositor escribió
    la cadena de cuatro bloques y el diseñador no la vio nunca. C-715.
    """
    import inspect
    import json as _json

    from dominio import encargo as _enc
    from dominio.escena import Escena

    sin = _json.dumps({"kind": "Apoyo", "props": {"clip": "x"}, "encargo": None})
    antes = _json.dumps({"kind": "Apoyo", "props": {"clip": "x"}})
    h.mide("C-715", _enc.tablero_desfasado({"tablero": sin, "grafico": "Cadena"}),
           "un tablero puesto sin encargo caduca cuando llega el grafico")
    h.mide("C-715", not _enc.tablero_desfasado({"tablero": sin, "grafico": ""})
           and not _enc.tablero_desfasado({"tablero": antes, "grafico": "Cadena"}),
           "y sin grafico sigue valiendo; la fila de antes, tambien")
    h.mide("C-715", "guardar_tablero(" in inspect.getsource(Escena.poner_tablero),
           "el tablero que entra por consulta lo escribe guardar_tablero, con huella")


def _el_horizontal_compone_su_tablero(h):
    """El cuadro horizontal centra, escala y pone su suelo; el vertical, igual. C-716.

    reel-23, 16-11-2026. Jaime: *«solo están utilizando un lado como si fuera
    vertical»*. Las formas estaban maquetadas a 1080 de ancho y alineadas a la
    izquierda, sobre una placa vertical recortada a su franja central.
    """
    import json as _json
    import subprocess

    from dominio.lienzo import LIENZOS

    todos = _json.load(open(LIENZOS, encoding="utf-8"))
    hz, vt = todos["horizontal"]["tablero"], todos["vertical"]["tablero"]
    h.mide("C-716", hz["alinea"] == "center" and hz["suelo"] == "cuadricula"
           and not hz["serie"], "el horizontal centra, pone la retícula y no lleva la serie")
    h.mide("C-716", vt == {"alinea": "flex-start", "cuerpo": 1, "suelo": "placa",
                           "serie": "El código del empresario"},
           "y el vertical se compone como siempre")
    pide = lambda f: _json.loads(subprocess.run(  # noqa: E731
        ["node", "scripts/dibujable.mjs"], capture_output=True, text=True, encoding="utf-8",
        input=_json.dumps({"formato": f, "tableros": [{"etapa_orden": 1, "kind": "causal",
                           "props": {"nodes": [{"stage": "1", "text": "A"}]}}]})).stdout or "{}")
    h.mide("C-716", bool(pide("horizontal")) and not pide("vertical"),
           "la puerta del diseño no deja en horizontal una forma no compuesta para él")


def _la_guia_va_antes_del_render(h):
    """El render no sale sin la hoja guía aprobada sobre su spec. C-717.

    Jaime, 16-11-2026: *«antes de renderizar yo quiero ver una hoja guía con
    cada fotograma segundo a segundo»*.
    """
    import guia

    m = open("scripts/montar.sh", encoding="utf-8").read()
    h.mide("C-717", -1 < m.find("scripts/guia.py") < m.find("node scripts/render.mjs"),
           "montar.sh pide la hoja guía antes de renderizar")
    g = guia.Guia.__new__(guia.Guia)
    g.huella = "h1"
    h.mide("C-717", g.aprobada({"aprobada": True, "huella": "h1"})
           and not g.aprobada({"aprobada": True, "huella": "h0"}),
           "y una aprobación de otro spec no vale")


#: Las que corre `humo.main()`, en su orden. La lista vivía allí y engordaba
#: `humo.py` con cada prueba de aquí, que es la razón por la que se partió.
PRUEBAS = (_lo_publicado_queda_escrito, _lo_firmado_se_puede_volver_a_poner,
           _el_corte_nace_derivado, _cada_corte_lleva_lo_decidido,
           _un_tablero_sin_encargo_caduca, _el_horizontal_compone_su_tablero,
           _la_guia_va_antes_del_render)
