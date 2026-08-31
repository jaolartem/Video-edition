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
        # **Y si la puerta sabe que paso lo arregla, manda la pieza ahi.**
        #
        # Una descripcion caducada no es un fallo que alguien tenga que ir a
        # desatascar: es el paso `descrito` corriendo sobre un texto que ya
        # cambio. La puerta lo diagnosticaba con nombre y numero de etapa —«la
        # descripcion de las etapas [6, 7, 8] habla de otro texto»— y despues
        # dejaba la pieza parada delante de ella misma, porque `descrito` ya
        # estaba dado por hecho y nadie lo volvia a pedir. reel-01 dio dos
        # vueltas asi, contando el mismo fallo cada vez.
        #
        # Es lo mismo que C-116 por otra puerta: el paso veia el defecto y no
        # tenia con que arreglarlo. Aqui el arreglo existe y estaba a un salto.
        # Las dos caras del mismo atasco: la descripcion caduco, y por eso hay
        # un pedido de `describir` sin contestar. La segunda es consecuencia de
        # la primera, asi que las dos juntas siguen siendo «vuelve a describir».
        _DESCRIBIR = ("habla de otro texto", "sin contestar: ['describir']")
        if all(any(x in m for x in _DESCRIBIR) for m in mal):
            return Resultado(True, volver_a="descrito",
                             salida="descripciones caducadas: "
                                    + mal[0].split(": ", 1)[-1][:120])
        return Resultado(False, motivo=mal[0].split(": ", 1)[-1][:140] + resto)
