"""La pieza: un anuncio, con su montaje, su fase y sus cintas.

**Por qué vive aquí y no en `servicios/`.** `Pieza` es un sustantivo del
dominio, no andamiaje del motor: existe antes que los pasos y seguiría
existiendo si el motor cambiara entero. Estaba en `servicios/base.py` porque es
donde hizo falta primero, y eso llevó ese fichero por encima del techo de 300
líneas — la señal de que algo estaba en el sitio equivocado.

Regla de Jaime: *«antes de declarar otra entidad reviso si cabe en una clase»*.
Aquí cabía; sólo estaba mal colocada.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402
import rutas  # noqa: E402

#: Dónde vive la base. La declara `basedatos`, que es su dueño; aquí sólo se
#: usa. Estaba escrita a mano y esa es la avería de siempre en pequeño.
BASE = basedatos.BASE


class Pieza:
    """Una pieza del lote. Lo que sabe de sí misma, en un solo sitio.

    Antes cada script reconstruía esto por su cuenta: componer el slug, abrir el
    EDL, buscar la versión, mirar la fase. Ahora se pregunta.
    """

    def __init__(self, n: int):
        self.n = int(n)
        self.slug = f"reel-{self.n:02d}"

    # ── lo que la pieza es ────────────────────────────────────────────────
    @property
    def ruta_edl(self) -> str:
        return f"ads/{self.slug}/edl-sell.json"

    @property
    def edl(self) -> dict | None:
        if not os.path.exists(self.ruta_edl):
            return None
        return json.load(open(self.ruta_edl, encoding="utf-8"))

    @property
    def existe(self) -> bool:
        return self.edl is not None

    @property
    def cintas(self) -> set:
        """De qué grabaciones está hecha. **La dependencia real de la pieza.**

        No es un dato de adorno: es lo que dice qué piezas pueden trabajar a la
        vez. reel-06 sale de una sola cinta y reel-07 de cuatro; que reel-04
        esté afinando la suya no tiene por qué parar a reel-06 — y hoy la para,
        porque el motor recorre de una en una sin saber esto.

        Sale del EDL, que es lo que de verdad se montó, y cae a `rutas.TOMAS`
        —la declaración— sólo cuando todavía no hay EDL.
        """
        edl = self.edl or {}
        de_edl = {d.get("toma") for d in edl.get("detalle", []) if d.get("toma")}
        de_edl |= {t for t in (edl.get("fuentes") or []) if t}
        if de_edl:
            return de_edl
        import rutas

        una = rutas.TOMAS.get(self.slug)
        return {una} if una else set()

    # ── lo que la pieza DICE ─────────────────────────────────────────────
    #
    # **Vivia en `verificar.py` como funcion privada, y ese fue el hueco.** El
    # paso que describe la escena leia otra cosa —la eleccion guardada en la
    # base— y la puerta comprobaba esta. Dos fuentes para «lo que dice esta
    # etapa» son dos verdades, y la descripcion acababa hablando de un texto
    # que el montaje ya no tenia sin que nadie lo notara.
    #
    # El cache es de clase a proposito: son siete cintas para seis piezas, y
    # releerlas por pieza multiplica por seis el trabajo para el mismo dato.
    _CINTAS: dict = {}

    @property
    def texto(self) -> dict:
        """Lo que dice cada etapa **en el montaje actual**, por beat."""
        import transcribir

        edl = self.edl
        if not edl:
            return {}
        por: dict = {}
        for rango, det in zip(edl["segmentos"], edl["detalle"]):
            toma = det.get("toma")
            if toma not in Pieza._CINTAS:
                try:
                    Pieza._CINTAS[toma] = transcribir.exigir(toma)["segmentos"]
                except SystemExit:
                    # Sin cinta no se inventa texto: se queda vacio y quien
                    # pregunte lo vera vacio. Un texto por defecto aqui es una
                    # descripcion que describe la nada y nadie se entera.
                    Pieza._CINTAS[toma] = []
            # La vara —que palabra suena dentro del corte— vive en
            # `transcribir.suena`, que es donde viven las palabras (C-84).
            ws = [w["text"] for w in Pieza._CINTAS[toma]
                  if transcribir.suena(w, rango[0], rango[1])]
            por.setdefault(det.get("beat"), []).extend(ws)
        return {b: " ".join(v) for b, v in por.items()}

    def _con(self):
        c = basedatos.abrir(BASE)
        c.row_factory = sqlite3.Row
        return c

    @property
    def video_id(self):
        con = self._con()
        r = con.execute("select id from video where slug = ?",
                        (self.slug,)).fetchone()
        con.close()
        return r["id"] if r else None

    @property
    def fase(self):
        """En qué fase está ahora. `None` si nunca entró al ciclo."""
        con = self._con()
        r = con.execute(
            "select f.id, f.nombre, f.orden, f.servicio from video_fase vf"
            " join fase f on f.id = vf.fase_id"
            " where vf.video_id = (select id from video where slug = ?)"
            " order by vf.id desc limit 1", (self.slug,)).fetchone()
        con.close()
        return dict(r) if r else None

    @property
    def version(self):
        con = self._con()
        r = con.execute(
            "select ve.* from version ve join video vi on vi.id = ve.video_id"
            " where vi.slug = ? order by ve.n desc limit 1",
            (self.slug,)).fetchone()
        con.close()
        return dict(r) if r else None

    # **Aqui vivia `aprobada`, y se va sin sustituto.** Leia `aprobacion` por
    # version —una tercera respuesta a «¿esta aprobada?»— y no la llamaba nadie.
    # La respuesta es una: `dominio.segmento.aprobada`.

    def __repr__(self):
        f = self.fase
        return f"<Pieza {self.slug} fase={f['nombre'] if f else '—'}>"
