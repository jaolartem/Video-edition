"""Entre las que dicen lo mismo, gana la que lo dice con más voz.

Es el paso 3 de Jaime —*«se busca la frase exacta que cumpla la función y
comunique lo que debe; entre las que dicen lo mismo manda la emoción»*— y va
**aquí y no antes** por el embudo: medir la voz sobre las 5.319 ventanas de un
reel es carísimo y sobre los cinco finalistas de cada etapa es gratis.

## La banda estaba mal escrita y el paso no hacía nada

Sólo compiten las que están cerca en mensaje (`beats.RELATIVO = 0,80`): la voz
no rescata a una que dice la mitad. Eso se escribía **multiplicando**:

    fila[x] >= fila[k] * 0.80

y la puntuación de una ventana **es negativa la mitad de las veces** —lleva
hasta 1,5 de castigo por extremos y `beats.puntua` ya resta por relleno y
tartamudeo—. Con `fila[k] = -1,15`, el suelo sale **-0,92**: más alto que la
propia ganadora. O sea que la banda se invertía y **la elegida quedaba fuera de
su propia comparación**.

Medido sobre los seis reels: de las **54 etapas** con toma, en **28** la
ganadora caía fuera de su banda y en **44** no llegaba a competir nadie. El
resultado es el que se ve en el informe de las seis piezas: **cero cambios por
voz**, nunca. El paso llevaba desconectado desde que se escribió, y cuando sí
había dos candidatas y la ganadora estaba fuera, `_vale(k)` reventaba con
`KeyError` — o no hacía nada, o rompía.

La banda es una **distancia**, no un producto: se admite a quien no está más de
un 20 % por debajo de la elegida, y para un número negativo eso es restar, no
multiplicar. Con eso la elegida está siempre dentro, por construcción.

## Y se mide sobre la cinta de cada candidata

`manda_la_voz` recibía **una** toma y filtraba `ventana.toma == toma`, así que
las candidatas de las otras grabaciones no competían — justo lo que C-74 abrió
al buscar en todo el material. Peor: si la ganadora venía de otra cinta,
tampoco entraba, y volvía el mismo `KeyError`. Aquí cada candidata se mide con
las palabras de **su** grabación, que es lo único que tiene sentido medir.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import beats  # noqa: E402
import depurar  # noqa: E402

from . import pesos  # noqa: E402


class Entrega:
    """La decisión cara: voz y limpieza sobre los finalistas de cada etapa."""

    def __init__(self, corpus, marcas, ventanas, rotas=(), prioridades=None):
        self.corpus = corpus
        self.marcas = marcas
        self.ventanas = ventanas
        #: Las que `depurar.py` marcó porque su mensaje se parte al quitar lo que
        #: no aporta. **No compiten menos: compiten con un escalón menos.** La
        #: fragmentación sólo pesa cuando el mensaje se rompe, nunca por contar
        #: cortes.
        self.rotas = set(rotas)
        #: Por etapa, si ahí manda la **entrega** o la **limpieza**. Lo decide el
        #: paso de descripción mirando la pieza entera, no un umbral.
        self.prioridades = prioridades or {}

    # ── lo que se mide de una candidata ──────────────────────────────────────
    def voz(self, v) -> float:
        """Cuánta emoción lleva, **sin signo**.

        Jaime: *«ojo, no hay emociones positivas o negativas: más emoción es más
        tristeza tanto como más rabia tanto como más alegría»*. `expresividad`
        mide el recorrido de F0 y eso **premia lo animado**: la tristeza baja el
        tono y estrecha el rango, así que puntuaba como plana. `intensidad` mide
        la distancia a la neutralidad de ESA cinta y la devuelve sin signo;
        grave y lento puntúa igual que agudo y rápido, y lo único que puntúa
        bajo es lo tibio, que es lo único que no transmite.

        El recorrido se conserva como segundo término, con un cuarto del peso:
        dice si dentro del tramo la voz se mueve, que es otra cosa distinta de
        estar lejos del punto cero.
        """
        # **Y si no se midio nada, `None`.** `voz_st` ya se declara
        # `float | None` en `ventana.py` y el paso de tablero de mas abajo ya
        # lo trata asi; lo que ponia el cero era este `except`, y un cero aqui
        # es «la peor entrega posible» dicho de una toma que nadie midio.
        inten = exp = None
        try:
            i = beats.intensidad(v.toma, v.a, v.b, self.corpus.dichos(v.toma))
            inten = i.get("intensidad")
            exp = beats.expresividad(v.toma, v.a, v.b)
            v.intensidad = inten
            v.altura_st = i.get("altura")
        except Exception:                             # noqa: BLE001
            pass
        if inten is None and exp is None:
            v.voz_st = None
            return None
        medida = float(inten or 0.0) + float(exp or 0.0) / 4.0
        v.voz_st = round(medida, 2)
        return medida

    def limpieza(self, v) -> float:
        """Cuánto de lo dicho sobrevive a quitarle los tropiezos. 1,0 es limpia.

        Jaime: *«para la intención comunicativa a veces es mejor una toma limpia
        y sin errores, pero no es en todos los casos»*. Como **no es en todos
        los casos**, esto no decide nada por sí solo.

        Se mide con la misma maquinaria que `depurar.py` usa después —repetición
        dentro del trozo y tartamudeo— porque tiene que predecir exactamente lo
        que ese paso va a recortar.
        """
        try:
            pal = self.corpus.dichos(v.toma)
            trozos = depurar.trozos_con_voz(pal, v.a, v.b)
            util = sum(y - x for x, y in trozos)
            if util <= 0:
                return 0.0
            t2 = [list(depurar.podar_dentro(pal, x, y)) for x, y in trozos]
            t2 = [t for x, y in t2 for t in depurar.sin_tartamudeo(pal, x, y)]
            return sum(y - x for x, y in t2) / util
        except Exception:                             # noqa: BLE001
            return 1.0

    # ── quiénes compiten ─────────────────────────────────────────────────────
    def finalistas(self, s0: int, k: int) -> list[int]:
        """Las que están cerca en mensaje, **con la elegida siempre dentro**.

        La banda es una distancia a la elegida, no un producto: ver la cabecera
        del fichero. Y si la elegida no entra en las cinco mejores por texto
        —puede no entrar, porque la eligió la cadena mirando a sus vecinas—
        entra igual: se la compara a ella, no a un sustituto.
        """
        fila = self.marcas[s0]
        base = fila[k]
        suelo = base - (1 - beats.RELATIVO) * abs(base)
        cerca = sorted((x for x in range(len(fila))
                        if fila[x] is not None and fila[x] >= suelo),
                       key=lambda x: -fila[x])[:beats.FINALISTAS]
        return cerca if k in cerca else [k] + cerca[:beats.FINALISTAS - 1]

    def decide(self, plan) -> list[tuple]:
        """Cambia la elegida de cada etapa cuando otra lo dice con más voz.

        El escalón es `beats.PASO_VOZ`: por debajo de un cuarto de semitono la
        diferencia es ruido del detector, y entonces manda el texto.
        """
        vs, cambios = self.ventanas, []
        for s0, k in enumerate(plan):
            if k is None or s0 >= len(self.marcas) or self.marcas[s0][k] is None:
                continue
            cerca = self.finalistas(s0, k)
            if len(cerca) < 2:
                continue
            for x in cerca:
                self.voz(vs[x])
                vs[x].limpieza = round(self.limpieza(vs[x]), 3)
            prioridades = self.prioridades
            manda_limpieza = (prioridades or {}).get(s0 + 1) == "limpieza"

            # **Sin medida no se compara.** `vale` restaba sobre `voz_st`, asi
            # que un `None` reventaba y un cero inventado hacia perder a la toma
            # que nadie pudo medir. Ahora la que no tiene medida no entra en la
            # comparacion: no gana ni pierde por algo que no se sabe, y si
            # ninguna se pudo medir la etapa se queda como estaba.
            def vale(x):
                if vs[x].voz_st is None:
                    return None
                # El handicap NO toca `voz_st`: lo medido se guarda como se
                # midió y sólo la comparación lo descuenta. Si se guardara
                # descontado, el informe diría que la toma tiene menos voz de la
                # que tiene.
                v = vs[x].voz_st - (beats.PASO_VOZ if x in self.rotas else 0.0)
                # Donde la etapa pide limpieza, la limpieza es la escala y la
                # voz desempata; donde pide entrega, al revés. Nunca se anula
                # ninguna: una toma limpia que no comunica no sirve, y una que
                # comunica pero se cae a pedazos tampoco.
                return (vs[x].limpieza * 10 + v) if manda_limpieza else (v + vs[x].limpieza)

            medidas = [x for x in cerca if vale(x) is not None]
            if len(medidas) < 2 or vale(k) is None:
                continue
            mejor = max(medidas, key=vale)
            # No se pisa con lo que ya ocupa otra etapa.
            choca = any(o is not None and o != k and vs[mejor].solapa(vs[o])
                        for o in plan)
            if mejor != k and not choca and vale(mejor) - vale(k) > beats.PASO_VOZ:
                cambios.append((s0 + 1, vs[k].voz_st, vs[mejor].voz_st))
                plan[s0] = mejor
        return cambios

    # ── la lectura plana se traslada a tablero ───────────────────────────────
    def a_tablero(self, plan, libreto) -> list[tuple]:
        """La toma leída y plana se va a tablero — **y ella misma es el copy**.

        Corrección de Jaime, en dos partes y las dos importan:

        - *«La toma leída compite si es entregada con expresividad.»* O sea que
          leer no descalifica: descalifica leer **sin voz**.
        - *«La toma leída es la ideal para generar tableros»*: justo porque leer
          es exacto, **su texto es copy fiable** — dice lo que el libreto quería
          decir, palabra por palabra, sin reescribir nada.

        Así que esto no descarta: **traslada**.

        **La voz se mide en TODAS las elegidas, no sólo en las literales.** Se
        medía sólo si leía, así que las demás llegaban como «no medida» —y plana
        leía eso como «no plana», o sea como entregada. Resultado: **cero
        tableros en los seis reels**. Es la trampa de siempre: un valor ausente
        interpretado como el valor bueno.
        """
        movidas = []
        for s0, k in enumerate(plan):
            if k is None or s0 >= len(libreto):
                continue
            # **La primera etapa no se va nunca a tablero: es el gancho.** En
            # reel-03 se llevó la etapa 1 y la pieza abría con un cartel en vez
            # de con su cara; y al irse, la tesis desapareció del habla y la
            # etapa 2 arrancaba por la conclusión sin premisa. Si la apertura
            # lee y viene plana, el remedio es elegir otra apertura.
            if s0 == 0:
                continue
            v = self.ventanas[k]
            v.lectura = round(v.lee(libreto[s0]), 3)
            if v.voz_st is None:
                try:
                    v.voz_st = round(
                        beats.expresividad(v.toma, v.a, v.b) or 0.0, 2)
                except Exception:                      # noqa: BLE001
                    v.voz_st = None
            if (v.lectura < pesos.LEIDA or v.voz_st is None
                    or v.voz_st >= pesos.VOZ_SALVA):
                continue          # no lee, o lee pero lo entrega: se queda
            movidas.append((s0 + 1, v.lectura, v.voz_st, v.texto))
            v.a_tablero = True
        return movidas
