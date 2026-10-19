"""Volver a oír sólo los tramos que salieron vacíos, con el modelo bueno.

**El camino de salvamento, y es donde vivieron los fallos.** Jaime lo
diagnosticó: *«estos problemas surgen por intentar salvar lo que había antes en
lugar de desarrollar de nuevo el proceso limpio»*. De los cinco fallos de
aquella sesión, cuatro salieron de conservar lo anterior y tres de aquí: la
costura duplicando palabras (C-64), el acuerdo desconocido reventando el
formateo, y la media sobre valores que ya podían ser nulos.

**Regla: no se usa para arreglar una corrida floja. Se rehace la corrida.** Se
conserva porque el peldaño barato del embudo sí lo necesita —catalogar con
`small` y afinar con `medium` sólo lo preseleccionado (C-59)—, y ahí la fusión
se justifica porque lo que cambia es el MODELO, no el número de pasadas.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import registro  # noqa: E402
import rutas  # noqa: E402


def afinar(toma, tramos, pasadas=4):
    """JUBILADO para la via normal. Re-transcribe SOLO esos tramos.

    **Este es el camino de salvamento y es donde vivieron los fallos.** Jaime lo
    diagnostico: *«estos problemas surgen por intentar salvar lo que habia antes
    en lugar de desarrollar de nuevo el proceso limpio»*. De los cinco fallos de
    esa sesion, cuatro salieron de conservar lo anterior, y tres de ellos de
    aqui: la costura duplicando palabras (C-64), el acuerdo desconocido
    reventando el formateo, y la media sobre valores que ya podian ser nulos.

    El proceso canonico es **una sola corrida con `--pasadas 4`**: cuesta 1,6x y
    no tiene fusion, que es lo unico que esta funcion anade. Se conserva porque
    el peldaño barato del embudo si la necesita —catalogar con `small` y afinar
    con `medium` solo lo preseleccionado (C-59)—, y ahi la fusion se justifica
    porque lo que cambia es el MODELO, no el numero de pasadas.

    Regla: **no se usa para arreglar una corrida floja. Se rehace la corrida.**

    Es el peldano que sube la robustez sin pagarla en toda la cinta. Jaime:
    *«utilizamos los recursos caros y pesados solo en lo que ya sabemos que va a
    funcionar, y vamos incrementando robustez conforme el funnel avanza»*.

    Medido sobre el reel 6: el barrido barato —`small`, una pasada— cuesta 60 s
    frente a los ~7 min del bueno, y **acierta el sitio en 7 de 9 etapas**. Las
    otras dos caen en otro lado. O sea sirve para **preseleccionar y no para
    elegir**, y esta funcion es la que convierte esa lista corta en una
    decision: se vuelve a oir con `medium` solo lo preseleccionado.

    El resultado se **funde** en el transcript: las palabras del tramo afinado
    sustituyen a las que habia, y el resto queda igual. Asi no hay dos ficheros
    describiendo la misma cinta (aprendizaje 33).
    """
    from transcribir import (LARGA, MODELOS, VENTANA, a_cinta, alucinado, atascado, audio, limpio, medoide, pasada, recorte, sin_fantasmas, sin_silencios)

    ruta = f"work/transcripts/{toma}.json"
    d = json.load(open(ruta, encoding="utf-8"))
    runs = json.load(open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]
    tmp = rutas.temporal("afinar", toma)
    voz_wav = os.path.join(tmp, "voz.wav")
    mapa, dur, sr, anchura = sin_silencios(audio(toma), runs, voz_wav)

    # De tiempo de cinta a tiempo de voz, que es donde vive el wav recortado.
    def a_voz(t):
        """De cinta a voz, **pegandose al tramo mas cercano si cae en el hueco**.

        Los extremos que llegan aqui vienen de `recortar()`, que resta 0,06 s
        para no comerse el ataque de la palabra — y con eso el instante cae en
        el silencio de antes del tramo. Devolver `None` ahi hacia que el tramo
        no se afinara y el aviso decia «sin voz», que es verdad y no es el
        problema.
        """
        for m in mapa:
            if m["cinta"] <= t < m["cinta"] + m["dur"]:
                return m["voz"] + (t - m["cinta"])
        cerca = min(mapa, key=lambda m: min(abs(m["cinta"] - t),
                                            abs(m["cinta"] + m["dur"] - t)),
                    default=None)
        if cerca and min(abs(cerca["cinta"] - t),
                         abs(cerca["cinta"] + cerca["dur"] - t)) < 1.5:
            return (cerca["voz"] if t < cerca["cinta"]
                    else cerca["voz"] + cerca["dur"])
        return None

    def al_tramo(a, b):
        """Estira el rango hasta las fronteras de los tramos que toca.

        Es lo que hace imposible la costura: se sustituye desde el arranque de
        un tramo hasta el final de otro, y entre medias no hay palabra partida
        porque ahi el detector midio silencio.
        """
        toca = [(x, y) for x, y in runs if y > a and x < b]
        if not toca:
            return None
        return min(x for x, _ in toca), max(y for _, y in toca)

    # **Y se ordenan por la cinta antes de fundir.** El fundido de abajo compara
    # cada tramo con el ULTIMO que entro, asi que da por supuesto que llegan en
    # orden. Y no llegan: `elegidos` los saca del EDL, o sea **en orden de
    # montaje**, que salta por la cinta. Dos tramos que se solapan pero llegan
    # separados no se funden, y entonces el segundo se barre sobre un trozo que
    # ya se toco — o no se barre.
    #
    # La huella estaba a la vista en la propia base: `20260825_225808` tiene
    # 122,65-131,41 **y** 122,65-150,64 como dos rangos distintos. Un fundido que
    # funciona no puede producir eso.
    #
    # Lo que costo: reel-04 e2 se quedo al 0% afinado con el barrido corrido tres
    # veces. La puerta pedia el barrido, el barrido decia haberlo hecho, y no
    # habia forma de salir mirando ninguno de los dos.
    tramos = sorted(tramos, key=lambda x: (x[0], x[1]))
    redondeados = []
    for a, b in tramos:
        r = al_tramo(a, b)
        if not r:
            registro.aviso("transcribir", "tramo a afinar sin voz",
                           toma=toma, detalle=f"{a:.2f}-{b:.2f}", eco=False)
            continue
        if redondeados and r[0] <= redondeados[-1][1] + 0.01:
            redondeados[-1] = (redondeados[-1][0], max(redondeados[-1][1], r[1]))
        else:
            redondeados.append(r)
    tramos = redondeados

    # **Solo se quita lo viejo de los tramos que SI dieron texto.** Si una
    # pasada no devuelve nada —whisper calla, la ventana sale alucinada, el
    # tramo no tiene voz— y aun asi se borran las palabras de antes, queda un
    # hueco: la cinta pierde ese trozo y todo lo que dependa de el se queda sin
    # texto. Medido: `20260825_135637` con seis huecos, y ocho de los once
    # trozos del reel-01 sin una sola palabra.
    # `hechos` son los tramos cuyas palabras se SUSTITUYEN; `oidos`, todos los
    # que pasaron por el modelo bueno — incluidos aquellos en los que se decidio
    # quedarse con lo viejo. Son cosas distintas y hacen falta las dos: lo
    # primero manda el borrado, lo segundo es lo que la puerta pregunta.
    hechos, oidos, nuevas, tocados, intentados = [], [], [], 0, []
    for a, b in tramos:
        va, vb = a_voz(a), a_voz(max(a, b - 0.01))
        if va is None or vb is None:
            registro.aviso("transcribir", "tramo a afinar sin voz",
                           toma=toma, detalle=f"{a:.2f}-{b:.2f}", eco=False)
            continue
        # Ventana centrada y con contexto: por debajo del suelo whisper calla.
        centro = (va + vb) / 2
        ancho = max(VENTANA, (vb - va) + 8.0)
        cands = []
        for k in range(pasadas):
            desp = (k - (pasadas - 1) / 2) * (ancho / (pasadas + 1))
            w0 = max(0.0, min(dur - ancho, centro - ancho / 2 + desp))
            trozo = os.path.join(tmp, f"a{k:02d}.wav")
            recorte(voz_wav, w0, min(w0 + ancho, dur), trozo, sr, anchura)
            ws = pasada(trozo, os.path.join(tmp, f"a{k:02d}"), MODELOS["bueno"])
            dentro = [w for w in ws
                      if va <= w["a"] + w0 + (w["b"] - w["a"]) / 2 < vb]
            for w in dentro:
                w["a"] += w0
                w["b"] += w0
            txt = " ".join(w["t"] for w in dentro)
            if dentro and not alucinado(txt) and not atascado(dentro):
                cands.append({"texto": txt, "ws": dentro, "borde": 0.0})
        if not cands:
            # **Y no se calla.** Este `continue` era la unica salida muda del
            # afinado: si las cuatro pasadas salian vacias, alucinadas o
            # atascadas, la funcion devolvia «0 afinados» sin decir de que
            # tramo ni por que. Eso bloquea la linea entera, porque la puerta
            # de composicion exige el CC afinado y no hay forma de saber que
            # falta: paso con el remate del reel-01 traido de otra cinta.
            registro.aviso("transcribir", "ningun candidato sobrevivio",
                           toma=toma,
                           detalle=f"{a:.2f}-{b:.2f}: {pasadas} pasadas, todas"
                                   f" vacias, alucinadas o atascadas", eco=True)
            # **Y queda dicho que se intentó** (C-599): sin esto la puerta de
            # composición lo volvía a pedir cada vuelta —reel-20 e10, la firma
            # de 0,78 s, seis minutos de whisper por vuelta toda la mañana—.
            intentados.append((a, b))
            continue
        elegido, acuerdo = medoide(cands)
        # **Y no se acepta si trae menos de lo que se va a llevar.**
        #
        # `afinar` sustituye el tramo entero: borra lo viejo que lo toca y pone
        # lo nuevo. Si la pasada nueva oye menos —pasa, y pasa justo en los
        # tramos dificiles, que son los que se mandan a afinar— la cinta pierde
        # palabras a cambio de nada y nadie se entera, porque el paso informa de
        # los tramos que hizo, no de las palabras que quedaron.
        #
        # Es la misma familia que C-89: medir el resultado y no el esfuerzo. Y
        # aqui la cuenta es trivial, que es lo que la hace imperdonable.
        viejas = [w for w in d["segmentos"]
                  if w["end"] > a + 0.001 and w["start"] < b - 0.001]
        if len(elegido["ws"]) < len(viejas):
            registro.aviso("transcribir", "afinado que resta: se queda lo viejo",
                           toma=toma,
                           detalle=f"{a:.2f}-{b:.2f}: {len(viejas)} palabras ->"
                                   f" {len(elegido['ws'])}", eco=False)
            # **Pero el tramo queda oido.** Se paso por el modelo bueno y la
            # decision fue conservar lo que habia, que es un resultado del
            # afinado y no una ausencia de el. Sin esto la puerta de
            # composicion pedia el barrido caro, el barrido se negaba a empeorar
            # el texto, y la pieza se quedaba trabada entre las dos — le paso al
            # remate del reel-01 traido de otra cinta.
            oidos.append((a, b))
            continue
        for w in elegido["ws"]:
            ini = a_cinta(w["a"], mapa)
            fin = a_cinta(min(w["b"], vb - 0.001), mapa)
            nuevas.append({"start": round(ini, 3), "end": round(max(ini, fin), 3),
                           "text": w["t"], "larga": int(fin - ini > LARGA)})
        hechos.append((a, b))
        tocados += 1
        # `acuerdo` es None cuando solo sobrevivio una pasada: con una no hay
        # acuerdo, hay ausencia de discrepancia. Formatearlo como numero
        # reventaba el afinado entero — y justo despues de arreglar que dejara
        # de mentir con un 1,00.
        registro.nota("transcribir", "tramo afinado", toma=toma,
                      detalle=f"{a:.2f}-{b:.2f} acuerdo "
                              f"{'sin medir' if acuerdo is None else f'{acuerdo:.2f}'}"
                              f" ({len(cands)} pasadas)")

    if not nuevas:
        if oidos:
            d["afinado"] = sorted(set(
                [tuple(x) for x in d.get("afinado", [])] + oidos))
            json.dump(d, open(ruta, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        return d, 0
    # **La costura duplica si no se corta por los dos lados.** Se quitaban las
    # palabras viejas cuyo CENTRO caia dentro del tramo, pero las nuevas se
    # salen un poco por el borde: al fundir quedaba «odontologo odontologo
    # odontologo» y «El contador es como es como el medico». Una palabra
    # duplicada aqui es un subtitulo duplicado despues.
    #
    # Asi que se quita lo viejo que **toca** el tramo —no solo lo que esta
    # centrado dentro— y se recorta lo nuevo a los limites del tramo.
    # **La costura no se arregla: se elimina.** Pregunta de Jaime, y es la
    # correcta: *«si lo haces desde el comienzo es mas solido o mas fragil? Si
    # es igual de fragil, entonces hay que corregir el problema»*.
    #
    # Los dos fallos de este camino —duplicar palabras al fundir (C-64), y el
    # acuerdo desconocido reventando el formateo— salian de lo mismo: unir dos
    # transcripciones de audio que se solapa. Parchear el borde es tapar el
    # sintoma; el arreglo es que **no haya borde que unir**.
    #
    # Lo consigue el tramo: su frontera es **silencio medido** por el detector,
    # no mitad de palabra. Si el afinado sustituye tramos ENTEROS, lo viejo y lo
    # nuevo nunca comparten una palabra y el solape deja de existir. Por eso
    # `afinar` redondea lo que le piden al tramo que lo contiene antes de nada.
    # **Tramo a tramo, nunca del primero al ultimo.** Esto tomaba el minimo y el
    # maximo de TODOS los tramos y borraba lo que hubiera en medio: afinar el
    # segundo 87 y el 590 de una cinta se llevaba por delante los 503 segundos
    # intermedios. Medido: la cinta 135637 paso de 935 palabras a 342, y en el
    # hueco 408-519 vivian las ocho tomas alternativas del bootcamp — o sea el
    # abanico entero donde hay que elegir, que es la materia prima del paso
    # siguiente. El sintoma es cruel: la pieza montada se ve perfecta, porque
    # sus tramos SI estan; lo que desaparece es todo lo que no se uso.
    def _toca(w):
        return any(w["end"] > x + 0.001 and w["start"] < y - 0.001
                   for x, y in hechos)

    fuera = [w for w in d["segmentos"] if not _toca(w)]
    d["segmentos"] = sin_fantasmas(fuera + nuevas)
    d["afinado"] = sorted(set(tuple(t) for t in
                              [tuple(x) for x in d.get("afinado", [])] +
                              [tuple(t) for t in hechos] + oidos))
    d["intentado"] = sorted(set(tuple(t) for t in
                                [tuple(x) for x in d.get("intentado", [])] + intentados))
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return d, tocados


# ── qué se vuelve a oír, y por qué ───────────────────────────────────────────
#
# Tres maneras de elegir los tramos, y las tres son el mismo trabajo: decidir
# dónde no quedó bien. Vivían dentro del `main()` de `transcribir.py`, mezcladas
# con leer argumentos, así que la regla de cada una estaba escrita donde nadie
# la busca.


def juntar(tramos, hueco=2.0):
    """Funde los que casi se tocan.

    Afinar dos veces lo mismo es pagarlo dos veces, y además una ventana más
    ancha da mejor contexto al modelo.
    """
    j = []
    for d, h in sorted(tramos):
        if j and d - j[-1][1] < hueco:
            j[-1] = (j[-1][0], h)
        else:
            j.append((d, h))
    return j


def dudosos(toma, suelo=0.6):
    """Los tramos donde el propio barrido dijo que no se fiaba.

    Jaime: *«si no hubo el primer paso, difícilmente podrás encontrar los demás;
    el primer paso es clave para confirmar o negar los videos y sobre este es que
    tenemos que corregir»*. El acuerdo entre pasadas ya está medido y guardado;
    aquí sólo se leen los que quedaron por debajo.
    """
    import basedatos

    cx = basedatos.abrir()
    tr = [(d, h) for d, h in cx.execute(
        "select s.desde, s.hasta from subtitulo s join toma t on t.id = s.toma_id"
        " where t.nombre = ? and s.acuerdo is not null and s.acuerdo < ?"
        " order by s.acuerdo", (toma, suelo))]
    cx.close()
    return juntar(tr)


#: Lo que se abre a cada lado de un tramo elegido. La redundancia suele empezar
#: justo antes del corte, y afinar sólo lo de dentro no la deja ver.
MARGEN = 1.5


def elegidos(slug):
    """Los tramos que la pieza va a usar, por cinta. **El caro, y sólo ahí.**

    Regla de Jaime, precisada por él mismo: *«la revisión cara no es para
    identificar redundancia, es para obtener los scripts ajustados a la
    realidad; la redundancia necesita criterio editorial»*. Lo que este paso
    aporta es **fidelidad** —saber qué se dijo, palabra por palabra, donde se va
    a usar—, no juicio.

    Antes se pagaban cuatro pasadas sobre la cinta entera —media hora larga— para
    acabar usando dos minutos de ella.
    """
    import json

    import rutas

    edl = json.load(open(f"ads/{slug}/edl-sell.json", encoding="utf-8"))
    por_toma = {}
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        t = det.get("toma") or rutas.TOMAS[slug]
        por_toma.setdefault(t, []).append(
            (max(0.0, rango[0] - MARGEN), rango[1] + MARGEN))
    return por_toma
