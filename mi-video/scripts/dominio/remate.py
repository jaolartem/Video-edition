"""El remate: cómo suena la voz en el punchline de un beat, **y sólo ahí**.

Jaime: *«que cambie mi voz en los punchlines»*. Es un recurso expresivo pedido
por él, sobre el remate de un beat, y hasta hoy no había por dónde declararlo:
la voz salía igual de principio a fin en las siete piezas.

## No contradice la regla de la mezcla, y hay que decirlo entero

La regla que parece prohibir esto es de la MÚSICA: *«bájale a las frecuencias
que compiten con mi voz, eso es bien importante (no agregues efectos o máscaras
al sonido, solo baja el volumen a esas frecuencias y ya)»*. Habla de la cama y
de las bandas donde estorba, y sigue vigente en `musica.sh` tal cual.

Y hay una segunda historia, ésa sí sobre la voz, que es mía: le puse una cadena
de corrección —highpass 85, campana de −3 dB a 250 Hz, presencia a 3200 y
de-esser— para contestar a *«no se mejoró la calidad»*, cuando lo que había
pedido era *«dejar el sonido de la voz un poco más natural»*. El corte de 250 Hz
es justo lo que le quita el cuerpo, y el veredicto fue inmediato: *«se perdieron
factores y suena muy feo»*. Por eso `musica.sh` dice, y sigue diciendo, que **a
la voz no se le hace nada**.

Lo de aquí es lo contrario de aquello por las tres cosas que lo hacían malo:

1. **Aquello iba sobre la pista entera; esto va sobre un tramo declarado.** Un
   remate dura 1,2 s de una pieza de noventa.
2. **Aquello no lo pidió nadie; esto lo pidió él con esas palabras.**
3. **Aquello era corrección disfrazada de mejora; esto es un recurso**, y se
   nota que es deliberado — que es la mitad del efecto.

Y una condición que sale de la misma historia: **ninguno de los dos tratos
adelgaza la voz**. `cerca` le SUMA cuerpo, que es exactamente lo que aquel corte
de 250 Hz le quitaba.

## Cómo queda acotado, y por qué es reversible por construcción

Cada filtro sale con `enable='between(t,a,b)'` —edición por línea de tiempo de
ffmpeg—: fuera de la ventana el filtro está en derivación y las muestras pasan
sin tocar. Y si una pieza no declara ningún remate, esto devuelve `anull` y la
cadena de audio queda **idéntica** a la de ayer. Quitar la declaración devuelve
la voz intacta sin que nadie tenga que deshacer nada.

Comprobado sobre reel-03, restando la entrega tratada de la sin tratar:

    antes de la primera ventana   -91 dB   <- silencio digital: el MISMO fichero
    dentro de la ventana          -25 dB   <- el tratamiento
    entre las dos ventanas        -52 dB   <- `loudnorm` readaptandose

Ese −52 dB del medio **no es el tratamiento escapándose**: es que `loudnorm` va
de una sola pasada y su ganancia depende de lo que ha oído, así que un cambio
en el segundo 23 le mueve unas centésimas de dB el resto. Está 27 dB por debajo
del propio tratamiento y 38 por debajo del programa. Se deja dicho porque medir
esto y callarlo es como no medirlo.

Y la vuelta atrás se comprobó por huella, que es lo único que no opina: entrega
sin declarar y entrega después de retirar la declaración dan el **mismo
SHA-256** del audio.

    python scripts/dominio/remate.py 1              # qué lleva la pieza 1
    python scripts/dominio/remate.py 1 --filtro     # la cadena, para `musica.sh`
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import sys

# **Tres `dirname`, no dos.** Este fichero vive en `scripts/dominio/`, así que
# subir dos veces deja `RAIZ` en `scripts/` y `src/reels.json` pasa a buscarse
# en `scripts/src/reels.json` — que no existe, y las ventanas salen vacías sin
# que nada falle. Es C-146 otra vez, y aquí costaría el tratamiento entero:
# ninguna etapa tendría cuándo suena y todas se rechazarían en silencio.
SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"

#: Lo que dura un remate por defecto. Un punchline es la frase de cierre, no el
#: beat: en el corpus medido, los remates de una etapa van de 0,9 a 1,6 s.
DURA = 1.2

#: Y los extremos. Por debajo de `MINIMO` el trato no llega a oírse —la campana
#: de un `equalizer` necesita unas decenas de ms para asentarse— y por encima de
#: `TOPE` deja de ser un remate: es la etapa entera con otra voz, que es lo que
#: esto NO es.
MINIMO = 0.3
TOPE = 2.5

#: Dónde cae la ventana dentro de la etapa. Dos, y no tres: «la etapa entera» no
#: se ofrece a propósito — un tratamiento que dura ocho segundos ya no marca un
#: remate, cambia el narrador.
ANCLAS = {
    "remate": "los últimos segundos de la etapa: el punchline",
    "entrada": "los primeros segundos de la etapa: la frase que abre",
}


@dataclasses.dataclass(frozen=True)
class Trato:
    """Un sabor de voz: qué se oye, cuándo se pide y con qué se hace.

    `cadena` son filtros de ffmpeg **con edición por línea de tiempo** (la `T`
    de `ffmpeg -filters`). Es la condición que los hace acotables, y por eso no
    hay aquí ningún compresor: `acompressor` no la tiene, así que no se puede
    encender sólo en un tramo — se aplicaría a la pieza entera sin decirlo.
    """

    que: str
    cuando: str
    cadena: tuple[str, ...]


#: Los dos sabores. **Sobrios y de la casa**: el canon es neoconstructivista, y
#: el equivalente sonoro del constructivismo no es un juguete de radio — es el
#: altavoz de plaza de Rodchenko, que proclama. Los dos se hacen con ecualización
#: y ganancia, sin reverberación, sin cambio de tono y sin resíntesis: nada que
#: reconstruya la señal, que es de donde salió *«suena muy feo»* la primera vez.
#:
#: Medido sobre su voz en el remate de reel-03, por bandas, `megafono` contra la
#: cruda: **−7,1 dB por debajo de 250 Hz y +5,9 dB entre 1,4 y 2 kHz**, con el
#: cuerpo de 250-500 Hz intacto (+0,4). O sea le quita el pecho y le abre la
#: consonante, que es lo que hace un altavoz — y no es la cadena que le quitaba
#: el cuerpo, porque aquella cortaba justo en 250 y ésta empieza en 420 y se
#: enciende segundo y pico.
TRATOS = {
    "megafono": Trato(
        que="la frase sale por un altavoz de plaza: se le quita el grave y el"
            " aire, se le abre la zona de la consonante y sube un punto. Deja de"
            " ser conversación y pasa a ser proclama",
        cuando="el remate AFIRMA algo y quieres que suene dicho a la calle."
               " Es el más audible de los dos: uno por pieza y ya está usado",
        cadena=("highpass=f=420:poles=2",
                "lowpass=f=2800:poles=2",
                "equalizer=f=1700:t=o:w=1.1:g=6",
                "volume=2.5dB"),
    ),
    "cerca": Trato(
        que="se acerca al micrófono y baja la voz: más cuerpo, menos aire y un"
            " punto menos de nivel. Suena confidencial, como si lo dijera para"
            " el que está mirando",
        cuando="el remate es una confesión, una advertencia o el dato que"
               " incomoda. Es el discreto: se nota sin que se vea el truco",
        cadena=("bass=g=3.5:f=140:t=q:w=0.7",
                "treble=g=-3.5:f=6000:t=q:w=0.7",
                "volume=-1.5dB"),
    ),
}


#: Lo que todavía no se puede, dicho como lo que es. Misma regla que
#: `camara.POR_CONSTRUIR`: se puede pedir, cuesta código, y **nunca se ofrece
#: como si ya estuviera**.
POR_CONSTRUIR = {
    "anclado_a_la_palabra": {
        "que": "que la ventana empiece en una PALABRA del subtítulo —«desde"
               " ‹la mitad›»— en vez de en los últimos N segundos de la etapa",
        "cuesta": "la ventana se deriva de `src/reels.json`, que sabe dónde"
                  " empieza y acaba cada beat pero no dónde cae cada palabra"
                  " dentro de la pieza montada. Haría falta llevar los tiempos"
                  " por palabra del transcript hasta el reloj del montaje",
    },
    "solo_la_voz": {
        "que": "tratar la voz sin tocar el efecto de sonido que caiga en la"
               " misma ventana",
        "cuesta": "en `musica.sh` la entrada `[0:a]` es el audio del render, y"
                  " ahí la voz y los efectos ya vienen sumados. Las dos pistas"
                  " existen por separado antes (`efectos.mjs` deja los efectos"
                  " solos), así que se abre el día que la mezcla se arme desde"
                  " los dos ficheros en vez de desde el render",
    },
}


def _fps() -> int:
    """Los frames por segundo, **leídos de quien pone el reloj**.

    De `scripts/reels/reloj.mjs`, que es donde `FPS` está declarado. Escribirlo
    aquí sería la segunda copia de siempre, y esta ventana se compone contra
    frames: un fps distinto no falla, desplaza el tratamiento.
    """
    try:
        t = open(os.path.join(RAIZ, "scripts", "reels", "reloj.mjs"),
                 encoding="utf-8").read()
    except OSError:
        return 30
    m = re.search(r"export const FPS = (\d+)", t)
    return int(m.group(1)) if m else 30


def ventanas(slug: str) -> dict:
    """Dónde suena cada etapa en la pieza ENTREGADA: `{beat: (desde, hasta)}`.

    Sale de `src/reels.json` —lo que el render dibujó— y no del EDL. Es la misma
    fuente que `caja.ya_en_pantalla`, y por el mismo motivo: el EDL lleva el aire
    que `plan-reel` quita, así que sus segundos no son los de la pieza. En
    reel-01 la diferencia crece hasta 6,8 s, y una ventana colocada con el EDL
    trataría la frase de al lado.
    """
    try:
        n = int(str(slug).split("-")[1])
        piezas = json.load(open(os.path.join(RAIZ, "src", "reels.json"),
                                encoding="utf-8"))
    except (OSError, ValueError, IndexError):
        return {}
    pieza = next((x for x in piezas if x.get("id") == f"Reel-R{n}"), None)
    if not pieza:
        return {}
    fps, arranca = _fps(), {}
    # De donde sale el arranque de cada beat: las capas que dicen a que beat
    # pertenecen. `caminos` no basta —en reel-03 el beat 2 no tiene ninguna y
    # vive entero en un tablero— y con `boards` y `tarjetas` quedan los tres
    # sitios donde una capa declara su beat. `paneles` no dice de cual es.
    def _anota(x, b):
        if b is None:
            return
        a = float(x.get("at") or 0)
        arranca[int(b)] = min(arranca.get(int(b), a), a)

    for c in pieza.get("caminos") or []:
        _anota(c, c.get("beat"))
    for b_ in pieza.get("boards") or []:
        _anota(b_, b_.get("beat"))
    for t_ in pieza.get("tarjetas") or []:
        _anota(t_, ((t_.get("props") or {}).get("beat") or [None])[0])
    if not arranca:
        return {}
    # **El beat acaba donde empieza el siguiente, no donde acaba su ultima capa.**
    #
    # Las capas se salen a proposito: el remate del gancho cruza la costura y el
    # tablero se estira por encima de la frontera para taparla. Tomando el maximo
    # de las capas, el beat 1 de reel-01 «acababa» en el frame 150 cuando el 2 ya
    # habia empezado en el 127 — y un remate colocado ahi trata la frase de al
    # lado. Los beats se suceden sin hueco, asi que el arranque del siguiente es
    # el unico borde que no depende de que capa se declaro.
    orden = sorted(arranca.items(), key=lambda kv: kv[1])
    fin = float(pieza.get("duracion") or 0) * fps
    fuera = {}
    for i, (b, a) in enumerate(orden):
        z = orden[i + 1][1] if i + 1 < len(orden) else fin
        if z > a:
            fuera[b] = (round(a / fps, 3), round(z / fps, 3))
    return fuera


@dataclasses.dataclass(frozen=True)
class Remate:
    """El tratamiento declarado sobre el tramo de una etapa. Se valida solo."""

    beat: int
    trato: str
    sobre: str = "remate"
    dura: float = DURA

    @classmethod
    def de_declaracion(cls, beat, crudo):
        """Lo que el diseñador dejó en `escena_desc.voz`. `None` si no dejó nada."""
        if not crudo:
            return None
        try:
            d = json.loads(crudo) if isinstance(crudo, str) else crudo
        except (TypeError, ValueError):
            return None
        if not isinstance(d, dict) or not d.get("trato"):
            return None
        try:
            dura = float(d.get("dura") or DURA)
        except (TypeError, ValueError):
            dura = DURA
        return cls(int(beat), str(d["trato"]).strip().lower(),
                   str(d.get("sobre") or "remate").strip().lower(), dura)

    def falta(self) -> str:
        """Por qué NO se puede aplicar, o cadena vacía si se puede.

        Se contesta antes de tocar la pista: un trato que no existe o una
        ventana que no cabe **se dice y no se aplica**, en vez de salir montado
        como otra cosa. Es la avería que `figuras_que_se_trazan` cerró por el
        lado visual — descrito con tus palabras no se dibuja, y no avisaba.
        """
        if self.trato not in TRATOS:
            return (f"«{self.trato}» no es un trato de voz;"
                    f" hay {', '.join(sorted(TRATOS))}")
        if self.sobre not in ANCLAS:
            return (f"«{self.sobre}» no es un ancla;"
                    f" hay {', '.join(sorted(ANCLAS))}")
        if not MINIMO <= self.dura <= TOPE:
            return (f"{self.dura:.2f}s se sale de [{MINIMO}, {TOPE}]:"
                    f" por debajo no se oye y por encima no es un remate")
        return ""

    def ventana(self, tramo) -> tuple:
        """Los segundos de la pieza que se tratan, recortados dentro del beat.

        `tramo` es `(desde, hasta)` de la etapa. La ventana **nunca sale de
        ahí**: es lo que hace que esto sea un tratamiento de tramo y no de
        pista, y por eso el recorte se hace aquí y no en quien llama.
        """
        a, z = float(tramo[0]), float(tramo[1])
        dura = min(self.dura, max(0.0, z - a))
        if dura < MINIMO:
            return ()
        if self.sobre == "entrada":
            return (round(a, 3), round(a + dura, 3))
        return (round(z - dura, 3), round(z, 3))

    def filtro(self, ventana) -> str:
        """La cadena de ffmpeg, encendida sólo entre esos dos segundos."""
        a, z = ventana
        puerta = f":enable='between(t,{a:.3f},{z:.3f})'"
        return ",".join(f + puerta for f in TRATOS[self.trato].cadena)


def declarados(slug: str) -> list:
    """Los remates de esa pieza, leídos de `escena_desc.voz` y de ningún otro sitio."""
    import sqlite3

    con = basedatos.abrir(BASE)
    try:
        filas = con.execute(
            "select etapa_orden, voz from escena_desc"
            " where video_slug = ? and voz is not null and voz <> ''"
            " order by etapa_orden", (str(slug),)).fetchall()
    except sqlite3.OperationalError:
        # Base sin migrar: no hay columna, luego no hay nada declarado. El paso
        # de audio NO se puede caer por esto — la pieza saldria sin nivelar, que
        # es mucho peor que salir sin un tratamiento que nadie pidio.
        return []
    fuera = []
    for beat, crudo in filas:
        r = Remate.de_declaracion(beat, crudo)
        if r is not None:
            fuera.append(r)
    return fuera


def resueltos(slug: str, velocidad: float = 1.0):
    """`[(Remate, ventana)]` y las faltas, ya colocados sobre la pieza entregada.

    `velocidad` es la de la entrega: si la pieza se aceleró, sus segundos ya no
    son los del montaje y la ventana hay que dividirla. Hoy vale 1 —Jaime revocó
    el 1,15x— pero el número viaja desde `musica.sh`, que es quien sabe qué
    fichero está mezclando; suponerlo aquí sería la segunda copia de una
    decisión que ya tiene dueño.
    """
    tramos, buenos, faltas = ventanas(slug), [], []
    for r in declarados(slug):
        mal = r.falta()
        if mal:
            faltas.append(f"e{r.beat}: {mal}")
            continue
        tramo = tramos.get(r.beat)
        if not tramo:
            faltas.append(f"e{r.beat}: esa etapa no aparece en `src/reels.json`,"
                          f" así que no se sabe cuándo suena")
            continue
        v = r.ventana(tramo)
        if not v:
            faltas.append(f"e{r.beat}: la etapa dura menos de {MINIMO}s")
            continue
        if velocidad and velocidad != 1.0:
            v = (round(v[0] / velocidad, 3), round(v[1] / velocidad, 3))
        buenos.append((r, v))
    return buenos, faltas


def cadena(slug: str, velocidad: float = 1.0) -> str:
    """Lo que `musica.sh` mete en `[0:a]`. `anull` si no hay nada declarado.

    **`anull` y no cadena vacía**: el filtro va dentro de un `filter_complex` con
    etiquetas, y un eslabón vacío deja `[0:a],loudnorm=…`, que ffmpeg rechaza.
    Es además la prueba de la reversibilidad: sin declaración, la cadena de audio
    es exactamente la de antes de que esto existiera.
    """
    buenos, _ = resueltos(slug, velocidad)
    return ",".join(r.filtro(v) for r, v in buenos) or "anull"


def menu() -> dict:
    """Lo que el diseñador ve en su pedido. Se arma de los mismos datos que se aplican."""
    return {
        "que_es": "El tratamiento de la voz de Jaime en el REMATE de una etapa."
                  " Jaime: «que cambie mi voz en los punchlines».",
        "como_se_pide": "Un objeto `voz` en esa etapa:"
                        " `{\"trato\": \"megafono\", \"sobre\": \"remate\","
                        " \"dura\": 1.2}`. `sobre` y `dura` son opcionales"
                        " (remate, 1,2 s). Para quitarlo, `\"voz\": null`.",
        "tratos": {k: {"suena": v.que, "cuando": v.cuando}
                   for k, v in TRATOS.items()},
        "sobre": ANCLAS,
        "ojo_con_la_ultima": "La última etapa llega hasta el final de la pieza,"
                             " tarjeta de cierre incluida, así que su remate"
                             " puede caer sobre la tarjeta —donde no habla"
                             " nadie— y entonces no se oye nada. Mira"
                             " `en_la_pista` de esa etapa antes de pedirlo ahí.",
        "dura": f"segundos, entre {MINIMO} y {TOPE}. Se recorta dentro de la"
                f" etapa: nunca sale de ella.",
        "la_tasa": "Uno o dos por pieza, como las marcas de humanidad y por el"
                   " mismo motivo: un recurso que aparece en todas las etapas"
                   " deja de ser un remate y pasa a ser el sonido de la pieza."
                   " Con 16-50 anuncios se gasta en el tercero.",
        "lo_que_NO_es": "No es limpiar la voz ni corregirla. A la voz no se le"
                        " hace nada en la mezcla —le costó a Jaime un «se"
                        " perdieron factores y suena muy feo»— y esto no lo"
                        " cambia: fuera de la ventana declarada la pista sale"
                        " sin tocar, y sin declaración sale idéntica.",
        "por_construir": {k: v["que"] for k, v in POR_CONSTRUIR.items()},
        "si_pides_algo_por_construir": "Pídelo en `por_construir: [\"…\"]` al"
                                       " primer nivel de la respuesta: abre su"
                                       " tiquet y queda agendado (C-697). Lo que"
                                       " no vale es componer suponiendo que ya"
                                       " está.",
    }


def main():
    if len(sys.argv) < 2:
        for k, v in TRATOS.items():
            print(f"{k:<10} {v.que}")
        return
    slug = sys.argv[1]
    if slug.isdigit():
        slug = f"reel-{int(slug):02d}"
    vel = 1.0
    if "--velocidad" in sys.argv:
        try:
            vel = float(sys.argv[sys.argv.index("--velocidad") + 1])
        except (IndexError, ValueError):
            vel = 1.0
    if "--filtro" in sys.argv:
        # Lo aplicado y lo rechazado van por `stderr` **y por eso se ven**:
        # `musica.sh` sólo captura `stdout`, así que la cadena entra en el
        # filtro y el parte sale por pantalla. Un tratamiento que se aplica sin
        # decirlo es la etiqueta contra el artefacto otra vez.
        buenos, faltas = resueltos(slug, vel)
        for r, v in buenos:
            print(f"    voz: e{r.beat} {r.trato} en el {r.sobre},"
                  f" {v[0]:.2f}-{v[1]:.2f}s", file=sys.stderr)
        for f in faltas:
            print(f"    voz NO aplicada — {f}", file=sys.stderr)
        print(cadena(slug, vel))
        return
    buenos, faltas = resueltos(slug, vel)
    for r, v in buenos:
        print(f"e{r.beat}  {r.trato:<10} {r.sobre:<8}"
              f" {v[0]:.2f}-{v[1]:.2f}s  ({v[1] - v[0]:.2f}s)")
    for f in faltas:
        print(f"NO se aplica — {f}")
    if not buenos and not faltas:
        print(f"{slug}: sin tratamiento de voz declarado")


if __name__ == "__main__":
    main()
