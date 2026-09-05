"""¿Esto ya lo contestó Jaime? Se pregunta ANTES de parar la línea.

Jaime, después de contestar tres veces lo mismo: *«cada pasada estoy resolviendo
los mismos problemas porque no se están guardando mis decisiones; no quiero estar
decidiendo 5 veces lo mismo y menos 50 asuntos similares. Sistematiza mi
respuesta a las dudas y que las consulten antes de parar»*.

## Lo que fallaba, y no era que no se guardaran

Se guardaban. `revision` tiene sus palabras literales, `instruccion` sus reglas,
y `servicio.pedir()` ya las mete en todos los pedidos de IA. Lo que faltaba es
la otra mitad: **quien PARA la línea no preguntaba**.

Medido el 4 de septiembre: el montaje se detuvo con *«reel-03 e6: sin material y
sin tablero»*, y en la misma base estaban la nota **#661** —*«la 3, busca en el
corpus y si no la 2; el frame funciona cuando hay coherencia»*, o sea: aplícalo
igual y R3 se queda sin esa etapa— y la **#662**, que dice que el corpus se buscó
y no hay urgencia en esa cinta. Decidido dos veces, preguntado una tercera.

## Cómo se decide que algo está contestado

Tres condiciones, y tienen que darse las tres:

1. **Es de esta pieza**, o es una regla del lote entero.
2. **Habla de la misma etapa**, si el motivo nombra una. Un motivo del beat 6 no
   lo tapa una decisión sobre el beat 2 — y sin esto, con el vocabulario de este
   proyecto, casi todo taparía casi todo.
3. **Es suya.** Las notas guardan sus palabras literales en `que` y las
   instrucciones son suyas por definición; una observación que escribió un paso
   no decide nada.

## Y nunca calla en silencio

Un motivo contestado **dice qué decisión lo contesta**, con su número y sus
palabras. Es la diferencia entre una guarda que aprende y una guarda que se
afloja: si la decisión no venía a cuento se ve en el acto y se discute. Callar
sin decir por qué es como se pierde una comprobación — y este proyecto ya lo
pagó con la cortinilla, que siguió ofrecida en la carta después de retirarla.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"

#: Las palabras que no distinguen nada. Sin quitarlas, «el tablero» casaría con
#: cualquier motivo que hable de un tablero y la comprobación dejaría de valer.
VACIAS = {
    "esta", "este", "estas", "estos", "para", "porque", "pero", "como", "mas",
    "sobre", "cuando", "donde", "todo", "toda", "todos", "hay", "sino", "asi",
    "que", "los", "las", "del", "una", "unos", "unas", "con", "sin", "por",
}

#: Cuántas palabras de contenido tienen que coincidir para dar el motivo por
#: contestado. Dos es poco —«tablero» y «etapa» salen en todo—; cuatro deja
#: fuera decisiones escritas con otras palabras. Tres, **y además la etapa**,
#: que es lo que de verdad ata una decisión a un motivo.
COINCIDEN = 3


def _palabras(t: str) -> set:
    return {w for w in re.findall(r"[a-záéíóúñ]{4,}", (t or "").lower())
            if w not in VACIAS}


def _etapa(t: str):
    """El número de etapa que nombra un texto, si nombra alguno.

    Los tres nombres que este proyecto usa para lo mismo —`e6`, `etapa 6` y
    `beat 6`—, porque el motivo escribe uno y la decisión de Jaime escribe otro.
    Sin los tres, «reel-03 e6: sin material» y «sobre el beat 6» son la misma
    cosa para cualquiera que las lea y dos cosas distintas para el código.
    """
    m = re.search(r"\b(?:e|etapa\s*|beat\s*)(\d{1,2})\b", (t or "").lower())
    return int(m.group(1)) if m else None


def suyas(slug):
    """Lo que Jaime ha decidido y puede contestar un motivo de esta pieza."""
    fuera = []
    try:
        cx = basedatos.abrir(BASE)
        cx.row_factory = sqlite3.Row
        for r in cx.execute(
                "select id, que from revision where video_slug = ?"
                " and que like '%Jaime%'", (slug,)):
            fuera.append((f"nota #{r['id']}", r["que"]))
        for r in cx.execute(
                "select id, dijo from instruccion where estado != 'descartada'"
                " and (ambito = 'lote' or pieza = ?)", (slug,)):
            fuera.append((f"instruccion #{r['id']}", r["dijo"]))
    except sqlite3.Error:
        return []
    return fuera


def contestado(motivo: str, slug: str):
    """Qué decisión suya cubre este motivo, o `None`.

    Devuelve `(de_donde, sus_palabras)` para poder decirlo en pantalla. Esto no
    silencia nada: da con qué explicarlo.
    """
    quiere = _palabras(motivo)
    etapa = _etapa(motivo)
    for de_donde, texto in suyas(slug):
        suya = _etapa(texto)
        # **La etapa ata mejor que las palabras, y por eso va primero.**
        #
        # El primer intento cruzaba vocabulario y no encontró nada: el motivo
        # decía «reel-03 e6: sin material y sin tablero» y la decisión de Jaime
        # decía «sobre el beat 6: la 3, busca en el corpus y si no la 2». Las
        # dos hablan de lo mismo y no comparten una sola palabra de contenido —
        # él decide sobre la PIEZA y la máquina informa sobre su MECANISMO.
        #
        # Misma pieza y misma etapa, dicho por él: **ésa es toda la señal, y no
        # hay segunda.** Probé una rama de reserva por vocabulario para los
        # motivos que no nombran etapa, y produjo lo peor que esto puede
        # producir: dio por decidido *«reel-05: pedido(s) de IA sin contestar»*
        # citando *«nunca un cliente es un caso real»*. Coincidían en «decisión»,
        # «pieza» y «reel» — palabras del proceso, no del asunto.
        #
        # Un motivo silenciado por una decisión que no venía a cuento es peor que
        # un motivo de más: el de más se ve y se contesta; el silenciado sale por
        # la puerta de la entrega. Así que sin etapa no se contesta nada, y se
        # para. Equivocarse hacia preguntar cuesta un turno suyo; equivocarse
        # hacia callar cuesta una pieza mal publicada.
        if etapa is not None and suya == etapa:
            return de_donde, " ".join((texto or "").split())[:150]
    return None
