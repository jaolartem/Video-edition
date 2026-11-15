"""**La placa de la pieza, declarada por el diseñador cuando no la hay** (C-702).

Jaime, 6-9-2026: *«es un FONDO de tablero por reel»*, y vive en
`ads/fondos.json → pieza`, con su `por_que`. Las piezas de agosto la tienen;
`reel-23` entró sin ella y nadie la escribía: los tableros salían sobre negro,
quietos —4,3 s medidos en e5—, y la única salida era editar la declaración a
mano. Elegir la placa es criterio estético, o sea del diseñador: el inventario
ya viaja en su pedido (`caja.placas_que_existen`). Aquí se recoge lo que
declara, **una vez**: declarada, no se cambia desde una respuesta — eso es lo
que el 6-9 costó tres placas en una pieza.
"""
import json
import os

FONDOS = os.path.join("ads", "fondos.json")


def guardar(slug, respuesta):
    """Escribe `pieza.placa` en `ads/fondos.json` si la pieza no tenía. Dice qué pasó."""
    pieza = respuesta.get("pieza") if isinstance(respuesta, dict) else None
    dicho = pieza.get("placa") if isinstance(pieza, dict) else None
    if not isinstance(dicho, dict) or not dicho.get("placa"):
        return None
    try:
        fondos = json.load(open(FONDOS, encoding="utf-8"))
    except (OSError, ValueError):
        return _di(f"{slug}: no se pudo leer {FONDOS} — la placa no se escribe")
    nombre = str(dicho["placa"]).strip()
    if nombre not in (fondos.get("placas") or {}):
        return _di(f"{slug}: la placa «{nombre}» no está en el inventario — no se escribe")
    ya = (fondos.get("pieza") or {}).get(slug)
    if ya:
        if ya.get("placa") != nombre:
            return _di(f"{slug}: ya tiene placa «{ya.get('placa')}» y la respuesta pide"
                       f" «{nombre}»: una por pieza, no se cambia desde aquí")
        return None
    fondos.setdefault("pieza", {})[slug] = {
        "placa": nombre, "por_que": str(dicho.get("por_que") or "").strip()}
    with open(FONDOS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(fondos, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return _di(f"{slug}: placa declarada — «{nombre}»")


def de_la_pieza(slug, respuesta):
    """Lo que la respuesta declara DE LA PIEZA, no de una etapa: portada y placa."""
    from .portada import guardar as _portada

    _portada(slug, respuesta)
    guardar(slug, respuesta)


def _di(linea):
    print(f"    {linea}")
    return linea
