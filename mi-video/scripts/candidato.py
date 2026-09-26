"""**Cuál de los ficheros de la carpeta es la voz que Jaime limpió.**

Sale de `voz-limpia.py` porque es un asunto entero —con su propia avería
documentada, C-518— y porque aquel fichero llegó a su techo de 300 líneas. La
regla de la casa: una cosa nueva no añade un fichero al lado, saca uno.
"""
import glob
import os

#: Donde mirar. Lo pasa quien llama para no tener dos listas de carpetas.
#: **Los sufijos que pone ESTE proyecto, y por eso no son respuestas de Adobe.**
#:
#: La regla estaba escrita tres veces en `candidato` y cada vez que aparecia un
#: sufijo nuevo habia que acordarse de la cuarta. No se acordo nadie: el 16-9,
#: con reel-11 ya montada y la voz limpia encajando al milimetro —0,0 s de
#: desfase en siete ventanas, medido con `sincronia.perfil`—, `candidato`
#: eligio `reel-11-voz-recortado.wav`, que lo escribe `dominio/correccion.py`.
#: Esa pista va 14,82 s corrida, asi que `encajar` la movio y despues se nego
#: por el desfase que acababa de meter. Lo que se leia era «NO encaja»: la voz
#: de Jaime, buena, rechazada por una copia nuestra.
#:
#: Lo de Adobe trae su propia marca; lo nuestro se excluye por nombre, que es
#: lo unico que no depende del orden en que se hagan las cosas. Aqui, en una
#: lista, para que anadir un sufijo sea anadir una linea y no acordarse de tres.
NUESTROS = ("-norm", "-sin-cola", "-con-cola", "-recortado")


def de(n, carpetas, base_voz):
    """El WAV limpiado del reel n, si lo hay.

    Por la convencion de nombres: el limpiado es el que **empieza por el nombre
    base y es mas largo** — `reel-01-voz.wav` -> `reel-01-voz-enhanced-v2.wav`.
    Entre varios, el mas reciente.
    """
    base = base_voz.format(slug=f"reel-{n:02d}").lower()
    vistos = []
    for carpeta in carpetas:
        if not os.path.isdir(carpeta):
            continue
        for f in glob.glob(os.path.join(carpeta, "*.wav")):
            nom = os.path.basename(f).lower()[:-4]
            # **Lo que produce ESTE script no es una respuesta.** `-norm` es la
            # copia con cabecera que se exporta junto a la voz cruda; comparte
            # base y es mas reciente, asi que ganaba el `max` y entraba como si
            # fuera la pista limpiada. La pieza habria salido con la voz SIN
            # limpiar y sonando igual de bien de nivel: invisible.
            #
            # Lo que vuelve de Adobe trae su propia marca (`-enhanced-v2`). Lo
            # nuestro se excluye por nombre y no por fecha, que es lo unico que
            # no depende de en que orden se hagan las cosas.
            if any(x in nom for x in NUESTROS):
                continue
            # **Y `-sin-cola` / `-con-cola` tampoco son respuestas: los hace ESTE
            # script.**
            #
            # Son el recorte y el relleno con que el propio paso cuadra la pista
            # al video. Al no excluirlos, cada corrida elegia el ajuste de la
            # anterior y le hacia otro encima: reel-07 llego a
            # `-con-cola-sin-cola-sin-cola-sin-cola`, cuatro capas de la misma
            # pista, y cada capa arrastraba el redondeo de la anterior.
            #
            if nom.startswith(base) and len(nom) > len(base):
                vistos.append(f)
    return max(vistos, key=os.path.getmtime) if vistos else None
