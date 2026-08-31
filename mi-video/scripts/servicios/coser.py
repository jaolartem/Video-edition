"""El servicio de costuras: la fase `cosido`, como objeto.

Deja de ser `ServicioScript("cosido", "scripts/costuras.py {n}")` —un
`subprocess` con una plantilla de texto— y pasa a llamar a `costuras.coser()`.

## Qué cambia, además de la forma

Un `ServicioScript` sólo sabe una cosa del paso: si el proceso salió con 0. Eso
es exactamente el fallo de C-48 —salir con éxito sin haber hecho nada— y aquí
había sitio para él: `coser()` no hace nada si la pieza no tiene EDL, y por la
vía del subprocess eso salía como éxito.

Como objeto, el paso puede:

- **decir que no puede correr** en vez de correr en vacío — `puede()` mira que
  el EDL exista, y el motor distingue «no se pudo» de «falló»;
- **contar lo que hizo**, comparando la huella del corte antes y después: si
  ninguna costura se movió, lo dice, y eso es información que antes no existía.

No se toca ni una decisión de `costuras.py`: son las mismas seis llamadas en el
mismo orden. Lo que cambia es quién las llama y qué se sabe después.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioCoser(Servicio):
    nombre = "cosido"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL: no hay costuras que mirar"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import costuras
        import modelo

        # La huella del corte antes y después. Es la misma que usa `version`
        # para no crear dos versiones del mismo montaje, así que aquí sirve para
        # lo contrario: saber si el paso movió algo de verdad.
        antes = modelo.huella_edl(pieza.slug)
        try:
            costuras.coser(pieza.slug)
        except Exception as e:                     # noqa: BLE001
            return Resultado(False, motivo=f"{type(e).__name__}: {str(e)[:120]}")
        despues = modelo.huella_edl(pieza.slug)

        if antes and antes == despues:
            # **Y no es un fallo.** Una pieza ya cosida vuelve a pasar por aquí
            # cada vez que la línea corre: que no haya nada que mover es el
            # estado bueno, no un problema.
            return Resultado(True, salida="las costuras ya estaban en su sitio")
        return Resultado(True, salida="costuras rehechas")
