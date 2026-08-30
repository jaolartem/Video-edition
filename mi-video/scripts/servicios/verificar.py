"""El servicio de verificación: la puerta, como objeto.

No hace trabajo: comprueba. Y por eso su fallo se lee distinto — una pieza que no
pasa la puerta no está rota, está incompleta, y el motivo dice exactamente qué le
falta.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioVerificar(Servicio):
    nombre = "verificado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import verificar

        mal = verificar.revisar(pieza.slug)
        if not mal:
            return Resultado(True, salida="pasa la puerta")
        # Se devuelve el primero y se cuentan los demas: el motivo tiene que
        # caber en una linea del log y ser accionable. La lista entera esta en
        # `verificar.py --avisa`.
        resto = f" (+{len(mal) - 1} mas)" if len(mal) > 1 else ""
        return Resultado(False, motivo=mal[0].split(": ", 1)[-1][:140] + resto)
