"""Los microscopios: medidas que el que compone pide cuando las necesita.

Regla de Jaime, y ordena toda la instrumentación del proyecto:

> *«La puerta de bordes puede ser un microscopio bueno para el LLM, que la puede
> utilizar con criterio editorial en los bordes que necesita ver; igual que las
> otras pruebas, que le pueden ser útiles cuando se declaran, pero son para casos
> fortuitos y siempre que sean necesarias, para **ahorrar tokens**. Todo lo que se
> pueda medir en código que se mida en código: **no quiero al LLM revisando script
> por script en cada viaje**.»*

## Los dos niveles

**Nivel 1 — se mide siempre.** Lo barato viaja ya medido dentro del pedido: el
texto que suena, los segundos de cada trozo, lo que quedó fuera a cada lado, la
expresividad y el tono de cada tramo. Eso no se pide: está.

**Nivel 2 — se pide.** Lo caro, o lo que sólo interesa en un punto concreto. Se
declara aquí con tres cosas: qué contesta, qué cuesta y cómo se invoca. El que
compone lo pide para el sitio que quiere mirar, y sólo para ése.

## Lo que esto NO es

No es que el código decida con la medida — eso fue el error que Jaime paró:
*«nada de eso se puede utilizar sin criterio editorial»*. Un instrumento devuelve
números; el criterio es de quien compone.

Y tampoco es que el LLM vaya a buscarlos leyendo los scripts. Si hace falta un
instrumento nuevo, se declara aquí y viaja en el contrato como los demás.
"""

#: Los instrumentos disponibles. Cada uno dice qué contesta y qué cuesta.
INSTRUMENTOS = {
    "borde_en_sonido": {
        "contesta": "Que bordes de la pieza dejan voz sonando despues del"
                    " corte, por etapa. El detector apunta; no decide.",
        "cuando": "Cuando sospechas que una salida se come el final de una"
                  " palabra y quieres saberlo antes de proponer moverla.",
        "cuesta": "Barato: lee la onda ya extraída. Un punto, milisegundos.",
        "invoca": "python scripts/consulta.py bordes_sucios '[\"<pieza>\"]'",
        "devuelve": "Los bordes a mirar, con su etapa y su segundo.",
    },
    "repeticion": {
        "contesta": "Cuánto sube la segunda entrega de una frase respecto a la"
                    " primera, en dB y en semitonos, y cuánto dura cada una.",
        "cuando": "Cuando una frase suena dos veces y hay que decidir si es"
                  " énfasis intencional o un rearranque. La vara es de Jaime:"
                  " vale si se NOTA intencional.",
        "cuesta": "Medio: extrae F0 de los dos tramos. Un par de segundos.",
        "invoca": "python scripts/consulta.py repeticion"
                  " '[\"<cinta>\", [d1, h1], [d2, h2]]'",
        "devuelve": "Los números y la vara. **No un veredicto**: decides tú.",
    },
    "abanico": {
        "contesta": "Dónde más se dice algo parecido en las siete cintas, con"
                    " sus segundos.",
        "cuando": "Cuando la toma que hay no sirve y hace falta otra. Es el"
                  " acceso al corpus: sin esto se elige entre lo que ya está"
                  " montado, que no es elegir.",
        "cuesta": "Caro: recorre el corpus entero. Pídelo con una frase"
                  " concreta, no con un tema.",
        "invoca": "python scripts/consulta.py abanico '[\"<frase>\"]'",
        "devuelve": "Los tramos que se parecen, con cinta y segundos.",
    },
}

#: Y lo que ya viene medido, para que nadie lo pida dos veces.
YA_MEDIDO = (
    "En cada trozo del montaje ya viajan: el texto que suena dentro del corte,"
    " sus segundos y su cinta, lo que quedó fuera a cada lado (`antes` /"
    " `despues`), y las medidas de voz (`voz`, `tono`) cuando el tramo da para"
    " medirlas. No hace falta pedir nada de eso: está en el pedido."
)


def lo_que_hizo_la_maquina(slug, desde=None):
    """Lo que los pasos automaticos movieron en esta pieza, para supervisarlo.

    Jaime: *«hay cosas que son imposibles de evitar; todos los procesos que estan
    ahi declarados no desaparecen, sino que son SUPERVISADOS y entendidos por el
    LLM, que entiende los resultados y se da cuenta cuando un borde quedo mas
    cerrado»*.

    Los pasos ya anotaban lo que hacian —`costuras` deja «2 corte(s), 9 dB» en
    `incidencia` en cada pasada— y nadie se lo ensenaba a quien compone. El
    escritor existia y el lector no: la misma averia de siempre, esta vez sobre
    el trabajo de la propia maquina.

    Con esto delante, un borde que quedo demasiado cerrado deja de ser una
    sorpresa en el render y pasa a ser una linea que se lee antes de componer.
    """
    import os
    import sqlite3
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import basedatos

    con = basedatos.abrir("ads/decisiones.db")
    con.row_factory = sqlite3.Row
    q = ("select asunto, detalle, cuando from incidencia"
         " where script in ('costuras', 'revision', 'fijar')"
         " and detalle like ?")
    args = [slug + "%"]
    if desde:
        q += " and cuando >= ?"
        args.append(desde)
    filas = [dict(r) for r in con.execute(q + " order by id desc limit 40", args)]
    con.close()
    return {
        "paso_dado": filas,
        "para_que": "Estos pasos corrieron solos sobre el corte. Miralos: si alguno cerro un borde de mas o quito algo que hacia falta, dilo — el paso no se quita, se supervisa.",
    }
