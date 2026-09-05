"""La escalera de precios: se declara entera, y no puede haber dos.

Jaime la fijó así: *«otro tiket, deja el precio de 20 dólares hasta el 9 de
septiembre»* y *«el bloque de 30 corrió hasta el 15 y el resto pues de 40»*.

## Por qué hace falta un paso, y no bastaba la tabla

La tabla `precio` admitía filas sueltas, así que cambiar la escalera era añadir
las nuevas — y las viejas se quedaban. Medido el 4 de septiembre: **seis filas y
dos escaleras a la vez**, la suya y la anterior ($20 hasta el 4, $30 hasta el
11). `precioVigente()` las leía todas y componía

    «$20 hasta el 4 sep · luego $20 y $30 y $30 y $40»

que salió **en pantalla, en las siete piezas**: una fecha vencida ese mismo día y
una escalera que no existe. Y encima los tramos de $30 y $40 se pisaban cuatro
días — el de 40 empezaba el 12 y el de 30 acababa el 15.

Es cumplimiento, no maquetación: **el precio es lo único de la pieza que el
espectador va a pagar**. Y es la avería de siempre por la puerta del dinero —
una decisión guardada dos veces, y el que lee se queda con la mezcla.

## Lo que impide que vuelva

Declararla **entera**: lo que se declara sustituye a lo que había, así que no se
puede acumular una escalera encima de otra. Y antes de guardar se comprueba que
los tramos no se pisen ni dejen hueco, porque un solapamiento no da error — da
un precio.

    python scripts/precio.py                       # la escalera de hoy
    python scripts/precio.py --declarar 20:2026-08-29:2026-09-09 \\
                             30:2026-09-10:2026-09-15 \\
                             40:2026-09-16:2026-09-21T11:30
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basedatos  # noqa: E402

BASE = "ads/decisiones.db"


def _con():
    cx = basedatos.abrir(BASE)
    cx.row_factory = sqlite3.Row
    return cx


def escalera():
    """Los tramos vivos, en orden. El ancla —lo ya pasado— va aparte."""
    with _con() as cx:
        return [dict(r) for r in cx.execute(
            "select * from precio where ancla = 0 order by desde")]


def revisar(tramos):
    """Qué está mal en una escalera. Lista vacía = se puede guardar."""
    mal = []
    for i, t in enumerate(tramos):
        if not t["desde"] or not t["hasta"]:
            mal.append(f"${t['importe']}: le falta desde o hasta")
            continue
        if t["hasta"][:10] < t["desde"][:10]:
            mal.append(f"${t['importe']}: acaba antes de empezar")
        if i:
            a = tramos[i - 1]
            # **Se pisan o dejan hueco: las dos cosas dan un precio equivocado**
            # y ninguna da error. El solape hace que dos tramos valgan a la vez
            # —y gana el que la consulta mire primero—; el hueco deja un día sin
            # precio, y ahí la pieza dice el que le quede más a mano.
            if t["desde"][:10] <= a["hasta"][:10]:
                mal.append(f"${a['importe']} y ${t['importe']} se pisan:"
                           f" {a['hasta'][:10]} y {t['desde'][:10]}")
            elif t["desde"][:10] > _dia_siguiente(a["hasta"][:10]):
                mal.append(f"entre ${a['importe']} y ${t['importe']} queda un"
                           f" hueco sin precio desde {a['hasta'][:10]}")
    return mal


def _dia_siguiente(iso):
    import datetime

    d = datetime.date.fromisoformat(iso) + datetime.timedelta(days=1)
    return d.isoformat()


def declarar(tramos):
    """Sustituye la escalera entera. Devuelve lo que impidió guardarla."""
    mal = revisar(tramos)
    if mal:
        return mal
    with _con() as cx:
        # **Se borra lo vivo y se escribe lo declarado, en una transacción.**
        # Añadir sin retirar es exactamente cómo llegaron a convivir dos
        # escaleras; el ancla no se toca porque es historia, no oferta.
        cx.execute("delete from precio where ancla = 0")
        cx.executemany(
            "insert into precio (importe, desde, hasta, ancla, nota)"
            " values (?, ?, ?, 0, ?)",
            [(t["importe"], t["desde"], t["hasta"], t.get("nota"))
             for t in tramos])
        cx.commit()
    return []


def _lee(txt):
    importe, desde, hasta = txt.split(":", 2)
    return {"importe": int(importe), "desde": desde, "hasta": hasta}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--declarar", nargs="+", metavar="IMPORTE:DESDE:HASTA")
    a = ap.parse_args()
    if a.declarar:
        mal = declarar([_lee(x) for x in a.declarar])
        for m in mal:
            print(f"  · {m}")
        if mal:
            print("\nprecio: NO se guardo. Una escalera que se pisa da un"
                  " precio equivocado en pantalla, y eso es cumplimiento.")
            return 1
    hoy = escalera()
    for t in hoy:
        print(f"  ${t['importe']:>3}  {t['desde'][:10]} -> {t['hasta'][:10]}"
              + (f"  ({t['nota']})" if t["nota"] else ""))
    mal = revisar(hoy)
    for m in mal:
        print(f"  · {m}")
    print(f"\nprecio: {len(hoy)} tramo(s), "
          + ("todos encadenados." if not mal else f"{len(mal)} problema(s)."))
    return 1 if mal else 0


if __name__ == "__main__":
    raise SystemExit(main())
