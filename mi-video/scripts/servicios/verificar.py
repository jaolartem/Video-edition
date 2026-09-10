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
        # **Y se le pasa la pieza, que es lo que hace que sea la misma regla.**
        #
        # `separa` solo le pregunta a lo que Jaime ya decidio `if not blando and
        # slug`, asi que sin el slug la consulta no ocurre. Esta puerta lo
        # omitia: `verificar.py 3` decia «OK, todo en pie» y la linea paraba la
        # misma pieza por «e6: sin material y sin tablero», que la nota #661
        # contesta desde el 5-9. reel-03 dio dos vueltas asi y el motor la
        # planto — con el detalle correcto en un log que decia lo contrario del
        # que se corre a mano. C-351.
        paran, avisan = verificar.separa(mal, slug=pieza.slug)
        # **Lo que Jaime ya contesto no vuelve como tiquet.** Con C-351 la
        # puerta empezo a ablandar esos motivos —bien— y este bucle los
        # convertia en tiquets igual: el #291 decia literalmente «e6 · sin
        # material y sin tablero — YA DECIDIDO (nota #661)», iba a `disenado` y
        # dejaba la pieza trabada por algo resuelto hace cinco dias. Un aviso
        # que cita la decision que lo contesta no es trabajo pendiente: es la
        # prueba de que no lo hay.
        for m in avisan:
            if verificar.CONTESTADO in m:
                continue
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


