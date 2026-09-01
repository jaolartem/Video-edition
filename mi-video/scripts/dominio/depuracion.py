"""Los segundos que no aportan de un trozo ya elegido: aire, ensayo y tartamudeo.

Regla de Jaime, y señala el paso que faltaba: *«el filtro de la redundancia se
aplica después de escoger la escena; lo que no aporte, o los segundos que no
aporten, se deben borrar»*.

Tres cosas, y las tres se pueden **medir** — por eso viven en código y no en un
paso de IA:

- **El aire.** Un hueco sin una sola palabra no aporta nada, y esto es formato
  corto. Se corta por encima de `AIRE_MAX`, no por debajo: las pausas cortas son
  el ritmo del habla. Y se mide contra **las palabras**, no contra los tramos de
  habla — el detector marca por nivel de señal y en el reel 1 había 21,5 s de
  «habla» con dos palabras dentro.
- **El ensayo.** *«Se grabó así para poder escoger una buena entre estas»*
  (C-81). Cuando la misma idea vuelve, se elige la que más comunica; quedarse
  con la última es tan arbitrario como quedarse con la primera.
- **El tartamudeo.** «el el», «y es y es». Es lo que queda cuando ya se fue la
  repetición de frase, y es lo que se lee como error.

Lo que **no** vive aquí es la redundancia de sentido: *«no es algo que se pueda
inferir con código; necesitaríamos un modelo probabilístico de predicción de
lenguaje, que es exactamente lo que tenemos contigo»*. Eso es `redundancia.py`,
y este módulo no lo intenta.
"""
from __future__ import annotations

from . import vocabulario as _voc
from .tramo import Tramo

#: Por encima de esto el hueco no es ritmo: es tiempo muerto. En formato corto
#: medio segundo mirando una cara que no habla ya es una invitación a deslizar.
AIRE_MAX = 0.5
#: El margen que se deja alrededor de cada palabra para no comerse el ataque ni
#: el final de la consonante.
MARGEN = 0.12
#: Cuánto se tienen que parecer dos trozos para ser la misma idea dicha dos
#: veces, en trigramas de contenido compartidos sobre el más corto.
MISMA_IDEA = 0.6
#: Lo que la cabeza puede sobresalir por delante de la primera repetición para
#: seguir siendo un ensayo, y no el puente que hace que la frase siga.
CABEZA_MAX = 0.4


def enteras_en(palabras, a: float, b: float, margen: float = 0.01) -> list:
    """Las palabras que caben **enteras** entre `a` y `b`. La vara del corte.

    **No es la vara del oído, y la diferencia importa.** `Palabra.suena_en`
    contesta qué se oye —más de la mitad dentro basta— y es la buena para
    describir, subtitular o comparar lo que dice un tramo. Aquí se decide dónde
    poner la tijera, y para eso la palabra a medias no cuenta: cortar por su
    mitad es justo el defecto que se quiere evitar.

    Dos varas, dos nombres, cada uno con su trabajo escrito. Con un solo nombre
    acabarían siendo dos reglas llamadas igual — la avería que `dominio.texto`
    existe para no repetir.
    """
    return [p for p in palabras
            if a - margen <= p.empieza and p.acaba <= b + margen]


def corte(a: float, b: float, cinta: str = ""):
    """Un `Tramo` redondeado a milésimas, o `None` si no queda nada que cortar.

    Redondear puede juntar los dos extremos, y un tramo de duración cero no es
    un tramo: es un corte que no existe. Como lista pelada entraba igual en el
    EDL —`[x, x]`— y llegaba al render como un segmento de cero frames.
    """
    a, b = round(a, 3), round(b, 3)
    return Tramo(a, b, cinta) if b > a else None


# ── el aire ─────────────────────────────────────────────────────────────────
def con_voz(palabras, tramo: Tramo) -> list:
    """Parte el tramo en los trozos donde de verdad se dice algo."""
    ws = enteras_en(palabras, tramo.desde, tramo.hasta)
    if not ws:
        return []
    fuera = []
    ini, fin = max(tramo.desde, ws[0].empieza - MARGEN), ws[0].acaba
    for p in ws[1:]:
        if p.empieza - fin > AIRE_MAX:
            fuera.append(corte(ini, min(tramo.hasta, fin + MARGEN), tramo.cinta))
            ini = p.empieza - MARGEN
        fin = p.acaba
    fuera.append(corte(ini, min(tramo.hasta, fin + MARGEN), tramo.cinta))
    return [t for t in fuera if t is not None and t.dura > 0.25]


# ── el ensayo ───────────────────────────────────────────────────────────────
def podar_dentro(palabras, tramo: Tramo) -> Tramo:
    """Corta la repetición que ocurre DENTRO de un mismo trozo.

    Comparar trozos enteros no ve la frase que vuelve a empezar sin salir del
    corte. Se busca el n-grama de contenido repetido y se entra en la ÚLTIMA
    aparición — Jaime repite hasta que sale, así que lo de antes es el ensayo.

    **Y lo de antes es el ensayo sólo si lo de antes ES la cabeza.** Esto entraba
    en la última aparición y tiraba todo lo anterior, repitiera o no. En reel-01
    e2 el trigrama repetido era «terminan ganando mucho», y al entrar en el
    segundo se llevó **el puente**: la pieza pasaba de «espera que usted tenga
    una cierta estructura y» a «terminan ganando mucho», que no se sigue de
    nada. Jaime lo nombró: *«se recortaron pasos intermedios entre secciones y no
    secciones completas»*.

    La repetición de en medio no se pierde — la quita `sin_tartamudeo`, que corta
    el tramo duplicado y **conserva los dos lados**.
    """
    ws = enteras_en(palabras, tramo.desde, tramo.hasta)
    cont = [(i, _voc.contenido(p.texto)[0]) for i, p in enumerate(ws)
            if _voc.contenido(p.texto)]
    for n in (4, 3):
        for x in range(len(cont) - 2 * n + 1):
            g = [c[1] for c in cont[x:x + n]]
            for y in range(x + n, len(cont) - n + 1):
                if [c[1] for c in cont[y:y + n]] != g:
                    continue
                cabeza = ws[cont[x][0]].empieza - tramo.desde
                if cabeza > CABEZA_MAX:
                    continue
                nuevo = ws[cont[y][0]].empieza - MARGEN
                if nuevo - tramo.desde < 0.2 or tramo.hasta - nuevo < 0.8:
                    continue
                return corte(nuevo, tramo.hasta, tramo.cinta) or tramo
    return tramo


def _trigramas(t: str) -> list:
    w = _voc.contenido(t)
    return [tuple(w[i:i + 3]) for i in range(len(w) - 2)]


def sin_repetir(palabras, trozos):
    """Cuando la misma idea vuelve, se queda **la que mejor la dice**.

    Antes se quedaba la última, por regla. Jaime lo cortó: *«se escoge la que más
    comunique»*, *«pareciera que no hay criterio de selección»* — y no lo había.
    Y por qué importa que sobre una sola: *«una herramienta de énfasis como la
    repetición deja de ser útil cuando la utilizas todo el tiempo»*.

    Se compara por trigramas de contenido, no por palabras sueltas: repetir
    «que» no es repetir, y repetir «no es mala suerte» sí.

    Devuelve `(los que quedan, los índices que se van)`.
    """
    gramas = [set(_trigramas(t.texto_de(
        enteras_en(palabras, t.desde, t.hasta, margen=0.0)))) for t in trozos]
    familias = {}
    for i in range(len(trozos)):
        for j in range(i + 1, len(trozos)):
            gi, gj = gramas[i], gramas[j]
            if gi and gj and len(gi & gj) / min(len(gi), len(gj)) > MISMA_IDEA:
                raiz = familias.get(i, familias.get(j, i))
                familias[i] = familias[j] = raiz

    def entrega(k: int) -> float:
        """Lo que comunica ese trozo. El mismo criterio con el que se eligió la toma.

        Medir cuatro trozos de dos segundos es gratis y aquí ya estamos en el
        peldaño caro. Sin cinta no hay con qué medir y manda el último, que es
        el comportamiento de antes.
        """
        t = trozos[k]
        if not t.cinta:
            return float(k)
        if t.dura < 0.6:
            return -1.0
        import beats

        try:
            # Lo no medido no suma cero: se cae del sumatorio.
            _e = beats.expresividad(t.cinta, t.desde, t.hasta)
            _c = beats.cambio_de_tono(t.cinta, t.desde, t.hasta)
            return ((float(_e) if _e is not None else 0.0)
                    + (float(_c) / 10.0 if _c is not None else 0.0))
        except Exception:                          # noqa: BLE001
            return float(k)

    grupos = {}
    for k, raiz in familias.items():
        grupos.setdefault(raiz, set()).add(k)
    quitar = set()
    for miembros in grupos.values():
        if len(miembros) > 1:
            quitar |= miembros - {max(miembros, key=entrega)}
    return [t for k, t in enumerate(trozos) if k not in quitar], quitar


# ── el tartamudeo ───────────────────────────────────────────────────────────
def sin_tartamudeo(palabras, tramo: Tramo) -> list:
    """Quita la palabra repetida de seguido: «el el», «y es y es», «que uno que uno».

    Se corta la PRIMERA aparición y se deja la segunda, que es la que sigue la
    frase. El trozo se parte en dos y se salta el tramo duplicado; los 50 ms de
    fundido por escena que ya aplica el corte tapan la costura.

    No toca la repetición con intención: «de cada 100 dólares que ÉL recibe… de
    cada 100 que USTED recibe» no es de seguido, así que no entra aquí.
    """
    ws = enteras_en(palabras, tramo.desde, tramo.hasta)
    cont = [(i, _voc.palabras(p.texto)[0]) for i, p in enumerate(ws)
            if _voc.palabras(p.texto)]
    cortes, k = [], 0
    while k < len(cont) - 1:
        # **Dos palabras iguales que se pisan en el tiempo no son un
        # tartamudeo: son la misma palabra contada dos veces.** El transcript
        # sale de varias pasadas y a veces deja la misma palabra duplicada con
        # tiempos solapados; tratarla como repetición corta el audio donde sólo
        # había UNA palabra, y la palabra desaparece. Así se fue el «20 dolares»
        # que cerraba la urgencia del reel 1 (C-64).
        pisadas = ws[cont[k + 1][0]].empieza < ws[cont[k][0]].acaba - 0.01
        if pisadas:
            k += 1
            continue
        largo = 0
        if cont[k][1] == cont[k + 1][1]:
            largo = 1
        elif (k + 3 < len(cont) and cont[k][1] == cont[k + 2][1]
              and cont[k + 1][1] == cont[k + 3][1]):
            largo = 2                              # un par repetido: «y es y es»
        if largo:
            # **El margen no puede comerse la palabra anterior.** `MARGEN` existe
            # para no cortar el ataque de la consonante, pero restado a secas
            # mete el corte dentro de la palabra de antes — y en habla rápida esa
            # palabra dura menos de 0,12 s. Así desaparecieron «CRA» delante de
            # «56 56», el «mas» delante de «que uno que uno» y «20 dolares»
            # delante de «luego sube luego sube».
            ini = ws[cont[k][0]].empieza - MARGEN
            if k:
                fin_previa = ws[cont[k - 1][0]].acaba
                ini = max(ini, fin_previa + 0.01)
            fin = ws[cont[k + largo - 1][0]].acaba
            cortes.append((max(tramo.desde, ini), min(tramo.hasta, fin + 0.02)))
            k += largo
        k += 1
    if not cortes:
        return [tramo]

    def con_palabra(x, y):
        """¿Sobrevive alguna palabra en este trozo?"""
        return bool(enteras_en(ws, x, y))

    # **Un trozo con una palabra dentro no se tira, dure lo que dure.** Esto
    # descartaba todo lo que quedara por debajo de 0,25 s, y ahí caben palabras
    # cortas que llevan TODO el peso de la frase: sin el «mas» la comparación se
    # invierte, sin «CRA» la cifra no tiene quien la cobre, sin «20 dolares» la
    # urgencia no cierra. La poda puede quitar repetición — nunca información.
    fuera, cursor = [], tramo.desde
    for x, y in cortes:
        if con_palabra(cursor, x) or x - cursor > 0.25:
            fuera.append(corte(cursor, x, tramo.cinta))
        cursor = max(cursor, y)
    if con_palabra(cursor, tramo.hasta) or tramo.hasta - cursor > 0.25:
        fuera.append(corte(cursor, tramo.hasta, tramo.cinta))
    return [t for t in fuera if t is not None] or [tramo]
