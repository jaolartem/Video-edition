"""Las consultas que necesitan los pasos de IA, **por nombre y desde la consola**.

El paso de IA vive en JavaScript porque ahí está el `fetch`, pero la base es de
Python en todo el resto del proyecto. En vez de abrir la base desde los dos
lados —dos formas de escribir la misma tabla es de donde salen los fallos de este
proyecto— el lado JS pide por nombre y aquí está la única puerta.

    python scripts/consulta.py escenas_por_describir '[[], false]'
    python scripts/consulta.py guardar_escena @work/escena.json

**Y esto es la puerta, no la implementación.** Cada verbo de aquí está escrito en
los prompts de los contratos: su nombre y su salida son un compromiso. Lo que
contesta cada uno vive en `dominio/`, donde el sustantivo que sabe la respuesta
es su dueño — `Montaje` sabe de sus tramos, `Guion` de sus pausas, `Escena` de
quién manda sobre cada campo de una descripción. Aquí queda el nombre que el CLI
llama y la traducción a ese objeto, que es exactamente lo que hace
`transcribir.exigir` con `dominio.Cinta`.

Leer y escribir son dos oficios y compartían fichero: diez consultas para los
agentes conviviendo con las dos escrituras que aceptan lo que los agentes
contestan. Siguen entrando por la misma puerta —el CLI es uno— y ya no comparten
código.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dominio import onda as _onda  # noqa: E402
from dominio.cruce import cruces as _cruces  # noqa: E402
from dominio.encargo import por_describir as _por_describir  # noqa: E402
from dominio.escena import Escena, EscenaInvalida  # noqa: E402
from dominio.guion import Guion  # noqa: E402
from dominio.material import abanico as _abanico  # noqa: E402
from dominio.material import brolls as _brolls  # noqa: E402
from dominio.montaje import Montaje  # noqa: E402
from dominio.precio import evento as _evento  # noqa: E402
from dominio.precio import vigente as _vigente  # noqa: E402
from dominio.repetido import repetido as _repetido  # noqa: E402


def _montado(slug):
    """El montaje de esa pieza, o `None` si todavía no hay corte que mirar."""
    m = Montaje(slug)
    return m if m.existe else None


# ── lo que se pregunta ──────────────────────────────────────────────────────
def escenas_por_describir(reels=None, rehacer=False):
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    return _por_describir(reels, rehacer)


def cc_afinado(slug):
    """Cuánto del montaje de esta pieza pasó por el barrido de cuatro pasadas."""
    m = _montado(slug)
    return m.afinado() if m else {}


def bordes_sucios(slug):
    """Los bordes que hay que mirar, por etapa. El detector apunta; no decide."""
    m = _montado(slug)
    return m.bordes_sucios() if m else {}


def cruces(slug):
    """Lo que se repite a los dos lados de una costura, sin cortarlo.

        python scripts/consulta.py cruces '["reel-01"]'
    """
    m = _montado(slug)
    return _cruces(m) if m else []


def onda(slug):
    """La curva emocional de la pieza, etapa por etapa. No decide: dibuja.

        python scripts/consulta.py onda '["reel-01"]'
    """
    m = _montado(slug)
    return _onda.curva(m) if m else []


def repetido(slug, n=3):
    """Lo que la pieza dice **dos veces**, con la entrega de cada una al lado."""
    m = _montado(slug)
    return _repetido(m, n) if m else []


def abanico(frase, cintas=None, tope=12):
    """Dónde está dicha esa frase **en todo el material**, y cómo de bien.

        python scripts/consulta.py abanico '["el 21 de septiembre"]'
    """
    return _abanico(frase, cintas, tope)


def brolls(minimo=2.0, maximo=8.0, cintas=None):
    """Los tramos donde él está en cuadro y no habla. Material de transición."""
    return _brolls(minimo, maximo, cintas)


def pausas(slug):
    """Las etapas cuyo silencio **no se recorta**, y de qué lado.

        {etapa: {"donde": "entrada" | "salida" | "ambas", "motivo": …}}
    """
    return Guion(slug).pausas()


def voz(toma):
    """Donde de verdad SUENA la voz de una cinta, sin la holgura del detector.

    `work/cuts/<toma>.json` no lleva tramos de habla: lleva los tramos que
    sobreviven **con la pausa recortada dentro** —`cut-silence.build_segments`
    conserva `PAUSA/2 + MARGEN` de silencio pegado a cada extremo—. Quien los
    lea como «aquí suena» reintroduce esos 0,285 s por lado en el montaje.

    Medido en reel-01 el 7-9-2026: trece silencios de 0,55 a 0,77 s dentro de la
    pieza entregada, once segundos de aire, y Jaime oyéndolos uno a uno
    —*«los demás sí están raros»*—. `Cinta.voz()` ya era la respuesta y sólo la
    sabía Python; `plan-reel.mjs` leía el fichero por su cuenta.

        python scripts/consulta.py voz '["20260825_135637"]'
    """
    from dominio.cinta import Cinta

    return [[a, b] for a, b in Cinta(toma).voz()]


def fijos(slug):
    """Los tramos que alguien DECLARO para esta pieza, en tiempo de cinta.

    **Un tramo declarado no se vuelve a partir.** `conHabla` recorta el silencio
    interno de cada segmento y devuelve trozos; cada trozo acaba siendo una
    escena, o sea un CORTE DE PLANO. Eso esta bien cuando el segmento lo eligio
    el automatismo, y esta mal cuando alguien dijo «esta frase va entera»: la
    declaracion existia justo para quitar ese corte, y el recorte la deshacia.

    Paso tres veces con el mismo sitio de reel-01. La tercera, el tramo se
    declaro entero —562,932-571,050— y el plan salio con dos escenas, 562,852-
    568,490 y 568,857-571,050: un cambio de plano entre «550 dolares» y
    «semanales». Jaime, otra vez: *«al final queda un semanales huerfano»*.
    """
    import basedatos
    cx = basedatos.abrir()
    v = cx.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        return []
    return [[a, b] for a, b in cx.execute(
        "select desde, hasta from corte_fijo where video_id = ?"
        " and desde is not null and hasta is not null", (v[0],))]


def precio_vigente(fecha=None):
    """El escalón de hoy y cómo se rotula. `None` si ya cerró todo."""
    return _vigente(fecha)


def evento(fecha=None):
    """Cuándo es el evento, derivado del último escalón de la escalera."""
    return _evento(fecha)


# ── lo que se escribe ───────────────────────────────────────────────────────
#
# **Un error de contenido tiene que salir por la consola como error.** El dominio
# lo dice con su propia excepción —`EscenaInvalida`, que es lo correcto para
# quien lo llama desde Python—; el CLI necesita además código de salida y
# mensaje, que es `SystemExit`. La traducción vive aquí, en el borde, y no dentro
# del objeto: un dominio que lanza `SystemExit` mata al que lo importa.
def montada_en_fotogramas(slug):
    """Como quedo cada escena YA MONTADA: cinco fotogramas por escena.

    El «despues» del par que pidio Jaime — *«los del video base y las 3 o 5 que
    genera por escena, en un antes y un despues»*. Los de la cinta dicen que se
    grabo; estos dicen que salio.

    Con uno solo se juzga a ciegas la mitad del trabajo: si esta leyendo se ve
    en el bruto, pero si el corte se comio la frase o el tablero le tapa la cara
    eso solo se ve en el montaje.

    Si la pieza todavia no esta montada devuelve la lista vacia — no hay
    despues, y no se inventa.
    """
    import fotogramas

    n = int(str(slug)[-2:])
    hechas, _ = fotogramas.sacar(n)
    return hechas or []


def proponer(slug, etapa, quien, texto):
    """Lo que un paso ve mal **fuera de lo que le toca**: sube, no se aplica.

    Jaime, 7-9-2026, afinando el reparto: *«que puedan ver el resto, aunque no
    editar»*, y acto seguido *«ver y proponer cambios, no generarlos»*.

    Las tres cosas son distintas y esta es la del medio. Al que compone se le da
    la pieza entera porque la coherencia no cabe en una escena suelta; lo que ve
    fuera de su encargo **no se tira** —seria desperdiciar el unico par de ojos
    que estaba mirando— pero tampoco entra sola en una etapa aprobada. Queda
    escrita con `estado='sube'`, que es el estado que este proyecto ya usa para
    «esto lo decide el».

    Y con su etapa, que es lo que Jaime pidio en la misma frase: *«cada tiquet va
    ligado a la escena»*. Sin etapa nadie puede acotar quien la atiende.
    """
    import basedatos

    con = basedatos.abrir()
    con.execute(
        "insert into revision (video_slug, accion, que, estado, fecha, etapa,"
        " quien, pasada, cual) values (?,?,?,'sube',?,?,?,1,1)",
        (slug, "otro", f"PROPUESTA de «{quien}», fuera de lo que le tocaba"
                       f" editar (e{etapa}): {texto}"[:1200],
         __import__("datetime").datetime.now().isoformat(timespec="seconds"),
         int(etapa), quien))
    con.commit()
    return "ok"


def tiquets_de(slug, fase):
    """Lo que Jaime dijo, tal cual, para que viaje DENTRO del pedido.

    `acotado` ya decia que etapas mirar; esto dice **por que**. Sin las dos, el
    pedido llega recortado y mudo: el que contesta ve una escena suelta y no
    sabe que se le pide de ella, asi que reconstruye el contexto por su cuenta
    —leyendo la base, el CLAUDE.md y los documentos— antes de escribir una
    linea. Jaime, con el reloj: *«6 minutos es demasiado para 8 segundos»*.

    El pedido esta hecho para contestarse sin reconstruir nada; esto es lo que
    faltaba para que sea verdad.
    """
    from dominio.alcance import Alcance

    return Alcance.de(slug, fase).tiquets


def acotado(slug, fase):
    """Las etapas que los tiquets abiertos de esa fase acotan, o `null`.

    `null` significa «la pieza entera», que es el modo normal —componer de cero—
    y tambien lo que pasa cuando una correccion suya no nombra etapa. Una lista
    significa: **solo estas**, y el resto ya esta aprobado.

    Existe porque `describir.mjs` pedia las siete escenas de reel-03 para
    arreglar ocho segundos de gancho. La medida ya estaba escrita en
    `dominio/abierto.py :: alcance`; lo que faltaba era que node pudiera
    preguntarla, que es lo unico que hace esta puerta.
    """
    from dominio.alcance import Alcance

    return Alcance.de(slug, fase).editables


def modo(slug, fase):
    """La segunda capa del contrato: el encargo de hoy. `""` si no hay tiquets.

    Jaime: *«hay dos modos para cada agente; el contrato tiene dos capas, una
    con las capacidades y otra con la instruccion»*. El prompt del paso son las
    capacidades y no cambia; esto dice que hoy **no se compone la pieza, se
    arreglan estos tiquets**.

    `servicios/disenar.py` la pone con `abierto.modo` antes de preguntar. El
    otro oficio vive en node y no tenia por donde pedirla, asi que recibia los
    tiquets como dato y ninguna frase que dijera que el encargo era ese. Esta
    puerta solo la deja cruzar; el texto es el de `dominio/abierto.py :: MODO` y
    se manda literal.
    """
    from dominio.alcance import Alcance

    return Alcance.de(slug, fase).instruccion


def cerrar_tiquets(slug, fase, por_que, atendidos):
    """Cierra los tiquets que una respuesta declara haber atendido.

    La regla —sólo los declarados, y por qué— vive en `dominio/abierto.py ::
    cerrar`, que es la que ya usa el paso de diseño. Esto es la puerta para que
    el paso que vive en node pueda llamarla, no una segunda versión.
    """
    from dominio import abierto

    return abierto.cerrar(slug, fase, por_que, atendidos)


def guardar_escena(slug, orden, d):
    """Guarda la descripción de una etapa, con el texto que describe."""
    try:
        return Escena(slug, orden).guardar(d)
    except EscenaInvalida as e:
        raise SystemExit(str(e)) from e


def guardar_tablero(slug, orden, tablero):
    """Guarda SOLO el tablero de una etapa. Es la entrega del paso de diseño."""
    try:
        return Escena(slug, orden).poner_tablero(tablero)
    except EscenaInvalida as e:
        raise SystemExit(str(e)) from e


def repeticion(toma, primera, segunda):
    """Cuanto sube la segunda entrega de una frase respecto a la primera.

    Un microscopio: se pide para UNA repeticion concreta, no barre la pieza.
    Devuelve dB, semitonos y duraciones — **no un veredicto**: la vara es
    editorial y la pone quien compone.

        python scripts/consulta.py repeticion
            '["20260825_135637", [93.30, 95.09], [95.09, 95.92]]'
    """
    from dominio.repeticion import medir

    return medir(toma, tuple(primera), tuple(segunda))


VERBOS = {"escenas_por_describir": escenas_por_describir,
          "repeticion": repeticion,
          "cc_afinado": cc_afinado,
          "bordes_sucios": bordes_sucios,
          "cruces": cruces,
          "onda": onda,
          "repetido": repetido,
          "abanico": abanico,
          "brolls": brolls,
          "pausas": pausas,
          "voz": voz,
          "fijos": fijos,
          "precio_vigente": precio_vigente,
          "evento": evento,
          "montada_en_fotogramas": montada_en_fotogramas,
          "proponer": proponer,
          "tiquets_de": tiquets_de,
          "acotado": acotado,
          "modo": modo,
          "cerrar_tiquets": cerrar_tiquets,
          "guardar_escena": guardar_escena,
          "guardar_tablero": guardar_tablero}


def _argumentos(argv):
    """Los argumentos del verbo. **`@fichero` en vez del JSON en la línea.**

    El argumento viaja por la consola, y la consola de Windows es cp1252 mientras
    que todo lo que se guarda aquí lleva tildes y comillas angulares. Pasar una
    descripción de escena como argumento es meter «qué pasa» por un canal que no
    sabe escribir la «é»: se rompe, o peor, entra mutilada.

    Coste medido: seis agentes de composición gastaron su turno entero peleando
    con el escapado —88 mensajes uno de ellos— y no escribieron ni una
    descripción. No era torpeza suya: era que el único camino que les di pasaba
    por ahí. Con `@`, el JSON viaja en un fichero UTF-8 y la línea lleva sólo
    ASCII — el mismo acuerdo que ya usa `work/servicio/` para los pasos de IA.
    """
    if len(argv) <= 2:
        return []
    if argv[2].startswith("@"):
        return json.load(io.open(argv[2][1:], encoding="utf-8"))
    return json.loads(argv[2])


if __name__ == "__main__":
    # **La consola escribe UTF-8, lo diga Windows o no.**
    #
    # La entrada ya estaba resuelta —`@fichero`, ahí arriba— y la salida no. En
    # Windows el `stdout` de Python es el de la consola, cp1252 aquí, así que el
    # «·» del precio salía como un solo byte 0xB7; node lo lee como UTF-8, ese
    # byte suelto no es UTF-8 válido y llegaba convertido en «�». Se veía en la
    # tarjeta de cierre de las siete piezas.
    #
    # Quien llama no puede arreglarlo: para cuando el texto sale del proceso ya
    # está roto. Por eso va aquí y no en cada `execFileSync` con su
    # `PYTHONIOENCODING` — la decisión «este CLI habla UTF-8» es de este CLI.
    #
    # Y va dentro del `__main__`, no arriba con los imports, porque `consulta`
    # lo importan siete scripts: un módulo que reconfigura el `stdout` de quien
    # lo importa decide por él. Esto es el borde de la consola; el borde es suyo.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    print(json.dumps(VERBOS[sys.argv[1]](*_argumentos(sys.argv)),
                     ensure_ascii=False))
