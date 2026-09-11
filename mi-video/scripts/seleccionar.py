"""La sección la marca el guion; los extremos, la pausa medida.

Los pasos 2 y 3 del proceso de Jaime, después de los subtítulos: *«con los
subtítulos de todo el video contrastamos contra el guion, evitamos las
repeticiones y puntuamos por sección: la mejor puntuada en la sección queda»*.

## Por qué no se busca «la frase»

Porque la frase no existe en el dato. `whisper -ml 1 -sow` **borra toda la
puntuación** —86 palabras del reel 3, cero signos—, y con `--prompt` sí puntúa
pero se come la primera frase y se queda pegado repitiendo. Así que cortar la
cinta en oraciones era pedirle al modelo justo lo que no sabe hacer, y de ahí
salían las unidades de 98 segundos.

La pausa sí está medida: la mide el detector de habla, no el modelo. Pero la
pausa sola tampoco define la unidad —hay tramos continuos de 50 s sin un solo
hueco de un segundo— y además Jaime avisó de lo contrario: *«hay silencios entre
la misma frase; no significa que sea otra toma, sólo me quedé callado
pensando»*.

Entonces **la sección la marca el guion**: para cada etapa del frame se busca el
trozo de cinta que mejor la dice, con los extremos anclados a pausa medida para
que el corte caiga en silencio. Es lo que hace que no haga falta puntuación.

## Dónde vive cada cosa

Esto eran 1.599 líneas y 28 funciones sueltas, y dentro convivían tres trabajos
distintos: **medir** una ventana, **decidir** cuál se queda y **escribir** lo
decidido. Mezclados, un peso mal puesto puede estar diez veces por debajo de lo
debido sin que nadie lo vea — pasó con `PESO_CUELGA`, y `PESO_REPE` llegó a
estar declarado y **nunca aplicado**.

Ahora cada trabajo tiene dueño en [`dominio/seleccion/`](dominio/seleccion/):

| Fichero | De qué es dueño |
|---|---|
| `pesos.py`    | los números con los que se corta |
| `ventana.py`  | la ventana y lo que se mide sobre ella |
| `corpus.py`   | las ventanas de todas las cintas, y sus palabras |
| `tijeras.py`  | extremos, repetición dentro y costura |
| `reparto.py`  | quién se queda con qué trozo, y la última palabra de Jaime |
| `entrega.py`  | entre las que dicen lo mismo, gana la que lo dice con más voz |
| `edl.py` · `eleccion.py` | el corte y la decisión, escritos |
| `corrida.py` · `informe.py` | el orden de los pasos y lo que se cuenta |

Aquí quedan la línea de órdenes y los nombres que ya usaba quien llamaba, cada
uno delegando en su dueño.

## Cómo se puntúa

Una ventana es cualquier trozo que **empieza donde arranca un tramo y acaba
donde acaba otro**. Se le mide:

- **cubre** — cuánto del mensaje de la etapa está dicho (`beats.puntua`).
- **dice** — si aparecen los términos que la etapa declara en `debe_decir`.
- **aire** — el silencio interno se descuenta, no se prohíbe.
- **costura** — si el extremo no cae en un hueco de verdad, está cortando dentro
  de una frase. El umbral sale de los 885 huecos medidos del lote.
- **sobra / trunca** — la firma del reintento: la cola de la ventana reaparece al
  principio del tramo siguiente, o el arranque repite la cola del anterior.
- **cuelga** — un extremo detrás de una palabra de función parte una unidad
  sintáctica. Es la regla de los subtítulos compuestos (C-23) aplicada al corte.
- **invade** — si la cola dice más de la etapa siguiente que de la suya.

La redundancia **no** puntúa: se recorta después, sobre la ganadora. Es la regla
de Jaime —*«a la mejor toma, y sólo a la mejor, le hacemos la revisión estricta
de redundancia»*— y por eso `repite()` no existe ya.

## Cómo se reparte

En orden de cinta y sin solaparse, maximizando el total: es la programación
dinámica de `encadenar()`. Y lo que ésa no puede ver —la misma frase dicha en
dos puntos distintos de la cinta— lo quita `sin_repetir()`.

    python scripts/seleccionar.py 3          # el plan del reel 3
    python scripts/seleccionar.py 3 --todo   # con los finalistas de cada etapa
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
from dominio.seleccion import edl as _edl  # noqa: E402
from dominio.seleccion import eleccion as _eleccion  # noqa: E402
from dominio.seleccion.corpus import Corpus, ventanas  # noqa: E402,F401
from dominio.seleccion.corrida import Corrida  # noqa: E402
from dominio.seleccion.entrega import Entrega  # noqa: E402
from dominio.seleccion.informe import Informe  # noqa: E402
# Los números siguen leyéndose desde aquí, pero **se declaran una sola vez** en
# `dominio.seleccion.pesos`. Re-exportarlos no es duplicarlos: no hay un segundo
# valor que pueda separarse del primero.
from dominio.seleccion.pesos import (COSTURA, LEIDA, MAX_VOZ,  # noqa: E402,F401
                                     MIN_VOZ, PAUSA_IDEA, PESO_AIRE,
                                     PESO_COSTURA, PESO_CUBRE, PESO_CUELGA,
                                     PESO_DICE, PESO_INVADE, PESO_SOLAPE,
                                     PREMIO, PREMIO_OBLIG, SUELO_DICE, UMBRAL,
                                     VOZ_SALVA)
from dominio.seleccion.reparto import Reparto, con_toma  # noqa: E402
from dominio.seleccion.reparto import manda_jaime as _manda_jaime  # noqa: E402
from dominio.seleccion.tijeras import Tijeras  # noqa: E402
from dominio.seleccion.tijeras import una_sola_vez as _una_sola_vez  # noqa: E402

#: Dónde vive la base. La declara `basedatos`, no este fichero.
BASE = _eleccion.BASE


# ─────────────────────────────────────────────────────────────────────────────
# Los nombres que ya usaba quien llamaba. Cada uno delega en su dueño: la
# implementación se movió, la puerta no. Es el patrón de `transcribir.suena`.
# ─────────────────────────────────────────────────────────────────────────────
def puntuar(parrafo, exige, v, siguiente=""):
    """Lo que vale una ventana para una etapa. Vive en `Ventana.puntua`."""
    return v.puntua(parrafo, exige, siguiente)


def cuelga(v):
    """Cuánto rompe la ventana por sus extremos. Vive en `Ventana.cuelga`."""
    return v.cuelga()


def invade(v, siguiente):
    """¿Se come el arranque de la etapa siguiente? Vive en `Ventana.invade`."""
    return v.invade(siguiente)


def literal(v, parrafo, n=4):
    """Cuánta secuencia exacta del libreto reproduce. Vive en `Ventana.lee`."""
    return v.lee(parrafo, n)


def remedir(v, habla):
    """Vuelve a medir voz y aire tras mover un extremo. Vive en `Ventana.remedida`."""
    return v.remedida(habla)


def corpus(tomas):
    """Las ventanas de TODAS las grabaciones. Vive en `dominio.seleccion.Corpus`."""
    return Corpus(tomas)


def escalera(corrida, cuantos=4):
    """Preselecciona barato y afina lo preseleccionado. Vive en `Corrida.escalera`."""
    return corrida.escalera(cuantos)


def encadenar(marcas, vs, premio, prohibidas=()):
    """Reparte en orden de cinta y sin solaparse. Vive en `Reparto.en_orden`."""
    return Reparto(marcas, vs, premio).en_orden(prohibidas)


def repartir_libre(marcas, vs, premio, prohibidas=()):
    """Reparte sin exigir orden de cinta. Vive en `Reparto.libre`."""
    return Reparto(marcas, vs, premio).libre(prohibidas)


def sin_repetir(marcas, vs, plan, premio):
    """Quita la copia peor puntuada. Vive en `Reparto.sin_repetir`."""
    return Reparto(marcas, vs, premio).sin_repetir(plan)


def recortar(v, palabras):
    """Quita del extremo lo que cuelga. Vive en `Tijeras.extremos`."""
    return Tijeras(palabras).extremos(v)


def podar_dentro(v, palabras, parrafo="", exige=()):
    """Lo dicho dos veces dentro de la ventana. Vive en `Tijeras.dentro`."""
    return Tijeras(palabras).dentro(v, parrafo, exige)


def limpiar_costura(cola, v, palabras):
    """La repetición que cruza el corte. Vive en `Tijeras.costura`."""
    return Tijeras(palabras).costura(cola, v)


def limpieza(corpus_, v):
    """Cuánto sobrevive a quitarle los tropiezos. Vive en `Entrega.limpieza`."""
    return Entrega(corpus_, [], []).limpieza(v)


def manda_la_voz(plan, corpus_, marcas, vs, rotas=(), prioridades=None):
    """Entre las que dicen lo mismo, manda la voz. Vive en `Entrega.decide`."""
    return Entrega(corpus_, marcas, vs, rotas=rotas,
                   prioridades=prioridades).decide(plan)


def a_tablero(plan, corpus_, vs, libreto):
    """La lectura plana se traslada a tablero. Vive en `Entrega.a_tablero`."""
    return Entrega(corpus_, [], vs).a_tablero(plan, libreto)


def manda_jaime(plan, marcas, vs, corpus_, slug, toma):
    """Lo que Jaime ya juzgó no se vuelve a elegir. Vive en `reparto.manda_jaime`."""
    return _manda_jaime(plan, marcas, vs, corpus_, slug, toma)


def una_sola_vez(plan, vs, frame):
    """Cada dato declarado se dice UNA vez. Vive en `tijeras.una_sola_vez`."""
    return _una_sola_vez(plan, vs, frame)


def segs_ok(plan):
    """Las etapas que salieron con material. Vive en `reparto.con_toma`."""
    return con_toma(plan)


def escribir_edl(slug, plan, vs, libreto, frame):
    """Escribe `ads/<slug>/edl-sell.json`. Vive en `dominio.seleccion.edl`."""
    return _edl.escribir(slug, plan, vs, libreto, frame)


def guardar(slug, toma, plan, vs, libreto, marcas=None, finalistas=5):
    """Deja el reparto en el modelo. Vive en `dominio.seleccion.eleccion`."""
    return _eleccion.guardar(slug, toma, plan, vs, libreto, marcas, finalistas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reel", type=int)
    ap.add_argument("--todo", action="store_true", help="los finalistas de cada etapa")
    ap.add_argument("--sin-voz", action="store_true",
                    help="no mide expresividad (mas rapido, decide solo el texto)")
    ap.add_argument("--finalistas", type=int, default=5,
                    help="cuantas tomas por etapa se guardan en la base")
    ap.add_argument("--escalera", action="store_true",
                    help="afina con el modelo bueno la lista corta de TODAS las"
                         " etapas y vuelve a repartir de cero")
    ap.add_argument("--propia", action="store_true",
                    help="busca solo en la cinta del reel")
    ap.add_argument("--edl", action="store_true",
                    help="escribe ads/<slug>/edl-sell.json con este reparto")
    a = ap.parse_args()

    c = Corrida(a.reel, propia=a.propia)
    inf = Informe(c)
    inf.cabecera()
    c.puntuar()
    if a.escalera:
        inf.escalera(*c.escalera())
    inf.handicap(c.rotas(), beats.PASO_VOZ)

    _plan, total = c.repartir()
    # **Lo que sólo se encontró leído se pide, no se tapa (T-05).** Ver
    # `Corrida._vuelven_las_leidas`.
    from dominio.seleccion.corrida import pide_otra_toma
    for b, toma, lect in c.sin_otra:
        pide_otra_toma(c.slug, b, toma, lect)
    if not a.sin_voz:
        inf.voz(c.entrega())
    # **Las tres reglas de no-redundancia**, y después los extremos, que es
    # cuando ya no se mueven. Lo que Jaime juzgó entra al final y ANTES de
    # volver a puntuar, para que su rango se mida igual que los demás.
    c.limpiar()
    c.de_jaime()
    perdidos, a_tab, repes = c.repuntuar(), c.a_tablero(), c.repetidos()

    inf.reparto(total)
    inf.tableros(a_tab)
    inf.perdidos(perdidos)
    inf.repetidos(repes)
    inf.etapas(todo=a.todo)

    if a.edl:
        ruta, voz = escribir_edl(c.slug, c.plan, c.ventanas, c.libreto, c.frame)
        print(f"-> {ruta}  ({len(segs_ok(c.plan))} cortes, {voz:.1f}s de voz)")
    puestos = guardar(c.slug, c.toma, c.plan, c.ventanas, c.libreto,
                      c.marcas, a.finalistas)
    print(f"modelo: {puestos} elecciones con fragmento,"
          f" {len(c.libreto)} parrafos de libreto")


if __name__ == "__main__":
    main()
