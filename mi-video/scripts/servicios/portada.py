"""**La portada que el diseñador declara**, y el fotograma que se saca por él.

Jaime, 16-9-2026, al ver que reel-11 salió sin ella: *«no me dejaste la
portada»*, y acto seguido dónde vive la decisión: *«inclúyela en el contrato del
diseñador»*. Antes sólo la tenía reel-13, hecha a mano, y por eso ninguna otra
la tuvo: un dato sin contrato es un dato que nadie produce.

## Va fuera del bucle de etapas, porque es de la pieza

No cuelga de ningún `etapa_orden`: una pieza tiene una portada y no una por
escena. Por eso `disenar` la aplica antes de recorrer los tableros.

## Él elige el instante; el fotograma lo saca la máquina

El diseñador trabaja con `Read` y `Write`: no puede exportar una imagen. Así que
declara **el segundo** —de los que ya mira en el `documento`— y aquí se
extrae.

**Del corte (`public/reel-NN.mp4`), no del render y no del bruto.** Los tres
tienen el mismo instante y no la misma imagen:

- El **render** lleva el rótulo y el subtítulo quemados, y una portada que
  reaprovecha un CC cuenta media frase del segundo 2, no de qué va la pieza.
- El **bruto** viene más abierto: el encuadre de la pieza es un acercamiento que
  se decidió al montarla, y sacar de ahí devuelve la habitación entera con él
  pequeño. Se probó con reel-11 el 16-9 y salió el sillón, el perro y el armario.
- El **corte** ya está a 1080×1920 —que es exactamente el tamaño de la portada,
  así que no hay pérdida— con el encuadre elegido y sin un solo gráfico encima.

## El texto sale del libreto, no se inventa

Es la misma regla que el resto del proyecto, y la portada es donde más tienta
saltársela: es lo único que se ve antes de darle al play.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rutas  # noqa: E402

#: Dónde vive lo que el spec lee: `FRAMES.reels[slug].portada`.
FRAMES = "ads/frames.json"


def _fotograma(slug, segundo):
    """Saca el fotograma del bruto, al segundo del MONTAJE que él declaró.

    Devuelve la ruta relativa a `public/` que el spec espera, o `None` si no se
    pudo: sin imagen no hay portada, y una portada a medias es peor que ninguna
    porque el render la da por buena.
    """
    n = int(slug.split("-")[1])
    corte = f"public/reel-{n:02d}.mp4"
    if not os.path.exists(corte):
        return None
    destino = f"public/portadas/reel-{n:02d}.jpg"
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{segundo:.3f}",
                        "-i", corte, "-frames:v", "1", "-q:v", "2", destino],
                       capture_output=True)
    return destino[len("public/"):] if not r.returncode else None


def guardar(slug, respuesta):
    """Escribe la portada que traiga esa respuesta, y dice qué pasó.

    Recibe la respuesta ENTERA y saca lo suyo: `portada` con `titulo`,
    `subtitulo`, `en` —el segundo del montaje— y `por_que`. Se lleva el asunto
    completo —sacarlo, decidir si vale, escribirlo y contarlo— para que quien
    llama sean dos líneas: el techo de 300 de `disenar.py` es un contrato, no
    una sugerencia, y esto no es suyo.

    Si falta el segundo o no se puede sacar la imagen, **no se escribe nada**:
    el spec lee esto como verdad y media portada entra en pantalla igual que
    una entera.
    """
    dicho = respuesta.get("portada") if isinstance(respuesta, dict) else None
    if not isinstance(dicho, dict) or not dicho.get("titulo"):
        return None
    try:
        en = float(dicho.get("en"))
    except (TypeError, ValueError):
        return _di(f"{slug}: la portada no dice en qué segundo — no se escribe")
    foto = _fotograma(slug, en)
    if not foto:
        return _di(f"{slug}: no se pudo sacar el fotograma del segundo {en}"
                   f" — no se escribe")
    d = json.load(open(FRAMES, encoding="utf-8"))
    d["reels"].setdefault(slug, {})["portada"] = {
        "titulo": dicho["titulo"],
        "subtitulo": dicho.get("subtitulo") or "",
        "fotograma": foto,
        "por_que": dicho.get("por_que") or "",
        # **La forma, si la declara.** `velo` es la de siempre y `bloque` la
        # que corta el plano en vez de oscurecerlo. Se deja pasar tal cual: qué
        # formas hay lo sabe el componente, no este paso.
        **({"forma": dicho["forma"]} if dicho.get("forma") else {}),
    }
    with open(FRAMES, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write(chr(10))
    return _di(f"{slug}: portada declarada — «{dicho['titulo']}» sobre {foto}")


def _di(linea):
    print(f"    {linea}")
    return linea


# ── La portada va con TODAS, y por la línea ─────────────────────────────────
#
# Jaime, 20-10-2026, viendo FINALES: *«en los finales no agregaste la
# cobertura, eso debe salir siempre con todos los videos»*. Era opcional en el
# contrato y nadie sacaba el PNG ni lo subía: las cinco que había se hicieron a
# mano. Ahora es obligatoria, `disenar` no da por diseñada una pieza sin ella,
# y `publicar.py` no sube un vídeo sin su portada al lado (C-618).

#: Donde queda la imagen que se sube, al lado de la entrega.
PNG = "out/entrega/reel-R{n}-portada.png"
#: El prompt del diseñador, que es donde vive el criterio de la portada.
PROMPT = "scripts/disenar.prompt.md"
#: El buzón del diseñador.
BUZON = "work/servicio/disenar"
#: El cuadro que se saca: el último de los 90 que dura `Portada-*` en
#: `src/Composition.tsx`. En el 0 el texto todavía no ha entrado.
CUADRO = 89


def declarada(slug):
    """La portada que la pieza declara en `frames.json`, o `None`."""
    d = json.load(open(FRAMES, encoding="utf-8"))
    return (d["reels"].get(slug) or {}).get("portada") or None


def png(n):
    """La portada como imagen, sacada de su declaración. `None` si no la hay.

    Se pinta con `Cover`, el mismo componente que la composición `Portada-*`,
    y con las mismas cuatro props. Va por `--props` sobre una composición de
    muestra y no por el spec: pasarla por `src/reels.json` cambiaría la huella
    del spec y caducaría un render que no ha cambiado. Se rehace sólo si la
    declaración cambió: al lado queda su huella.
    """
    import hashlib

    slug = f"reel-{int(n):02d}"
    p = declarada(slug)
    if not p or not p.get("fotograma"):
        return None
    props = {"hook": p["titulo"], "subtitulo": p.get("subtitulo") or "",
             "fotograma": p["fotograma"], "forma": p.get("forma"),
             # La muestra trae su antetítulo; aquí no lleva ninguno. Y nada más
             # a `null`: un null se salta el valor por defecto de `Cover`.
             "kicker": None}
    huella = hashlib.sha1(json.dumps(props, sort_keys=True).encode()).hexdigest()[:12]
    salida = PNG.format(n=int(n))
    try:
        if open(salida + ".huella", encoding="utf-8").read().strip() == huella:
            return salida
    except OSError:
        pass
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    tmp = os.path.join(rutas.TEMPORAL, f"portada-{slug}.json")
    json.dump(props, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Portada-Reel-1",
                        salida, f"--props={tmp}", f"--frame={CUADRO}", "--gl=angle"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=os.name == "nt")
    if r.returncode or not os.path.exists(salida):
        _di(f"{slug}: no se pudo pintar la portada — {(r.stderr or '')[-300:]}")
        return None
    open(salida + ".huella", "w", encoding="utf-8").write(huella)
    return salida


def _criterio():
    """El trozo del prompt del diseñador que trata la portada, tal cual."""
    lineas, dentro = [], False
    for ln in open(PROMPT, encoding="utf-8").read().splitlines():
        if ln.startswith("- `portada`"):
            dentro = True
        elif dentro and (ln.startswith("- `") or ln.startswith("## ")):
            break
        if dentro:
            lineas.append(ln)
    return chr(10).join(lineas).strip()


def pedido(n):
    """El encargo de sólo la portada, para una pieza ya diseñada que no la tiene.

    Mismo buzón y misma respuesta que el diseño: lo contesta el diseñador con
    el criterio de su prompt, lo que dice la pieza y sus hojas de contacto.
    """
    import fotogramas
    from dominio.pieza import Pieza

    slug = f"reel-{int(n):02d}"
    fotos, _ = fotogramas.sacar(int(n))
    dicho = Pieza(int(n)).dicho or {}
    ruta = os.path.join(BUZON, f"{slug}.portada.pedido.json")
    os.makedirs(BUZON, exist_ok=True)
    json.dump({
        "paso": "disenar", "slug": slug, "encargo": "portada",
        "criterios": _criterio(),
        "dice_la_pieza": {f"e{b}": t for b, t in sorted(
            dicho.items(), key=lambda x: (x[0] is None, x[0] or 0))},
        "mira_estos_fotogramas": [
            {"escena": e["escena"], "etapa": e["etapa"], **t}
            for e in (fotos or []) for t in e["mira"]],
        "formato_respuesta": {
            "titulo": "texto de la caja, MAYÚSCULAS, 2-10 palabras",
            "subtitulo": "la segunda línea, o null",
            "en": "el segundo del montaje del que se saca el fotograma",
            "forma": "velo | bloque", "por_que": "por qué ésta"},
        "escribe_en": os.path.join(BUZON, f"{slug}.portada.json").replace("\\", "/"),
    }, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return ruta


def recoger(n):
    """Si el diseñador contestó el encargo, se declara. Devuelve la línea o `None`."""
    slug = f"reel-{int(n):02d}"
    ruta = os.path.join(BUZON, f"{slug}.portada.json")
    if not os.path.exists(ruta):
        return None
    return guardar(slug, {"portada": json.load(open(ruta, encoding="utf-8"))})
