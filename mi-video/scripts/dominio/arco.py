"""**El arco narrativo y el emocional de una pieza**, en orden.

Regla de Jaime, y es la que sube el techo del paso que compone: *«el compositor
puede darle informacion respecto al arco narrativo y al arco emocional al
disenador; el disenador puede hacer un gancho visual mucho mas potente, por
ejemplo»*.

Vive en el dominio y no dentro del servicio porque **no es una pregunta de ese
paso**: es lo que la pieza ES. La contesta igual quien compone, quien audita y
quien informa, y salió de `servicios/disenar.py` el día que ese fichero pasó del
techo de 300 líneas — se parte por responsabilidad, y ésta es una.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def arco(slug):
    """El arco narrativo y el emocional, en orden. Los da el compositor.

    Regla de Jaime, y es la que sube el techo de este paso: *«el compositor puede
    darle informacion respecto al arco narrativo y al arco emocional al
    disenador; el disenador puede hacer un gancho visual mucho mas potente, por
    ejemplo»*.

    Sin esto el que monta ve un encargo por tablero y nada mas, asi que disena
    tableros correctos que **no saben donde caen**: el gancho no sabe que tiene
    que abrir, el cierre no sabe que tiene que rematar, y el tablero del medio no
    sabe si esta en la subida o en la caida. Con el arco delante, la forma puede
    acompanar al argumento en vez de ilustrarlo.

    Son dos arcos y no uno:

    - **narrativo** — que funcion cumple cada etapa en el frame, en orden. Es la
      estructura del argumento.
    - **emocional** — que siente el espectador en cada etapa. Jaime lo describio
      como onda: *«arriba, luego abajo, luego arriba»*.
    """
    con = _con()
    filas = [dict(r) for r in con.execute(
        "select e.orden, ec.nombre funcion, e.mensaje_esperado, e.obligatorio,"
        "       d.emocion, d.que_pasa, d.trato"
        "  from etapa e join video v on v.id = e.video_id"
        "  left join etapa_canonica ec"
        "         on ec.estructura_id = e.estructura_id"
        "        and ec.orden = e.etapa_orden"
        "  left join escena_desc d on d.video_slug = v.slug"
        "   and d.etapa_orden = e.orden"
        " where v.slug = ? order by e.orden", (slug,))]
    con.close()
    return {
        # **La intención narrativa de CADA segmento, no la de la pieza.** Jaime:
        # *«el segundo recibe la intención narrativa y el arco emocional de cada
        # segmento; con eso puede potenciarlo con diseño»*. Saber que la etapa 4
        # es la revelación y tiene que decir tal cosa es lo que deja diseñar
        # para eso, en vez de ilustrar la frase que se oye.
        "narrativo": [{"etapa": f["orden"], "funcion": f["funcion"],
                       "tiene_que_decir": f["mensaje_esperado"],
                       "obligatoria": bool(f["obligatorio"])}
                      for f in filas],
        # Y la onda: arriba, abajo, arriba. Con el tratamiento que ya lleva, que
        # es lo que dice si ese punto pide sostener o golpear.
        "emocional": [{"etapa": f["orden"], "emocion": f["emocion"],
                       "trato": f["trato"],
                       "que_pasa": (f["que_pasa"] or "")[:120]}
                      for f in filas],
    }
