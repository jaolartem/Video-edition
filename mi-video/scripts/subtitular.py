"""Transcribe el reel YA MONTADO y genera sus subtítulos.

Por qué no vale el transcript del bruto
---------------------------------------
Los subtítulos salían de las palabras del bruto mapeadas a la línea de tiempo, y
eso hereda todos sus defectos: las palabras estiradas que cruzan silencios
eliminados, y los tramos donde el transcript se salta palabras enteras. En el
reel 6 el tramo 22,08-30,66 dice de oído «nadie le mandó una carta, el banco no
le dijo que no, el CRA no lo llamó…», y el transcript del bruto empieza en «el
CRA»: los subtítulos se comían la primera mitad.

Transcribir lo montado no tiene ese problema — **es literalmente lo que se oye**,
sin huecos que remapear. Y como el montaje ya viene sin silencios, whisper tiene
menos donde alucinar.

Se pide granularidad de palabra (`-ml 1 -sow`) para poder agrupar en frases
cortas con tiempos reales.
"""
import json
import os
import unicodedata
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu  # noqa: E402

W = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
FPS = 30
# Medido sobre render: la Montserrat 800 gasta ~0,70 em por caracter, así que a
# 62 px caben ~22 por línea en los 950 útiles. 36 da dos líneas con holgura.
TOPE = 36


def transcribir(mp4, wav, base):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
                   check=True)
    subprocess.run(gpu.whisper() + [
                    "-m", os.path.join(W, "ggml-medium.bin"),
                    "-l", "es", "-mc", "0", "-ml", "1", "-sow",
                    "-oj", "-of", base, "-f", wav],
                   capture_output=True, check=True)
    with open(base + ".json", encoding="utf-8") as fh:
        d = json.load(fh)
    out = []
    for s in d["transcription"]:
        t = s["text"].strip()
        if not t or t.startswith("["):
            continue
        # Whisper mete comillas donde no las hay: en el reel 1 salio
        # «le queda lo que deberia"» con una comilla suelta al final. En un
        # subtitulo quemado eso no se puede corregir despues.
        t = t.replace('"', "").replace("“", "").replace("”", "")
        if not t:
            continue
        off = s["offsets"]
        out.append({"start": off["from"] / 1000, "end": off["to"] / 1000, "text": t})
    return out


def agrupar(words):
    caps, buf = [], None
    for w in words:
        cierra = w["text"][-1:] in ".?!"
        if buf and (len(buf["text"]) + 1 + len(w["text"]) > TOPE
                    or w["start"] - buf["end"] > 0.7):
            caps.append(buf); buf = None
        if not buf:
            buf = {"start": w["start"], "end": w["end"], "text": w["text"]}
        else:
            buf["text"] += " " + w["text"]
            buf["end"] = w["end"]
        if cierra:
            caps.append(buf); buf = None
    if buf:
        caps.append(buf)
    # **Sin huecos.** Cada subtitulo se estira hasta el siguiente: la mayoria ve
    # los reels sin audio, asi que un instante sin texto es un instante sin
    # argumento. Un hueco de medio segundo no descansa la vista, la corta.
    # La duracion se calcula EN FRAMES, restando los `at` ya redondeados. Al
    # redondear los segundos por separado —`round(inicio*30)` y
    # `round((fin-inicio)*30)`— quedaban huecos de un frame entre subtitulo y
    # subtitulo. Son 33 ms y no se ven, pero un detector de huecos que siempre
    # encuentra seis deja de servir para encontrar el que si importa.
    ats = [round(c["start"] * FPS) for c in caps]
    out = []
    for i, c in enumerate(caps):
        fin = ats[i + 1] if i + 1 < len(caps) else round((c["end"] + 0.4) * FPS)
        out.append({"at": ats[i],
                    "duration": max(8, fin - ats[i]),
                    "text": c["text"]})
    return out


def esperadas(slug):
    """Las palabras que el montaje DEBERIA decir, tomadas de la cinta.

    El transcript de la cinta lleva cuatro pasadas y el del montaje una sola —y
    una sola pasada *«se come cosas, se queda pegado»* (C-54). Por eso el
    subtitulo decia «pierda la mitad en **puestos**» donde la cinta dice
    «impuestos», «al **cR**» donde dice «CRA», y «estar costando **esta casa**»
    donde dice «hasta 550 dolares».

    **La division correcta: el tiempo lo da el montaje, las palabras las da la
    cinta.** Transcribir el montaje sigue siendo lo correcto para los tiempos
    —ahi no hay huecos que remapear— pero sus palabras son las peores del
    sistema y son justo las que el espectador lee.
    """
    import sys as _s
    _s.path.insert(0, os.path.dirname(__file__))
    import transcribir as _tr, rutas as _ru
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    cache, out = {}, []
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        t = det.get("toma") or _ru.TOMAS.get(slug)
        if t not in cache:
            try:
                cache[t] = _tr.exigir(t)["segmentos"]
            except SystemExit:
                cache[t] = []
        out += [w["text"] for w in cache[t]
                if rango[0] - 0.02 <= w["start"] and w["end"] <= rango[1] + 0.02]
    return out


def _limpia(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn"
                   and (c.isalnum() or c == " ")).strip()


def reconciliar(caps, esperado, ventana=6):
    """Sustituye la palabra del montaje por la de la cinta cuando difieren.

    Alineacion posicional con ventana: las dos secuencias dicen lo mismo y en el
    mismo orden, asi que basta mirar cerca.

    **Y solo una regla, la segura:** se sustituye cuando la palabra de la cinta
    *contiene* a la del montaje por el final y es mas larga — «impuestos» contra
    «puestos», que es el error tipico de una pasada unica, comerse el arranque.

    Hubo una segunda regla para palabras cortas —misma inicial, longitud
    parecida— pensada para las siglas, y **hacia mas dano que bien**: convertia
    «es» en «esta», «los» en «le» y «el» en «en». Tres destrozos por un acierto.
    Las siglas se arreglan con un glosario, que es la herramienta que les
    corresponde, no con parecido de letras.
    """
    if not esperado:
        return caps, 0
    plano = [_limpia(x) for x in esperado]
    j, cambios = 0, 0
    for c in caps:
        piezas = c["text"].split(" ")
        for k, pieza in enumerate(piezas):
            n = _limpia(pieza)
            if not n:
                continue
            # Avanza hasta encontrarla; si esta, no hay nada que corregir.
            hit = next((i for i in range(j, min(j + ventana, len(plano)))
                        if plano[i] == n), None)
            if hit is not None:
                j = hit + 1
                continue
            cand = None
            for i in range(j, min(j + ventana, len(plano))):
                e = plano[i]
                if len(n) >= 4 and e.endswith(n) and len(e) > len(n):
                    cand = i
                    break
            if cand is None:
                continue
            cola = "".join(ch for ch in pieza if not ch.isalnum())
            piezas[k] = esperado[cand] + cola
            j = cand + 1
            cambios += 1
        c["text"] = " ".join(piezas)
    return caps, cambios


if __name__ == "__main__":
    os.makedirs("work/subs", exist_ok=True)
    todo = {}
    for r in sys.argv[1:] or ["01", "02", "03", "04", "05", "06"]:
        mp4 = f"public/reel-{r}.mp4"
        if not os.path.exists(mp4):
            print(f"reel-{r}: falta {mp4}", file=sys.stderr)
            continue
        base = f"work/subs/reel-{r}"
        caps = agrupar(transcribir(mp4, base + ".wav", base))
        caps, n = reconciliar(caps, esperadas(f"reel-{r}"))
        todo[f"reel-{r}"] = caps
        print(f"reel-{r}: {len(caps)} subtitulos"
              + (f" · {n} palabra(s) corregidas contra la cinta" if n else ""))
    if todo:
        prev = {}
        if os.path.exists("work/subs/todos.json"):
            prev = json.load(open("work/subs/todos.json", encoding="utf-8"))
        prev.update(todo)
        json.dump(prev, open("work/subs/todos.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
