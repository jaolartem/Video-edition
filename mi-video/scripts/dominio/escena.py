"""La descripción de una etapa: qué se guarda, y **quién manda sobre cada campo**.

`escena_desc` la escriben dos pasos distintos. `descrito` (7) planea la escena
—qué pasa, qué emoción, qué encargo— y `disenado` (7.5) contesta ese encargo con
el tablero. Son dos oficios: pedirle al diseñador que reenvíe la descripción
entera para cambiar un campo es invitarle a reescribir lo que no le toca.

**Y la regla de quién manda vivía dentro de un `INSERT`.** Un `UPDATE` que decía
`tablero=excluded.tablero` hacía que re-describir una etapa —lo normal, porque el
compositor no diseña— dejara el tablero en NULL: **borraba en silencio lo que el
diseñador había montado**, y en la siguiente corrida esa etapa salía sin nada. Se
arregló con un `coalesce` escrito a mano campo por campo, o sea con una regla de
propiedad expresada como cadena SQL: quien añada una columna mañana tiene que
acordarse de en cuál de las dos mitades va, y nada se lo dice.

Aquí se declara: dos tuplas, y la sentencia se deriva de ellas. Añadir un campo
es ponerlo en la lista que le toca, que es la pregunta que hay que contestar de
todas formas.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

from .pieza import Pieza  # noqa: E402

TABLA = "escena_desc"
#: Lo que identifica la fila. No se actualiza nunca: es la fila.
CLAVE = ("video_slug", "etapa_orden")

#: **Los campos de quien compone.** Una descripción nueva manda sobre ellos: si
#: los deja vacíos es porque decidió vaciarlos.
MANDA_QUIEN_COMPONE = (
    "que_pasa", "emocion", "grafico", "trato", "trato_porque", "prioridad",
    "integridad", "remedio", "corrige_dice", "corrige_es", "sobre_texto",
    "quien", "fecha",
)

#: **Los campos que otro paso llena, y que el silencio no borra.** `tablero` lo
#: monta el diseño; `componente`, `color`, `sonido` y `plano` pueden venir de una
#: corrida anterior. Que una descripción no los mencione significa «no tengo nada
#: que decir de esto», nunca «bórralo». Vaciarlos a propósito se hace desde el
#: paso que es su dueño.
NO_SE_BORRAN = ("tablero", "componente", "color", "sonido", "plano")

COLUMNAS = CLAVE + MANDA_QUIEN_COMPONE + NO_SE_BORRAN


class EscenaInvalida(ValueError):
    """Lo que llega no describe una escena. Se dice, no se guarda a medias."""


def _upsert() -> str:
    """La sentencia, derivada de quién manda sobre cada campo."""
    puesta = ", ".join(
        [f"{c}=excluded.{c}" for c in MANDA_QUIEN_COMPONE]
        + [f"{c}=coalesce(excluded.{c}, {TABLA}.{c})" for c in NO_SE_BORRAN])
    return (f"insert into {TABLA} ({', '.join(COLUMNAS)})"
            f" values ({', '.join('?' * len(COLUMNAS))})"
            f" on conflict({', '.join(CLAVE)}) do update set {puesta}")


class Escena:
    """La etapa `orden` de la pieza `slug`, tal y como quedó descrita."""

    __slots__ = ("slug", "orden")

    def __init__(self, slug: str, orden):
        self.slug = str(slug)
        self.orden = int(orden)

    # ── lo que la descripción describe ──────────────────────────────────────
    def sobre_texto(self) -> str | None:
        """El texto que la descripción describe, **leído del montaje**.

        No se recibe: se deriva. Un campo que el llamador puede olvidar es un
        campo que se olvida — `sobre_texto` llevaba 54 filas escritas a mano y
        ninguna línea de código que lo mantuviera, así que la puerta comparaba
        contra lo que alguien tecleó una vez.

        Y sale del montaje, no de la base: la base guarda **lo que se eligió** y
        el montaje es lo que sobrevivió a los recortes posteriores. Describir lo
        elegido y verificar lo montado es como se llegó a tener seis piezas
        descritas contra un texto que ya no existía.
        """
        return (Pieza(int(self.slug.split("-")[1])).texto or {}).get(self.orden)

    # ── guardar ─────────────────────────────────────────────────────────────
    def guardar(self, d: dict) -> dict:
        """Guarda la descripción. `ninguno` se guarda como NULL, no como texto."""
        if not isinstance(d, dict) or not (d.get("que_pasa") or "").strip():
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: una descripción sin `que_pasa` no"
                f" describe nada")
        corrige = d.get("corrige") or {}
        tablero = d.get("tablero")
        valores = {
            "video_slug": self.slug, "etapa_orden": self.orden,
            "que_pasa": d["que_pasa"], "emocion": d.get("emocion"),
            "grafico": d.get("grafico"), "trato": d.get("trato"),
            "trato_porque": d.get("trato_porque"),
            "prioridad": d.get("prioridad"), "integridad": d.get("integridad"),
            "remedio": d.get("remedio"), "corrige_dice": corrige.get("dice"),
            "corrige_es": corrige.get("es"), "sobre_texto": self.sobre_texto(),
            # `quien` decía «gemini» y esa vía se descartó —*«no quiero a
            # Google»*—, así que el campo mentía sobre quién decidió.
            "quien": d.get("quien", "cli"), "fecha": _ahora(),
            # **El tablero, como DATO y no como prosa.** Era un literal por pieza
            # en `reels-spec.mjs`, así que re-describir una etapa no cambiaba su
            # tablero: tres entregas iguales después de dos refactorizaciones.
            "tablero": (json.dumps(tablero, ensure_ascii=False)
                        if tablero not in (None, "", {}) else None),
            "componente": (None if d.get("componente") in (None, "ninguno")
                           else d["componente"]),
            "color": d.get("color"), "sonido": d.get("sonido"),
            "plano": d.get("plano"),
        }
        con = basedatos.abrir()
        con.execute(_upsert(), [valores[c] for c in COLUMNAS])
        con.commit()
        con.close()
        return {"ok": True}

    def poner_tablero(self, tablero: dict) -> dict:
        """Guarda SOLO el tablero. Es la entrega del paso de diseño.

        `tablero` es `{"kind": …, "props": {…}}`, que es lo que el render sabe
        montar. Si trae `fuente`, entra en `props.source` — el pie de
        cumplimiento.
        """
        if not isinstance(tablero, dict) or not tablero.get("kind"):
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: el tablero necesita `kind`")
        props = tablero.get("props")
        if not isinstance(props, dict) or not props:
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: el tablero necesita `props` con copy")
        fuente = tablero.get("fuente")
        if fuente and fuente != "sin cifra":
            props = {**props, "source": fuente}
        con = basedatos.abrir()
        n = con.execute(
            f"update {TABLA} set tablero = ?, fecha = ?"
            f" where video_slug = ? and etapa_orden = ?",
            (json.dumps({"kind": tablero["kind"], "props": props},
                        ensure_ascii=False),
             _ahora(), self.slug, self.orden)).rowcount
        con.commit()
        con.close()
        if not n:
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: no existe esa escena; descríbela antes")
        return {"ok": True, "slug": self.slug, "etapa": self.orden,
                "kind": tablero["kind"]}

    def __str__(self) -> str:
        return f"{self.slug} e{self.orden}"


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")
