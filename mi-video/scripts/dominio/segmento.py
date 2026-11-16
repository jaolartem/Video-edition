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


def _quien_es(quien):
    """El id del autor que firma esto. `None` es nadie, y nadie no tiene permisos."""
    from .autor import Autor

    a = Autor.de(quien)
    return a.id if a else None


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

        Se lee de la base y **no del marcador**, y esa es la diferencia entre
        una guarda y un adorno. Jaime, 10-9-2026: *«la guarda es el Json, y lo
        que verifica y garantiza integridad es que solo se pueda modificar con
        los permisos»*.

        Lo tenia al reves. El marcador mandaba tambien al LEER, asi que un
        oficio —que tiene `Write` sobre el fichero— escribia
        `{"etiqueta": "aprobado", "por": "jaime"}` y quedaba aprobado, aunque
        `estado.aplica` rechazara la firma un segundo despues: comprobar el
        permiso al escribir no vale nada si al leer se cree el fichero.
        Medido, y por eso esta escrito.

        El reparto que si aguanta: **el marcador propone y la puerta decide.**
        Escribir un fichero solo puede proponer —un fichero no prueba quien lo
        escribio—; lo que paso el permiso queda en la base, y el marcador lo
        vuelve a publicar. La fuente de verdad sigue siendo el documento que
        viaja; lo que no puede es firmar por su cuenta.
        """
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
        _con_corte(cx)
        # **Y lo que Jaime aprueba se guarda entero, no sólo su huella** (C-659).
        # Con la huella sola, un paso que movía un borde un milisegundo le
        # quitaba la aprobación sin que nadie lo decidiera, y ya no había con
        # qué volver: el corte aprobado no estaba escrito en ningún sitio.
        corte = (json.dumps(entradas(self.slug, self.n), ensure_ascii=False)
                 if etiqueta == APROBADO and es_suya(quien) else None)
        cx.execute(
            "insert into segmento (video_id, etapa, etiqueta, huella, quien,"
            " cuando, autor_id, corte) values (?,?,?,?,?,?,?,?) on conflict"
            " (video_id, etapa) do update set etiqueta = excluded.etiqueta,"
            " huella = excluded.huella, quien = excluded.quien,"
            " cuando = excluded.cuando, autor_id = excluded.autor_id,"
            " corte = excluded.corte",
            (v["id"], self.n, etiqueta, self.huella, quien,
             datetime.datetime.now().isoformat(timespec="seconds"),
             _quien_es(quien), corte))
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
        # **Y reabrir también es el evento de la puerta** (C-492). Su tiquet se
        # abrió con la pieza firmada y la puerta no la movió; al reabrir el
        # segmento nadie volvía a preguntarle. reel-13, 14-9: #460 y #461 sin
        # devolver y la pieza parada en «verificado».
        try:
            from . import puertas
            for linea in puertas.del_tiquet([int(str(self.slug)[-2:])]):
                print(linea)
        except Exception:                          # noqa: BLE001
            pass
        return True

    @property
    def tiene(self):
        """**Lo decidido sobre este segmento**: trato, plano, tablero, cámara, voz.

        Jaime, 10-9-2026: *«revisa que el Json tenga acceso al nuevo modelo»*; y
        15-11-2026: *«el json tiene toda la información de cada corte y de cada
        elemento sobre el que se ha decidido»*. El oficio abre el marcador y nada
        más, así que lo que no se publica aquí **no existe para él**.

        **Se lee de la fuente única, `escena_desc`** (C-713), la que `verdad.py`
        declara para el tablero. Esto leía `etapa_tablero`, `etapa_camara` y
        `etapa_voz`, que el diseño no escribe —0 filas en reel-14, 22 y 23—, y la
        consulta del tipo pedía columnas que no existen y reventaba; el `except`
        se lo tragaba. Así el JSON llevaba cada corte sin un solo elemento
        decidido, y el diseñador de reel-23 escribió «las props completas a
        ciegas» y redactó una fuente. Y si no se puede leer, se dice en `falta`.
        """
        import json as _j

        def suelto(v):
            try:
                return _j.loads(v) if isinstance(v, str) and v[:1] in "{[" else v
            except ValueError:
                return v

        try:
            cx = _con()
            r = cx.execute(
                "select trato, plano, tablero, camara, voz, cc_lado, corrige_dice,"
                " corrige_es from escena_desc where video_slug = ? and etapa_orden = ?",
                (self.slug, self.n)).fetchone()
            ps = [dict(x) for x in cx.execute(
                "select p.bloques, p.cubre, p.lado, ep.hueco from etapa_panel ep"
                " join panel p on p.id = ep.panel_id join etapa e on e.id = ep.etapa_id"
                " join video v on v.id = e.video_id where v.slug = ? and e.orden = ?",
                (self.slug, self.n))]
            cx.close()
        except Exception as e:                     # noqa: BLE001
            return {"falta": f"no se pudo leer lo decidido: {e}"[:160]}
        fuera = {k: suelto(r[k]) for k in r.keys() if r[k] not in (None, "")} if r else {}
        if ps:
            fuera["paneles"] = ps
        return fuera

    def como_json(self):
        """Lo que de el se publica en el marcador."""
        return {"etapa": self.n, "etiqueta": self.etiqueta,
                "tramos": [list(t) for t in self.tramos], "dura": self.dura,
                "dice": self.dice, "huella": self.huella,
                "aprobado": self.aprobado, "por": self.por_quien,
                **self.tiene}

    def __str__(self):
        donde = self.etiqueta or "abierto"
        return f"{self.slug} e{self.n} ({self.dura}s, «{donde}»)"


def es_suya(quien) -> bool:
    """Si quien puso esa etiqueta **tenia derecho a aprobar**.

    Esto era `quien.startswith("jaime")`. Funcionaba con una persona y con una
    ortografia, y ninguna de las dos cosas es una regla: el dia que entrara otra
    persona no habria aprobado nada, y `Jaime` con mayuscula ya se colaba por
    los pelos. Jaime, 10-9-2026: *«quien es al final un declarador de agencia»*.

    Ahora lo contesta `agencia`, que cuelga del TIPO: «aprobar es de una
    persona» vale para cualquier persona. La guarda que importa sigue en pie —
    la linea y los oficios no aprueban— y ya no depende de como se escriba un
    nombre.
    """
    from .autor import puede

    return puede(quien, "aprobar")


def aprobada(slug) -> bool:
    """**La pieza esta aprobada cuando lo estan todos sus segmentos.**

    Regla de Jaime, y no es un atajo de calculo: es lo que hace que una
    correccion de un tramo no vuelva a poner en juego la pieza entera. Sin
    segmentos no hay pieza que aprobar, asi que devuelve falso.

    **Y aprobado por el.** `puertas._aprobada` leia la tabla `aprobacion` y esto
    leia el marcador: dos respuestas a la misma pregunta, que es la averia que
    este proyecto persigue. Ahora la fuente es una —el marcador— y la guarda
    que se perdia al unirlas se conserva aqui: una etiqueta que puso la linea
    no aprueba nada.
    """
    segs = Segmento.de(slug)
    return bool(segs) and all(s.aprobado and es_suya(s.por_quien) for s in segs)


def sello(slug, etapa):
    """La huella de UNA etapa como la lleva un tiquet: `e<n>:<huella>` (C-659)."""
    s = next((x for x in Segmento.de(slug) if x.n == int(etapa)), None)
    return f"e{int(etapa)}:{s.huella}" if s else None


def sigue(slug, marca) -> bool:
    """¿La etapa de ese sello está como cuando se puso? Falso si no es de etapa."""
    marca = str(marca or "")
    if not (marca.startswith("e") and ":" in marca):
        return False
    return sello(slug, marca[1:].split(":")[0]) == marca


def _con_corte(cx):
    """La columna `corte` de `segmento`, si la base aún no la tiene."""
    try:
        cx.execute("alter table segmento add column corte text")
    except Exception:                              # noqa: BLE001
        pass


def entradas(slug, etapa) -> list:
    """Lo que la etapa ocupa hoy en el EDL: `[[segmento, fuente, detalle], …]`."""
    try:
        edl = json.load(open(os.path.join(RAIZ, "ads", slug, "edl-sell.json"),
                             encoding="utf-8"))
    except (OSError, ValueError):
        return []
    fuentes = edl.get("fuentes") or []
    return [[s, fuentes[i] if i < len(fuentes) else None, d]
            for i, (s, d) in enumerate(zip(edl.get("segmentos") or [],
                                           edl.get("detalle") or []))
            if d.get("beat") == int(etapa)]


def congelados(slug) -> dict:
    """`{etapa: entradas}` de lo que una persona aprobó, tal y como lo aprobó.

    Es lo que `Tijera.restaurar` vuelve a poner si un paso lo movió. Lo
    aprobado por un oficio no entra: congela sólo quien tiene derecho a
    aprobar. Un tiquet de esa etapa lo libera con `reabre`, que borra la fila.
    """
    cx = _con()
    _con_corte(cx)
    filas = cx.execute(
        "select s.etapa, s.quien, s.corte from segmento s join video v"
        " on v.id = s.video_id where v.slug = ? and s.etiqueta = ?"
        " and s.corte is not null", (slug, APROBADO)).fetchall()
    cx.close()
    return {int(r["etapa"]): json.loads(r["corte"]) for r in filas
            if r["corte"] and es_suya(r["quien"])}


def reabre(slug, etapa) -> bool:
    """**Un tiquet de Jaime reabre su segmento aprobado, y solo ese** (C-605).

    La puerta no reabre una pieza aprobada, y hace bien: lo que levanta la
    maquina no rediscute lo aprobado. Pero el revisor tambien aprueba, asi que
    su tiquet sobre e1 de reel-19, en `revisado`, se quedo diciendo «sube a
    Jaime» con sus propias palabras. `abre` ya decia que lo hace «un tiquet
    suyo, o Jaime», y nadie lo llamaba.
    """
    # Y congelado cuenta como aprobado aunque hoy un paso lo haya movido: si no,
    # el tiquet de Jaime no podría liberar justo la etapa que quiere cambiar.
    helado = int(etapa) in congelados(slug)
    for s in Segmento.de(slug):
        if s.n == int(etapa) and (s.aprobado or helado):
            return s.abre()
    return False


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
