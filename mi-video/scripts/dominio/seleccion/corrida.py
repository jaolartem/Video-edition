"""La corrida entera de una pieza, paso a paso y en un solo sitio.

Estaba en el `main()` de `seleccionar.py`: doscientas cincuenta líneas donde el
orden de los pasos —que es lo que de verdad decide el corte— se leía entre los
`print`. Y el bloque que puntúa **estaba escrito dos veces**, una para la
corrida normal y otra para la escalera, con los comentarios sólo en la primera.
Dos copias de la regla que decide qué llega a candidata es exactamente la avería
que este proyecto paga cada vez.

El orden no es negociable y por eso está escrito una vez:

    puntuar → repartir → entrega → podar → costura → extremos
            → Jaime → volver a puntuar → tablero
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import basedatos  # noqa: E402
import beats  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402
import transcribir  # noqa: E402

from . import pesos  # noqa: E402
from .corpus import Corpus  # noqa: E402
from .entrega import Entrega  # noqa: E402
from .reparto import Reparto, con_toma, manda_jaime  # noqa: E402
from .tijeras import Tijeras, una_sola_vez  # noqa: E402


class Corrida:
    """Elegir qué trozo de cinta dice cada etapa de una pieza."""

    def __init__(self, n: int, propia: bool = False):
        self.n = n
        self.slug = f"reel-{n:02d}"
        self.toma = rutas.TOMAS[self.slug]
        self.libreto = beats.beats_del_libreto(n)
        self.frame = beats.frame_del_reel(n, self.libreto)
        self.marcas: list[list] = []
        self.plan: list = []
        self._tijeras: dict = {}
        # La cinta propia primero —para que la cadena secuencial siga teniendo
        # sentido— y detrás el resto del material.
        #
        # **El corpus se descubre, no se lee del mapa.** Esto decía
        # `rutas.TOMAS.values()`, el mapa reel -> cinta escrito a mano, y por eso
        # la búsqueda no salía de lo que alguien se había acordado de apuntar:
        # una cinta que la búsqueda no mira no tiene candidatas, y entonces «esa
        # frase no está grabada» es una afirmación sobre el mapa, no sobre el
        # material.
        toma = self.toma
        otras = [] if propia else [t for t in rutas.material() if t != toma]
        self.corpus = Corpus([toma] + otras)
        self._rotas: set | None = None

    # ── lo que la pieza pide en cada etapa ───────────────────────────────────
    @property
    def ventanas(self):
        return self.corpus.ventanas

    def parrafo(self, s0: int) -> str:
        return self.libreto[s0] if s0 < len(self.libreto) else ""

    def beat(self, s0: int) -> dict:
        return self.frame["beats"][s0] if s0 < len(self.frame["beats"]) else {}

    def exige(self, s0: int) -> list:
        return self.beat(s0).get("debe_decir") or []

    def tijeras(self, toma: str) -> Tijeras:
        if toma not in self._tijeras:
            self._tijeras[toma] = Tijeras(self.corpus.palabras(toma))
        return self._tijeras[toma]

    # ── 1. lo que vale cada ventana para cada etapa ──────────────────────────
    def puntuar(self) -> list[list]:
        """`marcas[s][k]`, o `None` si esa ventana no llega a candidata.

        Escrito una vez: la escalera vuelve a llamar aquí en vez de repetirlo.
        """
        self.marcas = []
        for s0, parr in enumerate(self.libreto):
            exige, fila = self.exige(s0), []
            sig = self.parrafo(s0 + 1)
            for v in self.ventanas:
                p, cubre, dice = v.puntua(parr, exige, sig)
                v.det[s0] = (cubre, dice)
                fila.append(p if v.compite(cubre, dice) else None)
            self.marcas.append(fila)
        return self.marcas

    def escalera(self, cuantos: int = 4) -> tuple[list, int]:
        """Preselecciona barato, afina lo preseleccionado y **reparte de cero**.

        Devuelve `(tramos afinados, cuántos)`. El reparto nuevo no es un segundo
        camino: es volver a puntuar sobre el corpus rehecho, que es lo que se
        hace siempre.
        """
        tramos = self.corpus.a_afinar(self.marcas, self.toma, cuantos)
        _d, n = transcribir.afinar(self.toma, tramos)
        registro.nota("seleccionar", "escalera",
                      detalle=f"{self.slug}: {n} tramos afinados")
        otras = [t for t in self.corpus.tomas if t != self.toma]
        self.corpus = Corpus([self.toma] + otras)
        self._tijeras.clear()
        self.puntuar()
        return tramos, n

    # ── 2. quién se queda con qué ────────────────────────────────────────────
    def rotas(self) -> set:
        """Las que `depurar` marcó porque su mensaje se parte al depurarlas.

        **Romper no elimina: pone handicap.** Jaime lo cortó: *«el criterio no es
        temporal, el criterio es emocional; la mejor es la que más comunique, no
        la que menos cortes tenga»*. Eliminar por número de costuras descarta
        justo a la que más comunica, porque la entrega viva trae falsos
        arranques. La rotura se paga en la **misma moneda que la entrega** —un
        escalón de voz— y se cobra en `Entrega.decide`.
        """
        if self._rotas is not None:
            return self._rotas
        con = basedatos.abrir(basedatos.BASE)
        fuera = con.execute(
            "select etapa_orden, desde, hasta from descartado where video_slug = ?",
            (self.slug,)).fetchall()
        con.close()
        self._rotas = {k for _s, dd, hh in fuera
                       for k, v in enumerate(self.ventanas)
                       if abs(v.a - dd) < 0.3 and abs(v.b - hh) < 0.3}
        return self._rotas

    def prioridades(self) -> dict:
        """Si cada etapa prioriza la entrega o la limpieza. Lo decidió el paso de
        descripción viendo la pieza entera; sin él, manda la entrega."""
        con = basedatos.abrir(basedatos.BASE)
        try:
            p = dict(con.execute(
                "select etapa_orden, prioridad from escena_desc"
                " where video_slug = ? and prioridad is not null", (self.slug,)))
        except sqlite3.OperationalError:
            p = {}
        con.close()
        return p

    def repartir(self) -> tuple[list, float]:
        """En orden de cinta si da, suelto si cubre más, y sin decir lo mismo dos
        veces. El orden de cinta es la preferencia, no la ley: una etapa vacía es
        un tablero más y una tirada de Jaime menos."""
        premio = [pesos.PREMIO_OBLIG if self.beat(i).get("obligatorio")
                  else pesos.PREMIO for i in range(len(self.libreto))]
        rep = Reparto(self.marcas, self.ventanas, premio)
        plan, total = rep.en_orden()
        suelto, total_s = rep.libre()
        if len(con_toma(suelto)) > len(con_toma(plan)):
            registro.nota("seleccionar", "reparto fuera de orden",
                          detalle=f"{self.slug}: {len(con_toma(suelto))} etapas"
                                  f" frente a {len(con_toma(plan))} en orden")
            plan, total = suelto, total_s
        self.plan = rep.sin_repetir(plan)
        return self.plan, total

    def entrega(self) -> list[tuple]:
        """El paso 3: entre las que dicen lo mismo, manda la voz."""
        e = Entrega(self.corpus, self.marcas, self.ventanas,
                    rotas=self.rotas(), prioridades=self.prioridades())
        return e.decide(self.plan)

    # ── 3. lo que sobra de la elegida ────────────────────────────────────────
    def limpiar(self) -> None:
        """Las tres tijeras, en el orden que importa: dentro, costura, extremos."""
        vs = self.ventanas
        for s0, k in enumerate(self.plan):
            if k is None:
                continue
            vs[k] = self.tijeras(vs[k].toma).dentro(
                vs[k], self.parrafo(s0), self.exige(s0))
        ult = None
        for k in self.plan:
            if k is None:
                continue
            if ult is not None:
                vs[k] = self.tijeras(vs[k].toma).costura(vs[ult].texto, vs[k])
            ult = k
        for k in self.plan:
            if k is None:
                continue
            antes = vs[k]
            habla = self.corpus.habla(antes.toma)
            despues = self.tijeras(antes.toma).extremos(antes).remedida(habla)
            # **El suelo se comprueba DESPUÉS de recortar, no sólo antes.**
            # `MIN_VOZ` filtra al construir las ventanas, pero el recorte y la
            # poda se aplican después y pueden dejarla en nada: el reel 5 salió
            # con una etapa de **0,16 segundos** —«un trimestre un año normal»—
            # que no es un enunciado, es un resto. Si recortar la deja por debajo
            # del suelo, el recorte era el error: se vuelve a la ventana entera.
            if despues.voz < pesos.MIN_VOZ <= antes.voz:
                registro.aviso("seleccionar", "el recorte dejaba la etapa en nada",
                               detalle=f"{self.slug} {despues.voz:.2f}s de"
                                       f" {antes.voz:.2f}s — se deja entera",
                               eco=False)
                despues = antes.remedida(habla)
            vs[k] = despues

    def de_jaime(self) -> None:
        """Lo que Jaime ya juzgó entra DESPUÉS de repartir y ANTES de volver a
        puntuar: así su rango se mide igual que los demás y sale en el informe."""
        self.plan = manda_jaime(self.plan, self.marcas, self.ventanas,
                                self.corpus, self.slug, self.toma)

    def repuntuar(self) -> list[tuple]:
        """**Recortar puede llevarse el dato declarado.**

        `dice` y `cubre` se calcularon sobre la ventana entera y después se le
        quitaron extremos: la etapa 7 del reel 1 salía marcada DICE con un texto
        donde la cifra ya no estaba. Se vuelve a puntuar sobre lo que de verdad
        queda, y si el dato se perdió se avisa — es el fallo silencioso de C-19.
        """
        perdidos = []
        for s0, k in enumerate(self.plan):
            if k is None:
                continue
            v = self.ventanas[k]
            exige = self.exige(s0)
            _p, cubre, dice = v.puntua(self.parrafo(s0), exige)
            antes = v.det.get(s0, (0, 0))[1]
            v.det[s0] = (cubre, dice)
            if antes and not dice:
                perdidos.append((s0 + 1, exige))
        return perdidos

    def a_tablero(self) -> list[tuple]:
        return Entrega(self.corpus, self.marcas, self.ventanas).a_tablero(
            self.plan, self.libreto)

    def repetidos(self) -> list[tuple]:
        return una_sola_vez(self.plan, self.ventanas, self.frame)
