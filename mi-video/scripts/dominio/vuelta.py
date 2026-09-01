"""Qué cambió desde la vuelta anterior, y qué pasó con lo que se pidió.

**Por qué existe.** Jaime, viendo arrancar la séptima vuelta de repaso del
reel-01: *«el repaso debe ser sobre lo que se cambió; ya el compositor revisó
todo»*.

Y tenía delante la prueba. El paso mandaba **la pieza entera** en cada vuelta, así
que quien contestaba volvía a juzgarla desde cero. Releer lo que ya pasó no lo
mejora: lo cambia. Cada lectura encuentra una mejora nueva, cada mejora rehace el
corte, y el corte rehecho pide otra lectura. reel-01 llegó así a la vuelta 7 sin
que ninguna de las seis anteriores estuviera mal.

## Las tres cosas que hacen falta para repasar un cambio

1. **Qué cambió** — las etapas cuyo texto no es el que se aprobó.
2. **Sus costuras** — la de antes y la de después de cada una, porque un borde
   que se mueve cambia lo que se oye a los dos lados. Van marcadas `vecina`, y no
   se juzgan enteras: se juzga que enganchen.
3. **Qué se pidió y qué pasó con ello.** Un borde declarado que no llegó a su
   sitio no es un borde que haya que volver a declarar: es una avería, y volver a
   pedirlo la esconde. Fue exactamente C-161 durante seis vueltas.

## Lo que NO hace

No decide si el cambio está bien —eso es comprender, y lo hace quien lee—, y no
recorta la primera vuelta: sin una vuelta anterior con la que comparar, «lo que
cambió» es la pieza entera, y decir otra cosa sería inventarse un aprobado.
"""
from __future__ import annotations

import glob
import json
import os


class Vuelta:
    """La vuelta N de un paso sobre una pieza, contra la N-1."""

    #: Un borde se da por puesto si cae a menos de esto de donde se pidió. No es
    #: tolerancia de gusto: es el redondeo del cosido a frontera de palabra, que
    #: sí puede mover un borde y **debe** poder.
    CERCA = 0.06

    def __init__(self, paso: str, slug: str, montaje: list, carpeta: str):
        self.paso, self.slug, self.montaje = paso, slug, list(montaje or [])
        self._dir = os.path.join(carpeta, "usadas")
        self._antes, self._pedi = self._anterior()

    # ── de dónde sale la vuelta anterior ────────────────────────────────
    def _anterior(self):
        """El montaje y la respuesta de la última vuelta archivada.

        Se lee del archivo y no de la base a propósito: lo que hay que comparar
        es **lo que se le enseñó a quien contestó**, no lo que la base cree hoy.
        Si la pieza cambió por otro sitio, eso también es un cambio que repasar.
        """
        ns = []
        for p in glob.glob(os.path.join(self._dir, f"{self.slug}.*.pedido.json")):
            trozo = os.path.basename(p)[len(self.slug) + 1:].split(".")[0]
            if trozo.isdigit():
                ns.append(int(trozo))
        if not ns:
            return None, []
        n = max(ns)
        antes = self._leer(f"{self.slug}.{n}.pedido.json")
        pedi = self._leer(f"{self.slug}.{n}.respuesta.json")
        montaje = ((antes or {}).get("datos") or {}).get("montaje")
        return (montaje if isinstance(montaje, list) else None,
                pedi if isinstance(pedi, list) else [])

    def _leer(self, nombre):
        try:
            with open(os.path.join(self._dir, nombre), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    # ── lo que se mira ──────────────────────────────────────────────────
    @property
    def primera(self) -> bool:
        """Sin vuelta anterior no hay «lo que cambió»: hay la pieza."""
        return not self._antes

    def _texto(self, filas):
        """El texto de cada etapa, **juntando sus tramos**.

        El montaje viene con una fila por tramo, no por etapa: una etapa cosida
        de tres trozos son tres filas con el mismo `beat`. Quedarse con una sola
        —lo que hace un `dict` por comprensión— compara un tercio contra la
        etapa entera, y entonces «no cambió» y «cambió» dejan de significar nada.
        """
        junto: dict = {}
        for f in filas:
            b = f.get("beat")
            if b is None:
                continue
            junto.setdefault(b, []).append(f.get("texto") or "")
        return {b: " ".join(x for x in ts if x) for b, ts in junto.items()}

    def _tramos_de(self, beat):
        """Por dónde entra cada trozo de esa etapa, hoy."""
        return [f.get("desde") for f in self.montaje
                if f.get("beat") == beat and f.get("desde") is not None]

    def cambiadas(self) -> set:
        """Las etapas cuyo texto no es el que se aprobó — o que no existían."""
        if self.primera:
            return {f.get("beat") for f in self.montaje}
        antes, ahora = self._texto(self._antes), self._texto(self.montaje)
        return {b for b, t in ahora.items() if antes.get(b) != t}

    def mirar(self) -> set:
        """Lo cambiado **y sus vecinas**, que es donde vive la costura."""
        if self.primera:
            return {f.get("beat") for f in self.montaje}
        beats = sorted(b for b in self._texto(self.montaje) if b is not None)
        cam = self.cambiadas()
        fuera = set(cam)
        for i, b in enumerate(beats):
            if b in cam:
                if i:
                    fuera.add(beats[i - 1])
                if i + 1 < len(beats):
                    fuera.add(beats[i + 1])
        return fuera

    # ── qué pasó con lo que se pidió ────────────────────────────────────
    def suerte(self) -> list:
        """Para cada cosa que se pidió la vuelta pasada, dónde acabó.

        Es la mitad que faltaba. Sin ella, quien lee sólo puede comprobar que
        algo sigue mal, y la respuesta natural a eso es volver a pedirlo — que
        es lo que convierte una avería en una vuelta más.
        """
        if self.primera:
            return []
        entero = " ".join(f.get("texto") or "" for f in self.montaje)
        salida = []
        for x in self._pedi or []:
            if x.get("tramos"):
                salida.append(self._suerte_borde(x))
            elif x.get("sube"):
                salida.append({"pedi": "sube", "beat": x.get("beat"),
                               "que": str(x.get("sube"))[:200],
                               "paso": "quedó anotado para Jaime"})
            elif x.get("ancla"):
                sigue = str(x["ancla"]) in entero
                salida.append({"pedi": "corte", "que": str(x["ancla"])[:120],
                               "paso": "sigue sonando — NO se aplicó" if sigue
                                       else "cortado"})
        return salida

    def _suerte_borde(self, x):
        """Un borde: se pidió que la etapa entrara ahí, ¿entra algún trozo ahí?

        La pregunta es «¿existe ese borde en el montaje?», no «¿es el primero?».
        Una etapa cosida de tres trozos tiene tres entradas, y comparar contra
        una sola daba desfases de dos minutos que no eran desfases: era la
        pregunta mal hecha.
        """
        b = x.get("beat")
        pedido = x.get("tramos") or []
        desde = pedido[0][0] if pedido and len(pedido[0]) > 1 else None
        hoy = self._tramos_de(b)
        if desde is None or not hoy:
            return {"pedi": "borde", "beat": b, "paso": "no se puede comprobar"}
        d = min(abs(float(h) - float(desde)) for h in hoy)
        return {"pedi": "borde", "beat": b, "pedido_en": round(float(desde), 3),
                "entra_en": [round(float(h), 3) for h in hoy],
                "paso": "puesto" if d <= self.CERCA else
                        f"NO llego: el mas cercano se quedo a {d * 1000:.0f} ms"
                        f" — es una averia de la maquina, no un borde que haya"
                        f" que repetir"}

    def pedidas(self) -> set:
        """Las etapas que la vuelta pasada **pidió** cambiar.

        Un borde dice su beat. Un corte dice su ancla, y el beat sale de buscar
        esa ancla en el texto anterior: es donde sonaba cuando se pidió quitarla.
        """
        if self.primera:
            return set()
        antes = self._texto(self._antes)
        fuera = set()
        for x in self._pedi or []:
            if x.get("tramos") and x.get("beat") is not None:
                fuera.add(x["beat"])
            elif x.get("ancla"):
                a = str(x["ancla"])
                fuera |= {b for b, t in antes.items() if a in t}
        return fuera

    # ── lo que viaja en el pedido ───────────────────────────────────────
    def datos(self) -> dict:
        """El bloque que se le manda a quien lee. Vacío en la primera vuelta.

        Separa las etapas en cuatro montones, y **los cuatro significan cosas
        distintas** — mezclarlos es lo que obligaba a releer la pieza entera:

        - `cambiaron_como_pedi` — se mira a fondo: es el trabajo de la vuelta.
        - `cambiaron_sin_pedirlo` — **la alarma.** Nadie pidió tocarlas y están
          tocadas, así que algo las movió de lado. Es el sitio por donde el
          reel-01 perdía texto entre vueltas.
        - `no_cambiaron_y_lo_pedi` — se pidió y no pasó: avería, no un
          re-intento.
        - `ya_aprobadas` — idénticas a la vuelta que pasó, y viaja **la huella**
          de cada una para poder decirlo sin leerlas. Comprobar que nada más
          cambió es contar, no interpretar; leerlas otra vez es lo que hace que
          la pieza no cierre nunca.
        """
        if self.primera:
            return {}
        cam, ped = self.cambiadas(), self.pedidas()
        ver = self.mirar()
        todas = self._texto(self.montaje)
        quietas = [b for b in sorted(x for x in todas if x is not None)
                   if b not in ver]
        return {
            "cambiaron_como_pedi": sorted(b for b in cam & ped if b is not None),
            "cambiaron_sin_pedirlo": sorted(b for b in cam - ped
                                            if b is not None),
            "no_cambiaron_y_lo_pedi": sorted(b for b in ped - cam
                                             if b is not None),
            "y_sus_costuras": sorted(b for b in ver - cam if b is not None),
            "ya_aprobadas": {str(b): _huella(todas[b]) for b in quietas},
            "suerte_de_lo_que_pedi": self.suerte(),
        }


def _huella(texto: str) -> str:
    """Ocho caracteres que cambian si el texto cambia. Para contar, no para leer."""
    import hashlib

    return hashlib.sha1((texto or "").encode("utf-8")).hexdigest()[:8]
