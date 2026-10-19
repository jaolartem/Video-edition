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
