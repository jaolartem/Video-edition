"""Quién puede trabajar a la vez, y quién tiene que esperar a quién.

**El problema que resuelve, medido el 1 de septiembre.** `avanzar` recorría las
piezas de una en una, así que el paso más lento paraba a las siete: tres cintas
transcribiéndose bloquearon media hora a cuatro piezas que no usan ninguna de
esas tres. La espera no era necesaria — era el orden del bucle.

**Y la dependencia real no es entre piezas: es entre pieza y cinta.** reel-06
sale de una sola grabación y reel-07 de cuatro. Que reel-04 esté afinando
`20260825_225808` no tiene por qué detener a reel-06, que no la toca.

**Qué se serializa, exactamente.** Sólo los pasos que **reescriben una cinta**,
y sólo contra las piezas que comparten esa cinta. Lo declara el propio paso con
`Servicio.escribe_cintas`; el motor no lo adivina. Todo lo demás —cortar, medir,
coser, describir— trabaja sobre el EDL y las filas de su pieza, y desde que la
base está en WAL eso puede pasar a la vez.

**Por qué el candado va en el paso y no en la pieza.** Bloquear la pieza entera
sería correcto y casi inútil: con las cintas de hoy casi todas comparten
`20260825_225808`, así que serían dos grupos y poco más. Bloqueando sólo el paso
que escribe, una pieza puede estar cosiendo mientras otra afina la cinta que
comparten — que es la mayor parte del tiempo.

**Lo que NO hace, y es a propósito:** no mete hilos dentro de un paso. Whisper,
ffmpeg y Remotion ya son procesos que usan la máquina entera; envolverlos en
hilos no acelera nada y sí complica el estado. Aquí sólo se solapan pasos de
piezas distintas.
"""
from __future__ import annotations

import contextlib
import threading


class Planificador:
    """Recorre varias piezas a la vez, respetando quién escribe qué cinta."""

    def __init__(self, hilos: int = 4):
        self.hilos = max(1, int(hilos))
        self._candados: dict = {}
        self._reparto = threading.Lock()
        #: Para el parte: cuántas veces alguien tuvo que esperar de verdad.
        self.esperas = 0

    def _candado(self, cinta: str) -> threading.Lock:
        with self._reparto:
            return self._candados.setdefault(cinta, threading.Lock())

    @contextlib.contextmanager
    def permiso(self, servicio, pieza):
        """El turno para correr ese paso sobre esa pieza.

        Si el paso no reescribe cintas, no hay turno que pedir: pasa. Si lo
        hace, se toman los candados de **sus** cintas y en orden alfabético —
        siempre el mismo orden, que es lo que impide que dos piezas se queden
        esperándose la una a la otra para siempre.
        """
        if not getattr(servicio, "escribe_cintas", False):
            yield
            return
        cintas = sorted(pieza.cintas)
        if not cintas:
            yield
            return
        tomados = []
        try:
            for c in cintas:
                cand = self._candado(c)
                if not cand.acquire(blocking=False):
                    with self._reparto:
                        self.esperas += 1
                    cand.acquire()
                tomados.append(cand)
            yield
        finally:
            for cand in reversed(tomados):
                cand.release()

    def correr(self, piezas, trabajo):
        """Lanza `trabajo(n)` por cada pieza y devuelve `{n: resultado}`.

        Los resultados se guardan y se imprimen fuera, no según van cayendo:
        con varias piezas a la vez, el parte por orden de llegada es ilegible y
        además cambia entre corridas iguales.
        """
        from concurrent.futures import ThreadPoolExecutor

        piezas = list(piezas)
        if self.hilos == 1 or len(piezas) < 2:
            return {n: trabajo(n) for n in piezas}
        salida: dict = {}
        with ThreadPoolExecutor(max_workers=self.hilos) as pool:
            futuros = {pool.submit(trabajo, n): n for n in piezas}
            for f, n in futuros.items():
                try:
                    salida[n] = f.result()
                except Exception as e:                 # noqa: BLE001
                    # **Una pieza que revienta no se lleva a las otras seis.**
                    # Se guarda el motivo y se sigue: el parte del final dice
                    # cuál cayó y por qué, que es más útil que una traza sola.
                    #
                    # **Y va al log, no sólo al parte.** El parte se lo lleva el
                    # viento en cuanto acaba la corrida; lo que queda en
                    # `incidencia` se puede mirar mañana. Un fallo que sólo
                    # existe en la pantalla es un fallo que no ocurrió.
                    import registro

                    slug = f"reel-{int(n):02d}"
                    motivo = f"{type(e).__name__}: {str(e)[:200]}"
                    registro.aviso("planificador", "la pieza revento en su hilo",
                                   detalle=f"{slug}: {motivo}"[:600], eco=True)
                    salida[n] = {"slug": slug, "fase": "?", "saltos": 0,
                                 "motivo": motivo[:300]}
        return salida
