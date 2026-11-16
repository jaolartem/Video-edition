"""La hoja guía: un fotograma por segundo, antes de renderizar (C-717).

Jaime, 16-11-2026: *«de acá en adelante antes de renderizar yo quiero ver una
hoja guía con cada fotograma segundo a segundo, sale más barato que tener el
producto renderizado»*.

Se saca del bundle, sin render: `mirar.sh --segundos` abre un solo Chrome y pide
un fotograma por segundo del spec de hoy. Las hojas se componen aquí, con el
segundo escrito en cada fotograma: es el segundo del **montaje**, así que lo que
Jaime diga sobre una hoja se anota con `ticket.py … --de montaje`.

La pieza se queda a las puertas del render con un pedido abierto en el buzón
`guia`, que no tiene oficio: lo contesta Jaime. Su aprobación se anota con sus
palabras y con la huella del spec que vio, así que si el spec cambia la guía
vuelve a salir. Una pieza ya firmada no la pide: lo que se vuelve a montar es lo
que él aprobó.

    python scripts/guia.py 23                          # la pide, o deja pasar
    python scripts/guia.py 23 --aprobar --de "…"       # anota que la aprobó
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import servicio  # noqa: E402

PASO = "guia"
#: Cuántos fotogramas por hoja, por forma del cuadro: `(columnas, filas, ancho)`.
#: Veinte segundos por hoja en horizontal, dieciséis en vertical: una hoja se
#: lee de un vistazo en el teléfono, y una de 116 no.
REJILLA = {True: (4, 5, 480), False: (8, 2, 240)}


class Guia:
    """La hoja guía de una pieza: sus fotogramas, sus hojas y su aprobación."""

    def __init__(self, n: int):
        self.n = int(n)
        self.slug = f"reel-{self.n:02d}"
        self.id = f"Reel-R{self.n}"
        with open("src/reels.json", encoding="utf-8") as f:
            spec = next((p for p in json.load(f) if p.get("id") == self.id), None)
        if not spec:
            raise SystemExit(f"guia: {self.id} no está en src/reels.json")
        self.huella = spec.get("huella") or "sin-huella"
        self.dura = float(spec["duracion"])
        self.fotos = os.path.join("work", "still", "guia", self.slug, self.huella)
        self.salida = os.path.join("out", "guia", self.slug)

    def firmada(self) -> bool:
        from dominio import version
        return bool(version.firmada(self.slug))

    def hojas(self) -> list[str]:
        """Las hojas de este spec; se sacan una vez por huella."""
        hechas = sorted(os.path.join(self.salida, f) for f in os.listdir(self.salida)
                        if f.startswith(self.huella)) if os.path.isdir(self.salida) else []
        if hechas:
            return hechas
        subprocess.run(["bash", "scripts/mirar.sh", "--segundos", str(self.n), self.fotos],
                       check=True)
        return self._compone()

    def _compone(self) -> list[str]:
        from PIL import Image, ImageDraw, ImageFont

        fotos = sorted(f for f in os.listdir(self.fotos) if f.endswith(".png"))
        if not fotos:
            raise SystemExit(f"guia: {self.slug} no dio fotogramas en {self.fotos}")
        w, h = Image.open(os.path.join(self.fotos, fotos[0])).size
        cols, filas, ancho = REJILLA[w > h]
        alto = round(ancho * h / w)
        rotulo = 40
        letra = ImageFont.load_default(size=28)
        os.makedirs(self.salida, exist_ok=True)
        por_hoja = cols * filas
        out = []
        for k in range(0, len(fotos), por_hoja):
            tanda = fotos[k:k + por_hoja]
            hoja = Image.new("RGB", (cols * ancho, filas * (alto + rotulo)), "#0B0B0F")
            pinta = ImageDraw.Draw(hoja)
            for i, f in enumerate(tanda):
                x, y = (i % cols) * ancho, (i // cols) * (alto + rotulo)
                im = Image.open(os.path.join(self.fotos, f)).convert("RGB")
                hoja.paste(im.resize((ancho, alto)), (x, y + rotulo))
                s = int(f[1:4])
                pinta.text((x + 8, y + 4), f"{s // 60}:{s % 60:02d}", fill="#fad02c", font=letra)
            ruta = os.path.join(self.salida, f"{self.huella}-{k // por_hoja + 1:02d}.jpg")
            hoja.save(ruta, quality=88)
            out.append(ruta)
        return out

    def pide(self, hojas: list[str]) -> dict | None:
        """Deja el pedido abierto para Jaime y devuelve su respuesta si ya está."""
        prompt = (f"Hoja guía de {self.slug}: un fotograma por segundo del spec"
                  f" {self.huella}, antes de renderizar. La aprueba Jaime; lo que"
                  " diga de un segundo es un tiquet con `--de montaje`.")
        return servicio.pedir(PASO, self.slug, prompt, {
            "huella": self.huella, "hojas": hojas, "segundos": round(self.dura, 1),
            "se_aprueba_con": f"python scripts/guia.py {self.n} --aprobar --de \"…\"",
        }, cli=False)

    def al_dia(self) -> bool:
        """Si el pedido en pie enseña el spec de hoy. Sin pedido, también (C-723)."""
        try:
            with open(servicio.ruta_pedido(PASO, self.slug), encoding="utf-8") as f:
                return (json.load(f).get("datos") or {}).get("huella") == self.huella
        except FileNotFoundError:
            return True

    def aprobada(self, r) -> bool:
        return bool(r and r.get("aprobada") and r.get("huella") == self.huella)

    def aprueba(self, dijo: str) -> None:
        """Anota que Jaime aprobó la guía que tiene delante, con sus palabras."""
        with open(servicio.ruta_pedido(PASO, self.slug), encoding="utf-8") as f:
            vio = (json.load(f).get("datos") or {}).get("huella")
        if vio != self.huella:
            raise SystemExit(f"guia: Jaime vio el spec {vio} y el de hoy es {self.huella};"
                             " la guía vuelve a salir, no se aprueba la vieja")
        with open(servicio.ruta_respuesta(PASO, self.slug), "w", encoding="utf-8") as f:
            json.dump({"aprobada": True, "huella": self.huella, "de": dijo,
                       "cuando": datetime.datetime.now().isoformat(timespec="seconds")},
                      f, ensure_ascii=False, indent=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pieza", type=int)
    ap.add_argument("--aprobar", action="store_true")
    ap.add_argument("--de", metavar="LO_QUE_DIJO_JAIME")
    a = ap.parse_args()
    g = Guia(a.pieza)
    if a.aprobar:
        if not a.de:
            raise SystemExit("guia: se aprueba con las palabras de Jaime en --de")
        g.aprueba(a.de)
        print(f"guia: {g.slug} aprobada con el spec {g.huella}")
        return 0
    if g.firmada():
        return 0
    hojas = g.hojas()
    r = g.pide(hojas)
    if g.aprobada(r):
        print(f"guia: {g.slug} aprobada por Jaime; se renderiza")
        return 0
    # Una aprobación de otro spec no vale, y al lado del pedido nuevo lo daría
    # por contestado: la línea dejaría de esperar a Jaime y contaría un fallo.
    if r:
        servicio._archivar(PASO, g.slug, sufijo="otro_spec", solo_respuesta=True)
    print(f"espera a Jaime: hoja guía de {g.slug}, {len(hojas)} hoja(s) en {hojas[0]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
