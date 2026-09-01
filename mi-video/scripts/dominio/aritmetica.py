"""Los arreglos del corte que **no necesitan entender una frase**.

La distinción es del proyecto y está escrita en el log: *«aritmética, y corre
sola»*. Un corte que cae a mitad de palabra, dos trozos de la misma cinta que se
pisan, un resto de tres décimas sin una sola palabra dentro — nada de eso exige
leer lo que se dice, así que puede correr en la fase sin que nadie mire.

Y por eso `bordes` **no está aquí**: decidir si la palabra de delante es la
cabeza que falta o la cola de otra idea es criterio, y Jaime lo sacó del
automatismo — *«el detector apunta y tu decidas caso a caso»*. Lo que sí comparte
con estos es el mecanismo, `recorre`, porque recorrer los bordes de un montaje
aplicando lo que alguien proponga no es una decisión: es un bucle.

**Por qué es un objeto.** Los cinco eran funciones sueltas que abrían el mismo
fichero, montaban cada una su caché de palabras y escribían por su cuenta — cinco
copias del mismo bucle, y las copias no eran iguales.
"""
from __future__ import annotations

from .borde import Borde
from .habla import Habla
from .tijera import Tijera
from .tramo import Tramo


class Aritmetica:
    """Las garantías que el corte de `slug` tiene que cumplir, y se cumplen solas.

    Con `ver` no se escribe nada: se dice lo que se haría. Es el mismo código,
    que es lo que permite que una puerta pregunte por él en seco sin tener su
    propio criterio — un criterio aparte se separa del arreglo en la primera
    corrección.
    """

    __slots__ = ("slug", "ver", "tij")

    def __init__(self, slug, ver: bool = False):
        self.slug = str(slug)
        self.ver = bool(ver)
        self.tij = Tijera(self.slug)

    @property
    def existe(self) -> bool:
        return self.tij.existe

    def habla(self, cinta) -> Habla:
        """Las palabras de esa cinta. Las tiene el montaje, no cada paso."""
        return Habla.de(cinta, self.tij.m.palabras(cinta))

    # ── el mecanismo ────────────────────────────────────────────────────────
    def recorre(self, propone, resumen: str) -> int:
        """A cada borde se le pregunta, y lo que conteste se mueve.

        `propone(borde, i, tijera)` devuelve `(Tramo, qué se hizo)` o `None`.
        """
        if not self.existe:
            return 0
        tocados = 0
        for i in range(len(self.tij)):
            t = self.tij.tramo(i)
            h = self.habla(t.cinta)
            if not h:
                continue            # sin palabras no se puede afirmar nada
            propuesta = propone(Borde(t, h), i, self.tij)
            if propuesta is None:
                continue
            nuevo, dice = propuesta
            tocados += 1
            if self.ver:
                print(f"  {self.slug} e{self.tij.beat(i)}: {t} -> {nuevo}"
                      f"{'  ' + dice if dice else ''}")
            else:
                self.tij.mover(i, nuevo)
        if not self.ver:
            self.tij.guardar()
        print(f"{self.slug}: {tocados} {resumen}")
        return tocados

    # ── las garantías ───────────────────────────────────────────────────────
    def palabras_enteras(self) -> int:
        """Ningún corte cae dentro de una palabra. Ver `Borde.entero`."""
        return self.recorre(lambda b, i, t: _di(b.entero()),
                            "corte(s) sacados de dentro de una palabra")

    def ataques(self) -> int:
        """Ningún corte entra pisando la primera palabra. `Borde.con_ataque`.

        El suelo del retroceso lo pone el audio, no el texto: no se cruza el
        final del tramo de voz anterior —medido en `work/cuts`— ni el del trozo
        anterior del montaje. Medido en el lote: 42 cortes empezaban justo en el
        ataque.
        """
        from .cinta import Cinta

        vad: dict = {}

        def propone(b, i, tij):
            if b.t.cinta not in vad:
                vad[b.t.cinta] = Cinta(b.t.cinta).habla()
            pisos = [y + 0.01 for _, y in vad[b.t.cinta]
                     if y <= b.t.desde + 0.001]
            if i and tij.tramo(i - 1).cinta == b.t.cinta:
                pisos.append(tij.tramo(i - 1).hasta + 0.01)
            hecho = b.con_ataque(max(pisos) if pisos else None)
            return hecho and (hecho[0],
                              f"para que se oiga {hecho[1].texto!r}")

        return self.recorre(propone, "corte(s) respiran el ataque")

    def colas(self, pausas=()) -> int:
        """Ningún trozo entra antes de hablar ni se queda después de callar.

        `pausas` son las etapas donde el silencio **está declarado**: quitar aire
        es aritmética, conservarlo es una decisión, y ahí el silencio es el
        trabajo del beat.
        """
        ganado = []

        def propone(b, i, tij):
            if tij.beat(i) in pausas:
                return None
            nuevo = b.al_habla()
            if nuevo is None:
                return None
            ganado.append(b.t.dura - nuevo.dura)
            return nuevo, f"(-{ganado[-1]:.2f}s)"

        n = self.recorre(propone, "trozo(s) ajustados al habla")
        if n:
            print(f"  {self.slug}: -{sum(ganado):.1f}s de aire en los bordes")
        return n

    def mudos(self) -> int:
        """Fuera los trozos que no dicen ni una palabra entera. `Borde.mudo`."""
        if not self.existe:
            return 0
        fuera = []
        for i in range(len(self.tij)):
            t = self.tij.tramo(i)
            h = self.habla(t.cinta)
            # **Sin palabras no se declara mudo a nadie.** Esto miraba una caché
            # vacía igual que una llena, así que una cinta sin transcript
            # sostenible hacía desaparecer todos los trozos cortos de la pieza.
            if not h or not Borde(t, h).mudo:
                continue
            fuera.append(i)
            if self.ver:
                print(f"  {self.slug} e{self.tij.beat(i)}: fuera {t}"
                      f" ({t.dura:.2f}s sin una palabra)")
        if not self.ver and fuera:
            self.tij.quitar(fuera)
            self.tij.guardar()
        print(f"{self.slug}: {len(fuera)} trozo(s) mudos fuera")
        return len(fuera)

    def sin_solapes(self) -> int:
        """Dos trozos de la misma cinta no pueden pisarse: es audio repetido.

        Salió de una nota de Jaime sobre el primer render —«segundo 8 repite "eso
        no es"»— y eran cinco solapes en el lote, uno de **10,4 s** en `reel-01`:
        la convocatoria entera sonando dos veces.

        Se arregla por lo que significa: misma etapa, es el mismo tramo partido y
        se funden; etapas distintas, el segundo empieza donde acaba el primero.
        """
        if not self.existe:
            return 0
        tij = self.tij
        orden = sorted(range(len(tij)),
                       key=lambda i: (tij.tramo(i).cinta, tij.tramo(i).desde))
        fuera, tocados = set(), 0
        for k in range(len(orden) - 1):
            i, j = orden[k], orden[k + 1]
            a, b = tij.tramo(i), tij.tramo(j)
            if i in fuera or a.cinta != b.cinta or b.desde >= a.hasta - 0.05:
                continue
            tocados += 1
            # Recortarle la entrada al que cabía entero dentro del otro dejaría
            # un tramo que acaba antes de empezar, que es lo que `Tramo` ya no
            # deja escribir: fundirlo es lo único que se puede hacer.
            if tij.beat(i) == tij.beat(j) or b.hasta <= a.hasta + 0.001:
                hasta = max(a.hasta, b.hasta)
                tij.mover(i, Tramo(a.desde, hasta, a.cinta))
                fuera.add(j)
                dice = f"fundidos en [{a.desde:.2f}-{hasta:.2f}]"
            else:
                tij.mover(j, Tramo(a.hasta, b.hasta, b.cinta))
                dice = (f"entrada {b.desde:.2f} -> {a.hasta:.2f}"
                        f" (pisaba a e{tij.beat(i)})")
            if self.ver:
                print(f"  {self.slug} e{tij.beat(j)}: {dice}")
        if not self.ver:
            tij.quitar(fuera)
            tij.guardar()
        print(f"{self.slug}: {tocados} solape(s) resueltos")
        return tocados

    def pasada_callada(self, bar: float) -> tuple[int, float]:
        """Cada corte al punto más callado de su ventana. Devuelve `(n, dB)`.

        No pregunta al texto: mira la onda (ver `dominio.senal`). Y no estrecha
        un tramo hasta romperlo — por debajo de un cuarto de segundo el trozo
        deja de decir nada, así que ahí no se mueve nada.
        """
        import rutas

        from .senal import Senal

        if not self.existe:
            return 0, 0.0
        movidos, ganado = 0, []
        for i in range(len(self.tij)):
            t = self.tij.tramo(i)
            cinta = t.cinta or rutas.TOMAS.get(self.slug)
            if not cinta:
                continue
            senal = Senal(cinta)
            na, ga = senal.mas_callado(t.desde)
            nb, gb = senal.mas_callado(t.hasta)
            if ga < bar:
                na, ga = t.desde, 0.0
            if gb < bar:
                nb, gb = t.hasta, 0.0
            if nb - na <= 0.25 or (na == t.desde and nb == t.hasta):
                continue
            movidos += (na != t.desde) + (nb != t.hasta)
            ganado += [g for g in (ga, gb) if g > 0]
            if not self.ver:
                self.tij.mover(i, Tramo(na, nb, t.cinta))
        if not self.ver:
            self.tij.guardar()
        return movidos, (sum(ganado) / len(ganado) if ganado else 0.0)

    def __str__(self) -> str:
        return f"aritmetica de {self.slug}"


def _di(nuevo, dice: str = ""):
    return None if nuevo is None else (nuevo, dice)
