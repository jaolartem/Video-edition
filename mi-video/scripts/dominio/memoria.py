"""**Lo que un paso ya preguntó, por segmento.** C-561.

Jaime, al menos treinta veces: *se aprueba por segmento, y un segmento que
cambia no puede hacer releer la pieza*. Ningún paso de IA lo cumplía: una
respuesta consumida archivaba el par entero y la vuelta siguiente volvía a
preguntar lo mismo, y redundancia y revalidar mandaban **todas** las etapas
siempre. Medido el 18-10: 1,5 MB de pedidos de revalidar y 2,2 MB de diseño en
un día para cinco piezas, y más de un millón de tokens.

Esto recuerda, por paso y etapa, **la huella de lo que se preguntó** cuando su
respuesta se aceptó. No guarda la respuesta: lo que decidió ya está aplicado
donde vive (el EDL, `revision`, `escena_desc`). Lo que hace falta saber para no
volver a pagar es si esa etapa ha cambiado desde entonces.

    m = Memoria("revalidar", "reel-20")
    pide = m.cambiados(filas, campos=("desde", "hasta", "texto"))
    ...  # preguntar sólo por `pide`
    m.guarda([f for f in filas if f["beat"] in pide], campos=...)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os

TABLA = "respuesta_segmento"


def _con():
    import sys

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    import basedatos

    cx = basedatos.abrir()
    crea(cx)
    return cx


def crea(cx) -> bool:
    """La tabla. La llama `migraciones.migrar` y, por si acaso, quien abre."""
    cx.execute(f"""
      CREATE TABLE IF NOT EXISTS {TABLA} (
        paso     TEXT NOT NULL,
        video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
        etapa    INTEGER NOT NULL,
        -- Lo que se pregunto de esa etapa cuando se acepto su respuesta.
        huella   TEXT NOT NULL,
        cuando   TEXT NOT NULL,
        PRIMARY KEY (paso, video_id, etapa)
      )""")
    return True


def huella(filas, campos) -> str:
    """De las filas de UNA etapa, sólo lo que el paso declara que pregunta."""
    nucleo = [{k: f.get(k) for k in campos} for f in filas]
    plano = json.dumps(nucleo, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(plano.encode("utf-8")).hexdigest()[:16]


def _por_etapa(filas, clave="beat") -> dict:
    grupos: dict = {}
    for f in filas:
        try:
            grupos.setdefault(int(f.get(clave)), []).append(f)
        except (TypeError, ValueError):
            continue
    return grupos


class Memoria:
    """La memoria de un paso sobre una pieza."""

    def __init__(self, paso: str, slug: str):
        self.paso = paso
        self.slug = slug

    def _video(self, cx):
        r = cx.execute("select id from video where slug = ?", (self.slug,)).fetchone()
        return r[0] if r else None

    def recordado(self) -> dict:
        """`{etapa: huella}` de lo que este paso ya tiene contestado."""
        cx = _con()
        vid = self._video(cx)
        filas = cx.execute(f"select etapa, huella from {TABLA}"
                           " where paso = ? and video_id = ?",
                           (self.paso, vid)).fetchall() if vid else []
        cx.close()
        return {int(e): h for e, h in filas}

    def cambiados(self, filas, campos, clave="beat", abiertas=()) -> set:
        """Las etapas que hay que preguntar: nuevas, cambiadas, o que abre un tiquet.

        **Un segmento aprobado no se pregunta** salvo que un tiquet lo nombre:
        su huella en `segmento` es la del corte que Jaime vio.
        """
        antes = self.recordado()
        try:
            from .segmento import Segmento
            aprobados = {s.n for s in Segmento.de(self.slug) if s.aprobado}
        except Exception:                          # noqa: BLE001
            aprobados = set()
        abiertas = {int(e) for e in abiertas}
        pide = set()
        for etapa, suyas in _por_etapa(filas, clave).items():
            if etapa in abiertas:
                pide.add(etapa)
            elif etapa in aprobados:
                continue
            elif antes.get(etapa) != huella(suyas, campos):
                pide.add(etapa)
        return pide

    def guarda(self, filas, campos, clave="beat") -> int:
        """Anota como contestadas las etapas de `filas`, con su huella de hoy."""
        cx = _con()
        vid = self._video(cx)
        if vid is None:
            cx.close()
            return 0
        ahora = datetime.datetime.now().isoformat(timespec="seconds")
        n = 0
        for etapa, suyas in _por_etapa(filas, clave).items():
            cx.execute(f"insert or replace into {TABLA} (paso, video_id, etapa,"
                       " huella, cuando) values (?,?,?,?,?)",
                       (self.paso, vid, etapa, huella(suyas, campos), ahora))
            n += 1
        cx.commit()
        cx.close()
        return n

    def siembra(self, pedido_json: str, campos, clave="beat") -> int:
        """Lo ya contestado de un pedido consumido entra en la memoria.

        Es como no se pierde lo de hoy al estrenar esto: cada respuesta que la
        línea ya aplicó cuenta como pregunta hecha sobre lo que decía su pedido.
        """
        try:
            datos = json.load(open(pedido_json, encoding="utf-8")).get("datos")
        except (OSError, ValueError, AttributeError):
            return 0
        if not isinstance(datos, list):
            return 0
        return self.guarda(datos, campos, clave)


#: Los pasos que preguntan por segmento: de donde sale su dossier y que campos
#: forman su pregunta. Los mismos que declaran sus servicios.
PASOS = {
    "revalidar": ("revalidar", "servicios.revalidar"),
    "redundancia": ("redundancia", "servicios.redundancia"),
}


def sembrar(paso: str, slug: str) -> int:
    """Da por contestado lo que hoy esta en el EDL de esa pieza para ese paso.

    Para estrenar la memoria sin volver a pagar lo que la linea ya aplico: el
    EDL de hoy es el resultado de esas respuestas.
    """
    import importlib

    origen, servicio = PASOS[paso]
    dossier = importlib.import_module(origen).dossier(slug)
    campos = importlib.import_module(servicio).CAMPOS
    return Memoria(paso, slug).guarda(dossier, campos)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if len(sys.argv) < 4 or sys.argv[1] != "--sembrar":
        raise SystemExit("uso: python scripts/dominio/memoria.py --sembrar PASO N...")
    for n in sys.argv[3:]:
        slug = f"reel-{int(n):02d}"
        print(f"{sys.argv[2]}/{slug}: {sembrar(sys.argv[2], slug)} segmento(s)")
