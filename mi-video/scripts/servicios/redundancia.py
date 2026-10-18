"""El servicio de redundancia: pide al modelo y carga lo que conteste.

Es un servicio de IA, así que no decide aquí: escribe un pedido y espera una
respuesta. La conteste el CLI o la sesión, el contrato es el mismo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioRedundancia(Servicio):
    nombre = "sin_redundancia"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import redundancia
        import servicio as contrato

        filas = redundancia.dossier(pieza.slug)
        if not filas:
            return Resultado(False, motivo="el dossier sale vacio")
        # **Se pregunta por los segmentos que cambiaron** (C-561). Del resto va
        # sólo lo que dicen, para que una repeticion entre etapas se vea sin
        # releer la pieza entera; si ninguno cambio, no hay pedido.
        from dominio.alcance import Alcance
        from dominio.memoria import Memoria

        mem = Memoria("redundancia", pieza.slug)
        pide = mem.cambiados(filas, CAMPOS, abiertas=Alcance.de(
            pieza.slug, "sin_redundancia").etapas)
        if not pide:
            return Resultado(True, salida="ningun segmento cambio desde su"
                                          " ultima lectura")
        datos = [f if _beat(f) in pide else
                 {"beat": f.get("beat"), "texto": f.get("texto"), "contexto": True}
                 for f in filas]
        prompt = open(redundancia.PROMPT, encoding="utf-8").read()
        r = contrato.pedir("redundancia", pieza.slug, prompt, datos)
        if r is None:
            # **Un pedido abierto no es un fallo: es una espera.** El motor
            # distingue las dos cosas, y por eso el motivo lo dice con esas
            # palabras — una pieza que espera no hay que desatascarla, hay que
            # contestarla.
            return Resultado(
                False,
                motivo=f"espera respuesta del servicio -> "
                       f"{contrato.ruta_pedido('redundancia', pieza.slug)}")
        n = redundancia.cargar(pieza.slug, r)
        mem.guarda(filas, CAMPOS)
        return Resultado(True, salida=f"{n} corte(s) anotados")


#: Lo que redundancia pregunta de un segmento: lo que dice (C-561).
CAMPOS = ("beat", "texto")


def _beat(f):
    try:
        return int(f.get("beat"))
    except (TypeError, ValueError):
        return None
