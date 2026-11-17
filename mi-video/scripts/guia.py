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
#: La huella de un spec, como la calcula `reels-spec.mjs`: lo que va antes de
#: `huella`, con la portada en `null`.
HUELLA_JS = ("const fs=require('fs'),{createHash}=require('crypto');"
             "const p=JSON.parse(fs.readFileSync(process.argv[1],'utf8')),o={};"
             "for(const k of Object.keys(p)){if(k==='huella')break;o[k]=p[k];}"
             "console.log(createHash('sha1').update(JSON.stringify({...o,portada:null}))"
             ".digest('hex').slice(0,12));")
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
        self.spec = spec
        self.huella = spec.get("huella") or "sin-huella"
        self.dura = float(spec["duracion"])
        self.fotos = os.path.join("work", "still", "guia", self.slug, self.huella)
        self.salida = os.path.join("out", "guia", self.slug)

    def firmada(self) -> bool:
        from dominio import version
        return bool(version.firmada(self.slug))

    # **Lo aprobado queda aprobado, segundo a segundo** (C-728). Jaime, 16-11:
    # *«las escenas aprobadas no se cancelan; quedan aprobadas, sólo cambian las
    # que necesitan cambio»*. La aprobación iba por la huella del spec entero, y
    # un cambio en e14 le volvía a pedir los 117 segundos. Ahora se guarda lo que
    # vio cada segundo (`Fotogramas.contenido`) y sólo se le enseña lo que no vio.
    def segundos(self, spec: dict | None = None) -> dict:
        """Los segundos de la guía, **por escena** (C-742): los dice `Fotogramas.rejilla`."""
        from dominio.fotograma import Fotogramas
        return Fotogramas(spec or self.spec).rejilla()

    def _aprobado(self) -> tuple[str, dict]:
        ruta = os.path.join("work", "still", "guia", self.slug, "aprobado.json")
        try:
            with open(ruta, encoding="utf-8") as f:
                return ruta, json.load(f)
        except FileNotFoundError:
            return ruta, {}

    def faltan(self) -> list[str]:
        """Los segundos cuyo contenido Jaime todavía no ha visto aprobado."""
        from dominio.fotograma import Fotogramas
        fotos, visto = Fotogramas(self.spec), self._aprobado()[1]
        return [n for n, f in self.segundos().items() if fotos.contenido(f) not in visto]

    def hojas(self, solo: list[str]) -> list[str]:
        """Las hojas de este spec, sólo con los segundos por aprobar; una vez por tanda.

        El nombre lleva la tanda: unas hojas del mismo spec con otros segundos
        —las de antes de traer una aprobación— no son éstas.
        """
        import hashlib
        self.tanda = f"{self.huella}-{hashlib.sha1(','.join(solo).encode()).hexdigest()[:6]}"
        hechas = sorted(os.path.join(self.salida, f) for f in os.listdir(self.salida)
                        if f.startswith(self.tanda)) if os.path.isdir(self.salida) else []
        if hechas:
            return hechas
        subprocess.run(["bash", "scripts/mirar.sh", "--segundos", str(self.n), self.fotos],
                       check=True, env={**os.environ, "GUIA_SOLO": ",".join(solo)})
        return self._compone(set(solo))

    def _compone(self, solo: set) -> list[str]:
        from PIL import Image, ImageDraw, ImageFont

        rejilla = self.segundos()
        fotos = sorted(f for f in os.listdir(self.fotos) if f.endswith(".png") and f[:-4] in solo)
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
        # **Una hoja por escena** (C-742): la escena es la unidad que se mira.
        grupos = {}
        for f in fotos:
            grupos.setdefault(f[:3] if f[0] == "e" else "", []).append(f)
        paginas = [(g, fs[k:k + por_hoja]) for g, fs in grupos.items()
                   for k in range(0, len(fs), por_hoja)]
        for k, (grupo, tanda) in enumerate(paginas):
            hoja = Image.new("RGB", (cols * ancho, filas * (alto + rotulo)), "#0B0B0F")
            pinta = ImageDraw.Draw(hoja)
            for i, f in enumerate(tanda):
                x, y = (i % cols) * ancho, (i // cols) * (alto + rotulo)
                im = Image.open(os.path.join(self.fotos, f)).convert("RGB")
                hoja.paste(im.resize((ancho, alto)), (x, y + rotulo))
                s = int(rejilla.get(f[:-4], 0) / 30)
                rot = f"{s // 60}:{s % 60:02d}" + (f" · {grupo}" if grupo else "")
                pinta.text((x + 8, y + 4), rot, fill="#fad02c", font=letra)
            ruta = os.path.join(self.salida, f"{self.tanda}-{grupo + '-' if grupo else ''}{k + 1:02d}.jpg")
            hoja.save(ruta, quality=88)
            out.append(ruta)
        return out

    def costuras(self) -> dict:
        """**La unión, mirada antes del render** (C-745): la hoja de costuras.

        Los dos segundos a cada lado de cada corte entre escenas, con lo que se
        mide marcado (salto de encuadre, palabra repetida a través del corte) y
        la intención de cada lado escrita, para juzgar la continuidad.
        """
        from dominio.union import Union
        u = Union(self.slug, self.spec)
        falta = [n for n in u.nombres() if not os.path.isfile(os.path.join(self.fotos, f"{n}.png"))]
        if falta:
            subprocess.run(["bash", "scripts/mirar.sh", "--segundos", str(self.n), self.fotos],
                           check=True, env={**os.environ, "GUIA_SOLO": ",".join(falta)})
        cs = u.costuras()
        return {"hojas": u.hoja(self.fotos, self.salida, getattr(self, "tanda", self.huella)),
                "marcadas": [c.como_json() for c in cs if c.marcas],
                "cortes": len(cs)}

    def pide(self, hojas: list[str], faltan: list[str]) -> dict | None:
        """Deja el pedido abierto para Jaime y devuelve su respuesta si ya está."""
        prompt = (f"Hoja guía de {self.slug}: un fotograma por segundo del spec"
                  f" {self.huella}, antes de renderizar. La aprueba Jaime; lo que"
                  " diga de un segundo es un tiquet con `--de montaje`.")
        return servicio.pedir(PASO, self.slug, prompt, {
            "huella": self.huella, "hojas": hojas, "segundos": round(self.dura, 1),
            "por_aprobar": faltan, "costuras": self.costuras(),
            "se_aprueba_con": f"python scripts/guia.py {self.n} --aprobar --de \"…\"",
        }, cli=False)

    def al_dia(self) -> bool:
        """Si el pedido en pie enseña el spec de hoy y los segundos que faltan (C-723, C-728).

        Sin los segundos, un pedido de antes de C-728 —con los 117— seguía «al
        día» y la línea esperaba sobre él sin sacar la tanda que le toca a Jaime.
        """
        try:
            with open(servicio.ruta_pedido(PASO, self.slug), encoding="utf-8") as f:
                d = json.load(f).get("datos") or {}
        except FileNotFoundError:
            return True
        return (d.get("huella") == self.huella and d.get("por_aprobar") == self.faltan()
                and not self._antes_caduca())

    def _antes_caduca(self) -> bool:
        """Si la cadena caduca antes del render: la guía de hoy sale de un plan viejo (C-731).

        reel-23, 16-11: C-730 cambió `plan-reel.mjs`, la cadena decía «plan
        caducado», y la línea seguía esperando a Jaime sobre la guía de antes:
        sin montar no se rehacía el plan, y sin plan nuevo no salía la guía.
        """
        import cadena
        d = cadena.desde(self.n)
        orden = [e[0] for e in cadena.ESLABONES]
        return bool(d) and d[0] < orden.index("render")

    def aprobada(self, r) -> bool:
        return bool(r and r.get("aprobada") and r.get("huella") == self.huella)

    def aprueba(self, dijo: str) -> None:
        """Anota que Jaime aprobó la guía que tiene delante, con sus palabras."""
        with open(servicio.ruta_pedido(PASO, self.slug), encoding="utf-8") as f:
            vio = (json.load(f).get("datos") or {}).get("huella")
        if vio != self.huella:
            raise SystemExit(f"guia: Jaime vio el spec {vio} y el de hoy es {self.huella};"
                             " la guía vuelve a salir, no se aprueba la vieja")
        cuando = datetime.datetime.now().isoformat(timespec="seconds")
        with open(servicio.ruta_respuesta(PASO, self.slug), "w", encoding="utf-8") as f:
            json.dump({"aprobada": True, "huella": self.huella, "de": dijo, "cuando": cuando},
                      f, ensure_ascii=False, indent=1)
        self._anota(self.spec, {"de": dijo, "huella": self.huella, "cuando": cuando})
        hechas = self._escenas_aprobadas(self.spec)
        if hechas:
            print(f"guia: {self.slug} e{', e'.join(map(str, hechas))} aprobadas por Jaime")

    def _escenas_aprobadas(self, spec: dict) -> list:
        """**Lo que Jaime aprueba en la guía queda aprobado en su escena** (C-741).

        Las aprobaciones iban por segundo y no llegaban a las escenas: en reel-23
        las 18 figuraban abiertas hasta que aprobó la pieza entera, y el
        diseñador, la memoria y el visto trataron como abiertas escenas ya
        aprobadas. Una escena con **todos** sus segundos aprobados se aprueba con
        su firma; un tiquet suyo la reabre (`segmento.reabre`). Nunca desaprueba.
        """
        from dominio.fotograma import Fotogramas
        from dominio.reloj import beat_en
        from dominio.segmento import APROBADO, Segmento
        fotos, (_, visto) = Fotogramas(spec), self._aprobado()
        por = {}
        for nombre, f in self.segundos(spec).items():
            # El nombre dice la escena (C-742); sin escenas, el reloj del plan.
            b = int(nombre[1:3]) if nombre[0] == "e" else beat_en(self.slug, f / 30)
            if isinstance(b, int):  # ni sin plan ni sin EDL (`reloj.SIN_EDL`)
                por.setdefault(b, []).append(fotos.contenido(f) in visto)
        hechas = []
        for s in Segmento.de(self.slug):
            if por.get(s.n) and all(por[s.n]) and s.etiqueta != APROBADO:
                s.aprueba("jaime")
                hechas.append(s.n)
        return hechas

    def _anota(self, spec: dict, quien: dict) -> int:
        """Deja aprobado, segundo a segundo, lo que se ve en `spec`."""
        from dominio.fotograma import Fotogramas
        fotos, (ruta, visto) = Fotogramas(spec), self._aprobado()
        antes = len(visto)
        for f in self.segundos(spec).values():
            visto.setdefault(fotos.contenido(f), quien)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(visto, f, ensure_ascii=False)
        # Y el spec que vio, para que el plan conserve sus encuadres (C-730).
        copia = os.path.join(os.path.dirname(ruta), "aprobados", f"{spec.get('huella')}.json")
        os.makedirs(os.path.dirname(copia), exist_ok=True)
        with open(copia, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False)
        return len(visto) - antes

    def trae(self, ruta: str) -> int:
        """Pasa a segundos una aprobación de Jaime anterior a C-728.

        `ruta` es el spec que vio. Sólo cuenta si su huella —calculada como la
        calcula `reels-spec.mjs`— es la de una aprobación suya que está en el
        buzón: lo que se trae es su palabra, comprobada, no un criterio nuevo.
        """
        with open(ruta, encoding="utf-8") as f:
            spec = json.load(f)
        h = subprocess.run(["node", "-e", HUELLA_JS, ruta], capture_output=True, text=True,
                           check=True).stdout.strip()
        for d in (os.path.join("work", "servicio", PASO), os.path.join("work", "servicio", PASO, "usadas")):
            for nombre in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if nombre.startswith(self.slug + ".") and nombre.endswith("respuesta.json"):
                    with open(os.path.join(d, nombre), encoding="utf-8") as f:
                        r = json.load(f)
                    if r.get("aprobada") and r.get("huella") == h:
                        return self._anota(spec, {k: r.get(k) for k in ("de", "huella", "cuando")})
        raise SystemExit(f"guia: el spec de {ruta} da la huella {h} y Jaime no aprobó ninguna así")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pieza", type=int)
    ap.add_argument("--aprobar", action="store_true")
    ap.add_argument("--de", metavar="LO_QUE_DIJO_JAIME")
    ap.add_argument("--trae", metavar="SPEC_QUE_VIO")
    a = ap.parse_args()
    g = Guia(a.pieza)
    if a.trae:
        print(f"guia: {g.slug}: {g.trae(a.trae)} segundo(s) aprobados traídos de {a.trae}")
        return 0
    if a.aprobar:
        if not a.de:
            raise SystemExit("guia: se aprueba con las palabras de Jaime en --de")
        g.aprueba(a.de)
        print(f"guia: {g.slug} aprobada con el spec {g.huella}")
        return 0
    if g.firmada():
        return 0
    faltan = g.faltan()
    if not faltan:
        print(f"guia: {g.slug}: Jaime ya aprobó lo que se ve en cada segundo; se renderiza")
        return 0
    hojas = g.hojas(faltan)
    r = g.pide(hojas, faltan)
    if g.aprobada(r):
        print(f"guia: {g.slug} aprobada por Jaime; se renderiza")
        return 0
    # Una aprobación de otro spec no vale, y al lado del pedido nuevo lo daría
    # por contestado: la línea dejaría de esperar a Jaime y contaría un fallo.
    if r:
        servicio._archivar(PASO, g.slug, sufijo="otro_spec", solo_respuesta=True)
    print(f"espera a Jaime: hoja guía de {g.slug}, {len(faltan)} segundo(s) por aprobar,"
          f" {len(hojas)} hoja(s) en {hojas[0]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
