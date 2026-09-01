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
        # **Lo que se anota y no para**, con el porque de cada uno:
        #
        # - la descripcion que habla de otro texto: rehacerla es rehacer criterio
        #   estetico ya tomado, y la IA no es determinista (C-166);
        # - la repeticion que sobrevive al cosido: el eco de la costura ya lo
        #   cerro `sin_eco`, asi que lo que queda es tropiezo dentro de la toma o
        #   **figura deliberada**, y distinguirlos es entender, no medir.
        #
        # Los dos comparten forma: la maquina los ve, no los sabe resolver sola,
        # y pararse ahi deja la pieza sin nadie que pueda desatascarla. Se anotan
        # con su etapa y viajan con la pieza hasta que alguien mire el montaje.
        _DESCRIBIR = ("habla de otro texto", "sin contestar: ['describir']",
                      "dos veces seguidas")
        # **La caducidad se aparta ANTES de juzgar, no despues.**
        #
        # La primera version pedia que TODOS los motivos fueran de caducidad
        # para dejar pasar la pieza, y con eso reel-02 seguia trabado: tenia una
        # caducidad y dos motivos mas, asi que caia al bloqueo y el primer motivo
        # que se imprimia era justo el que no debe bloquear nunca. Se aparta y se
        # juzga lo que queda.
        caducas = [m for m in mal if any(x in m for x in _DESCRIBIR)]
        if caducas:
            _apunta_caducadas(pieza, caducas)
            mal = [m for m in mal if m not in caducas]
        if not mal:
            return Resultado(True, salida="descripciones de otro texto anotadas"
                                          " como ticket; la pieza sigue")
        # Se devuelve el primero y se cuentan los demas: el motivo tiene que
        # caber en una linea del log y ser accionable. La lista entera esta en
        # `verificar.py --avisa`.
        resto = f" (+{len(mal) - 1} mas)" if len(mal) > 1 else ""
        return Resultado(False, motivo=mal[0].split(": ", 1)[-1][:140] + resto)


def _apunta_caducadas(pieza, motivos):
    """Deja la caducidad como ticket, con su etapa. No para la pieza.

    Puntual es la palabra: dice *que* etapa y *que* dice de mas o de menos, no
    «vuelve a describir la pieza». Y no se repite — `ticket.abrir` es una fila
    nueva, pero el motivo lleva la etapa dentro, asi que dos corridas iguales no
    producen dos tickets distintos que haya que leer dos veces.
    """
    try:
        from dominio import ticket as tk

        for m in motivos:
            texto = m.split(": ", 1)[-1][:400]
            if any(t.get("dijo", "").startswith(texto[:60])
                   for t in tk.abiertos(pieza.slug)):
                continue          # ya esta dicho: repetirlo es ruido
            tk.abrir(pieza.slug, texto, None, "objecion")
    except Exception:                              # noqa: BLE001
        import registro

        registro.aviso("verificar", "no se pudo anotar la caducidad",
                       detalle=pieza.slug, eco=False)
