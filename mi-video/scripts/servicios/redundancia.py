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
        prompt = open(redundancia.PROMPT, encoding="utf-8").read()
        r = contrato.pedir("redundancia", pieza.slug, prompt, filas)
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
        return Resultado(True, salida=f"{n} corte(s) anotados")
