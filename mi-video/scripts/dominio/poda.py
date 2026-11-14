"""Lo que se dice dos veces **dentro de una unidad**, y cómo se quita.

Regla de Jaime: *«correctivos para la redundancia, y mas cuando lo que se dice es
directamente contradictorio»*. Y la regla del proyecto: nada se dice dos veces —
la redundancia se **recorta**, no se penaliza.

Aquí viven las dos tijeras que no necesitan entender la frase:

- `podar` quita una racha repetida dentro de una misma unidad;
- `unir` pega dos frases seguidas de la misma toma quitando la cola de la
  primera que la segunda vuelve a decir.

Lo que **no** vive aquí es decidir si dos ideas distintas dicen lo mismo: eso
exige leer, y cuando el código lo intentó dejó la pieza más larga que antes.
"""
from __future__ import annotations

import re

from . import vocabulario as _voc
from .candidata import dice


def podar(u, exige=(), idioma=None):
    """Quita las repeticiones de DENTRO de una unidad.

    ## Que cuenta como repeticion

    Una racha de tres palabras o mas que vuelve a aparecer mas adelante en la
    misma unidad. Vale igual si **una palabra cambia** -«se queda con 64» y «se
    queda con 67»-, que es el caso peor: dos cifras para el mismo hueco es
    informacion contradictoria en pantalla.

    ## Cual se queda: la que sigue diciendo algo

    La primera version miraba solo repeticiones **pegadas**, y el habla real no
    repite asi: en el reel 3, «usted tiene un contador y se queja de que paga
    mucho impuesto» vuelve **diez palabras despues**, con la frase clave del beat
    en medio. Pegado no habia nada, asi que no podaba nada y la pieza decia la
    tesis tres veces.

    Y no vale quedarse siempre con la ultima. Aqui la buena es la PRIMERA,
    porque detras lleva *«pero nunca le ha preguntado al contador por que»* —el
    giro que hace la tesis— y la ultima no lleva nada detras: es un rearranque.

    Asi que la regla es: **se queda la aparicion que va seguida de mas material
    nuevo**, y las otras se van con lo que arrastran hasta la siguiente. Cubre
    los dos casos con el mismo criterio -en «64 / 67» gana la segunda, porque es
    la que continua la frase- y no depende de adivinar cual quiso decir.
    """
    # **Solo lo que de verdad queda de la unidad.** `pal` son las palabras de la
    # frase entera, y para entonces ya se le pudo aplicar un recorte declarado
    # (`entra_en` / `sale_en`). Sin acotar, la poda proponia tramos fuera del
    # recorte y **deshacia una decision de oido** — en el reel 3 devolvia el
    # precio que se acababa de recortar a proposito.
    pal = [w for w in (u.get("pal") or [])
           if w[0] >= u["a"] - 0.05 and w[1] <= u["b"] + 0.05]
    if len(pal) < 8:
        return None
    tok = []
    for w in pal:
        t = _voc.contenido(w[2], idioma)
        tok.append(t[0] if t else "")
    esnum = [bool(re.search(r"\d", w[2])) for w in pal]

    def igual2(vivos, x, y, n):
        """Igual que `igual`, pero sobre las posiciones que siguen vivas."""
        return igual(vivos[x], vivos[y], n, [vivos[x + k] for k in range(n)],
                     [vivos[y + k] for k in range(n)])

    def igual(i, j, n, ii=None, jj=None):
        # **La racha tiene que decir algo.** Con puras palabras de funcion
        # -«es para usted»- cualquier frase repite: en el reel 3 eso se llevo
        # por delante el remate del registro. Se exigen dos palabras de
        # contenido dentro de la racha.
        ii = ii or [i + k for k in range(n)]
        jj = jj or [j + k for k in range(n)]
        # **Si la racha lleva una cifra, con dos palabras basta.**
        #
        # Jaime: *«repites demasiadas veces 21 dolares... lo mismo con 189.000...
        # el libreto marca una sola, no dos»*. «21 dolares, 21 dolares» son dos
        # palabras y el suelo general son cuatro, asi que pasaba entera. Una
        # cifra repetida no es enfasis: es el hablante afianzandose, y en
        # pantalla queda como tartamudeo.
        #
        # El suelo alto sigue para lo demas, que es lo que evita que «es para
        # usted» se lea como repeticion.
        concifra = any(esnum[k] for k in ii)
        if not concifra and sum(1 for k in ii if len(tok[k]) > 3) < 2:
            return False
        # **La cifra distinta solo vale como autocorreccion inmediata.**
        #
        # Con tolerancia numerica libre, «se queda con 44» y «se queda con 67»
        # cuentan como la misma racha — y son **las dos caras de la
        # comparacion**, no una repeticion. La poda se llevaba 18 s del reel 2 y
        # con ellos el 67.
        #
        # Una autocorreccion se dice pegada («con 64, el se queda con 67»); dos
        # datos distintos van separados y con material en medio. Asi que el
        # numero distinto solo se admite si las dos rachas estan a menos de su
        # propio largo de distancia, y en rachas de cuatro palabras o mas.
        pegadas = (jj[0] - ii[0]) <= max(n, 4)
        distinto = 0
        for ka, kb in zip(ii, jj):
            if tok[ka] == tok[kb]:
                continue
            if esnum[ka] and esnum[kb] and n >= 4 and pegadas:
                distinto += 1
                continue
            return False
        return distinto <= 1

    # **Se poda hasta que no quede ninguna, no una y a otra cosa.**
    #
    # La primera version quitaba **la repeticion mas larga** y paraba. Y una
    # unidad real trae varias: en el reel 2, *«esa diferencia, esta diferencia,
    # 21 dolares, 21 dolares cada 100 dolares que recibe, cinco anos son 189 mil
    # dolares, 189 mil dolares, 189 mil dolares que el electricista trabajo»*
    # lleva tres. Jaime: *«repites demasiadas veces 21 dolares... lo mismo con
    # 189.000... repeticion redundante e inoficiosa»*.
    vivos = list(range(len(pal)))
    fuera = []
    for _ in range(8):
        mejor = None
        m = len(vivos)
        for n in range(min(12, m // 2), 1, -1):
            for x in range(m - 2 * n + 1):
                for y in range(x + n, m - n + 1):
                    if igual2(vivos, x, y, n):
                        mejor = (x, y, n)
                        break
                if mejor:
                    break
            if mejor:
                break
        if not mejor:
            break
        x, y, n = mejor

        def nuevas(desde, hasta):
            vistas = {tok[vivos[k]] for k in range(desde) if len(tok[vivos[k]]) > 3}
            return len({tok[vivos[k]] for k in range(desde, hasta)
                        if len(tok[vivos[k]]) > 3} - vistas)

        # Se queda la aparicion que va seguida de mas material nuevo.
        if nuevas(x + n, y) >= nuevas(y + n, m):
            quita = list(range(y, m))
        else:
            quita = list(range(x, y))
        # **Nunca se poda lo que la etapa tiene que decir.** Si el trozo que
        # tocaria quitar lleva la cifra declarada, se prueba con la otra
        # aparicion; y si tampoco, esta repeticion se deja estar. Limpiar no es
        # elegir: entre quitar una repeticion y quitar el dato, se queda el dato.
        def sobrevive(ks):
            """Lo que la etapa debe decir sigue estando despues de quitar `ks`."""
            fuera_ = set(ks)
            queda = " ".join(pal[vivos[k]][2] for k in range(m) if k not in fuera_)
            return all(dice(queda, e) for e in exige)
        # **Se poda si lo declarado SOBREVIVE, no si el trozo lo contiene.**
        #
        # La version anterior rechazaba quitar el trozo en cuanto llevaba la
        # palabra declarada — y eso es justo lo que pasa al quitar una
        # repeticion: las dos copias la llevan. Resultado: «y si usted no sabe
        # que pedir, pues nadie se lo va a ofrecer solo» se decia dos veces
        # seguidas en el reel 3 porque la etapa declaraba «pedir».
        #
        # Lo que hay que garantizar es que **quede dicho**, no que no se toque.
        if exige and not sobrevive(quita):
            otro = list(range(x, y)) if quita[0] == y else list(range(y, m))
            if not sobrevive(otro):
                break
            quita = otro
        fuera.append((vivos[quita[0]], vivos[quita[-1]] + 1))
        vivos = [v for k, v in enumerate(vivos) if k not in set(quita)]
    if not fuera:
        return None
    fuera.sort()
    # Se funden los tramos que se tocan, para no partir de mas.
    unidos = [list(fuera[0])]
    for a_, b_ in fuera[1:]:
        if a_ <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], b_)
        else:
            unidos.append([a_, b_])
    fuera = [tuple(t) for t in unidos]

    tramos, ini = [], 0
    for a_, b_ in fuera:
        if a_ > ini:
            tramos.append([round(pal[ini][0], 3), round(pal[a_ - 1][1], 3)])
        ini = b_
    if ini < len(pal):
        tramos.append([round(pal[ini][0], 3), round(u["b"], 3)])
    if not tramos:
        return None
    quitado = sum(pal[min(b_, len(pal)) - 1][1] - pal[a_][0] for a_, b_ in fuera)
    return tramos, round(quitado, 2), " ".join(
        " ".join(w[2] for w in pal[a_:b_]) for a_, b_ in fuera)


def unir(u1, u2, idioma=None):
    """Dos frases seguidas de la misma toma, como una sola unidad.

    Regla de Jaime: *«a la frase 5 quitale "por cada 100 dolares" en adelante,
    es completamente redundante con la frase 6; la redundancia hay que
    evitarla»*.

    Y no hace falta escribir donde cortar: **se deriva**. Se recorre la cola de
    la primera de atras adelante y se corta en la ultima palabra cuyo contenido
    ya no este en la segunda. En el reel 2 eso deja la [5] en «...y que tiene
    yate en el lago Muscoca,» y tira «por 100 dolares, por cada 100 dolares que
    el recibe,», que es exactamente lo que la [6] vuelve a decir.

    El corte es por palabra y con su tiempo, asi que la union sigue siendo un
    tramo continuo de la misma toma: no se cose nada.
    """
    wb = set(_voc.contenido(u2["texto"], idioma))
    pal = u1["pal"]
    corte = len(pal)
    for i in range(len(pal) - 1, 3, -1):
        toks = _voc.contenido(pal[i][2], idioma)
        if toks and not set(toks) <= wb:
            break
        corte = i
    fin = pal[corte - 1][1] if corte < len(pal) else u1["b"]
    txt = " ".join(w[2] for w in pal[:corte]).strip() + " " + u2["texto"]
    # **Dos tramos, no uno continuo.** El hueco entre el corte y el arranque de
    # la segunda es justo lo redundante, asi que tiene que quedarse fuera del
    # montaje: si se emite el tramo entero, la cola repetida vuelve a sonar y no
    # habriamos quitado nada.
    return {**u2, "a": u1["a"], "b": u2["b"], "corte_uno": round(fin, 3),
            "tramos": [[round(u1["a"], 3), round(fin, 3)],
                       [round(u2["a"], 3), round(u2["b"], 3)]],
            "texto": txt.strip(), "clave": set(_voc.contenido(txt, idioma)),
            "aire": round(u1.get("aire", 0) + u2.get("aire", 0), 2)}
