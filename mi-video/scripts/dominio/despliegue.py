"""Qué código corre la línea. Se le pregunta al despliegue, no a git.

Jaime, 23-10-2026: *«hay que separar la aplicación funcionando del desarrollo;
la aplicación no debe estar guiada por git, para eso tiene o debe tener un
sistema de memoria interna»*.

La línea corre desde `F:/linea/codigo`, una copia que sólo cambia cuando
`scripts/desplegar.py` la pone al día, y ese paso deja al lado de `rutas.json`
el fichero `DESPLIEGUE` con el commit que copió y cuándo. Lo que la línea
necesita saber de su código —con qué se selló una versión, si hay que
rearrancar— sale de ahí.

En un checkout de desarrollo no hay fichero, y entonces sí se contesta con git:
es el único sitio donde git sigue sabiendo algo, y no es la línea.
"""
import json
import os
import subprocess

#: `mi-video/DESPLIEGUE`, al lado de `rutas.json`.
FICHERO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "DESPLIEGUE")


def leer():
    """`{"sha", "fecha", "rama"}` del despliegue, o `None` fuera de la línea."""
    try:
        return json.load(open(FICHERO, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def en_linea() -> bool:
    """¿Corre esto desde un despliegue, y no desde un checkout de desarrollo?"""
    return leer() is not None


def actual(corto=True):
    """El commit del código que corre, o `None` si no se sabe."""
    d = leer()
    if d:
        return d["sha"][:7] if corto else d["sha"]
    orden = ["git", "rev-parse"] + (["--short"] if corto else []) + ["HEAD"]
    try:
        r = subprocess.run(orden, capture_output=True, text=True,
                           cwd=os.path.dirname(FICHERO))
    except OSError:
        return None
    return r.stdout.strip() or None
