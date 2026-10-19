"""**El contrato de un paso, por apartados: sólo lo que ese paso lee.** C-583.

El visto recibía el contrato entero del diseño —45 KB, y 62 KB con el piso
delante— para contestar una sola cosa: si la pieza se le puede enseñar a Jaime.
Medido el 18-10-2026 sobre W40: el contrato eran 33 K de los 108-155 K tokens
de cada visto, y lo leía en dos tandas porque la primera salía cortada.

El contrato ya sabía que el visto no recibe encargos: `Momento("visto")` declara
qué trae y qué no. Lo que faltaba era la otra mitad, **qué lee**. Cada momento
la declara en `Momento.lee`, con los títulos de sus apartados, y el pedido lleva
esos y ninguno más.

**Se corta, no se copia.** El texto sigue viviendo en un solo fichero: un
apartado que cambia, cambia en todos los momentos que lo leen. Y lo que el
momento declara y el fichero ya no tiene no se calla: `faltan` lo dice, y el
registro de contratos para el build (ver `contrato/registro.py`).
"""
from __future__ import annotations

import re

#: Un apartado empieza en un título de markdown, de uno a tres `#`.
TITULO = re.compile(r"(?m)^(?=#{1,3} )")


def _llano(s: str) -> str:
    """El título sin marcas ni acentos, para compararlo con lo declarado."""
    import unicodedata

    s = unicodedata.normalize("NFKD", s.lstrip("#").strip())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[*`_]", "", s).lower().strip()


class Pliego:
    """Un contrato de IA leído por apartados."""

    def __init__(self, texto: str):
        #: `(titulo, texto)` en orden. El primero puede no tener título.
        self.apartados = [(p.splitlines()[0] if p.startswith("#") else "", p)
                          for p in TITULO.split(texto or "") if p]

    @classmethod
    def de(cls, ruta: str) -> "Pliego":
        with open(ruta, encoding="utf-8") as f:
            return cls(f.read())

    def _es(self, titulo: str, declarado: str) -> bool:
        return bool(titulo) and _llano(titulo).startswith(_llano(declarado))

    def faltan(self, lee) -> list:
        """Lo declarado que este fichero ya no tiene. Vacío es lo sano."""
        return [d for d in lee or ()
                if not any(self._es(t, d.lstrip("-")) for t, _ in self.apartados)]

    def solo(self, lee) -> str:
        """Los apartados declarados, en el orden del fichero. Sin `lee`, entero.

        Si todo lo declarado empieza por `-`, es lo que **no** se lee: el
        diseño lee su contrato entero menos el apartado del visto.
        """
        if not lee:
            return "".join(p for _, p in self.apartados)
        if all(d.startswith("-") for d in lee):
            return "".join(p for t, p in self.apartados
                           if not any(self._es(t, d[1:]) for d in lee))
        return "".join(p for t, p in self.apartados
                       if any(self._es(t, d) for d in lee))

    def frase_dentro(self, lee, frase: str) -> bool:
        """Si una frase del contrato cae en lo que ese momento lee."""
        from contrato.aguja import plano

        return plano(frase).lower() in plano(self.solo(lee)).lower()


def para(paso: str, prompt: str) -> str:
    """El contrato que viaja en el pedido de `paso`: sus apartados y no más.

    Si el momento no declara `lee`, o declara un título que ya no está, viaja
    entero: lo conservador es leer de más, no dejar fuera una regla.
    """
    try:
        from contratos import momento
        from dominio.oficio import LA_FASE

        par = momento(LA_FASE.get(paso, paso))
        lee = par[1].lee if par else ()
        pliego = Pliego(prompt)
        if not lee or pliego.faltan(lee):
            return prompt
        return pliego.solo(lee)
    except Exception:                              # noqa: BLE001
        return prompt
