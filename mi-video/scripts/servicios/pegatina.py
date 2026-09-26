"""**Su cara en un tablero es él hablando, nunca una pegatina quieta.**

Jaime, 14-9-2026, sobre reel-13 en el segundo 36: *«la cara es un activo solo
cuando habla y expresa, nunca puede ser un estiquer»*.

`sujeto_desde` congela el recorte o lo saca de otro instante (C-451, C-459,
C-485), así que una respuesta de diseño que lo traiga no se aplica: se para y se
dice qué hacer en su lugar. C-490.

Vive fuera de `servicios/disenar.py` porque es un asunto entero —una regla suya,
su porqué y su medida— y porque aquel fichero llegó a su techo de 300 líneas. La
regla de la casa es que una cosa nueva no añade un fichero al lado: saca uno. El
que salió fue éste.
"""


def quietas(tableros):
    """Las etapas que declaran `sujeto_desde`. Vacía es que no hay ninguna.

    Se mira tanto en la raíz del tablero como dentro de `props`: las dos formas
    han llegado, y mirar sólo una es no mirar.
    """
    return [t.get("etapa_orden") for t in tableros if isinstance(t, dict)
            and "sujeto_desde" in {**t, **(t.get("props")
                                           if isinstance(t.get("props"), dict) else {})}]


def motivo(etapas):
    """Lo que se le dice al que contestó, con la salida delante."""
    return (f"etapa(s) {etapas} declaran `sujeto_desde`: su cara en un tablero"
            " es él hablando, sincronizado con su voz, nunca una pegatina"
            " quieta (Jaime, 14-9). Quita `sujeto_desde`; si debajo no habla,"
            " compón sin `sujeto` o pide otra toma.")
