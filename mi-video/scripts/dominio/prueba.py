"""La prueba de una declaración: el texto que sonaba en su tramo al declararla.

**Por qué es una responsabilidad propia.** `corte_fijo` guarda con cada tramo
declarado una huella del texto que se oía dentro (C-149), y `fijar` aparta la
declaración cuando ahí «ahora se dice otra cosa». Pero eso junta dos cosas
distintas: que cambie lo que se **dice** y que cambie lo que el **transcript**
cree que se dice. Rehacer o afinar una cinta cambia lo segundo sin tocar la
grabación, y cada vez la decisión iba al compositor para volver con los mismos
bordes: #504 a #508 y #791 en reel-18, «la decisión no cambió; cambió la
segmentación del afinado».

Se reestampa **al reescribir el transcript**, que es el único momento en que el
texto viejo todavía existe: la huella son doce caracteres y no dice qué había.

La regla es estrecha a propósito: los bordes no se tocan, la prueba casaba con
el texto viejo y el texto nuevo **contiene** al viejo. Lo demás —palabras que
se van, una frase que era otra— sigue yendo al compositor, que es quien decide.
"""
from __future__ import annotations

from .texto import huella_de_texto
from .texto import palabras as _palabras
from .tramo import Tramo


def contiene(nuevo: str, viejo: str) -> bool:
    """¿Están las palabras del viejo, seguidas y en orden, dentro del nuevo?"""
    v, n = _palabras(viejo), _palabras(nuevo)
    return bool(v) and any(n[i:i + len(v)] == v
                           for i in range(len(n) - len(v) + 1))


def reestampables(cinta, filas, viejas, nuevas) -> list:
    """Las declaraciones cuya prueba pasa al texto nuevo, sin leer ni escribir.

    `filas` son de `corte_fijo` (`desde`, `hasta`, `huella`); `viejas` y
    `nuevas`, las `Palabra` de la cinta antes y después. Devuelve
    `(fila, huella_nueva, texto_viejo, texto_nuevo)`.
    """
    out = []
    for f in filas:
        t = Tramo(float(f["desde"]), float(f["hasta"]), cinta)
        viejo = t.texto_de(viejas)
        # Si ya no casaba con el texto viejo, no es de este cambio: lo dirá
        # `fijar`, como hasta ahora.
        if not f["huella"] or huella_de_texto(viejo) != f["huella"]:
            continue
        nuevo = t.texto_de(nuevas)
        h = huella_de_texto(nuevo)
        if h and h != f["huella"] and contiene(nuevo, viejo):
            out.append((f, h, viejo, nuevo))
    return out


def antes(cinta) -> list:
    """Las palabras de la cinta **antes** de reescribirla. Vacío si no había."""
    from .cinta import Cinta

    c = Cinta(cinta)
    try:
        return c.palabras() if c.existe() else []
    except (OSError, ValueError):
        return []


def reestampar(cinta, viejas) -> int:
    """Tras reescribir el transcript de `cinta`, pasa las pruebas que lo admiten."""
    import basedatos
    import registro

    from .cinta import Cinta

    if not viejas:
        return 0
    try:
        nuevas = Cinta(cinta).palabras()
    except (OSError, ValueError):
        return 0
    cx = basedatos.abrir()
    filas = [dict(zip(("id", "desde", "hasta", "huella"), r)) for r in cx.execute(
        "select id, desde, hasta, huella from corte_fijo where toma = ?", (cinta,))]
    hechas = reestampables(cinta, filas, viejas, nuevas)
    for f, h, viejo, nuevo in hechas:
        cx.execute("update corte_fijo set huella = ? where id = ?", (h, f["id"]))
        registro.nota("fijar", "prueba reestampada", toma=cinta,
                      detalle=f"{f['desde']:.2f}-{f['hasta']:.2f}: «{viejo[:60]}»"
                              f" -> «{nuevo[:60]}»")
    if hechas:
        print(f"  {cinta}: {len(hechas)} prueba(s) de corte_fijo pasadas al"
              f" texto nuevo; las demas, si no casan, las aparta `fijar`")
    return len(hechas)
