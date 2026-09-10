"""Un segmento de la pieza: la unidad con la que se revisa y se aprueba.

Jaime, 10-9-2026: *«en el Json van los segmentos del video, y van los que estan
aprobados y los que no; la aprobacion de la pieza es igual a la aprobacion de
todos los segmentos, y cada segmento se debe revisar como la unidad de
analisis»*.

## Y no es una idea nueva: es la que estaba escrita sin nadie que la sostuviera

`CLAUDE.md` lleva desde el principio diciendo *«la unidad de analisis es el
segmento, no el video ni el guion: la seccion de frame, union de lo teorico —el
libreto— y lo practico —la grabacion»*. Pero aprobar era un veredicto sobre la
pieza entera: `aprobacion` es `version_id, veredicto, quien` y no sabe decir
«la etapa 3 esta bien y la 1 no». Por eso una correccion de un tramo volvia a
poner en juego las seis, y por eso «lo aprobado no se rediscute» no se podia
cumplir — no habia con que.

## Aprobado CONTRA UN CORTE, que es lo unico que lo hace verdad

Un segmento no se aprueba en abstracto: se aprueba tal y como suena hoy. Si su
tramo se mueve, lo aprobado era otra cosa. Por eso la fila lleva la **huella**
de sus tramos y deja de aplicar sola cuando el corte cambia, sin que nadie
tenga que acordarse de retirarla. Es la misma vara que `corte_fijo` usa para
sus declaraciones y `ticket` para sus quejas.

## Donde vive, y por que no en el JSON

El marcador de la pieza —`ads/<slug>/estado.json`— **se borra al cerrar**: es
memoria de trabajo. Una aprobacion tiene que sobrevivir a eso, asi que la fila
va en la base y el JSON la publica. El agente escribe en el JSON, `estado`
aplica lo que escribio, y aqui queda.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os

#: Las dos formas de entrar a una pieza, y no hay una tercera. Jaime,
#: 10-9-2026: *«dos modos: refactor, que es todo el documento, o segmento por
#: segmento, que ya esta declarado en el Json»*.
REFACTOR = "refactor"
SEGMENTO = "segmento"

#: La etiqueta que saca a un segmento de la lista de trabajo.
APROBADO = "aprobado"

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _con():
    from . import ticket as _t

    return _t._con()


class Segmento:
    """La etapa `n` de `slug`, con sus tramos y su estado de aprobacion."""

    __slots__ = ("slug", "n", "tramos", "dice")

    def __init__(self, slug, n, tramos, dice=""):
        self.slug, self.n = slug, int(n)
        self.tramos = [(round(a, 3), round(b, 3)) for a, b in tramos]
        self.dice = " ".join((dice or "").split())[:220]

    # ── de donde salen ──────────────────────────────────────────────────────
    @classmethod
    def de(cls, slug):
        """Los segmentos de una pieza, leidos de su EDL. En orden de etapa."""
        r = os.path.join(RAIZ, "ads", slug, "edl-sell.json")
        try:
            edl = json.load(open(r, encoding="utf-8"))
        except (OSError, ValueError):
            return []
        por = {}
        for (a, b), d in zip(edl.get("segmentos", []), edl.get("detalle", [])):
            k = d.get("beat")
            if k is None:
                continue
            e = por.setdefault(k, {"tramos": [], "dice": []})
            e["tramos"].append((a, b))
            if d.get("texto"):
                e["dice"].append(d["texto"])
        return [cls(slug, k, v["tramos"], " / ".join(v["dice"]))
                for k, v in sorted(por.items())]

    # ── su verdad ───────────────────────────────────────────────────────────
    @property
    def huella(self) -> str:
        """Los tramos de este segmento, reducidos a doce caracteres.

        Es contra lo que se aprobo. Se redondea a la milesima a proposito: el
        paso `afinado` reescribe los transcripts y los bordes bailan
        microsegundos sin que cambie una sola palabra.
        """
        crudo = ";".join(f"{a:.3f}-{b:.3f}" for a, b in self.tramos)
        return hashlib.sha1(crudo.encode()).hexdigest()[:12]

    @property
    def dura(self) -> float:
        return round(sum(b - a for a, b in self.tramos), 3)

    def _fila(self):
        """Lo etiquetado para este segmento, **contra su corte de hoy**.

        Jaime, 10-9-2026: *«ahora la fuente de verdad es el Json, una sola
        fuente»*. Asi que se mira ahi primero: el marcador es lo que el oficio
        puede abrir y escribir, y tener dos sitios donde leer lo mismo es la
        averia que este proyecto lleva persiguiendo desde el principio.

        La base es la **copia que sobrevive**: el marcador se borra al cerrar la
        pieza —memoria de trabajo— y entonces la fila es lo unico que queda. Por
        eso se lee de segunda y nunca por delante.
        """
        from . import estado as _e

        for f in (_e.lee(self.slug).get("segmentos") or []):
            if f.get("etapa") == self.n and f.get("huella") == self.huella:
                return {"etiqueta": f.get("etiqueta") or "",
                        "quien": f.get("por") or "", "cuando": ""}
        cx = _con()
        r = cx.execute(
            "select etiqueta, huella, quien, cuando from segmento s"
            " join video v on v.id = s.video_id"
            " where v.slug = ? and s.etapa = ?", (self.slug, self.n)).fetchone()
        cx.close()
        return dict(r) if (r and r["huella"] == self.huella) else None

    @property
    def etiqueta(self) -> str:
        """Donde esta ESTE segmento. Vacio es «abierto, nadie lo ha mirado».

        Y vacio es tambien lo que devuelve cuando su corte se movio: la
        etiqueta se puso contra otros tramos, asi que no dice nada de estos.
        """
        r = self._fila()
        return (r["etiqueta"] if r else "") or ""

    @property
    def aprobado(self) -> bool:
        return self.etiqueta == APROBADO

    @property
    def por_quien(self) -> str:
        r = self._fila()
        return (r["quien"] if r else "") or ""

    # ── lo que se puede hacer con el ────────────────────────────────────────
    def mueve(self, etiqueta, quien):
        """Le pone su etiqueta, contra el corte que tiene hoy.

        Es lo que escribe el que trabaja —un oficio por el marcador, un paso de
        codigo por aqui—, y es lo unico que hace avanzar a un segmento.
        """
        cx = _con()
        v = cx.execute("select id from video where slug = ?",
                       (self.slug,)).fetchone()
        if not v:
            cx.close()
            return False
        cx.execute(
            "insert into segmento (video_id, etapa, etiqueta, huella, quien,"
            " cuando) values (?,?,?,?,?,?) on conflict (video_id, etapa) do"
            " update set etiqueta = excluded.etiqueta, huella = excluded.huella,"
            " quien = excluded.quien, cuando = excluded.cuando",
            (v["id"], self.n, etiqueta, self.huella, quien,
             datetime.datetime.now().isoformat(timespec="seconds")))
        cx.commit()
        cx.close()
        return True

    def aprueba(self, quien):
        """Deja dicho que este segmento, tal y como esta hoy, esta bien."""
        return self.mueve(APROBADO, quien)

    def abre(self):
        """Lo devuelve a sin etiqueta. Lo hace un tiquet suyo, o Jaime."""
        cx = _con()
        cx.execute(
            "delete from segmento where etapa = ? and video_id ="
            " (select id from video where slug = ?)", (self.n, self.slug))
        cx.commit()
        cx.close()
        return True

    def como_json(self):
        """Lo que de el se publica en el marcador."""
        return {"etapa": self.n, "etiqueta": self.etiqueta,
                "tramos": [list(t) for t in self.tramos], "dura": self.dura,
                "dice": self.dice, "huella": self.huella,
                "aprobado": self.aprobado, "por": self.por_quien}

    def __str__(self):
        donde = self.etiqueta or "abierto"
        return f"{self.slug} e{self.n} ({self.dura}s, «{donde}»)"


def aprobada(slug) -> bool:
    """**La pieza esta aprobada cuando lo estan todos sus segmentos.**

    Regla de Jaime, y no es un atajo de calculo: es lo que hace que una
    correccion de un tramo no vuelva a poner en juego la pieza entera. Sin
    segmentos no hay pieza que aprobar, asi que devuelve falso.
    """
    segs = Segmento.de(slug)
    return bool(segs) and all(s.aprobado for s in segs)


def abiertos(slug, modo=SEGMENTO):
    """Los segmentos sobre los que se trabaja, segun el modo.

    Jaime, 10-9-2026: *«ahora si dos modos: refactor, que es todo el documento,
    o segmento por segmento, que ya esta declarado en el Json»*.

    - `REFACTOR` — la pieza entera vuelve a estar en juego. Es componer de
      cero, y solo se entra ahi a proposito.
    - `SEGMENTO` — el modo normal: **solo los que no estan aprobados**. Lo
      aprobado no se rediscute, se comprueba, y por eso no entra en la lista.
    """
    segs = Segmento.de(slug)
    if modo == REFACTOR:
        return segs
    return [s for s in segs if not s.aprobado]
