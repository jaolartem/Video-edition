"""Monta el reel **por beats del libreto**, no por calidad de enunciado.

Por qué se reescribió
---------------------
El montaje anterior elegía enunciados por densidad y fluidez hasta gastar el
presupuesto. Con eso, cuatro intentos de la misma idea puntúan alto los cuatro y
entran los cuatro: el reel 1 decía «la mayoría de los emprendedores asume que si
vende más le va a quedar más» y catorce segundos después «la mayoría de gente
piensa que si usted vende mucho más va a conseguir más plata». Misma idea, otras
palabras — el detector de repetición no la ve porque compara n-gramas, y el
espectador sí la ve porque compara sentido.

Jaime: *«el frame debe estar presente siempre, y debe mantener el orden del
libreto así no se diga igual»*. Eso es exactamente lo que hace este montaje:

1. La estructura se parte en **etapas** — cada una, una función en el argumento.
   Cuáles son y en qué orden lo declara `ads/frames.json`. El frame no se deduce
   aquí: se lee.
2. Para cada etapa se busca en la toma el enunciado que mejor la cumple.
3. **Una etapa, un enunciado.** Cumplida, su idea queda cerrada para toda la
   pieza: los demás intentos de decirla quedan fuera, estén donde estén.
4. Salen **en el orden de la estructura**, no en el de la grabación.

El resultado no es «las mejores frases»: es el argumento entero, una vez cada
cosa, en el orden en que convence.

**El libreto es accidental; el módulo es el copy.** Jaime: *«no es el libreto lo
importante, lo importante es el framework y el copy… los módulos son el copy»*.
El párrafo del libreto entra aquí sólo como **vocabulario de su etapa** —una
forma de decirla, no la forma—, así que un enunciado que cumple la etapa con
otras palabras vale igual. Lo que no se negocia es la secuencia de la estructura
y que cada etapa se cumpla **una vez**.

Y el orden de prioridad es el que fijó Jaime: *«lo más importante es el mensaje,
lo que se dice; luego cómo se dice; luego cómo se ve»*. Aquí eso es literal —
**el texto filtra y la voz decide**, en dos pasos, no en una suma ponderada:
sólo compiten los enunciados que dicen el beat, y entre ellos gana el más
expresivo. Con la suma, una toma apagada que cubría un poco más ganaba a una
viva; con el filtro, la apagada ni siquiera compite si no dice el beat.

Qué hace este fichero y qué NO
------------------------------
Este fichero **monta**: recorre las etapas, cruza lo que decidió el paso 2 con lo
que decidió Jaime de oído, y escribe el EDL. Lo que **mide** y lo que **juzga**
vive en el dominio, porque no es de este paso: lo usan otros doce scripts y
tenerlo aquí era la razón de que `beats.py` fuese el fichero más largo del
proyecto.

    dominio.libreto      qué dice la pieza y qué estructura ejecuta
    dominio.etapa        una etapa del frame y qué tiene que decir
    dominio.enunciado    cómo se parte la cinta en unidades de sentido
    dominio.candidata    si una unidad cumple su etapa, y cómo de bien
    dominio.decidido     lo que ya está decidido, y de dónde sale
    dominio.concurso     qué unidad se lleva una etapa
    dominio.armado       el montaje mientras se construye
    dominio.extremos     la apertura y el cierre declarados
    dominio.poda         lo que se dice dos veces dentro de una unidad
    dominio.voz          si la voz está viva, y si se nota al unir dos trozos
    dominio.f0           el tono de la señal, medido sobre la onda
    dominio.neutralidad  el punto cero de una cinta
    dominio.vocabulario  de qué palabras está hecho un texto

Las funciones de abajo se quedan como **delegación de una línea**: medio proyecto
llama `beats.puntua`, `beats.expresividad` o `beats.norm`, y mover una
implementación no tiene por qué mover a quien la llama.

Uso:
    python scripts/beats.py --reel 1
"""
import argparse
import json
import os
import sys

# **La velocidad del montaje, y vive aqui porque la usan cinco pasos.**
#
# 1, no 1,15. Jaime, al ver las duraciones reales: *«ninguno hay que acelerar la
# verdad, todos estan por debajo de los 120 y en el rango de los 90s»*. A
# velocidad natural el lote va de 47,6 a 118,5 s, con cuatro de seis entre 72 y
# 89 — formato corto sin forzar nada.
#
# Y quita de la cadena la resintesis mas grande: `rubberband` no es un filtro,
# reconstruye la senal. Con la voz limpiada fuera eran **dos resintesis
# encadenadas**, y ahi es donde empezo a sonar a papilla.
#
# Estaba repetido en seis ficheros, que es como se acaba teniendo dos
# velocidades distintas en el mismo montaje.
VELOCIDAD = 1.0

sys.path.insert(0, os.path.dirname(__file__))
import transcribir  # noqa: E402
import rutas  # noqa: E402
from dominio import candidata, enunciado, extremos, f0, poda  # noqa: E402
from dominio import vocabulario  # noqa: E402
from dominio import voz as _voz  # noqa: E402
from dominio.armado import Armado  # noqa: E402
from dominio.concurso import Concurso  # noqa: E402
from dominio.decidido import Decidido  # noqa: E402
from dominio.etapa import Etapa  # noqa: E402
from dominio.libreto import Libreto  # noqa: E402
from dominio.voz import Voz  # noqa: E402


def _di(msg):
    """Los avisos del montaje van por stderr: la salida limpia es el listado."""
    print(msg, file=sys.stderr)

# Los nombres que ya usaban doce scripts. El valor lo declara quien es su dueño;
# aquí sólo se apunta, para que no haya dos números con el mismo nombre.
VENTANA_MIN = f0.VENTANA_MIN
SALTO_TONO = _voz.SALTO_TONO
SALTO_RITMO = _voz.SALTO_RITMO
IGUAL = candidata.IGUAL
UMBRAL = candidata.UMBRAL
RELATIVO = candidata.RELATIVO
FINALISTAS = candidata.FINALISTAS
PASO_VOZ = candidata.PASO_VOZ


# ── lo que se sabe de un texto ───────────────────────────────────────────────
def palabras(t):
    """Las palabras tal cual, sin tildes ni puntuación. No filtra nada.

    La regla vive en `dominio.texto` y la memoria en `dominio.vocabulario`.
    """
    return vocabulario.palabras(t)


def norm(t):
    """De qué habla un texto, sólo lo que distingue. Regla en `dominio.texto`."""
    return vocabulario.contenido(t)


# ── lo que la pieza tiene que decir ──────────────────────────────────────────
def beats_del_libreto(n):
    """Los beats de la pieza, **desde la base**. Un párrafo, un beat.

    La lee `dominio.Libreto`, que es su dueño, y **no** `docs/libretos.md`: dos
    ficheros para el mismo dato se separan en cuanto uno cambia.
    """
    return Libreto(n).beats


def frame_del_reel(n, beats):
    """Qué estructura ejecuta el reel y qué función cumple cada beat.

    Sale de `ads/frames.json`. Lo sabe `dominio.Libreto`.
    """
    return Libreto(n).frame(beats)


# ── cómo se parte la cinta, y cómo se juzga cada trozo ───────────────────────
def oraciones(toma):
    """Los candidatos: **oraciones completas**, no tramos de silencio.

    Cómo se reconstruyen —puntuación, tramos de voz, aire interno, `MAX_ORACION`—
    lo sabe `dominio.enunciado`.
    """
    return enunciado.oraciones(toma)


def tartamudeo(texto):
    """Cuánto se repite el enunciado consigo mismo. Ver `dominio.candidata`."""
    return candidata.tartamudeo(texto)


def integridad(texto):
    """Cuántos extremos de la frase están enteros. Ver `dominio.candidata`."""
    return candidata.integridad(texto)


def trabado(texto):
    """Palabras pegadas repetidas: «usted usted». Ver `dominio.candidata`."""
    return candidata.trabado(texto)


def parecido(u, v):
    """Cuánto dicen lo mismo dos enunciados. Ver `dominio.candidata`."""
    return candidata.parecido(u, v)


def puntua(beat, u):
    """Cuánto dice este enunciado el beat. Ver `dominio.candidata`."""
    return candidata.puntua(beat, u)


def dice(texto, termino):
    """Si un enunciado dice de verdad un termino. Ver `dominio.candidata`."""
    return candidata.dice(texto, termino)


def podar(u, exige=()):
    """Quita las repeticiones de DENTRO de una unidad. Ver `dominio.poda`."""
    return poda.podar(u, exige)


def unir(u1, u2):
    """Dos frases seguidas de la misma toma, como una sola unidad. Ver `dominio.poda`."""
    return poda.unir(u1, u2)


# ── cómo suena ───────────────────────────────────────────────────────────────
#
# **Estas cuatro pueden devolver `None`, y eso es el arreglo, no un descuido.**
# Devolvían `0.0` para decir «no medido» —ventana corta, sin energía sonora, el
# detector saltando de octava— y `0.0` también significaba «medido y plano». Los
# dos casos son opuestos y salían con el mismo número: un tramo que nadie llegó a
# oír entraba en las comparaciones como el peor posible. Ver `dominio.voz`.
def cabe(a, b):
    """Si ese tramo da para medir. La precondicion, preguntable antes de gastar."""
    return f0.cabe(a, b)


def contorno(toma, a, b):
    """El contorno de F0 del tramo, en Hz y corregido de octava. Ver `dominio.f0`."""
    return f0.contorno(toma, a, b)


def expresividad(toma, a, b):
    """Cuánta vida tiene la voz, en semitonos de recorrido de F0.

    `None` si no se pudo medir — que **no** es lo mismo que salir plana.
    """
    return Voz(a, b, toma).expresividad


def cambio_de_tono(toma, a, b):
    """Cuánto se MUEVE la voz, en semitonos por segundo. `None` si no se midió."""
    return Voz(a, b, toma).cambio_de_tono


def ritmo(palabras, a, b, ventana=2.0):
    """Cuánto varía la velocidad del habla dentro del tramo. `None` si no se midió."""
    return Voz(a, b).ritmo(palabras, ventana)


def intensidad(toma, a, b, palabras=None):
    """Cuánta emoción lleva el tramo, **sin signo**. Ver `dominio.voz`."""
    return Voz(a, b, toma).intensidad(palabras)


def salto(toma_a, fin_a, toma_b, ini_b, palabras=None, ventana=1.5,
          palabras_b=None):
    """Cuánto salta la voz AL CRUZAR una costura. Es lo que se oye del corte.

    Se mide sobre `ventana` segundos a cada lado —lo que el oído usa para
    situarse— y lo contesta `dominio.voz.Voz.salta_a`.
    """
    sale = Voz(max(0.0, fin_a - ventana), fin_a, toma_a)
    entra = Voz(ini_b, ini_b + ventana, toma_b)
    return sale.salta_a(entra, palabras, palabras_b)


def _cumple(etapa, decidido, concurso, armado):
    """Quién le da la toma a esta etapa, y **en qué orden mandan**.

    Éste es el reparto de autoridad del montaje, y estaba escrito como una
    escalera de `if`s en medio de un bucle de quinientas líneas. Ahí se perdió
    una vez: la guarda de «una etapa refutada no vuelve a concurso» **se cayó al
    reordenar el fichero** y tres etapas refutadas salieron montadas en el reel
    4. Escrito de arriba abajo y en un sitio, el orden se lee:

    1. **Lo aprobado de oído no se re-elige** — ni se mide, ni compite.
    2. **Lo rechazado va con tarjeta** — la etapa existe y se queda sin toma.
    3. **Los tramos declarados** mandan sobre cualquier heurística.
    4. **Lo refutado por el paso 2** no vuelve a concurso; sólo `recortar` lo
       rescata, y por eso `recorta_en_vez_de_tumbar` va antes que esta guarda.
    5. **La asignación del paso 2** manda sobre la puntuación de texto, salvo
       que no diga lo que la etapa exige ni barriendo hacia delante.
    6. Y sólo si no hay nada de lo anterior, **el concurso**.
    """
    if decidido.aprobada(etapa):
        g = decidido.guardado(etapa)
        armado.pon(etapa, {"a": g["desde"], "b": g["hasta"],
                           "texto": g.get("texto", ""),
                           "clave": set(norm(g.get("texto", "")))})
        _di(f"  beat {etapa.n} ({etapa.nombre}): APROBADO, se conserva")
        return
    if decidido.rechazada(etapa):
        _di(f"  beat {etapa.n} ({etapa.nombre}): RECHAZADO, va con tarjeta — "
            f"{decidido.guardado(etapa).get('por_que', '')}")
        return

    decidido.recorta_en_vez_de_tumbar(etapa)

    tr = decidido.tramos_declarados(etapa)
    if tr:
        armado.pon(etapa,
                   {"a": tr[0][0], "b": tr[-1][1],
                    "tramos": [list(x) for x in tr],
                    "texto": "", "clave": set(), "pal": []},
                   voz=Voz(tr[0][0], tr[-1][1], armado.toma).expresividad)
        _di(f"  beat {etapa.n} ({etapa.nombre}): tramos declarados "
            f"{', '.join('%.2f-%.2f' % (x[0], x[1]) for x in tr)}")
        return

    if decidido.refutada(etapa):
        _di(f"  beat {etapa.n} ({etapa.nombre}): refutada por el paso 2 — "
            f"va con tarjeta")
        return

    i = decidido.asignada(etapa)
    if i is not None:
        u = concurso.completar(concurso.cands[i], etapa)
        if etapa.debe_decir and not etapa.cumplida_por(u["texto"]):
            _di(f"  beat {etapa.n} ({etapa.nombre}): la asignacion del paso 2 "
                f"no dice {etapa.debe_decir} ni barriendo — se vuelve a elegir")
            decidido.olvida_asignacion(etapa)
        else:
            armado.pon(etapa, u,
                       voz=Voz(u["a"], u["b"], armado.toma).expresividad)
            return

    elegida = concurso.elige(armado.libres(concurso.cands), etapa, armado.ultimo)
    if elegida:
        armado.pon(etapa, *elegida)


def montar(n, budget):
    """El corte de una pieza: qué etapa se lleva qué trozo de cinta.

    Devuelve `(frame, parrafos, elegidos, total, fijados, segs)` — la misma tupla
    de siempre, porque es la que lee el CLI y la que `revision` espera.

    El cuerpo es corto a propósito: **aquí no se decide nada, se ordena.** Quién
    manda sobre quién lo dice `_cumple`; qué unidad cumple una etapa, el
    `Concurso`; qué está ya decidido, `Decidido`; y lo que se lleva armado se lo
    guarda `Armado`. Esta función era de 523 líneas y por eso una guarda podía
    caerse dentro sin que nadie lo viera.
    """
    toma = rutas.TOMAS[f"reel-{n:02d}"]
    parrafos = beats_del_libreto(n)
    frame = frame_del_reel(n, parrafos)
    etapas = Etapa.todas(frame, parrafos)

    ws = transcribir.exigir(toma)["segmentos"]
    runs = json.load(open(f"work/cuts/{toma}.json",
                          encoding="utf-8"))["segmentos"]

    decidido = Decidido(n)
    concurso = Concurso(oraciones(toma), toma, ws, runs)
    armado = Armado(etapas, toma)

    for etapa in etapas:
        _cumple(etapa, decidido, concurso, armado)

    # **El presupuesto ya no recorta.** Jaime: *«respeta el guion; si hay
    # necesidad de recortar lo definimos al final»* y *«el ajuste de tiempo lo
    # hacemos al final con el reel montado»*.
    #
    # Antes, al pasarse de presupuesto, caía el beat peor cubierto — y eso es
    # una decisión de montaje tomada por una resta. Un beat que sobra por
    # duración no sobra por argumento: qué se va se mira con la pieza delante,
    # no con una cuenta. Se avisa con la cifra, que es lo que hace falta para
    # decidir después.
    if budget and armado.duracion > budget:
        _di(f"  ojo: {armado.duracion:.1f}s sobre la indicación de {budget:.0f}s "
            f"(+{armado.duracion - budget:.1f}s). NO se recorta: el ajuste se "
            f"decide al final, sobre el montaje.")

    # Y encima de lo elegido, en este orden: primero los recortes finos que
    # están declarados, después la limpieza que no elige nada, y al final los
    # dos extremos de oído, que mandan sobre todo lo anterior.
    armado.recorta(decidido.ajustes(frame))
    armado.poda()
    segs = armado.segs()
    segs = extremos.abrir(armado, frame, segs, ws)
    segs = extremos.cerrar(armado, frame, segs)
    return (frame, parrafos, armado.elegidos,
            sum(b - x for x, b in segs), decidido.fijados, segs)


def _voz_de(u):
    """Cómo se escribe la voz de una unidad en el listado. `None` se dice."""
    v = u.get("voz")
    return f"voz {v:.1f}st" if v is not None else "voz sin medir"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reel", type=int, required=True)
    # **Indicación, no tope.** Ad 120 s, reel 90 s, y varía según lo que la
    # pieza tenga que decir. Sólo avisa: el ajuste se decide al final, sobre el
    # montaje. Ver «Duración» en CLAUDE.md.
    ap.add_argument("--budget", type=float, default=120.0)
    ap.add_argument("--escribir", action="store_true")
    a = ap.parse_args()

    frame, beats, elegidos, total, fijados, segs = montar(a.reel, a.budget)

    print(f"\n=== reel-{a.reel:02d} · {frame['estructura']} · "
          f"{len(elegidos)}/{len(beats)} beats · {total:.1f}s ===")
    print(f"    mecanismo: {frame['mecanismo']['primario']} "
          f"(secundario: {frame['mecanismo']['secundario']})")
    puestos = {u["beat"] for u in elegidos}
    # Se imprime DESPUES de aplicar recortes, apertura y cierre: antes el
    # listado ensenaba tiempos que el EDL ya no tenia.
    porBeat = {u["beat"]: u for u in elegidos}
    for i, b in enumerate(frame["beats"], 1):
        u = porBeat.get(i)
        marca = "!" if b.get("obligatorio") else " "
        if u:
            print(f" {marca}{i:2} {b['etapa']:34} {u['a']:7.2f}-{u['b']:7.2f} "
                  f"({u['b']-u['a']:4.1f}s, {_voz_de(u)})  "
                  f"{u['texto'][:58]}")
        else:
            print(f" {marca}{i:2} {b['etapa']:34} — SIN TOMA: va con tarjeta")
    faltan = [b["etapa"] for i, b in enumerate(frame["beats"], 1)
              if i not in puestos and b.get("obligatorio")]
    if faltan:
        print(f"\n  OBLIGATORIOS SIN TOMA: {', '.join(faltan)}", file=sys.stderr)

    if a.escribir:
        # **Biblioteca de partes: lo que QUEDO, no lo que se cayo.**
        #
        # Jaime: *«lo descartado se tira; lo que no se tira es lo que quedo, eso
        # es lo que puede reutilizarse en otro video que hable del mismo tema»*.
        # Un descarte se descarto por algo; un enunciado elegido ya paso por
        # todo — cubre su etapa, esta entero y es el mas expresivo de sus
        # rivales. Se indexa por etapa, que es lo que lo hace buscable.
        toma = rutas.TOMAS[f"reel-{a.reel:02d}"]
        os.makedirs("work/biblioteca", exist_ok=True)
        bf = f"work/biblioteca/reel-{a.reel:02d}.json"
        json.dump({"toma": toma, "estructura": frame["estructura"],
                   "mecanismo": frame["mecanismo"],
                   "partes": [{"etapa": u["etapa"],
                               "start": round(u["a"], 3),
                               "end": round(u["b"], 3),
                               "dur": round(u["b"] - u["a"], 2),
                               "voz_st": u["voz"],
                               "texto": u["texto"]}
                              for u in elegidos]},
                  open(bf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"biblioteca -> {bf} ({len(elegidos)} partes reutilizables)")

        # **Este paso ya no escribe el EDL, y es a proposito.**
        #
        # Lo hacia: leia `ads/<slug>/edl-sell.json`, le cambiaba
        # `segmentos`, `detalle` y `revision`, y lo volvia a escribir. O sea
        # que el fichero del que sale el montaje tenia **dos escritores con
        # esquemas distintos** —este y `dominio/seleccion/edl.py`—, que es
        # exactamente el patron del que salieron C-149, C-151 y C-153.
        #
        # Y este no estaba en ninguna fase: `beats.py --reel N` es una
        # entrada de mano. Un escritor sin mantener sobre el artefacto
        # central es una pistola cargada, como los diez de C-157.
        #
        # Se conserva el listado, que es para lo que sirve mirar una pieza;
        # para escribir esta la fase `elegido`.
        print("")
        print("(este listado no escribe el EDL: eso es de"
              " scripts/seleccionar.py {n} --edl, la fase elegido)")
