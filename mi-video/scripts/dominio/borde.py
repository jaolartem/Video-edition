"""Los dos extremos de un trozo, y a dónde deberían ir.

**Aquí no se mide: se decide.** `dominio.habla` dice dónde el habla permite
cortar y `dominio.senal` dónde calla la onda; esto elige, con esas dos varas,
qué corte propone. Estaban mezclados en cinco funciones de `costuras.py` que
además abrían el fichero y lo escribían, así que no se podía preguntar «¿dónde
debería entrar este trozo?» sin mover el montaje.

Cada método devuelve **un `Tramo` nuevo o `None`**. Ninguno escribe nada: quien
escribe es el paso, y por eso el mismo código puede correr en seco para la
puerta y en firme para el arreglo.
"""
from __future__ import annotations

from .habla import AIRE, ATAQUE, cierra, colgante
from .tramo import Tramo

#: Lo que se deja después de la última palabra: el aire justo para que la frase
#: cierre sin sonar cortada. Más que esto ya es silencio, y el silencio se
#: declara.
COLA = 0.25
#: Cuánto se mira a cada lado buscando una frontera de frase antes de rendirse.
#: Mover más de dos segundos sí cambiaría lo que se oye, y eso es otra decisión.
BUSCA = 2.0
#: Lo mínimo que puede quedar de un trozo sin romperlo, y lo que un trozo tiene
#: que decir para que valga la pena moverle un borde.
MINIMO = 0.3
VIVE = 0.8


class Borde:
    """El trozo `tramo`, mirado por sus extremos, contra el habla de su cinta."""

    __slots__ = ("t", "h")

    def __init__(self, tramo: Tramo, habla):
        self.t = tramo
        self.h = habla

    # ── aritmética: no puede equivocarse, corre siempre ─────────────────────
    def entero(self) -> Tramo | None:
        """El mismo trozo con los dos cortes fuera de cualquier palabra.

        Un corte dentro de una palabra no se arregla con criterio: se saca. En
        el segundo 58 se oía «30, much» y en el 1:15 quedaba «rente», la cola de
        «diferente» — las dos son el mismo fallo.
        """
        na = round(self.h.fuera_de_palabra(self.t.desde, "ini"), 3)
        nb = round(self.h.fuera_de_palabra(self.t.hasta, "fin"), 3)
        if nb - na < MINIMO or self._igual(na, nb):
            return None
        return Tramo(na, nb, self.t.cinta)

    @property
    def mudo(self) -> bool:
        """No dice ni una palabra entera: es un resto que suena a chasquido.

        Los deja el propio ajuste de bordes — cinco trozos de 0,26 a 0,57 s en
        el lote, sin una sola palabra completa.
        """
        return self.t.dura < 0.7 and not self.h.en(self.t)

    def al_habla(self) -> Tramo | None:
        """Recortado a lo que de verdad se dice en sus extremos.

        Jaime, sobre las piezas largas: *«ve cortando silencios entre frases,
        que quede todo muy justo»*, y la predicción *«eso da unos segundos
        siempre»*. Medido antes de tocar nada, el aire no estaba entre frases
        —`plan-reel` ya corta cualquier hueco de más de 0,16 s— sino en los
        bordes: 15,4 s en reel-06 y 9,1 en reel-05, con e3 sosteniendo 5,40 s
        después de la última palabra. Por delante se respeta el `ATAQUE`.
        """
        ws = self.h.en(self.t)
        if not ws:
            return None
        na = max(self.t.desde, ws[0].empieza - ATAQUE)
        nb = min(self.t.hasta, ws[-1].acaba + COLA)
        if (na - self.t.desde) + (self.t.hasta - nb) < 0.15:
            return None
        return Tramo(round(na, 3), round(nb, 3), self.t.cinta)

    def con_ataque(self, suelo: float | None = None) -> tuple[Tramo, object] | None:
        """Retrocedido hasta `ATAQUE` para que se oiga la consonante inicial.

        Jaime, oyendo el reel-01: *«el "no es mala suerte" se entrega sin alma,
        falta el "eso"»*. Y el «eso» estaba: el corte empezaba exactamente donde
        el transcript pone el arranque de la palabra.

        **El transcript no sirve para medir un ataque.** Reparte las marcas sin
        dejar hueco entre palabras, así que estira la anterior por encima del
        silencio: «suerte,» figura hasta 93,44 cuando la voz se corta en 92,29 y
        vuelve en 92,89. La vara buena es el audio, y `suelo` es lo que quien
        pregunta ya midió sobre él: hasta dónde se puede retroceder sin traerse
        la cola de lo anterior.
        """
        prim = self.h.primera_tras(self.t.desde)
        if not prim or abs(prim.empieza - self.t.desde) > 0.02:
            return None                  # no entra pisando nada: se deja
        piso = self.t.desde - ATAQUE
        if suelo is not None:
            piso = max(piso, suelo)
        if self.t.desde - piso < 0.01:
            return None
        return Tramo(round(piso, 3), self.t.hasta, self.t.cinta), prim

    # ── criterio: apunta, y quien monta decide ──────────────────────────────
    def a_frontera(self, antes_fin=None) -> tuple[Tramo | None, str]:
        """Lleva cada extremo a la frontera de frase más cercana, o completa.

        **No cambia lo que la etapa dice**: mueve el corte al silencio que ya
        existe, dentro de `BUSCA`. Medido antes de esto: 27 de 85 entradas del
        lote entraban con menos de 0,2 s de aire; `reel-06` e6 empezaba en
        «anos» cuando lo anterior era «En 10».

        Devuelve `(None, "")` si no hay nada que hacer y `(None, "sucio")` si
        además no hay ninguna frontera cerca — eso último no es un arreglo, es
        un aviso.
        """
        if not self.h:
            return None, ""
        a, b = self.t.desde, self.t.hasta
        ini, fin = self.h.fronteras()
        na = min((x for x in ini if abs(x - a) <= BUSCA),
                 key=lambda x: abs(x - a), default=None)
        nb = min((x for x in fin if abs(x - b) <= BUSCA),
                 key=lambda x: abs(x - b), default=None)
        if na is None:
            cabeza = self._cabeza(antes_fin)
            if cabeza:
                return cabeza
        cola = self._cola()
        if cola:
            return cola
        movido = self._acercado(na, nb, antes_fin)
        if movido:
            return movido, "borde a frontera"
        return None, ("sucio" if na is None else "")

    def _cabeza(self, antes_fin) -> tuple[Tramo, str] | None:
        """La cabeza de la frase que el corte se comió, devuelta.

        Una entrada pegada a la palabra anterior sin pausa a la vista no se
        arregla moviéndola: se arregla **incluyendo** lo que le falta. Medido:
        `reel-06` e5 entraba en «mil dolares al año» con el «30» fuera, y
        `reel-05` e7 en «activo esa tasa» con el «no» fuera —que invierte la
        frase—.

        **Y la cabeza no puede ser un arranque en falso.** Si lo que hay delante
        repite lo que la etapa ya dice —«esto es diferente, esto es
        diferente»— no es la cabeza: es el intento anterior, y meterlo es meter
        tartamudeo.
        """
        ws, a = self.h.palabras, self.t.desde
        k = next((j for j, p in enumerate(ws) if p.empieza >= a - 0.001), None)
        if not k:
            return None
        j = k
        while j > 0:
            # La coma cuenta como frontera **sólo aquí**, al estirar hacia
            # atrás: se busca la cabeza de ESTA frase, no la anterior entera.
            # Con el punto solo, `reel-03` se traía «usted tiene un contador»
            # dos veces.
            if ws[j].empieza - ws[j - 1].acaba >= AIRE or cierra(ws[j - 1], coma=True):
                break
            j -= 1
        cand = round(max(0.0, ws[j].empieza - 0.08), 3)
        cabeza = [p.comparable.replace(" ", "") for p in ws[j:k]]
        cabeza = [x for x in cabeza if x]
        primeras = {p.comparable.replace(" ", "") for p in ws[k:k + 5]}
        if not (j < k and len(cabeza) >= 2
                and sum(1 for x in cabeza if x in primeras) <= 1
                and a - cand <= 4.0
                and (antes_fin is None or cand >= antes_fin - 0.001)):
            return None
        dice = " ".join(p.texto for p in ws[j:k])
        return Tramo(cand, self.t.hasta, self.t.cinta), f"cabeza devuelta «{dice}»"

    def _cola(self) -> tuple[Tramo, str] | None:
        """La cola que cuelga: o se completa la frase, o se corta la palabra.

        `reel-02` acababa una etapa en «se queda con» —sin la cifra— y otra en
        «voy a» —sin el verbo—. Una frase que muere en una preposición no dice
        nada y el espectador se queda esperando.
        """
        ws, ult = self.h.palabras, self.h.en(self.t)
        if not ult or not colgante(ult[-1].texto):
            return None
        # **El conector volando: la primera palabra de la frase siguiente que se
        # coló al final.** Jaime lo vio en el primer render —«hay un conector
        # volando (y cuando)»—. Se reconoce porque va en mayúscula o porque lo
        # anterior cerró con punto: no falta el objeto, sobra la palabra.
        if len(ult) >= 2 and (ult[-1].texto.strip()[:1].isupper()
                              or cierra(ult[-2])):
            corte = round(ult[-2].acaba, 3)
            if corte - self.t.desde > VIVE:
                return (Tramo(self.t.desde, corte, self.t.cinta),
                        f"conector suelto fuera «{ult[-1].texto}»")
        k = ws.index(ult[-1])
        j = k
        while j + 1 < len(ws):
            if ws[j + 1].empieza - ws[j].acaba >= AIRE:
                break
            j += 1
            if cierra(ws[j], coma=True) and not colgante(ws[j].texto):
                break
        cand = round(ws[j].acaba, 3)
        if j > k and cand - self.t.hasta <= 3.0:
            dice = " ".join(p.texto for p in ws[k + 1:j + 1])
            return (Tramo(self.t.desde, cand, self.t.cinta),
                    f"cola cerrada «{dice}»")
        # **Si completar la frase costaría más de tres segundos, se corta la
        # palabra que cuelga.** Mejor una etapa que acaba un poco seca que una
        # que acaba en «voy a», y mejor eso que alargar la pieza por una
        # preposición.
        if len(ult) >= 2:
            corte = round(ult[-2].acaba, 3)
            if corte - self.t.desde > VIVE:
                return (Tramo(self.t.desde, corte, self.t.cinta),
                        f"cola cortada «{ult[-1].texto}»")
        return None

    def _acercado(self, na, nb, antes_fin) -> Tramo | None:
        """Los dos extremos, cada uno a su frontera, si no cuesta lo que se dice.

        **Dos guardas, y las dos salen de verlo fallar.** Sin la primera, un
        borde se iba 1,9 s y el segmento pasaba a decir otra cosa; sin la
        segunda, la entrada de una etapa se metía dentro de la salida de la
        anterior y los dos trozos se solapaban en el montaje.
        """
        dentro = self.h.en(self.t)

        def mantiene(x, y):
            if not dentro:
                return True
            quedan = sum(1 for p in dentro if p.suena_en(x, y))
            return quedan >= max(1, int(len(dentro) * 0.8))

        a, b = self.t.desde, self.t.hasta
        if na is not None and abs(na - a) > 0.01 and (nb or b) - na > VIVE:
            # Se entra un pelín antes de la primera palabra, para no comerse el
            # ataque de la consonante.
            cand = round(max(0.0, na - 0.08), 3)
            if (antes_fin is None or cand >= antes_fin - 0.001) and mantiene(cand, b):
                a = cand
        if nb is not None and abs(nb - b) > 0.01 and nb - a > VIVE:
            cand = round(nb + 0.12, 3)
            if mantiene(a, cand):
                b = cand
        return None if self._igual(a, b) else Tramo(a, b, self.t.cinta)

    def _igual(self, a, b) -> bool:
        return abs(a - self.t.desde) <= 0.001 and abs(b - self.t.hasta) <= 0.001

    def __str__(self) -> str:
        return f"borde de {self.t}"
