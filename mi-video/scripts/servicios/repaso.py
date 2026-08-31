"""El ultimo repaso de redundancia, con la pieza ya cosida.

Regla de Jaime, y la pidio despues de ver la misma repeticion volver tres veces
en una tarde: *«revisemos si otra pasada extra de redundancia al final antes de
renderizar para revisar todo vale la pena hacerla — siempre»*.

## Por que hace falta un SEGUNDO repaso

`sin_redundancia` corre en la fase 5, sobre el corte recien depurado, y esta
bien ahi: es cuando la repeticion es mas barata de quitar. Pero **lo que se
juzga ahi no es lo que se oye al final**. Entre esa fase y el render pasan
`recortado`, `revalidado` y `cosido`, y cada uno rehace el corte:

- `fijar` reconstruye la etapa entera cuando entra una declaracion nueva, y con
  ella vuelve el texto que se habia recortado dentro.
- Una nota se estampa con la huella de su montaje (C-92), asi que en cuanto el
  corte cambia deja de aplicarse — con razon, pero el hueco queda.
- Cambiar de toma en una etapa mete texto que nadie ha leido todavia.

Medido en reel-01 en una sola tarde: «luego sube» volvio dos veces, «en Ontario,
un dueno de negocio en Ontario» aparecio al cambiar de toma, y la costura de la
etapa 2 acabo diciendo «estructura y y los que usan». Ninguno era un fallo del
primer repaso: los tres nacieron despues de el.

## Por que aqui y no justo antes del render

Va **entre `cosido` y `descrito`**, que es el ultimo punto donde el texto ya esta
cerrado y cortar todavia es barato. Un corte despues de `descrito` invalida las
descripciones —hablan de un texto que ya no es— y despues de `cortado` obliga a
rehacer los recortes y la voz. Aqui no cuesta nada de eso.

## Y no decide nadie mas que quien lee

Es el mismo contrato que la fase 5 —pedido fuera, respuesta dentro— porque la
razon no ha cambiado: reconocer que dos frases dicen lo mismo es comprender, no
comparar cadenas (C-81). Lo unico que cambia es **cuando se mira**.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioRepaso(Servicio):
    nombre = "repasado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import redundancia
        import revision
        import servicio as contrato

        filas = redundancia.dossier(pieza.slug)
        if not filas:
            return Resultado(True, salida="sin material que repasar")
        # **Y va la curva con el texto.** El contrato pregunta si el tono va con
        # el momento, y sin la curva delante eso no se puede contestar: la
        # intensidad es sin signo y el texto no dice como se dijo. Es el mismo
        # error que costo C-100 —medir la direccion y no pasarsela a quien
        # decide— y aqui seria peor, porque este es el ultimo que mira.
        try:
            import consulta

            curva = consulta.onda(pieza.slug)
        except Exception:                          # noqa: BLE001
            curva = []
        datos = {"montaje": filas, "onda": curva,
                 "estructura": (pieza.edl or {}).get("estructura")
                               or "Information Gap"}
        # **Tiene su propio contrato, y no es el de redundancia.** Jaime:
        # *«la revision de redundancia es revision de composicion, logica,
        # libreto, tono: es tu revision final»*. Reusar el prompt de la fase 5
        # pedia buscar frases repetidas, que es una de las cinco cosas que hay
        # que mirar aqui y la menos grave de todas.
        prompt = open(
            os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "repaso.prompt.md"),
            encoding="utf-8").read()
        r = contrato.pedir("repaso", pieza.slug, prompt, datos)
        if r is None:
            return Resultado(
                False,
                motivo=f"espera el repaso final -> "
                       f"{contrato.ruta_pedido('repaso', pieza.slug)}")
        n = redundancia.cargar(pieza.slug, r, pasada=2)
        # **Se aplican aqui mismo.** En la fase 5 anotar y aplicar son dos pasos
        # porque entre medias pasan cosas; aqui no queda nada entre el repaso y
        # el corte, y dejarlo anotado sin aplicar seria repetir el fallo que
        # este paso viene a cerrar.
        puestos = revision.aplicar(pieza.slug) if n else 0
        if not puestos:
            return Resultado(True, salida="pieza limpia, sin repeticiones")
        # **Si corto algo, no se compone: se vuelve a coser y se relee.** El
        # texto ya no es el que se juzgo, y describir sobre un texto viejo es el
        # fallo que este paso viene a cerrar. Jaime: *«asegurate de hacerlo
        # ciclico: si no pasa redundancia, no se compone»*.
        # **Y se dice lo que significa.** Jaime: *«si no pasa perfecta, no
        # hiciste un buen trabajo»*. Un corte aqui no es este paso funcionando:
        # es este paso rescatando algo que tenia que haber llegado limpio. Que
        # el numero salga en el parte es lo que impide que el rescate se vuelva
        # rutina — un paso que siempre corta algo deja de ser una red y pasa a
        # ser parte del proceso, y entonces nadie arregla lo que lo llena.
        return Resultado(True, volver_a="cosido",
                         salida=f"{puestos} corte(s) aplicados — la pieza no"
                                f" llego limpia, mira que paso antes")
