"""Lo que la pieza dice **dos veces**, y no debería.

Regla de Jaime, que es la que separa el énfasis del ruido:

> *«La redundancia o es explícita en el libreto, o es continua en la grabación;
> pero dejar énfasis cada corte no es énfasis sino ruido.»*

Así que una repetición vale cuando el guion la pide —está dos veces en el
libreto— y no vale cuando la produjo el montaje. Lo que aparece aquí es lo
segundo: n-gramas que suenan dos veces en la pieza y una sola vez en el libreto.

Existía `repeticiones.py` y hacía justo esto, pero **no lo llamaba nadie**: un
paso que depende de que alguien se acuerde no es un paso.

**Y la entrega se mide, pero que sea énfasis no se decide aquí.** Regla de
Jaime: *«lo de énfasis legítimo no se mide con código, se mide en las revisiones
del agente»*, y la que la ordena: *«con el contrato; no es tu papel juzgarlo, ni
arreglar algo que el código no puede arreglar»*. Este número llegó a ser un voto
—si la mejor destacaba, el grupo se daba por énfasis y desaparecía del informe—
y eso es el código absolviendo: 20 de 37 grupos se caían antes de que nadie
leyera la frase. Aquí la intensidad viaja como **prueba**, al lado del texto.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import vocabulario as _voc  # noqa: E402
from .guion import Guion  # noqa: E402


#: El tartamudeo pegado —«eso, eso»— es de dos palabras, y con tríos no se ve.
#: Jaime lo cazó a ojo en el segundo 8 del reel-01 después de que la pieza pasara
#: todas las puertas: *«segundo 8 otra vez repite eso, eso, inoficioso»*.
#:
#: Se busca aparte y sólo **pegado** (`separadas_por == 0`), que es lo que lo
#: distingue de una palabra que vuelve más tarde por buenas razones. Con dos
#: palabras y separación, casi cualquier pieza repetiría algo.
PEGADO = 2


def repetido(montaje, n: int = 3) -> list:
    """Los n-gramas que la pieza dice más de una vez, con la prueba al lado.

    **La regla de qué se perdona, y es de Jaime, literal:** *«para repeticiones
    la regla establecida era cumplir dos de tres características; la primera
    completamente obligatoria, que es que esté en la misma toma; la segunda que
    esté en el libreto; y la tercera que aporte a la construcción de un
    punchline — no sólo que no sea redundante, sino que la repetición sirva como
    punchline»*.

    De las tres, dos son hechos y una es criterio. `una_toma` y `en_libreto` se
    miden aquí. El punchline no: eso hay que entenderlo, así que lo que sale de
    aquí sin las dos primeras **se señala** y lo decide quien compone.

    Y la primera siendo obligatoria quiere decir que una repetición que cruza dos
    tomas se corta sin más pregunta: no la salva ni el libreto ni el remate.
    """
    import beats

    pares = montaje.tramos()
    # Las palabras de la pieza, en orden de montaje, cada una con **de qué trozo
    # viene**. Ese índice es lo que decide: si las dos veces caen en el mismo
    # trozo, el hablante lo dijo así de seguido.
    seq = []
    for k, (t, d) in enumerate(pares):
        for p in montaje.dentro(t):
            for w in _voc.palabras(p.texto):
                seq.append((w, k, d.get("beat"), p.empieza, p.acaba, t.cinta))
    guion = Guion(montaje.slug)

    gramas = {}
    for i in range(len(seq) - n + 1):
        gramas.setdefault(" ".join(x[0] for x in seq[i:i + n]), []).append(i)

    fuera = []
    for g, sitios in gramas.items():
        if len(sitios) < 2:
            continue
        # **Se repite más de dos veces, y por eso no se comparan dos: se miden
        # todas.** Jaime: *«usualmente se repite más de dos veces»*, y ésa es la
        # razón de que la cinta sea un abanico — *«se grabó así para poder
        # escoger una buena entre estas»* (C-81). Elegir «la segunda» sería tan
        # arbitrario como elegir la última.
        veces = [_medida(pares, seq[k0:k0 + n], beats) for k0 in sitios]
        for v in veces:
            # **El `try` va por medida, no por grupo.** Envolviendo el bucle, una
            # ventana que no se puede medir dejaba sin medir a todas las demás
            # del grupo — un fallo se convertía en ausencia de pruebas, y la
            # ausencia de pruebas se leía como prueba.
            try:
                # Con las palabras: sin ellas `velocidad` es siempre `None` y la
                # intensidad se queda con media dimensión de las dos que tiene.
                m = beats.intensidad(v["toma"], v["mide_desde"], v["mide_hasta"],
                                     montaje.crudas(v["toma"])) or {}
            except Exception:                      # noqa: BLE001
                continue
            v["intensidad"] = (round(float(m["intensidad"]), 2)
                               if m.get("intensidad") is not None else None)
        medidas = [v for v in veces if v["intensidad"] is not None]
        beat = seq[sitios[0]][2]
        una_toma = len({v["trozo"] for v in veces}) == 1
        en_libreto = " ".join(
            _voc.palabras(guion.texto(beat))).count(g) >= len(sitios)

        # Lo único que se resuelve por aritmética es la regla de Jaime, literal:
        # *«la redundancia o es explícita en el libreto, o es continua en la
        # grabación»*. Las dos son hechos comprobables —el mismo trozo, y el
        # libreto pidiéndola esas veces—, no lecturas de intención.
        if una_toma and en_libreto:
            continue
        mejor = max(medidas, key=lambda v: v["intensidad"]) if medidas else None
        fuera.append({
            "etapa": beat, "dice": g, "veces": len(sitios),
            "separadas_por": sitios[1] - sitios[0] - n,
            "trozos": sorted({v["trozo"] for v in veces}),
            "motivo": _motivo(len(sitios), una_toma, medidas),
            "en_libreto": en_libreto, "una_toma": una_toma, "tomas": veces,
            # **Siempre lo decide quien compone.** Esto valía `not medidas`, o
            # sea «sólo cuando el código no supo»; con lo anterior el código sí
            # creía saber, y por eso absolvía.
            "decide_quien_compone": True,
            # La que más entrega de las medidas. Es una **pista para quien
            # decide**, no la elegida: cuál se queda depende de qué dice cada
            # una, y eso no está aquí.
            "se_queda": (None if mejor is None else
                         {"empieza": mejor["empieza"], "acaba": mejor["acaba"],
                          "intensidad": mejor["intensidad"]})})
    # **Y el tartamudeo pegado, que con trios no se ve.**
    #
    # «eso, eso» son dos palabras y `n` vale 3, asi que ninguna puerta lo miraba.
    # Se busca sobre la misma secuencia ya construida, sin volver a leer nada, y
    # solo cuando las dos apariciones son consecutivas: eso es un rearranque del
    # hablante, no una palabra que vuelve.
    if n > PEGADO:
        for i in range(len(seq) - PEGADO * 2 + 1):
            a = [x[0] for x in seq[i:i + PEGADO]]
            b = [x[0] for x in seq[i + PEGADO:i + PEGADO * 2]]
            if a != b:
                continue
            beat = seq[i][2]
            trozos = {seq[k][1] for k in range(i, i + PEGADO * 2)}
            g = " ".join(a)
            en_libreto = " ".join(
                _voc.palabras(guion.texto(beat))).count(g) >= 2
            # La misma regla: la misma toma es obligatoria y no basta sola.
            if len(trozos) == 1 and en_libreto:
                continue
            fuera.append({
                "etapa": beat, "dice": g, "veces": 2, "separadas_por": 0,
                "trozos": sorted(trozos),
                "motivo": "lo dice dos veces pegado — rearranque del hablante,"
                          " y no lo salva estar en la misma toma: esa es la"
                          " condicion de entrada, no el permiso",
                "en_libreto": en_libreto, "una_toma": len(trozos) == 1,
                "tomas": [], "decide_quien_compone": True, "mejor": None,
                "pegado": True,
            })

    return fuera


def _medida(pares, tramo, beats) -> dict:
    """Dónde se mide esa aparición: **la frase con el aire que la medida exige**.

    Un trigrama dura 0,675 s de mediana y el contorno no devuelve nada por debajo
    de `beats.VENTANA_MIN`. Midiendo las tres palabras sueltas, 52 de 78
    apariciones salían sin medir y 19 de los 37 grupos decidían sin una sola
    medida — y «no medido» llegaba al consumidor como `destaca = False`, o sea
    como «esto es ruido del corte», que es una conclusión que nadie sacó.

    Se crece a los dos lados hasta el mínimo y **se recorta al propio trozo**,
    que es lo que garantiza que no cruce una costura ni se meta en otra toma: se
    mide como suena, no como se cortó.
    """
    trozo = tramo[0][1]
    ini, fin = round(tramo[0][3], 2), round(tramo[-1][4], 2)
    corte = pares[trozo][0]
    falta = beats.VENTANA_MIN - (fin - ini)
    if falta > 0:
        ini, fin = ini - falta / 2, fin + falta / 2
        if ini < corte.desde:
            ini, fin = corte.desde, corte.desde + beats.VENTANA_MIN
        if fin > corte.hasta:
            ini = max(corte.desde, corte.hasta - beats.VENTANA_MIN)
            fin = corte.hasta
    return {"empieza": round(tramo[0][3], 2), "acaba": round(tramo[-1][4], 2),
            "mide_desde": round(ini, 2), "mide_hasta": round(fin, 2),
            "trozo": trozo, "toma": tramo[0][5], "intensidad": None}


def _motivo(veces: int, una_toma: bool, medidas: list) -> str:
    if not una_toma:
        return f"se dice {veces} veces cruzando cortes"
    if not medidas:
        return f"se dice {veces} veces y no se pudo medir la entrega"
    return (f"se dice {veces} veces y el libreto la pide una"
            f" (entrega {[v['intensidad'] for v in medidas]}):"
            f" si es enfasis o sobra, lo dice quien lee la frase")
