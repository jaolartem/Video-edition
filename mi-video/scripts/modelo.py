"""El modelo de datos: **dice qué le falta** y llama a quien lo arregla.

Regla de Jaime: *«valida el modelo de datos y agrega lo que haga falta, une y
crea, optimiza el modelo, lo mínimo básico es tercer nivel de normalización»*. Y
el ciclo que tiene que soportar, con sus palabras:

> *«Copio un vídeo de un lado, sale el vídeo renderizado, se aprueba uno por
> uno, y de cada versión aprobada me das el audio virgen para pasarlo por Adobe
> Podcast, lo reemplazas y lo subimos.»*

## Lo que faltaba, y no era poco

El modelo sabía **cómo se decide** una pieza —libretos, etapas, candidatos,
elecciones, descripciones— y no sabía **nada de su vida después**. No existía la
versión, así que «la versión aprobada» no se podía nombrar; ni la aprobación, así
que «se aprueba uno por uno» vivía en el chat; ni el audio por versión, así que
cuál WAV corresponde a qué corte era cosa de mirar fechas; ni la publicación.

Sin eso, el ciclo que él describe **no se puede ejecutar dos veces igual**, que
es justo lo que un pipeline tiene que garantizar.

## Dónde vive cada mitad

Esto eran tres cosas en un fichero de 473 líneas, y de esas 473 había **249 de
SQL** metidas en una cadena de Python: el DDL pesaba más que todo lo demás junto
y no lo coloreaba ni lo comprobaba nadie. Ahora:

    scripts/esquema-modelo.sql   qué forma tienen las tablas que añade el modelo
    scripts/migraciones.py       cómo se llega hasta ahí, una función por cambio
    scripts/dominio/fase.py      `CICLO`: el camino de fases y su servicio
    scripts/dominio/version.py   la huella del corte y el registro de versiones
    scripts/modelo.py            qué falta por hacer, y la puerta de la línea

La superficie pública no se movió: lo que `donde.py`, `revision.py` y
`verificar.py` importaban de aquí —`huella_edl`— se sigue importando de aquí.

## Las cuatro tablas del ciclo

    version       cada render de una pieza, con la huella de SU corte
    aprobacion    el veredicto sobre una version concreta
    audio_version el virgen que sale y el limpio que vuelve, atados a la version
    publicacion   donde y cuando se subio

La **huella** es lo que hace que esto no mienta, y por qué se calcula sobre el
corte y no sobre el fichero está en `dominio/version.py`.

## Tercer nivel

Se arregla lo que estaba en segunda: `revision`, `escena_desc`, `densidad` y
`descartado` referían al vídeo **por texto** (`video_slug`), no por clave. Un
slug repetido en cinco tablas es cinco sitios donde se puede escribir mal y
ninguno donde salte. Se les añade `video_id` con clave foránea y se rellena; la
columna de texto se conserva por compatibilidad, pero la que manda es la clave.

    python scripts/modelo.py            # valida y dice que falta
    python scripts/modelo.py --migrar   # crea y rellena lo que falte
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import basedatos  # noqa: E402
import rutas  # noqa: E402
from dominio.fase import CICLO  # noqa: E402,F401  (lo lee `migraciones._ciclo`)
from dominio.version import huella_edl, registrar_version  # noqa: E402,F401
from migraciones import MUERTAS, POR_SLUG, migrar  # noqa: E402,F401

# **Y tres que parecian muertas y son vocabularios sin usar.**
#
# `tipo_medicion` trae exactamente lo que `musica.sh` mide en cada render
# —sonoridad, pico real, muestras saturadas, duracion—; `estado_decision` es el
# vocabulario de `ads/estado.json`; `decidido_por` es el `quien` que hoy viaja
# como texto suelto en cuatro tablas.
#
# Borrarlas habria sido lo comodo. Lo correcto es **usarlas**: eso es unir en vez
# de crear, que es lo que Jaime pidio. Un vocabulario en una tabla es un sitio
# donde el valor esta escrito bien; el mismo vocabulario repetido como cadena en
# cuatro sitios son cuatro sitios donde puede estar mal.
#: Y el nombre dice cual de los dos es: `entidades.VOCABULARIOS` es «que columna
#: es que catalogo» y esto es «que catalogos tienen que tener filas». Con el
#: mismo nombre en los dos, una aguja no sabia a cual apuntaba.
VOCABULARIOS_SEMBRADOS = ("tipo_medicion", "estado_decision", "decidido_por")


def validar():
    """Qué le falta al modelo. Lista vacía es que está entero.

    Comprueba **el resultado de las migraciones**, y por eso las listas de
    tablas se importan de `migraciones` en vez de repetirse aquí: escritas dos
    veces, el día que una tabla saliera de una lista y no de la otra, migrar y
    validar dejarían de hablar de lo mismo y las dos parecerían correctas.
    """
    con = basedatos.abrir()
    con.row_factory = sqlite3.Row
    hay = {r[0] for r in con.execute(
        "select name from sqlite_master where type='table'")}
    mal = []
    for t in ("version", "aprobacion", "audio_version", "publicacion"):
        if t not in hay:
            mal.append(f"falta la tabla «{t}» — el ciclo de vida no se puede"
                       f" registrar")
    for t in POR_SLUG:
        if t in hay:
            cols = {r[1] for r in con.execute(f"pragma table_info({t})")}
            if "video_id" not in cols:
                mal.append(f"«{t}» refiere al video por texto y no por clave"
                           f" (2NF)")
    # **Las tablas declaradas y vacias NO se cuentan aqui.** C-356 lo decidio:
    # una tabla que el esquema declara y nadie llena es una **promesa
    # pendiente**, y su sitio es `conectado.py`, que para eso esta. Contarla
    # tambien aqui tenia dos costes: el aviso salia dos veces, y —peor— dejaba
    # a `validar()` devolviendo siempre algo, asi que el `|| exit 1` con el que
    # `pipeline.sh` lo llama no podia dispararse nunca. Un guarda que avisa y
    # sigue no es un guarda; uno que no puede fallar tampoco.
    cf = {r[1] for r in con.execute("pragma table_info(corte_fijo)")}
    if cf and "toma" not in cf:
        mal.append("«corte_fijo» solo sabe de apertura y cierre: no hay donde"
                   " declarar el tramo de una etapa, y sin eso la composicion"
                   " no se puede aplicar por la linea")
    if "precio" not in hay:
        mal.append("falta la tabla «precio» — el precio vuelve a ser una cadena"
                   " literal, y una cadena no caduca (C-28)")
    for t in ("fuente", "dato"):
        if t not in hay:
            mal.append(f"falta la tabla «{t}» — una cifra en pantalla no tiene"
                       f" donde declarar de donde sale, y eso es cumplimiento")
    if "medicion" not in hay:
        mal.append("falta «medicion»: lo que se mide de cada render no se guarda"
                   " en ningun sitio, asi que no se puede comparar entre tandas")
    sin_usar = [t for t in VOCABULARIOS_SEMBRADOS if t in hay and not con.execute(
        f"select count(*) from {t}").fetchone()[0]]
    if sin_usar:
        mal.append(f"vocabularios vacios: {sin_usar}")
    con.close()
    return mal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--migrar", action="store_true")
    ap.add_argument("--registrar", action="store_true",
                    help="apunta el corte actual de las seis como version")
    a = ap.parse_args()
    if a.migrar:
        hecho = migrar()
        print("modelo migrado:", ", ".join(hecho) if hecho else "nada que hacer")
    if a.registrar:
        for n in rutas.piezas():
            slug = f"reel-{n:02d}"
            v = registrar_version(slug)
            print(f"{slug}: version {v}" if v else f"{slug}: sin EDL")
        return 0
    mal = validar()
    if not mal:
        print("modelo: entero")
        return 0
    # **Y sale con codigo, que es lo que `pipeline.sh` esperaba.** Estaba
    # cableado como `python scripts/modelo.py || exit 1` y `main()` devolvia
    # `None`: el paso salia con 0 dijera lo que dijera. Es la misma averia que
    # `tamano.py` describe como ya corregida en su propio caso — imprimir el
    # problema y seguir es tenerlo contado, no cerrado.
    print(f"modelo: {len(mal)} cosa(s) que arreglar")
    for m in mal:
        print(f"    · {m}")
    print("\n  python scripts/modelo.py --migrar")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
