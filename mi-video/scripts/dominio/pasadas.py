"""Qué hacer con lo que devuelve el modelo cuando se le pregunta varias veces.

**Por qué existe.** Transcribir la misma ventana cuatro veces no da cuatro
respuestas iguales: da una buena, dos parecidas y a veces una alucinada. Elegir
entre ellas es un trabajo con reglas propias —etiquetas que el modelo se
inventa, texto que se repite porque se quedó pegado, la votación entre pasadas—
y no tiene nada que ver con arrancar whisper ni con escribir el fichero.

Estaba dentro de `transcribir.py`, mezclado con las otras cuatro cosas que hace
ese paso. Aquí es lo único que hay.
"""
from __future__ import annotations

import difflib
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import registro  # noqa: E402


def sin_etiquetas(ws):
    """Quita las etiquetas de sonido, que con `-ml 1` vienen partidas.

    `[Sonido de la puerta abriendo]` no llega como un token: llega como seis, y
    solo el primero abre y el ultimo cierra. Filtrar palabra a palabra dejaba
    pasar las cuatro de en medio — que es peor que no filtrar, porque el
    subtitulo sale diciendo «Sonido de la puerta» como si Jaime lo hubiera
    dicho. Trece de estas habia en el reel 1.

    Asi que se filtra por ESTADO: desde el token que abre corchete hasta el que
    cierra, todo fuera. Y se cierra sola a las ocho palabras por si el modelo
    abrio y no cerro, que si no se comeria el resto de la ventana.
    """
    out, dentro = [], 0
    for w in ws:
        t = w["t"].strip()
        if dentro:
            dentro -= 1
            if t.endswith("]") or t.endswith(")") or t.endswith("*"):
                dentro = 0
            continue
        if t.startswith("[") or t.startswith("(") or t.startswith("*"):
            # **El modelo tambien anota con asteriscos.** `*sonido de caja*`
            # entro entero en el reel 1 por la puerta que dejaba el filtro:
            # miraba corchete y parentesis y nada mas, asi que la anotacion
            # salia en el subtitulo como si Jaime la hubiera dicho. Aparecio
            # justo donde el afinado tapo un hueco, que es donde el modelo se
            # inventa cosas: no tiene habla que transcribir y rellena.
            dentro = (0 if (t.endswith("]") or t.endswith(")")
                            or (t.startswith("*") and t.endswith("*") and len(t) > 1))
                      else 8)
            continue
        out.append(w)
    return out


def sin_fantasmas(ws):
    """Quita la palabra duplicada que **no tiene audio propio que cortar**.

    El transcript sale de fundir varias pasadas y deja dos formas de duplicado
    que ninguna tijera puede arreglar, porque el problema no esta en el audio:

    - **La de duracion cero.** `Revise,` de 590.664 a 590.664, pegada a
      `revise`. `sin_tartamudeo` la detecta y corta su tramo — que mide cero
      segundos, o sea no corta nada — y la palabra sigue en el texto. El
      subtitulo dice «Revise, revise» para siempre.
    - **La que se pisa con su gemela.** `cuenta` 591.354-591.962 y `cuenta`
      591.744-593.276. Ahi el cinturon de C-64 hace bien en no cortar —es UNA
      palabra oida dos veces, y cortarla la borraria— pero se limita a no
      tocarla, y el texto sigue diciendo «cuenta cuenta».

    Las dos veces el fallo es el mismo: se trato como problema de montaje algo
    que es un defecto del transcript. Aqui se arregla donde esta, fundiendo las
    dos en una que abarca de la primera a la ultima.

    No toca la repeticion de verdad —«luego sube, luego sube» son dos tramos
    separados y con audio cada uno—: eso lo decide quien monta, no esto.
    """
    from transcribir import beats_palabras

    out = []
    for w in sorted(ws, key=lambda x: (x["start"], x["end"])):
        p = beats_palabras(w["text"])
        q = beats_palabras(out[-1]["text"]) if out else None
        if p and q and p[0] == q[0]:
            hueco = w["start"] - out[-1]["end"]
            cero = (w["end"] - w["start"] <= 0.001
                    or out[-1]["end"] - out[-1]["start"] <= 0.001)
            if cero or hueco < -0.01:
                # Una sola palabra, del arranque mas temprano al final mas
                # tardio: asi el corte que la use la abarca entera.
                out[-1] = dict(out[-1],
                               start=min(out[-1]["start"], w["start"]),
                               end=max(out[-1]["end"], w["end"]),
                               text=(w["text"] if len(w["text"]) >= len(out[-1]["text"])
                                     else out[-1]["text"]))
                continue
        out.append(w)
    return out


def atascado(palabras):
    """El modelo repitiendo el mismo trigrama es el modelo pegado."""
    ws = [w["t"].lower() for w in palabras]
    if len(ws) < 6:
        return False
    for n in (3, 4):
        for i in range(len(ws) - 2 * n + 1):
            if ws[i:i + n] == ws[i + n:i + 2 * n]:
                return True
    return False


def etiqueta(txt):
    """Lo que el modelo escribe ENTRE CORCHETES no es habla.

    En el reel 1 salieron trece `[Sonido de la puerta abriendo]` y en el 3 un
    `[SILENCIO]`. Es la misma familia que «Gracias por ver el video» —relleno
    aprendido de video subtitulado— pero por otra puerta: aquella se filtraba
    por su texto y esta no se filtraba en absoluto, asi que **acababa en un
    subtitulo**, que es portante.

    Se quita la palabra, no la ventana: alrededor de la etiqueta suele haber
    habla real.
    """
    return bool(re.match(r"^[\[\(].*[\]\)]$", txt.strip())
                or txt.strip() in ("[", "]", "(", ")"))


def alucinado(texto):
    from transcribir import ALUCINACIONES, limpio

    t = " ".join(limpio(texto))
    return any(a.replace(".", "") in t for a in
               (" ".join(limpio(x)) for x in ALUCINACIONES))


def _recuerda(c, otra):
    """Cuánto de lo que oyó la otra pasada está también en ésta."""
    from transcribir import limpio

    b = limpio(otra["texto"])
    if not b:
        return 1.0
    a = limpio(c["texto"])
    sm = difflib.SequenceMatcher(None, a, b)
    return sum(bl.size for bl in sm.get_matching_blocks()) / len(b)


def medoide(cands):
    """La que recoge lo que oyeron las demás, sin inventar lo que nadie oyó.

    El parecido simétrico —`ratio()`— no sirve aquí y costó una palabra real:
    entre «porque le duele una muela no» y «porque le duele no» las dos se
    parecen lo mismo la una a la otra, así que el desempate lo decidía la
    distancia al borde y ganó la que se comió «una muela».

    Lo que de verdad distingue una pasada buena de una que se comió algo es
    **asimétrico**: una palabra que oyeron las otras y ésta no es una palabra
    comida; una que sólo oyó ésta es una palabra inventada. Así que se puntúa
    con las dos cosas —lo que recoge de las demás, menos lo que no confirma
    ninguna—, que es exactamente para lo que sirven varias pasadas.

    Los bucles ya no llegan aquí: `atascado()` y `alucinado()` los tiraron antes.
    """
    from transcribir import limpio

    if len(cands) == 1:
        # **Con una sola pasada no hay acuerdo: hay ausencia de discrepancia.**
        # Devolver 1,0 hacia que el barrido barato —una pasada— saliera con
        # «0 tramos por oir» y acuerdo perfecto, o sea que el peldaño menos
        # fiable se presentaba como el mas fiable. `None` dice lo que hay: no
        # se ha podido comprobar.
        return cands[0], None
    mejor, mejor_p, acuerdo = None, -1e9, 0.0
    for c in cands:
        otras = [o for o in cands if o is not c]
        recoge = sum(_recuerda(c, o) for o in otras) / len(otras)
        # Palabras que no confirma ninguna otra pasada: invencion del modelo.
        mias = set(limpio(c["texto"]))
        suyas = set()
        for o in otras:
            suyas |= set(limpio(o["texto"]))
        sola = len(mias - suyas) / max(1, len(mias))
        p = recoge - 0.35 * sola - 0.10 * c["borde"]
        if p > mejor_p:
            mejor, mejor_p, acuerdo = c, p, recoge
    return mejor, round(acuerdo, 3)
