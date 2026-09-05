"""Una grabación: su audio, su habla medida y sus palabras.

**Por qué es un objeto.** Lo que hoy se sabe de una cinta estaba repartido entre
`transcribir.py` (28 funciones sueltas), `rutas.TOMAS`, los ficheros de
`work/cuts/`, `beats.py` y **siete copias a mano del mapa de reel a cinta**.
Nadie poseía la cinta, así que cada sitio decidía por su cuenta qué era verdad
de ella — y las averías del 31 de agosto salieron todas de ahí:

- 194 s de habla sin una sola palabra viajaron enteros, porque el guarda que lo
  mide vivía en un `main()` y la línea entra por otra puerta (C-147);
- una cinta de una sola pasada pasó el sello, porque se comprobaba que la clave
  existiera y no lo que decía (C-148);
- 186 palabras cruzaban silencio medido inventando 620 s de duración.

Aquí la cinta responde por sí misma, y lo hace **una vez y para todos**.
"""
from __future__ import annotations

import dataclasses
import json
import os

from .habla import AIRE
from .palabra import Palabra

#: Habla medida sin una sola palabra por encima de esto: la cinta no sirve.
#: Es el mismo número que usa el paso que la repara, para que los dos digan lo
#: mismo — un umbral repetido con dos valores son dos reglas.
SIN_TEXTO_MAX = 20.0
#: Por debajo de dos pasadas el transcript se come frases y se queda pegado.
PASADAS_MIN = 2.0

#: La pausa que `cut-silence.py` respeta, y el margen que deja a cada lado del
#: corte para no comerse el ataque de la consonante.
PAUSA = 0.45
MARGEN = 0.06
#: **El silencio que un tramo de `work/cuts` lleva pegado a cada extremo.**
#:
#: No es un detalle del fichero: es la diferencia entre lo que el tramo declara
#: y lo que se oye. `build_segments` conserva `PAUSA/2 + MARGEN` de silencio por
#: delante y por detrás, así que **un tramo empieza 0,285 s antes de que suene
#: la voz** y acaba 0,285 s después de que calle. Medido sobre 39 tramos de tres
#: cintas: mediana 0,28-0,29 s de desfase entre el arranque declarado y el real.
#:
#: Vive aquí, que es quien LEE los tramos, y `cut-silence.py` —quien los
#: escribe— lo importa de aquí. Escrito en los dos sitios son dos reglas: basta
#: que alguien corra el detector con otro `--keep` para que este fichero mienta.
HOLGURA = PAUSA / 2 + MARGEN


class CintaIncompleta(Exception):
    """Tiene habla sin texto. No es «rehazla»: es «tápale los huecos».

    Excepción propia a propósito: el bucle que transcribe caza `SystemExit`
    como «rehazla entera», y eso son treinta minutos de CPU repitiendo el
    barrido que ya dejó esos tramos vacíos.
    """


@dataclasses.dataclass(frozen=True, slots=True)
class Cinta:
    """La grabación `nombre`, tal y como se puede sostener hoy."""

    nombre: str

    # ── dónde vive ───────────────────────────────────────────────────────────
    @property
    def transcript(self) -> str:
        return f"work/transcripts/{self.nombre}.json"

    @property
    def cortes(self) -> str:
        return f"work/cuts/{self.nombre}.json"

    def existe(self) -> bool:
        return os.path.exists(self.transcript)

    # ── lo que se midió sobre la onda ────────────────────────────────────────
    def habla(self) -> list:
        """Los tramos con voz, medidos por el detector de silencio.

        Es el único «esto suena» que no depende de ningún modelo, así que es
        contra esto contra lo que se comprueba todo lo demás.
        """
        try:
            with open(self.cortes, encoding="utf-8") as f:
                return [(float(a), float(b)) for a, b in json.load(f)["segmentos"]]
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def voz(self) -> list:
        """Los mismos tramos **sin la holgura**: donde de verdad suena la voz.

        `habla()` devuelve lo que el detector conservó, y eso lleva `HOLGURA` de
        silencio a cada lado. Quien pregunta «¿estaba hablando en el segundo
        384,695?» no quiere lo conservado: quiere lo que se oye.
        """
        return [(a + HOLGURA, b - HOLGURA) for a, b in self.habla()
                if b - a > 2 * HOLGURA]

    # ── lo que dijo el modelo, ya sostenible ─────────────────────────────────
    def palabras(self) -> list:
        """Las palabras de la cinta, **pegadas al habla y con orden**.

        Dos arreglos que no son de quien llama sino de la cinta:

        1. **Ninguna palabra suena donde se midió silencio.** El modelo reparte
           los tiempos dentro de su ventana y cuando calla estira la última.
        2. **Ninguna empieza después de que la voz haya arrancado.** Es la misma
           avería por el otro extremo, y es la que dejaba entrar el corte a
           mitad de palabra: la primera palabra de un tramo empieza cuando el
           tramo empieza a sonar, no cuando el modelo se dio cuenta.
        3. **Ninguna se queda sin tiempo.** Una palabra de ancho cero no se
           puede ordenar contra sus vecinas: el subtítulo la repite, y un corte
           que empiece en su instante se la lleva sin que nadie lo cuente.
        """
        import bisect

        d = self._crudo()
        ws = [Palabra.de_dict(w) for w in (d.get("segmentos") or [])]
        ws.sort(key=lambda p: p.empieza)
        runs = self.habla()
        if runs:
            ini = [a for a, _ in runs]
            fin = [b for _, b in runs]
            pegadas, primera = [], set()
            for p in ws:
                i = bisect.bisect_right(ini, p.empieza) - 1
                # La que empieza fuera de todo tramo no se toca: ahí tampoco
                # sabemos dónde empieza, y moverla sería adivinar.
                if i < 0 or p.empieza >= fin[i]:
                    pegadas.append(p)
                    continue
                if i not in primera:
                    primera.add(i)
                    p = p.desde_el_ataque(min(ini[i] + HOLGURA, fin[i]), AIRE)
                pegadas.append(p.pegada_a(fin[i]))
            ws = pegadas
        return self._con_sitio(ws)

    @staticmethod
    def _con_sitio(ws: list) -> list:
        """Reparte el hueco libre entre las palabras que se quedaron sin tiempo.

        **Por bloque, no una a una.** El modelo no estampa una palabra suelta en
        el mismo instante: estampa un grupo entero —«de septiembre le explico el
        resto», siete palabras en el segundo 45,843— y la de al lado empieza en
        ese mismo instante, así que preguntando sólo por la siguiente no hay
        hueco y no se puede ordenar ninguna. El hueco de verdad llega hasta el
        siguiente arranque **distinto**, y se parte entre las del bloque.

        Cuando el hueco no da ni para el mínimo, cada palabra queda marcada
        `sin_sitio`: no se borra —eso lo decide quien monta— pero deja de poder
        pasar por texto que suena ahí.
        """
        out, k = [], 0
        while k < len(ws):
            p = ws[k]
            if not p.sin_duracion:
                out.append(p)
                k += 1
                continue
            j = k
            while j < len(ws) and ws[j].empieza <= p.empieza:
                j += 1
            tope = ws[j].empieza if j < len(ws) else p.empieza
            bloque = ws[k:j]
            paso = max(0.0, tope - p.empieza) / max(len(bloque), 1)
            for i, q in enumerate(bloque):
                a = p.empieza + i * paso
                out.append(q.en_el_hueco(a, a + paso) if q.sin_duracion else q)
            k = j
        return out

    # ── si se puede usar ─────────────────────────────────────────────────────
    def pasadas(self) -> float:
        return float(self._crudo().get("pasadas") or 0)

    def sin_texto(self) -> float:
        """Segundos de habla medida sin una sola palabra dentro."""
        return sum(b - a for a, b in self.huecos())

    def huecos(self, minimo: float = 1.0) -> list:
        """**Dónde** falta el texto, no sólo cuánto: se afinan uno a uno.

        Los declarados como oídos y descartados no vuelven a parar el paso: esa
        decisión está escrita y se puede discutir.
        """
        ws = self.palabras()
        hue = [(a, b) for a, b in self.habla()
               if b - a >= minimo and not any(a <= p.empieza < b for p in ws)]
        return [x for x in hue if not self._descartado(*x)]

    def exigir(self, cobertura: bool = True, varias: bool = True) -> None:
        """La cinta sirve, o se para. Sin avisos que nadie lee.

        Es la puerta: existencia, sello, frescura y cobertura. Lo que no pase
        por aquí puede seguir leyendo el fichero, y eso es exactamente lo que
        dejó viajar media cinta sin texto durante semanas.
        """
        receta = "  ->  python scripts/transcribir.py --toma <N>"
        if not self.existe():
            raise SystemExit(f"falta {self.transcript}. Los subtitulos van"
                             f" PRIMERO." + receta)
        d = self._crudo()
        if "pasadas" not in d or (varias and self.pasadas() < PASADAS_MIN):
            raise SystemExit(
                f"{self.transcript} es de UNA pasada de whisper y no sirve: se"
                f" come frases, se queda pegado y no puntua." + receta)
        if (os.path.exists(self.cortes)
                and os.path.getmtime(self.cortes)
                > os.path.getmtime(self.transcript)):
            raise SystemExit(
                f"{self.transcript} es mas viejo que {self.cortes}: los tramos"
                f" cambiaron despues de transcribir." + receta)
        if cobertura:
            falta = self.sin_texto()
            if falta > SIN_TEXTO_MAX:
                raise CintaIncompleta(
                    f"{self.transcript}: {falta:.0f}s de habla medida sin una"
                    f" sola palabra. Lo que se decide por palabra no puede"
                    f" verla." + receta)

    def datos(self) -> dict:
        """Lo que hay escrito en el transcript, tal cual.

        Público porque el fichero lleva cosas que no son de la cinta —el modelo
        con que se hizo, el acuerdo entre pasadas, los tramos con su texto— y
        quien las necesita no tiene por qué pedirlas por la puerta de atrás.
        Las **palabras** no se sacan de aquí: se piden a `palabras()`, que es
        donde están pegadas al habla.
        """
        return self._crudo()

    # ── lo de dentro ─────────────────────────────────────────────────────────
    def _crudo(self) -> dict:
        with open(self.transcript, encoding="utf-8") as f:
            return json.load(f)

    def _descartado(self, a: float, b: float) -> bool:
        import basedatos

        try:
            cx = basedatos.abrir()
            ya = cx.execute("select desde, hasta from hueco_oido"
                            " where toma = ? and veredicto = 'descartado'",
                            (self.nombre,)).fetchall()
            cx.close()
        except Exception:                          # noqa: BLE001
            return False
        return any(abs(a - d) < 0.3 and abs(b - h) < 0.3 for d, h in ya)

    def __str__(self) -> str:
        return self.nombre
