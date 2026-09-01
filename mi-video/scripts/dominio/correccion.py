"""Una corrección de Jaime, aplicada **sin rehacer la pieza**.

**Por qué existe, y es una frase suya.** El 1 de septiembre, viendo el primer
render del reel-01: *«las correcciones son puntuales, no es una recomposición,
no quiero volver a correr todo»*.

Hasta aquí una observación suya entraba como ticket —y ahí sigue, `ticket.py` no
cambia— pero para ejecutarla había que empujar la línea entera: la pieza volvía a
pasos que ya estaban decididos, cada paso encontraba algo nuevo que ajustar, y lo
que empezó siendo «quita ese "eso, eso" del segundo 8» acababa en otra vuelta
completa. Eso es exactamente el reproceso que él lleva el día entero pidiendo que
desaparezca.

## Y el arreglo tiene que llevarse el audio consigo

Es la parte que no es obvia y la que decide el diseño. Jaime limpia la voz a
mano y la devuelve; ese trabajo es suyo y es caro. Si una corrección recorta el
corte y deja el audio como estaba, `voz-limpia` se planta —con razón: *«el vídeo
dura 110,44 s y el audio 109,67 s, no se sustituye, desincronizaría la pieza
entera»*— y la única salida es pedirle que limpie otra vez.

Así que un recorte se aplica **a los dos a la vez y con los mismos segundos**.
La sincronía no se comprueba después: no se puede perder.

## Las clases

`Puntual` es la base y no hace nada por sí sola: sabe de qué ticket viene y
sabe cerrarlo diciendo qué se hizo. Las subclases son los tipos de corrección que
sí se pueden ejecutar; las que no —«el panel es figurativo», «el hook más
movido»— siguen siendo tickets abiertos, que es lo honesto: no existe la manera
de ejecutarlas sin criterio.
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import ticket as tk  # noqa: E402


class Puntual:
    """Una corrección con nombre, su ticket y su forma de cerrarse.

    No decide si hay que hacerla —eso ya lo decidió Jaime al abrir el ticket— y
    no la aplica: eso es de la subclase. Lo que aporta es que **ninguna se
    ejecute sin quedar contestada**, que es la mitad que se perdía cuando una
    corrección se hacía a mano.
    """

    tipo = "puntual"

    def __init__(self, pieza: str, ticket_id: int | None = None):
        self.pieza = pieza
        self.ticket = ticket_id

    def puede(self) -> tuple[bool, str]:
        """¿Se puede ejecutar sin criterio? Por defecto no."""
        return False, "esta correccion necesita criterio: se queda en el ticket"

    def aplicar(self) -> str:
        raise NotImplementedError

    def correr(self) -> str:
        """Aplica y **cierra el ticket diciendo qué se hizo**."""
        vale, porque = self.puede()
        if not vale:
            return porque
        hecho = self.aplicar()
        if self.ticket:
            tk.contestar(self.ticket, hecho, estado="arreglado",
                         quien="la linea")
        return hecho


class Recorte(Puntual):
    """Quita un texto de la pieza **y el mismo trozo del audio limpiado**.

    El corte se anota por `revision`, que es quien ya sabe hacerlo y —lo que
    importa— **sabe re-aplicarlo si la pieza se vuelve a montar**: el ancla es el
    texto, no el segundo, así que sobrevive a que el montaje cambie debajo. No se
    corta el EDL a mano; eso es justo lo que hace que una corrección se pierda.
    """

    tipo = "recorte"

    def __init__(self, pieza, ancla: str, por_que: str,
                 ticket_id=None, cual: int = 1):
        super().__init__(pieza, ticket_id)
        self.ancla, self.por_que, self.cual = ancla, por_que, cual

    def puede(self):
        if not (self.ancla or "").strip():
            return False, "un recorte sin texto que anclar no se puede aplicar"
        return True, ""

    def aplicar(self) -> str:
        import revision

        antes = _linea(self.pieza)
        revision.anotar(self.pieza, "cortar", None, None, self.ancla,
                        regla=self.por_que[:500], estado="pendiente",
                        pasada=3, ancla=self.ancla, cual=self.cual)
        puestos = revision.aplicar(self.pieza)
        if not puestos:
            return (f"«{self.ancla}» no se pudo anclar en el montaje de hoy:"
                    f" queda anotado, no aplicado")
        # **Y el mismo trozo sale del audio limpiado, en la misma operacion.**
        #
        # Si no, `voz-limpia` se planta —con razon— porque el video y el audio
        # dejan de durar lo mismo, y la unica salida es pedirle a Jaime que lo
        # limpie otra vez. Su limpieza es trabajo manual suyo: perderla por un
        # recorte de tres palabras es el peor cambio posible.
        fuera = _lo_que_falta(antes, _linea(self.pieza))
        voz = Voz(self.pieza)
        hecho = voz.quitar(fuera) if fuera and voz.fichero else None
        return (f"cortado «{self.ancla}» del corte"
                + (f" y del audio limpiado ({os.path.basename(hecho)})"
                   if hecho else ""))


class Voz:
    """El audio limpiado de una pieza, y cómo seguir al corte sin perderse.

    **Vive aquí y no en `voz-limpia` a propósito.** Aquel integra un audio que YA
    encaja; esto es lo otro: mantenerlo encajando cuando el corte cambia después
    de que Jaime lo haya limpiado. Son dos preguntas distintas y confundirlas es
    lo que obliga a limpiar dos veces.
    """

    #: Donde él lo deja. F: es la memoria de trabajo; G: sólo se mira al recoger.
    CARPETA = "out/audio-puro"

    def __init__(self, slug: str):
        self.slug = slug

    @property
    def fichero(self) -> str | None:
        """El limpiado más reciente, sea cual sea el sufijo que traiga."""
        base = f"{self.slug}-voz"
        if not os.path.isdir(self.CARPETA):
            return None
        cs = [os.path.join(self.CARPETA, f) for f in os.listdir(self.CARPETA)
              if f.startswith(base) and f.lower().endswith((".wav", ".flac"))]
        return max(cs, key=os.path.getmtime) if cs else None

    def dura(self) -> float | None:
        f = self.fichero
        if not f:
            return None
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", f],
                capture_output=True, text=True, check=True)
            return float(r.stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            return None

    def quitar(self, tramos) -> str | None:
        """Quita esos tramos del audio limpiado, **en su propia línea**.

        `tramos` son segundos de la PIEZA MONTADA, no de la cinta: es lo que se
        ve y lo que se oye, y es la única referencia común entre el corte y este
        fichero. Se escribe una versión nueva y se conserva la anterior — un
        audio que Jaime limpió a mano no se sobrescribe nunca.
        """
        f = self.fichero
        if not f or not tramos:
            return None
        dur = self.dura()
        if dur is None:
            return None
        # Lo que se QUEDA es el complemento de lo que se quita, en orden.
        quedan, t = [], 0.0
        for a, b in sorted(tramos):
            if a > t:
                quedan.append((t, a))
            t = max(t, b)
        if t < dur:
            quedan.append((t, dur))
        if not quedan:
            return None
        salida = f.rsplit(".", 1)[0] + "-recortado." + f.rsplit(".", 1)[1]
        trozos = "".join(
            f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}];"
            for i, (a, b) in enumerate(quedan))
        pega = "".join(f"[a{i}]" for i in range(len(quedan)))
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", f, "-filter_complex",
                 f"{trozos}{pega}concat=n={len(quedan)}:v=0:a=1[out]",
                 "-map", "[out]", salida],
                capture_output=True, check=True)
        except (OSError, subprocess.SubprocessError):
            return None
        return salida


def pendientes(slug: str) -> list:
    """Los tickets abiertos de la pieza, con lo que se puede ejecutar marcado.

    **No inventa el ancla.** Un ticket dice lo que Jaime oyó; convertirlo en un
    recorte exige saber qué texto exacto sobra, y eso es leer. Lo que hace esto
    es enseñar los dos montones separados —lo ejecutable y lo que necesita
    criterio— para que ninguno de los dos se dé por hecho mirando al otro.
    """
    return [{"id": t["id"], "segundo": t.get("segundo"), "beat": t.get("beat"),
             "dijo": t["dijo"], "tipo": t["tipo"]}
            for t in tk.abiertos(slug)]


def _linea(slug: str) -> list:
    """La linea de tiempo del montaje: `(desde, hasta, cinta)` por trozo.

    Son segundos de CINTA con su duracion; comparando la de antes con la de
    despues se sabe **que trozo desaparecio y donde caia en la pieza**, que es lo
    unico que hace falta para recortar el audio igual.
    """
    try:
        from .montaje import Montaje

        return [(t.desde, t.hasta, t.cinta) for t, _ in Montaje(slug).tramos()]
    except Exception:                              # noqa: BLE001
        return []


def _lo_que_falta(antes: list, despues: list) -> list:
    """Donde caia, en la PIEZA, lo que ya no esta. `[(desde, hasta), ...]`.

    Se recorre la linea vieja llevando la cuenta del tiempo de pieza; cada trozo
    que no sobrevive marca su hueco. No se comparan segundos absolutos porque el
    corte los desplaza: se compara **quien sigue estando**.
    """
    vivos, fuera, t = set(despues), [], 0.0
    for tr in antes:
        dur = tr[1] - tr[0]
        if tr not in vivos:
            fuera.append((round(t, 3), round(t + dur, 3)))
        t += dur
    # Se funden los huecos pegados: dos trozos seguidos que se van son un hueco.
    junto = []
    for a, b in fuera:
        if junto and a - junto[-1][1] < 0.01:
            junto[-1] = (junto[-1][0], b)
        else:
            junto.append((a, b))
    return junto
