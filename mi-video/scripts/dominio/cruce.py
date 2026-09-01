"""Lo que se repite **cruzando el corte**, apuntado y no cortado.

Tercer sitio de la regla que el proyecto tiene escrita —dentro de la ventana,
cruzando el corte, y el mismo dato en dos etapas (C-58)— y el único donde la
aritmética no llega. Jaime lo cazó dos veces en la misma pieza: *«en el segundo
55 "esto es diferente" sobra, acabas de decir "yo soy diferente aca no hacemos
eso", redundancia de nuevo»*.

**Y ya no corta: apunta.** Regla de Jaime, la misma de C-88: *«la solución es que
el detector apunte y tú decidas caso a caso, sin degradar el esfuerzo que
haces»*. Cortaba hasta la palabra repetida incluida, y esa palabra puede ser la
unidad de dos cifras distintas: en reel-01 e7 la cola decía «550 dólares,
semanales» y la cabeza «Esta semana el bootcamp está en 20 dólares», y la regla
se llevó **el precio de la oferta**. El corte cayó en 584,78: exacto, y
exactamente equivocado.

Saber si «dólares» repetido es redundancia o son dos cifras exige entender la
frase. Se anota y lo resuelve quien compone, que tiene el texto de las dos etapas
delante.

*(`dominio.costura` mira la misma unión con otra pregunta —si el empalme se
oye—; si algún día las dos se piden juntas, ese es el objeto donde caben.)*
"""
from __future__ import annotations

from . import vocabulario as _voc
from .depuracion import MARGEN, enteras_en
from .tramo import Tramo

#: Una palabra de contenido: lo bastante larga como para que repetirla signifique
#: algo. «diferente» sí; «es», «no», «que» no. Cinco letras es donde cae la raya
#: en castellano sin necesitar lista de vacías.
CONTENIDO = 5
#: Cuántas palabras se miran a cada lado de la costura. Diez es una frase corta:
#: más allá, repetir una palabra ya no se oye como repetición.
BORDE = 10
#: Lo que tiene que quedar de la cabeza para que valga la pena proponer el corte.
RESTO_MIN = 0.8


def _clave(p) -> str | None:
    """La palabra de contenido de esa `Palabra`, o `None` si no distingue nada."""
    ws = _voc.contenido(p.texto)
    return ws[0] if ws else None


def repite_en_el_corte(cola: Tramo, palabras_cola,
                       cabeza: Tramo, palabras_cabeza):
    """Dónde arrancaría la cabeza si se quitara lo que repite. `None` si nada.

    No busca trigramas: «yo soy diferente» y «esto es diferente» no comparten
    ninguno. Busca **una palabra de contenido repetida cerca de la costura**, que
    es lo que se oye como repetición aunque la frase sea otra.

    **Cada lado trae las palabras de SU cinta.** Antes entraba una sola lista y se
    filtraba con los tiempos de los dos tramos: cuando la costura une dos
    grabaciones —que es de donde sale el escalón del precio— uno de los dos lados
    salía vacío o, peor, con las palabras que sonaban a esos segundos en la cinta
    que no era.
    """
    fin = enteras_en(palabras_cola, cola.desde, cola.hasta)
    ini = enteras_en(palabras_cabeza, cabeza.desde, cabeza.hasta)
    if not fin or not ini:
        return None
    antes = {c for c in (_clave(p) for p in fin[-BORDE:])
             if c and len(c) >= CONTENIDO}
    if not antes:
        return None
    for p in ini[:BORDE]:
        if _clave(p) in antes:
            # Se cortaría HASTA esa palabra incluida: lo que repite se va y la
            # frase arranca en lo que aporta. Y sólo si queda pieza al otro lado.
            nuevo = round(p.acaba + MARGEN, 3)
            return nuevo if cabeza.hasta - nuevo > RESTO_MIN else None
    return None


def cruces(montaje) -> list:
    """Las costuras donde algo se repite: la etapa, los dos lados y hasta dónde.

    Lo resuelve quien compone, que tiene el texto de las dos etapas delante.
    """
    fuera, pares = [], montaje.tramos()
    for (t0, _), (t1, d1) in zip(pares, pares[1:]):
        ws1 = montaje.palabras(t1.cinta)
        nuevo = repite_en_el_corte(t0, montaje.palabras(t0.cinta), t1, ws1)
        if nuevo is None:
            continue
        fuera.append({
            "etapa": d1.get("beat"),
            "cola": montaje.texto(t0)[-70:],
            "repite": Tramo(t1.desde, nuevo, t1.cinta).texto_de(ws1),
            "cortaria_hasta": nuevo,
        })
    return fuera
