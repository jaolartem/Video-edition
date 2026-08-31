"""Los objetos del dominio: `Pieza` y `Servicio`.

Regla de Jaime: *«buscamos construir y mantener servicios, no un monolito, no
spaghetti — eso significa POO»*.

## Qué había y por qué era spaghetti

Cuarenta scripts sueltos que se hablan por ficheros y por la base. `beats.py`
importado por casi todos, `seleccionar.py` en mil quinientas líneas, y el
conocimiento de qué es una pieza —dónde vive su EDL, cuál es su versión, en qué
fase está— **repetido en cada uno**. Cambiar dónde se guarda un EDL era tocar
once ficheros y acordarse de los once.

Y el motor hablaba con los pasos **por cadena de texto**: `"scripts/depurar.py
{n}"`. Eso funciona y no es un servicio: no hay contrato, no hay forma de
preguntarle si puede correr, y un fallo sólo se distingue por el código de
salida.

## Qué hace esto, y qué NO hace

**No reescribe nada.** Los scripts siguen siendo los que trabajan — esa es la
regla: *«cambias la máquina, no la rehaces»*. Lo que se añade es la costura:

- `Pieza` — lo que una pieza **es**: su slug, su EDL, su versión, su fase, su
  texto. Deja de estar repetido en cada script.
- `Servicio` — lo que un paso **promete**: un nombre, la fase a la que lleva,
  un `puede()` que dice si tiene sentido correr, y un `correr()` que devuelve
  un resultado con motivo, no un código de salida.

Un paso nuevo se escribe heredando de `Servicio`. Un paso viejo se envuelve en
tres líneas con `ServicioScript`. Los dos hablan el mismo idioma con el motor, y
el motor deja de saber que por debajo hay un `subprocess`.
"""
from __future__ import annotations

import dataclasses
import json
import os
import shlex
import subprocess
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "ads/decisiones.db"


@dataclasses.dataclass
class Resultado:
    """Lo que devuelve un servicio. **Motivo siempre, no sólo un código.**

    Un `returncode` dice que algo falló y nada más; el motor necesita poder
    escribirlo en `video_fase.por_que` para que alguien lo desatasque después.
    """

    ok: bool
    motivo: str = ""
    salida: str = ""
    # **Y puede pedir volver.** La linea no es una secuencia —eso quedo cuando
    # las fases pasaron a ser un dato— asi que un paso puede decir «esto cambio
    # lo que ya habiamos dado por bueno, hay que rehacerlo desde ahi».
    #
    # Lo pide el repaso final: si corta algo, el texto ya no es el que se
    # cosio, y componer sobre un texto viejo es justo el fallo que ese paso
    # viene a cerrar. Regla de Jaime: *«asegurate de hacerlo ciclico: si no
    # pasa redundancia, no se compone»*.
    volver_a: str = ""


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
        c = sqlite3.connect(BASE)
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

    @property
    def aprobada(self) -> bool:
        v = self.version
        if not v:
            return False
        con = self._con()
        r = con.execute("select veredicto from aprobacion where version_id = ?",
                        (v["id"],)).fetchone()
        con.close()
        return bool(r and r["veredicto"] == "aprobada")

    def __repr__(self):
        f = self.fase
        return f"<Pieza {self.slug} fase={f['nombre'] if f else '—'}>"


class Servicio:
    """Lo que un paso promete al motor.

    Tres cosas y ninguna opcional:

    - `nombre` — cómo se llama en el log y en la tabla `fase`.
    - `puede(pieza)` — si tiene sentido correrlo ahora. Un servicio que no puede
      correr **no es un fallo**: es un servicio que espera algo, y el motor
      distingue las dos cosas.
    - `correr(pieza)` — hace el trabajo y devuelve `Resultado` con motivo.
    """

    nombre: str = ""

    def puede(self, pieza: Pieza) -> tuple[bool, str]:
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.nombre}>"


class ServicioScript(Servicio):
    """Envuelve un script que ya existe y funciona.

    **Esto es la costura, y es a propósito.** Los cuarenta scripts no se
    reescriben: se envuelven. El motor habla con objetos y por debajo sigue
    habiendo el mismo `depurar.py` que lleva días funcionando.

    Un paso nuevo se escribe heredando de `Servicio` directamente; uno viejo
    entra aquí en una línea. Migrar de golpe sería rehacer la máquina, que es lo
    que la regla prohíbe.
    """

    def __init__(self, nombre: str, plantilla: str):
        self.nombre = nombre
        self.plantilla = plantilla

    def correr(self, pieza: Pieza) -> Resultado:
        partes = shlex.split(self.plantilla.format(n=pieza.n, slug=pieza.slug))
        if partes[0].endswith(".py"):
            partes = [sys.executable] + partes
        elif partes[0].endswith(".mjs"):
            partes = ["node"] + partes
        elif partes[0].endswith(".sh"):
            partes = ["bash"] + partes
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(partes, capture_output=True, text=True, env=env)
        salida = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return Resultado(True, salida=salida)
        ultima = (salida.strip().splitlines() or ["sin salida"])[-1]
        return Resultado(False, motivo=ultima[:160], salida=salida)


class Espera(Servicio):
    """La fase que no mueve un servicio, sino Jaime.

    `aprobado` es la única, y tiene su propia clase en vez de un `if serv is
    None` en el motor: **una excepción con nombre es una clase; una sin nombre
    es un parche.**
    """

    def __init__(self, nombre: str, quien: str = "Jaime"):
        self.nombre = nombre
        self.quien = quien

    def puede(self, pieza: Pieza):
        return False, f"espera a {self.quien}"

    def correr(self, pieza: Pieza) -> Resultado:
        return Resultado(False, motivo=f"espera a {self.quien}")
