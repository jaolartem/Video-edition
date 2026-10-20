"""**El documento de revisión: la pieza en imágenes y en lo que suena en cada una.** C-594.

Jaime, 19-10-2026: *«la función mirar debe crear el documento más óptimo de
lectura para la IA»*, y lo que lo ordena: *«las imágenes no son respaldo, son el
corazón del documento y lo que le permite al diseñador tomar decisiones, sin
tener que gastar recursos en ver él mismo el video; y que guarde el análisis del
audio —no el audio mismo, los valores que el audio tiene en el momento
concreto—»*.

Así que el documento son **las hojas** (`fotogramas.Hoja`, una imagen legible
con los fotogramas elegidos) y, por escena y por cada uno de esos fotogramas:

- lo que se dice en ese instante (el subtítulo del spec que se renderizó);
- lo que suena en ese instante: sonoridad momentánea del render (ebur128, la
  misma pasada de `suena`), si es silencio, y la voz —intensidad, altura y
  velocidad— medida en la cinta con `dominio.voz.Voz`, la vara del compositor;
- lo que hay en pantalla en la escena según el spec, con cuánto dura y cuánto
  pide leerse (`src/brand/lectura.json`), y dónde está su cara;
- lo que el control de emisión dijo de esa escena, si ya corrió.

Los fotogramas los elige `Hoja.elegidos`: un documento y una hoja hablan de los
mismos fotogramas, porque los elige uno.
"""
from __future__ import annotations

import json
import os
import re

#: Las claves del spec que llevan texto que se lee en pantalla.
TEXTOS = ("texto", "titulo", "title", "hook", "kicker", "subtitulo", "premisa",
          "remate", "label", "cifra", "lineas", "concepto", "linea1", "linea2")
CAPAS = {"boards": "tablero", "paneles": "panel", "recortes": "recorte"}
VENTANA = 0.75                     # la voz se mide ±0,75 s alrededor del fotograma


def _textos(x, fuera):
    """Los textos que se leen, en el orden en que salen en el spec."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in TEXTOS and isinstance(v, str) and v.strip():
                fuera.append(v.strip())
            elif k in TEXTOS and isinstance(v, list):
                fuera += [s.strip() for s in v if isinstance(s, str) and s.strip()]
            elif k not in ("src", "css", "fuente") and isinstance(v, (dict, list)):
                _textos(v, fuera)
    elif isinstance(x, list):
        for v in x:
            _textos(v, fuera)
    return fuera


class Documento:
    """Lo que el agente mira y oye de una pieza, escena por escena."""

    def __init__(self, slug: str, hechas, etapas=None, nombre: str = "documento"):
        self.slug, self.hechas, self.etapas, self.nombre = slug, hechas or [], etapas, nombre
        self.n = int(slug.split("-")[1])

    def _spec(self) -> dict:
        try:
            spec = json.load(open("src/reels.json", encoding="utf-8"))
            return next((x for x in spec if x.get("id") == f"Reel-R{self.n}"), {})
        except (OSError, ValueError):
            return {}

    def _render(self):
        import rutas

        for c in ("entrega", "reels"):
            mp4 = rutas.salida(c, f"reel-R{self.n}.mp4")
            if os.path.exists(mp4):
                return mp4
        return None

    def _onda(self):
        """`(momentanea, silencios)` del render: una pasada de ffmpeg, la de `suena`."""
        mp4 = self._render()
        if not mp4:
            return [], []
        import suena

        t = suena._ffmpeg(["-i", mp4, "-af", suena.CADENA.format(umbral=-40, minimo=0.6)])
        m = [(float(a), float(b)) for a, b in
             re.findall(r"t:\s*([\d.]+)\s+TARGET:\S+ LUFS\s+M:\s*(-?[\d.]+)", t)]
        ini = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", t)]
        fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", t)]
        return m, list(zip(ini, fin + [1e9] * (len(ini) - len(fin))))

    def _voz(self, plan, escena, t):
        """La voz en la cinta en ese instante, con la vara de `revalidar._direccion`."""
        try:
            from dominio.voz import Voz
            import transcribir

            e = plan[escena - 1]
            c = e["origen_desde"] + (t - e["montado_desde"])
            pal = transcribir.exigir(e["fuente"])["segmentos"]
            v = Voz(c - VENTANA, c + VENTANA, e["fuente"]).intensidad(pal) or {}
            return {k: v.get(k) for k in ("intensidad", "altura", "velocidad")
                    if v.get(k) is not None}
        except Exception:                          # noqa: BLE001 — se mide o se calla
            return {}

    def _alertas(self) -> dict:
        try:
            import emision

            return emision.por_escena(self.n) or {}
        except Exception:                          # noqa: BLE001 — C aún no está
            return {}

    @staticmethod
    def _capas(spec, lee) -> list:
        """Lo que el spec pinta con texto: tableros, paneles, recortes, titulares
        y el rótulo del gancho (`lineas`, de `entra` a `sostiene`)."""
        fuera = []

        def capa(nombre, c, txt, at, dur):
            pal, props = sum(len(s.split()) for s in txt), c.get("props") or {}
            fuera.append({"capa": nombre, "kind": c.get("kind"), "texto": " / ".join(txt),
                          "fuente": c.get("fuente"), "desde": round(at / 30, 1),
                          "dura": round(dur / 30, 1),
                          "pide": round(max(lee["sueloFrames"] / 30,
                                            pal / lee["palabrasPorSegundo"]), 1),
                          **{x: props.get(x, c.get(x)) for x in ("cubre", "lado")
                             if props.get(x, c.get(x))}})

        for k, nombre in CAPAS.items():
            for c in spec.get(k) or []:
                if isinstance(c, dict) and "at" in c and "duration" in c:
                    capa(nombre, c, _textos(c, []), c["at"], c["duration"])
        for c in spec.get("caminos") or []:
            if c.get("tipo") in ("titular", "diapositiva") and c.get("duration"):
                capa(c["tipo"], c, _textos(c.get("props"), []), c["at"], c["duration"])
        if spec.get("lineas"):
            capa("rótulo", {}, list(spec["lineas"]), spec.get("entra") or 0,
                 spec.get("sostiene") or 0)
        return [c for c in fuera if c["texto"]]

    def escribe(self) -> dict:
        """`{"hojas": [...], "escenas": [...]}`: lo que va dentro del pedido."""
        from fotogramas import Hoja

        spec = self._spec()
        try:
            plan = json.load(open(f"work/scenes/{self.slug}/plan-full.json",
                                  encoding="utf-8"))["escenas"]
        except (OSError, ValueError, KeyError):
            plan = []
        lee = json.load(open("src/brand/lectura.json", encoding="utf-8"))
        dicho, _ = Hoja._spec(self.slug)
        momentanea, silencios = self._onda()
        alertas = self._alertas()
        capas = self._capas(spec, lee)
        por_escena = {}
        caras = {c["escena"]: c for c in spec.get("cc") or [] if isinstance(c, dict)}
        for e, k, t in Hoja.elegidos(self.slug, self.hechas, self.etapas):
            n = e["escena"]
            p = plan[n - 1] if 0 < n <= len(plan) else {}
            d = por_escena.setdefault(n, {
                "escena": n, "etapa": e.get("etapa"), "desde": round(e["desde"], 1),
                "hasta": round(e["hasta"], 1), "encuadre": p.get("encuadre"),
                # **La cara medida sobre el corte, y si el cc se la tapa**
                # (C-624): la del plan era una suposición, y con ella la hoja
                # le decía al revisor que no la tapaba.
                "cara": {k: v for k, v in (caras.get(n - 1) or {}).items()
                         if k in ("banda", "boca", "tapa")},
                "en_pantalla": [c for c in capas if c["desde"] < e["hasta"] - 0.1
                                and c["desde"] + c["dura"] > e["desde"] + 0.1],
                "sueltos": [x["fichero"] for x in e["mira"]],
                "alertas": alertas.get(n, {}).get("alertas", []), "fotogramas": []})
            lufs = min(momentanea, key=lambda x: abs(x[0] - t))[1] if momentanea else None
            d["fotogramas"].append({
                "t": round(t, 1), "imagen": e["mira"][k]["fichero"],
                "dice": " / ".join(x for a, b, x in dicho if a <= t < b),
                "suena": {"lufs": lufs, "silencio": any(a <= t <= b for a, b in silencios),
                          **(self._voz(plan, n, t) if plan else {})}})
        hojas = Hoja.del_render(self.slug, self.hechas, self.etapas, self.nombre).escribe()
        return {"hojas": hojas, "escenas": list(por_escena.values())}
