"""Las palabras del subtítulo que el libreto no dice, ordenadas por sospecha.

Pregunta de Jaime sobre el cc de reel-05 —*«"una futura situación gratuita"
dicen los subtítulos, ¿composición no los revisa de cara al libreto?»*— y
después, al ver que no: *«es que es muy obvio que no dicen eso»*.

La respuesta era no. `subtitular.py` corrige dos cosas y ninguna cubre ésta:
`reconciliar` compara el montaje contra la cinta —y no ve nada cuando las dos
pasadas se equivocan igual— y `glosario` sustituye lo que **alguien ya notó una
vez y escribió**. Una palabra nueva mal oída pasa entera hasta que Jaime la lee
en pantalla. Mientras tanto el libreto está en la base, y no lo cruzaba nadie.

## Esto señala, no corrige

Regla del proyecto: *«no se toma el libreto literal, se toma la intención
comunicativa»*. La pieza es hablada, no leída: en las siete hay entre 8 y 41
palabras del subtítulo que el libreto no contiene y **casi todas están bien**.
Así que aquí no se compara texto ni se corta nada. Se cruzan tres señales que ya
existen y se ordena lo que queda:

- **La cinta dice otra que suena igual.** El subtítulo sale de UNA pasada de
  whisper sobre el montaje; la cinta lleva cuatro por tramo. Mismo audio, mejor
  transcripción y palabra distinta es lo más cerca de una prueba que hay: así
  salta «gratuita» donde la cinta dice «fortuita».
- **No está en la cinta.** Aunque no se parezca a nada, una palabra que la cinta
  no dice en ese trozo la puso la pasada floja.
- **El tramo es dudoso.** `work/transcripts/<toma>.json` guarda el `acuerdo`
  entre pasadas de cada tramo, y por debajo de `SUELO` el propio barrido lo marcó
  como «hay que oírlo». Dudosa **y** fuera del libreto es casi seguro un error de
  oído.
- **Hay una palabra del libreto que se le parece**, en el mismo beat. «persegue»
  contra «persigue» no es una paráfrasis: es la misma palabra mal escrita.

Lo que produce es una lista para mirar y, cuando el candidato es claro, la línea
que hay que añadir a `ads/glosario.json`. Corregir sigue siendo una decisión de
quien edita — el glosario **sustituye, no borra**, y una entrada inventada rompe
una frase que estaba bien.

    python scripts/oido.py            # las siete
    python scripts/oido.py 5          # sólo el reel 5
    python scripts/oido.py --todas    # también las que la cinta confirma
"""
import argparse
import difflib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registro  # noqa: E402
import rutas  # noqa: E402
from dominio import texto as tx  # noqa: E402
from dominio.cinta import Cinta  # noqa: E402
from dominio.idioma import Idioma  # noqa: E402
from dominio.libreto import Libreto  # noqa: E402
from dominio.montaje import Montaje  # noqa: E402

SUBS = os.path.join("work", "subs", "todos.json")
GLOSARIO = os.path.join("ads", "glosario.json")
FPS = 30
#: El mismo suelo con el que `transcribir.py` cuenta sus tramos dudosos. Vive
#: repetido en el `--suelo` de aquel paso; aquí se lee la misma marca, no otra.
SUELO = 0.6
#: A partir de este parecido, una palabra del libreto se propone como candidata.
#: Por debajo son dos palabras distintas y proponerla es mandar a mirar a ciegas.
PARECIDO = 0.75
#: Y éste, más flojo, para la palabra de la CINTA: ahí no se propone nada, se
#: dice qué se oyó en el mismo trozo. «fortuita» contra «gratuita» da 0,75 y
#: «una» contra «alguna» 0,67; por debajo de esto ya no suenan parecido y lo que
#: sale es la palabra más cercana de un tramo entero, que no dice nada.
SUENA = 0.6


def del_glosario():
    """Las dos caras del glosario: lo que escribe y lo que venía a borrar.

    - **`hechas`**, lo que escribe. `glosario.json` corrige «que vente» -> «que
      vende», y «vende» no está en el libreto de reel-05, que dice «vendió». Sin
      esto el paso denunciaría su propia corrección en cada corrida, y un
      detector que siempre encuentra lo mismo deja de servir para encontrar lo
      que sí importa.
    - **`escapadas`**, lo que sigue apareciendo pese a tener entrada. El glosario
      compara literal: la entrada «su contado» no toca un «contado.» suelto, y
      reel-05 lo tiene dos veces —una corregida y otra no—. Una corrección
      declarada que no llega es el fallo caro de este proyecto, así que pesa.

    Se restan las palabras que la propia corrección escribe: «carne» está en la
    clave «moldura de carne» y también en su valor «moledora de carne», o sea que
    ahí la palabra no es el error.
    """
    try:
        terminos = json.load(open(GLOSARIO, encoding="utf-8"))["terminos"]
    except (OSError, ValueError, KeyError):
        return set(), set()
    hechas = {w for v in terminos.values() for w in tx.palabras(v.get("es") or "")}
    claves = {w for k in terminos for w in tx.palabras(k)}
    return hechas, {w for w in claves - hechas if len(w) > 2}


def linea_de_montaje(m):
    """Los tramos en orden de montaje, cada uno con su hueco de reloj.

    El subtítulo vive en tiempo de la pieza —lo transcribió el mp4 montado— y
    todo lo demás vive en tiempo de cinta. Ésta es la única traducción.
    """
    fuera, t = [], 0.0
    for tramo, det in m.tramos():
        dur = tramo.hasta - tramo.desde
        fuera.append((t, t + dur, tramo, det))
        t += dur
    return fuera


def acuerdos(m):
    """Por cinta, los tramos con su acuerdo entre pasadas."""
    fuera = {}
    for cinta in {tramo.cinta for tramo, _ in m.tramos()}:
        try:
            datos = Cinta(cinta).datos()
        except Exception:                              # noqa: BLE001
            datos = {}
        fuera[cinta] = [(x["cinta"], x["cinta"] + x["dur"], x.get("acuerdo"))
                        for x in (datos.get("tramos") or [])]
    return fuera


def _densas(ws, vacias=tx.VACIAS):
    """Sólo las palabras que distinguen algo.

    Proponer «que» donde el subtítulo escribe «quemá», o «una» donde escribe
    «alguna», es no proponer nada: son las palabras que se parecen a todo. Es la
    misma criba de `texto.contenido`, aplicada al candidato y no al texto.
    """
    return [w for w in ws if len(w) > 2 and w not in vacias]


def _parecida(palabra, entre, vacias=tx.VACIAS):
    """La más parecida de `entre`, con su parecido. Ninguna si no hay nada."""
    mejor, cuanto = None, 0.0
    for otra in _densas(entre, vacias):
        r = difflib.SequenceMatcher(None, palabra, otra).ratio()
        if r > cuanto:
            mejor, cuanto = otra, r
    return mejor, round(cuanto, 2)


def sospechosas(n, todas=False):
    """Las palabras del subtítulo de esa pieza que el libreto no dice.

    Ordenadas por sospecha, que es la suma de las tres señales. Sin filtro
    —`todas`— salen también las que la cinta confirma y las pasadas no discuten:
    ésas son paráfrasis del hablante y son la mayoría.
    """
    slug = f"reel-{int(n):02d}"
    vacias = Idioma.de_pieza(slug).vacias
    caps = json.load(open(SUBS, encoding="utf-8")).get(slug)
    if not caps:
        return slug, None, 0.0
    beats = Libreto(int(n)).beats
    del_libreto = {i: set(tx.palabras(b)) for i, b in enumerate(beats, 1)}
    todo_el_libreto = set().union(*del_libreto.values())
    hechas, escapadas = del_glosario()

    m = Montaje(slug)
    if not m.existe:
        return slug, None, 0.0
    linea, duda = linea_de_montaje(m), acuerdos(m)
    # Lo que la cinta dice DENTRO de la pieza, palabra a palabra y por tramo: lo
    # primero para saber si el montaje se inventó algo, lo segundo para proponer.
    dice_la_cinta, por_tramo = set(), {}
    for i, (_, _, tramo, _) in enumerate(linea):
        ws = [p.texto for p in m.dentro(tramo)]
        por_tramo[i] = {w for t in ws for w in tx.palabras(t)}
        dice_la_cinta |= por_tramo[i]

    fuera = []
    for c in caps:
        piezas = c["text"].split()
        for k, cruda in enumerate(piezas):
            pal = tx.palabras(cruda)
            if not pal:
                continue
            pal = pal[0]
            if (len(pal) <= 2 or pal.isdigit() or pal in vacias
                    or pal in todo_el_libreto or pal in hechas):
                continue
            # Dónde suena, y con eso en qué beat cae y con qué acuerdo se oyó.
            cuando = (c["at"] + c["duration"] * k / max(1, len(piezas))) / FPS
            i = next((j for j, s in enumerate(linea) if s[0] <= cuando <= s[1]),
                     None)
            beat = linea[i][3].get("beat") if i is not None else None
            acuerdo = None
            if i is not None:
                tramo = linea[i][2]
                en_cinta = tramo.desde + (cuando - linea[i][0])
                acuerdo = next((a for x, y, a in duda.get(tramo.cinta, [])
                                if x <= en_cinta <= y), None)
            candidato, parecido = _parecida(pal, del_libreto.get(beat, ()), vacias)
            oye, suena = _parecida(pal, por_tramo.get(i, ()), vacias)
            sin_cinta = pal not in dice_la_cinta
            dudoso = acuerdo is not None and acuerdo < SUELO
            # **Cuatro señales, y pesan distinto.** Que la cinta oyera OTRA que
            # suena igual es lo más cerca de una prueba que hay —mismo audio,
            # cuatro pasadas contra una—; que no la diga en absoluto delata a la
            # pasada floja; el acuerdo bajo dice dónde mirar; el parecido con el
            # libreto no acusa de nada, dice qué poner.
            gemela = sin_cinta and suena >= SUENA
            escapada = pal in escapadas
            puntos = (3 * gemela + 2 * sin_cinta + 2 * dudoso + 2 * escapada
                      + 1 * (parecido >= PARECIDO))
            if not puntos and not todas:
                continue
            fuera.append({"palabra": cruda, "beat": beat, "escapada": escapada,
                          "en": round(cuando, 1), "sospecha": puntos,
                          "sin_cinta": sin_cinta, "acuerdo": acuerdo,
                          "candidato": candidato if parecido >= PARECIDO else None,
                          "parecido": parecido, "oye": oye if gemela else None})
    fuera.sort(key=lambda x: (-x["sospecha"], x["en"]))
    # **Y lo que el subtítulo dice después de que el EDL se acabe.** El mp4 es de
    # una corrida y el EDL puede ser de otra: en reel-02 el vídeo dura 85,5 s y su
    # EDL 68,5, o sea que hay diecisiete segundos hablando sin tramo del que
    # salgan. Esas palabras no se pueden situar en ningún beat, así que el paso lo
    # dice en vez de dejarlas con un interrogante que parece un fallo suyo.
    final = linea[-1][1] if linea else 0.0
    ultimo = max((c["at"] + c["duration"]) / FPS for c in caps)
    return slug, fuera, round(max(0.0, ultimo - final), 1)


def contar(reels=None, todas=False, detalle=True):
    """El parte: cuántas por pieza y cuáles, de más sospechosa a menos."""
    total = 0
    for n in (reels or rutas.piezas()):
        slug, filas, colas = sospechosas(n, todas)
        if filas is None:
            print(f"{slug}: sin subtitulos todavia — corre antes subtitular.py")
            continue
        total += len(filas)
        print(f"{slug}: {len(filas)} palabra(s) sospechosa(s)")
        if colas > 1.0:
            print(f"   ojo: {colas:.0f}s de subtitulo despues de donde acaba el"
                  f" EDL — el mp4 y el corte son de corridas distintas, asi que"
                  f" esas palabras no tienen beat con el que compararse")
            registro.aviso("oido", "subtitulo mas largo que el EDL",
                           detalle=f"{slug}: {colas:.1f}s sin tramo", eco=False)
        if filas:
            # Va al log porque el paso corre dentro del montaje y su salida se
            # pierde entre la del render. En la base sigue estando mañana.
            registro.aviso("oido", "palabras que el libreto no dice",
                           detalle=f"{slug}: {len(filas)} — "
                                   + ", ".join(f["palabra"] for f in filas[:6]),
                           eco=False)
        if not detalle:
            continue
        for f in filas:
            razones = []
            if f["escapada"]:
                razones.append("ya tiene entrada en el glosario y sigue aqui")
            if f["sin_cinta"]:
                razones.append("no esta en la cinta")
            if f["acuerdo"] is not None and f["acuerdo"] < SUELO:
                razones.append(f"pasadas en desacuerdo ({f['acuerdo']:.2f})")
            if f["candidato"]:
                razones.append(f"el libreto dice «{f['candidato']}»"
                               f" ({f['parecido']:.2f})")
            if f["oye"]:
                razones.append(f"la cinta dice «{f['oye']}»")
            beat = f"e{f['beat']}" if f["beat"] else "?"
            print(f"   [{f['sospecha']}] {f['palabra']:<16} {beat:<4}"
                  f" {f['en']:6.1f}s  {' · '.join(razones) or 'fuera del libreto'}")
    print(f"\noido: {total} palabra(s) para mirar."
          f" Lo que sea error de oido se arregla en {GLOSARIO} —"
          f" clave lo que whisper escribe, valor lo que se dice. Sustituye,"
          f" nunca borra: una entrada vacia deja el subtitulo sin palabra.")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--todas", action="store_true",
                    help="tambien las que la cinta confirma (son parafrasis)")
    ap.add_argument("--callado", action="store_true",
                    help="solo el numero por pieza, sin la lista")
    a = ap.parse_args()
    # **Avisa y no para, a proposito.** Esto no mide un defecto: senala palabras
    # para que alguien las mire. Plantar el montaje por una paráfrasis seria
    # cambiar un problema por otro — y la lista deja de leerse en cuanto bloquea.
    contar(a.reels, a.todas, detalle=not a.callado)


if __name__ == "__main__":
    main()
