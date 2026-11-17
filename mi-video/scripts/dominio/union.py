"""La unión: las escenas, ya cerradas, se juntan en una pieza que tenga sentido.

Jaime, 16-11-2026: *«una vez tengamos todas las escenas y ya se hayan analizado
todas las escenas, el paso lógico es unir las escenas en un solo video que tenga
sentido»*, y *«cada escena tiene que ir pensando en la que venía antes y en la
que viene después. Tiene que haber continuidad tanto de plano como de
intención»* (C-745).

Lo que se mira al unir son **las costuras**: los dos segundos antes y los dos
después de cada corte entre escenas, sacados de la guía. Y lo que se puede
medir se marca sin preguntar a nadie:
- **el plano**: el encuadre cambia en el corte;
- **lo dicho**: una palabra de contenido se repite a los dos lados del corte
  (la misma regla que `cruce.repite_en_el_corte`, sobre lo que dice cada
  escena).

La continuidad de **intención** no se mide: se entiende. Va escrita al lado de
cada costura —lo que tiene que lograr cada escena— para que la juzgue quien
mira la hoja.
"""
from __future__ import annotations

import os

from . import estado
from .fotograma import Fotogramas

#: Cuántos segundos de la guía se ponen a cada lado del corte.
LADO = 2


def _contenido(texto: str) -> set:
    from . import vocabulario
    from .cruce import CONTENIDO

    return {w for w in vocabulario.contenido(texto or "") if len(w) >= CONTENIDO}


class Costura:
    """El corte entre la escena `a` y la siguiente, `b`."""

    def __init__(self, a: dict, b: dict, nombres: list):
        self.a, self.b, self.nombres = a, b, nombres

    @property
    def marcas(self) -> list:
        out = []
        ea = (self.a.get("camara") or {}).get("encuadre") if isinstance(self.a.get("camara"), dict) else None
        eb = (self.b.get("camara") or {}).get("encuadre") if isinstance(self.b.get("camara"), dict) else None
        if ea and eb and ea != eb:
            out.append({"tipo": "plano", "detalle": f"el encuadre pasa de «{ea}» a «{eb}»"})
        antes = " ".join((self.a.get("dice") or "").split()[-10:])
        despues = " ".join((self.b.get("dice") or "").split()[:10])
        rep = sorted(_contenido(antes) & _contenido(despues))
        if rep:
            out.append({"tipo": "repite", "detalle": f"«{', '.join(rep)}» a los dos lados del corte"})
        return out

    def como_json(self) -> dict:
        def lado(j):
            return {"etapa": j["etapa"], "intencion": (j.get("intencion") or {}).get("debe_decir"),
                    "trato": j.get("trato"), "camino": j.get("camino")}
        return {"de": lado(self.a), "a": lado(self.b), "segundos": self.nombres,
                "marcas": self.marcas}


class Union:
    """Las costuras de una pieza: de sus documentos de escena y de su guía."""

    def __init__(self, slug: str, spec: dict):
        self.slug, self.fotos = slug, Fotogramas(spec)
        docs = estado.lee(slug).get("segmentos") or []
        self.docs = {j["etapa"]: j for j in docs if isinstance(j, dict) and "etapa" in j}

    def costuras(self) -> list[Costura]:
        rejilla = list(self.fotos.rejilla())
        beats = [b for b in self.fotos.tramos if b in self.docs]
        out = []
        for a, b in zip(beats, beats[1:]):
            fin = [n for n in rejilla if n.startswith(f"e{a:02d}-")][-LADO:]
            ini = [n for n in rejilla if n.startswith(f"e{b:02d}-")][:LADO]
            out.append(Costura(self.docs[a], self.docs[b], fin + ini))
        return out

    def nombres(self) -> list:
        return sorted({n for c in self.costuras() for n in c.nombres})

    def hoja(self, carpeta: str, salida: str, tanda: str) -> list[str]:
        """Las hojas de costuras: una fila por corte, con sus marcas debajo."""
        from PIL import Image, ImageDraw, ImageFont

        rejilla, cs = self.fotos.rejilla(), self.costuras()
        if not cs:
            return []
        primero = next((os.path.join(carpeta, f"{n}.png") for c in cs for n in c.nombres
                        if os.path.isfile(os.path.join(carpeta, f"{n}.png"))), None)
        if not primero:
            return []
        w, h = Image.open(primero).size
        ancho = 360 if w > h else 200
        alto, rot, pie, por_hoja = round(ancho * h / w), 34, 56, 6
        letra = ImageFont.load_default(size=24)
        os.makedirs(salida, exist_ok=True)
        out = []
        for k in range(0, len(cs), por_hoja):
            tanda_cs = cs[k:k + por_hoja]
            hoja = Image.new("RGB", (2 * LADO * ancho, len(tanda_cs) * (alto + rot + pie)), "#0B0B0F")
            pinta = ImageDraw.Draw(hoja)
            for i, c in enumerate(tanda_cs):
                y = i * (alto + rot + pie)
                pinta.text((8, y + 4), f"e{c.a['etapa']} | e{c.b['etapa']}", fill="#fad02c", font=letra)
                for j, n in enumerate(c.nombres):
                    p = os.path.join(carpeta, f"{n}.png")
                    if os.path.isfile(p):
                        hoja.paste(Image.open(p).convert("RGB").resize((ancho, alto)), (j * ancho, y + rot))
                    s = int(rejilla.get(n, 0) / 30)
                    pinta.text((j * ancho + 8, y + rot + 4), f"{s // 60}:{s % 60:02d}",
                               fill="#fad02c", font=letra)
                # El corte, donde cae: entre el último de una y el primero de la otra.
                x = sum(1 for n in c.nombres if n.startswith(f"e{c.a['etapa']:02d}-")) * ancho
                pinta.line([(x, y + rot), (x, y + rot + alto)], fill="#fad02c", width=4)
                texto = "; ".join(m["detalle"] for m in c.marcas) or "sin marcas"
                pinta.text((8, y + rot + alto + 12), texto[:120], fill="#fad02c" if c.marcas
                           else "#8a8a8a", font=letra)
            ruta = os.path.join(salida, f"{tanda}-costuras-{k // por_hoja + 1:02d}.jpg")
            hoja.save(ruta, quality=88)
            out.append(ruta)
        return out


def visto(guia, hojas: list) -> bool | None:
    """**El visto, sobre la guía y antes del render** (C-746).

    Jaime: *«sacamos esta guía y ya tú la lees»*. Si una costura sale marcada
    —una palabra repetida a través del corte, un salto de encuadre—, el
    diseñador mira las hojas de la guía y la de costuras antes que Jaime, y
    aprueba o devuelve escenas como en el visto de siempre
    (`servicios.visto.aplicar`). Sin marcas no se le llama: pasa a Jaime.
    `None` es que espera su respuesta; `False`, que devolvió escenas.
    """
    import servicio as contrato
    from servicios.base import Pieza
    from servicios.visto import PROMPT, aplicar

    costuras = guia.costuras()
    marcadas = costuras.get("marcadas") or []
    if not marcadas:
        return True
    prompt = ((open(PROMPT, encoding="utf-8").read() if os.path.exists(PROMPT) else "")
              )
    # La instrucción va en los datos: del prompt, el pliego sólo deja pasar los
    # apartados del contrato (`dominio/pliego.py`).
    r = contrato.pedir("visto", f"reel-{guia.n:02d}", prompt, {
        "modo": "guia", "como_se_mira": (
            "HOY MIRAS LA HOJA GUÍA, NO UN RENDER: un fotograma por segundo de cada"
            " escena (`hojas`) y la hoja de costuras (`costuras.hojas`), con los cortes"
            " marcados en `costuras.marcadas`. Juzgas la continuidad de plano y de"
            " intención en cada corte marcado. Contestas como en el visto: `se_ensena`,"
            " `por_que`, `aprueba`, `devuelve` y `mirado`."),
        "huella": guia.huella, "hojas": hojas, "costuras": costuras,
        "por_que_se_mira": [f"e{c['de']['etapa']}|e{c['a']['etapa']}: "
                            + "; ".join(m["detalle"] for m in c["marcas"]) for c in marcadas]})
    if r is None:
        return None
    return bool(aplicar(Pieza(guia.n), r).ok)
