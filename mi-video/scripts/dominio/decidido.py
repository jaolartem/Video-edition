"""Lo que ya está decidido de una pieza, **y de dónde sale cada cosa**.

Antes de montar nada hay decisiones tomadas, y no son heurísticas: son de oído o
de sentido, y el código las **ejecuta**, no las discute. Vienen de dos sitios y
ninguno de los dos es este fichero:

    la base        `estado.del_reel(n)` — aprobado, rechazado, recortar
    el paso 2      `work/asignacion/reel-NN.json` — qué unidad dice cada etapa

**Por qué es un objeto.** Estaban como cuatro diccionarios sueltos y un `set`
—`asignado`, `propuesto`, `refutado`, `tramos_decl`— construidos en medio de
`montar()` y leídos treinta líneas más abajo con `(i + 1) in …`. Con eso, la
guarda de «una etapa refutada no vuelve a concurso» **se perdió al reordenar el
fichero** y tres etapas refutadas salieron montadas en el reel 4. Una regla que
depende de que nadie mueva un `if` no es una regla.

La pregunta que ordena todo esto es la de CLAUDE.md: **«¿de dónde lo lee el que
monta?»**. Aquí, de un solo sitio.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import estado as _estado  # noqa: E402


class Decidido:
    """Las decisiones ya tomadas para `reel-NN`, listas para consultar por etapa."""

    def __init__(self, n: int, avisar=None):
        self.n = int(n)
        self.slug = f"reel-{self.n:02d}"
        #: Tal cual sale de la base: lo que `montar` devuelve y `revision` lee.
        self.fijados = _estado.del_reel(self.n)
        self.asignado, self.propuesto = {}, {}
        self.refutado, self.tramos_decl = set(), {}
        self._leer_paso2(avisar)

    # ── lo que dijo el paso 2 ────────────────────────────────────────────────
    def _leer_paso2(self, avisar) -> None:
        """**La asignación del paso 2 manda sobre la puntuación de texto.**

        Faltaba esto y era el hueco del proceso: la IA elegía por sentido y
        `beats.py` seguía eligiendo por su cuenta con solapamiento de palabras,
        que es justo el criterio que fallaba. Si existe la asignación, el texto
        ya no elige — sólo desempata cuando no hay asignación para esa etapa.
        """
        f = f"work/asignacion/{self.slug}.json"
        if not os.path.exists(f):
            return
        with open(f, encoding="utf-8") as fh:
            filas = json.load(fh)["asignaciones"]
        for a in filas:
            if a.get("unidad_id") is None:
                continue
            self.propuesto[a["etapa_n"]] = a["unidad_id"]
            if a.get("sostiene"):
                self.asignado[a["etapa_n"]] = a["unidad_id"]
            elif a.get("tramos"):
                self.tramos_decl[a["etapa_n"]] = a["tramos"]
            else:
                self.refutado.add(a["etapa_n"])
        # **Un `null` sostenido tambien es una decision.** El paso 2 puede decir
        # «ninguna unidad sirve» y la refutacion darle la razon; eso es tan
        # vinculante como una asignacion. Sin esto la etapa caia al concurso de
        # texto y salia elegida justo la unidad que el refutador habia
        # descartado por su nombre — pasaba en la urgencia del reel 3.
        for a in filas:
            if a.get("unidad_id") is None and a.get("sostiene"):
                self.refutado.add(a["etapa_n"])
        if avisar:
            avisar(f"  paso 2: {len(self.asignado)} etapas asignadas por sentido")

    # ── lo que Jaime dejó dicho de oído ──────────────────────────────────────
    def guardado(self, etapa) -> dict:
        """Lo que la base guarda de esa etapa. `{}` si nunca se tocó."""
        return self.fijados.get(str(etapa.n), {}) or {}

    def estado(self, etapa) -> str:
        """`aprobado`, `rechazado`, `recortar` o vacío."""
        return self.guardado(etapa).get("estado") or ""

    def aprobada(self, etapa) -> bool:
        """**Lo aprobado no se re-elige.**

        Idea de Jaime: una base que registre qué segmento está bien y cuál no,
        para que al corregir uno no se muevan los demás. Es el aprendizaje 13
        resuelto de forma estructural — ya no depende de que alguien recuerde
        re-imponer lo elegido de oído.
        """
        return self.estado(etapa) == "aprobado"

    def rechazada(self, etapa) -> bool:
        return self.estado(etapa) == "rechazado"

    # ── qué unidad le toca a una etapa ───────────────────────────────────────
    def tramos_declarados(self, etapa):
        """Los tramos que se eligieron de oído, o `None`.

        Cuando la frase que la etapa necesita está partida en la cinta por un
        intento fallido en medio, no hay heurística que lo resuelva. El caso:
        *«no siempre el que paga MAS impuestos es el que menos trabaja, es el
        que menos sabe»*. Entre las dos mitades hay una autocorrección que
        **invierte el sentido** y dos «muy regularmente». La regla de quedarse
        con la última (aprendizaje 25) elegiría justo la equivocada, así que
        aquí decide el oído y el código lo ejecuta igual siempre.
        """
        return self.tramos_decl.get(etapa.n)

    def asignada(self, etapa):
        """El índice de la unidad que el paso 2 sostiene para esta etapa."""
        return self.asignado.get(etapa.n)

    def refutada(self, etapa) -> bool:
        """**Una etapa refutada va con tarjeta, no vuelve a concurso.**

        El paso 2 la tumba por una razón escrita y sin esto la etapa caía al
        concurso de texto, que **volvía a elegir la misma unidad** — justo el
        criterio que la refutación venía a corregir.
        """
        return etapa.n in self.refutado and etapa.n not in self.asignado

    def recorta_en_vez_de_tumbar(self, etapa) -> None:
        """**`recortar` conserva la unidad.**

        Cuando Jaime dice que un segmento no sirve por dónde entra, la respuesta
        es recortarlo, no tirarlo — así que se toma la unidad que el paso 2
        propuso aunque la refutación la tumbara, y el recorte la arregla. Tumbar
        y recortar son respuestas a problemas distintos: una frase que no dice
        el beat se tira; una que lo dice pero arranca mal, se recorta.
        """
        if self.estado(etapa) == "recortar" and etapa.n in self.propuesto:
            self.asignado[etapa.n] = self.propuesto[etapa.n]

    def olvida_asignacion(self, etapa) -> None:
        """La asignación estaba vieja: no dice lo que la etapa exige.

        Puede ser de una pasada anterior, con otras unidades y otro criterio; la
        intención comunicativa está declarada en el frame y es lo que no cambia.
        Si ni la unidad asignada ni el barrido hacia delante llegan a decirlo, se
        vuelve al concurso, que **sí** filtra por `debe_decir`.
        """
        self.asignado.pop(etapa.n, None)

    # ── los recortes finos ───────────────────────────────────────────────────
    def ajustes(self, frame) -> dict:
        """Dónde entra y dónde sale cada etapa, del frame **y** de la base.

        Una unidad puede arrancar con el intento fallido que la precede — el
        reel 1 empieza su etapa 7 con un «hasta 500» suelto antes de la frase
        buena. Recortar eso es ejecución, no mensaje, así que no se consulta: se
        declara y se aplica. Los recortes que Jaime marcó en la base entran por
        la misma puerta que los declarados en `frames.json`.
        """
        fuera = dict(frame.get("ajustes", {}))
        for k, v in self.fijados.items():
            if v.get("estado") == "recortar":
                if v.get("entra_en"):
                    fuera[f"beat_{k}_entra_en"] = v["entra_en"]
                if v.get("sale_en"):
                    fuera[f"beat_{k}_sale_en"] = v["sale_en"]
        return fuera

    def __str__(self) -> str:
        return (f"decidido de {self.slug}: {len(self.asignado)} asignadas,"
                f" {len(self.refutado)} refutadas, {len(self.fijados)} de oído")
