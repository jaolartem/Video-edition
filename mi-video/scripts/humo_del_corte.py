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
    import json as _json
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
