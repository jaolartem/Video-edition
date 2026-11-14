"""Cómo se juzga una unidad **contra la etapa que quiere cumplir**.

`dominio.enunciado` parte la cinta; esto dice cuál de los trozos sirve. Son dos
oficios y estaban en el mismo fichero, que es como una medida acabó decidiendo:
la fluidez de una toma se sumaba a su cobertura y una toma apagada que cubría un
poco más ganaba a una viva.

Aquí no se suma nada. Jaime fijó el orden: *«lo más importante es el mensaje, lo
que se dice; luego cómo se dice; luego cómo se ve»*, y eso es **en dos pasos, no
en una suma ponderada**: sólo compiten los enunciados que dicen el beat
(`puntua`, `dice`, `UMBRAL`, `RELATIVO`), y entre ellos gana el más expresivo,
que ya es cosa de `dominio.voz`.

**Y el libreto entra como vocabulario, no como texto.** Jaime: *«no es el
libreto lo importante, lo importante es el framework y el copy… los módulos son
el copy»*. El párrafo es una forma de decir la etapa, no la forma; por eso lo
que se compara son palabras de contenido y no la frase.
"""
from __future__ import annotations

from . import texto as _tx
from . import vocabulario as _voc
from .enunciado import FIN

# Por encima de esto, dos enunciados son el mismo intento y sólo entra uno.
# Medido sobre los intentos repetidos del reel 1: los duplicados reales caen
# entre 0,55 y 0,8; dos beats distintos del mismo libreto rara vez pasan de 0,35.
IGUAL = 0.5
# Suelo absoluto de cobertura: por debajo, el enunciado no dice el beat.
UMBRAL = 0.18
# Y suelo relativo: sólo compite quien se acerca al que mejor lo dice. Es lo que
# impide que la voz rescate a uno que dice la mitad — el mensaje filtra primero.
RELATIVO = 0.80
# Finalistas por beat. Antes eran 3; con la voz decidiendo de verdad conviene
# mirar algunos más, porque el mejor de texto y el mejor de voz rara vez son el
# mismo enunciado.
FINALISTAS = 5
# Escalón con que se comparan dos expresividades. Por debajo de un cuarto de
# semitono la diferencia es ruido del detector, no de la voz, y en ese caso
# vuelve a mandar la cobertura en vez de decidir el azar de la medición.
PASO_VOZ = 0.25


def tartamudeo(texto, idioma=None):
    """
    Cuánto se repite el enunciado consigo mismo. 0 = limpio, 1 = todo repetido.

    Es la firma del intento fallido: «pasa sin cada semana que pasa sin saber
    sin saber cada semana que pasa cada». Sin esto, ese trozo ganaba su beat
    porque **repetir las palabras del libreto sube la cobertura** — el
    tartamudeo puntuaba como acierto.
    """
    ws = _voc.contenido(texto, idioma)
    if len(ws) < 4:
        return 0.0
    return 1 - len(set(ws)) / len(ws)


def integridad(texto):
    """
    Cuántos extremos de la frase están enteros: 0, 1 ó 2.

    El transcript conserva mayúsculas y puntuación, así que un enunciado que
    empieza en minúscula **empieza a mitad de frase** y uno que no acaba en
    punto **se corta a mitad de idea**. Es el aprendizaje 36 hecho criterio:
    entrar en frontera de tramo no garantiza entrar en la frase.

    Va por encima de la voz a propósito. Una frase rota es un defecto de
    mensaje, y el mensaje manda sobre cómo se dice.
    """
    ws = texto.split()
    if not ws:
        return 0
    abre = ws[0][:1].isupper() or ws[0][:1] in "¿¡"
    return int(abre) + int(ws[-1][-1:] in FIN)


def trabado(texto):
    """
    Palabras pegadas repetidas: «usted usted», «no no», «su negocio su».

    Es exactamente lo que Jaime oyó en el reel 3 —*«el tercero se traba, usted
    usted tiene un contador»*— y lo que `tartamudeo` no ve: aquel mide repetición
    en todo el enunciado y se diluye con la longitud; esto mira sólo el pegado,
    que es lo que se nota al oído.
    """
    ws = _voc.palabras(texto)
    return sum(1 for a, b in zip(ws, ws[1:]) if a == b)


def parecido(u, v):
    """
    Cuánto dicen lo mismo dos enunciados. 0 = nada, 1 = idénticos.

    Es lo que distingue **dos intentos de una idea** de dos ideas distintas, y
    hacía falta porque el descarte por solape de tiempo no los ve: los cuatro
    intentos de «la mayoría de los emprendedores asume…» están en instantes
    distintos de la toma, así que ninguno solapa con otro y los cuatro podían
    entrar bajo etapas distintas. En el reel 1 entraron.

    Jaime: *«que no se repita lo que ya se dijo y se cumplió de acuerdo al
    copy»*. Una etapa cumplida cierra su idea para toda la pieza, no sólo para
    su propio hueco.
    """
    a, b = u["clave"], v["clave"]
    return len(a & b) / max(1, len(a | b))


def puntua(beat, u, idioma=None):
    """
    Cuánto dice este enunciado el beat, y cómo de bien lo dice.

    Cobertura del beat, no parecido general: importa **cuánto del beat está
    dicho**, no cuánto del enunciado sobra. Un enunciado largo que dice el beat
    entero vale más que uno corto que dice la mitad.

    Y la fluidez pesa: entre dos tomas que dicen lo mismo gana la que no
    tropieza. Sin ese término, la que tropieza gana — porque repite palabras del
    beat y eso subía la cobertura.
    """
    pedidas = set(_voc.contenido(beat, idioma))
    if not pedidas:
        return 0.0
    cubre = len(pedidas & u["clave"]) / len(pedidas)
    # Penaliza el relleno: mucho texto que no es del beat es divagación.
    sobra = len(u["clave"] - pedidas) / max(1, len(u["clave"]))
    return cubre - 0.25 * sobra - 0.8 * tartamudeo(u["texto"], idioma)


def dice(texto, termino):
    """Si un enunciado dice de verdad un termino, con la ortografia que sea.

    Los numeros se escriben de tres maneras en el mismo transcript -«30.000»,
    «30,000», «30000»- asi que se comparan sin separadores. Y sin tildes, que es
    lo que ya hace el resto del proyecto (`dominio.texto.numerico`).

    **La intencion, no la letra.** Jaime: *«la idea no es tomar el libreto
    literal, es tomar la intencion comunicativa de cada parte, respetando su
    funcion»*. Una cifra se puede decir de varias maneras y un desliz de dos
    dolares no cambia el mensaje ni la estructura, asi que el termino admite
    alternativas con `|`: «44|46» se cumple con cualquiera de las dos.
    """
    limpio = _tx.numerico            # comparar cifras, con su separador fuera
    return any(limpio(t) in limpio(texto) for t in str(termino).split("|"))
