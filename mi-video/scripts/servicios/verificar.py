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
        # **Lo que no para, se anota. Todo, sin excepcion.**
        #
        # Jaime: *«si ven algo raro, levanten tickets»*. La puerta ve cosas que
        # no sabe resolver sola y hasta ahora unas se convertian en ticket y
        # otras solo se imprimian — o sea que se perdian en cuanto la corrida
        # acababa. Un aviso que solo existe en la pantalla es un aviso que no
        # ocurrio.
        #
        # Que pare o no lo decide `verificar.separa`, que es una sola regla y la
        # leen las dos puertas. Lo que no para viene aqui y sale como ticket con
        # su pieza, para que viaje con ella hasta que alguien lo mire.
        paran, avisan = verificar.separa(mal)
        for m in avisan:
            _anota(pieza, m)
        if not paran:
            return Resultado(True, salida=f"pasa; {len(avisan)} ticket(s)"
                                          f" levantados" if avisan
                             else "pasa la puerta")
        # Se devuelve el primero y se cuentan los demas: el motivo tiene que
        # caber en una linea del log y ser accionable. La lista entera esta en
        # `verificar.py --avisa`.
        resto = f" (+{len(paran) - 1} mas)" if len(paran) > 1 else ""
        return Resultado(False, motivo=paran[0].split(": ", 1)[-1][:140] + resto)


def _anota(pieza, motivo: str) -> None:
    """Levanta el ticket, sin repetirlo si ya esta dicho."""
    from dominio import ticket as tk

    try:
        texto = motivo.split(": ", 1)[-1][:2000]
        if any((t.get("dijo") or "").startswith(texto[:60])
               for t in tk.abiertos(pieza.slug)):
            return
        tk.abrir(pieza.slug, texto, None, "objecion")
    except Exception:                              # noqa: BLE001
        import registro

        registro.aviso("verificar", "no se pudo levantar el ticket",
                       detalle=f"{pieza.slug}: {motivo[:120]}", eco=False)


