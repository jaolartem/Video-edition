"""Qué unidad cumple una etapa. **El texto filtra y la voz decide**, en dos pasos.

Orden de Jaime: *«lo más importante es el mensaje, lo que se dice; luego cómo se
dice; luego cómo se ve»*. Aquí eso es literal y **no es una suma ponderada**:

1. `debe_decir` filtra —condición dura, la declara el frame—;
2. entre los que lo dicen, la cobertura decide quién compite (`RELATIVO`);
3. entre los finalistas, primero la frase entera y sin trabarse, y sólo después
   la voz.

Con la suma, una toma apagada que cubría un poco más ganaba a una viva. Con el
filtro, la apagada ni siquiera compite si no dice el beat.

**Y si ninguna unidad lo dice, todavía no se ha terminado de buscar.** Jaime:
*«siempre va a estar; puede estar fragmentado o cortado, pero está»*. De ahí las
dos puertas que este módulo abre antes de rendirse: el barrido hacia delante
(`completar`) y la búsqueda en la cinta entera (`en_la_cinta`).
"""
from __future__ import annotations

import sys

from . import enunciado as _enun
from . import vocabulario as _voc
from .candidata import (FINALISTAS, PASO_VOZ, RELATIVO, UMBRAL, dice,
                        integridad, puntua, trabado)
from .poda import unir
from .voz import Voz


def _di(msg: str) -> None:
    print(msg, file=sys.stderr)


class Concurso:
    """Las unidades de una cinta compitiendo por cumplir una etapa."""

    def __init__(self, cands, toma, ws, runs):
        #: Todas las unidades de la cinta, incluidas las ya usadas: el barrido
        #: hacia delante necesita mirar más allá de las que quedan libres.
        self.cands = cands
        self.toma = toma
        self.ws = ws
        self.runs = runs

    # ── la primera puerta: seguir leyendo hacia delante ──────────────────────
    def completar(self, u, etapa):
        """Sigue leyendo hacia delante hasta que la etapa esté dicha.

        **Protocolo de Jaime**, y es el que manda sobre todo lo demas:

        > *«Siempre va a estar. Puede estar fragmentado o cortado, pero esta.
        > Revisa el texto de la parte siguiente a la que ya esta; luego para de
        > revisar el texto si aparece lo del siguiente segmento. Repites el
        > proceso con cada segmento.»*

        Sale de como graba: en orden, y sin pasar a la frase siguiente hasta
        tener una toma ajustada. Asi que el material de una etapa esta
        **despues** del de la anterior y **antes** del de la siguiente, y
        buscarlo es un barrido hacia delante con dos frenos:

        1. **Se para cuando la etapa ya esta dicha.**
        2. **Se para si aparece lo del segmento siguiente** — se mide con la
           misma puntuacion de cobertura: si una unidad se parece mas al beat de
           al lado que a este, ya no es de este.

        La version anterior solo miraba **la frase inmediatamente pegada**
        (1,5 s), y por eso el reel 1 se quedaba sin sus tres cifras: estaban dos
        o tres frases mas alla, con un intento fallido en medio.

        No es coser tomas ni usar fragmentos: son **dos oraciones enteras y
        seguidas** de la misma toma —en el reel 2 la [3] empieza a nueve
        centesimas del final de la [2]—, que es hablar seguido. La regla de una
        frase por etapa protegia contra el fragmento, no contra la idea completa.
        """
        if not etapa.debe_decir or etapa.cumplida_por(u["texto"]):
            return u
        adelante = sorted((c for c in self.cands if c["a"] > u["a"] + 0.2),
                          key=lambda c: c["a"])
        junto = u
        for c in adelante[:6]:
            # **Freno de contiguidad.** Jaime: *«no siempre secuencial, pero
            # siempre por etapas completas; casi siempre secuencial»*. El
            # material de una etapa es un bloque seguido: si hay que saltar mas
            # de ocho segundos para encontrar la continuacion, lo de en medio es
            # de otra etapa y esto ya no es la misma.
            #
            # Sin este freno el barrido se llevaba 113 s del reel 1 -de 215 a
            # 328- cosiendo tres etapas en una.
            if c["a"] - junto["b"] > 8.0:
                break
            # Freno 2: esto ya es del segmento siguiente.
            if (etapa.siguiente
                    and puntua(etapa.siguiente, c) > puntua(etapa.parrafo, c) + 0.05):
                break
            junto = unir(junto, c)
            # Freno 1: la etapa ya esta dicha.
            if etapa.cumplida_por(junto["texto"]):
                _di(f"  beat {etapa.n}: barrido hacia delante hasta decir "
                    f"{etapa.debe_decir} ({u['a']:.2f}-{c['b']:.2f})")
                return junto
        return u

    # ── la última puerta: buscarlo en la cinta entera ────────────────────────
    def en_la_cinta(self, etapa):
        """La frase de la cinta que dice lo que la etapa exige, o `None`.

        Jaime: *«siempre va a estar; puede estar fragmentado o cortado, pero
        esta»*. Y aqui estaba: la frase de los 30.000 del reel 1 vive en un tramo
        tan repetido que pasa de los 22 s de voz y el filtro de candidatos la
        tira entera. Que una unidad no sea publicable **no significa que el dato
        no este**.

        Sale larga y con repeticiones; de eso se encarga la poda despues.
        """
        for t in etapa.debe_decir:
            hallados = _enun.frase_con(self.ws, self.runs, t, dice)
            if not hallados:
                continue
            # **Se catalogan TODAS las veces que se dice, no la primera.** Jaime:
            # *«buscas pero no catalogas todo lo que hay en el video... si no
            # encuentras nada es porque honestamente ni has mirado»*. Se toma la
            # ultima, que por como graba es la version ajustada.
            _di(f"    {t}: {len(hallados)} apariciones en la cinta "
                f"({', '.join('%.1f' % h[0] for h in hallados)}) — se toma la ultima")
            a_, b_ = hallados[-1]
            txt = _enun.texto_en(self.ws, (a_, b_))
            _di(f"  beat {etapa.n} ({etapa.nombre}): {etapa.debe_decir} no estaba "
                f"en ninguna unidad; encontrado en la cinta ({a_:.2f}-{b_:.2f})")
            return {"a": a_, "b": b_, "texto": txt,
                    "clave": set(_voc.contenido(txt)), "aire": 0.0,
                    "pal": [[w["start"], w["end"], w["text"]] for w in self.ws
                            if a_ <= w["start"] <= b_]}
        return None

    # ── el concurso ──────────────────────────────────────────────────────────
    def elige(self, libres, etapa, ultimo=0.0):
        """La unidad que se queda con la etapa, o `None` si no hay material.

        Devuelve `(unidad, cobertura, voz)`. `voz` puede ser `None`: es «no
        medida», que no es lo mismo que «plana» — ver `dominio.voz`.
        """
        puntuados = [(puntua(etapa.parrafo, u), u) for u in libres]
        exige = etapa.debe_decir
        if exige:
            antes = len(puntuados)
            puntuados = [x for x in puntuados if etapa.cumplida_por(x[1]["texto"])]
            if not puntuados:
                hallado = self.en_la_cinta(etapa)
                if hallado:
                    return (hallado, 1.0,
                            Voz(hallado["a"], hallado["b"], self.toma).expresividad)
                _di(f"  beat {etapa.n} ({etapa.nombre}): ninguna unidad dice "
                    f"{exige} — de {antes} candidatas. La etapa se queda sin "
                    f"material antes que decirlo a medias.")
                return None
        # **Con `debe_decir` cumplido, el umbral absoluto sobra.** Ese umbral
        # mide parecido de vocabulario con el libreto, y ya no hace falta para
        # decidir si la unidad viene al caso: **dice la cifra que la etapa
        # exige**, que es una prueba mas fuerte. Dejandolo, el reel 1 tiraba la
        # unica unidad que decia los 30.000 por no parecerse bastante al parrafo.
        #
        # El `default` no es adorno: sin `debe_decir` y sin candidatas libres,
        # `max()` reventaba con un ValueError en vez de decir SIN MATERIAL.
        techo = max((p for p, _ in puntuados), default=0.0)
        suelo = RELATIVO * techo if exige else max(UMBRAL, RELATIVO * techo)
        finalistas = sorted((x for x in puntuados if x[0] >= suelo),
                            key=lambda x: -x[0])[:FINALISTAS]
        if not finalistas:
            _di(f"  beat {etapa.n} ({etapa.nombre}): SIN MATERIAL — "
                f"«{etapa.parrafo[:60]}…»")
            return None

        # Tres criterios, en el orden que fijó Jaime: **el mensaje, luego cómo
        # se dice, luego cómo se ve**.
        #
        # 1. La cobertura ya filtró quién compite — eso es el mensaje.
        # 2. Entre los que lo dicen, primero la frase entera y sin trabarse: una
        #    frase rota o un «usted usted» siguen siendo defectos de mensaje.
        # 3. Y sólo entonces decide la voz, que es lo que se oye.
        #
        # Sin el paso 2, la voz rescataba tomas trabadas: el arranque fallido
        # tiene saltos de tono, así que **puntúa alto justamente por tropezar**.
        #
        # Si la toma de ese audio no sirve visualmente, se pone una tarjeta — el
        # plano se sustituye, la voz no.
        medidos = [(Voz(u["a"], u["b"], self.toma).expresividad, p, u)
                   for p, u in finalistas]
        # **Casi siempre secuencial.** Entre dos candidatas que dicen lo mismo,
        # gana la que va **despues de la etapa anterior**: Jaime graba en orden.
        # Es desempate y no filtro, porque el mismo dijo *«no siempre»* — un
        # filtro duro tiraria la buena las veces que se sale del orden.
        voz, cubre, mejor = max(
            medidos,
            key=lambda t: (-trabado(t[2]["texto"]), integridad(t[2]["texto"]),
                           _escalon(t[0]), t[2]["a"] >= ultimo, t[1]))
        return (self.completar(mejor, etapa), round(cubre, 3),
                round(voz, 2) if voz is not None else None)

    def __str__(self) -> str:
        return f"concurso sobre {len(self.cands)} unidades de {self.toma}"


def _escalon(e):
    """El peldaño de voz de una candidata. **`None` no es cero.**

    Una candidata cuya expresividad no se pudo medir —poca energia sonora, el
    detector saltando de octava— no es una candidata plana: es una de la que no
    sabemos nada, y hasta ahora entraba con `0.0` y competia como la peor medida
    de su beat. Aqui queda por debajo de cualquier medida real, que es lo unico
    que se puede sostener: si de una sabemos que la voz esta viva y de la otra no
    sabemos nada, se monta la que sabemos.
    """
    return int(e / PASO_VOZ) if e is not None else -1
