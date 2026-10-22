"""Sube a Drive lo aprobado, y sólo lo aprobado.

Regla de Jaime: *«los fragmentos aprobados los subimos a la carpeta de Drive en
el PC `G:\\My Drive\\Creación de videos\\Segmentos` en su propia carpeta, y los
finales en `…\\FINALES`, pero sólo los que ya están a punto, mejor dicho listos
para salir»*.

Es el último peldaño del embudo, y su valor está en lo que **no** sube. Drive
sincroniza: lo que se copia ahí sale de esta máquina y puede acabar publicado.
Así que la puerta es explícita y no se puede saltar sin decirlo:

- Un **fragmento** sube si su `paso` está en `aprobado` y tiene fichero.
- Una **pieza** sube si está entregada y `verificacion.mjs` no le deja nada
  pendiente que impida publicarla.

Nada de «lo subo por si acaso». Si no hay nada aprobado, no sube nada y lo dice
—que es lo que pasa la primera vez, y es la prueba de que la puerta existe.

Cada fragmento va **en su propia carpeta**, con un `identidad.json` al lado: de
qué cinta sale, qué rango, qué etapa del frame cumple y qué esperaba el libreto
ahí. Una carpeta que no se explica sola es una carpeta que dentro de un mes no
se sabe qué es.

    python scripts/publicar.py --ver          # que subiria, sin tocar nada
    python scripts/publicar.py --fragmentos   # sube los aprobados
    python scripts/publicar.py --finales      # sube las piezas listas
    python scripts/publicar.py --finales 18 19   # solo esas
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import basedatos
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
import rutas  # noqa: E402

BASE = os.path.join("ads", "decisiones.db")

#: Cómo escribe `puerta.mjs` el motivo de una cifra pintada sin fila (C-616).
SIN_FILA = "la etapa no declara esa cifra"


# El apodo lo hace `dominio.texto`, que es el dueño de cómo se normaliza un
# texto en este proyecto. Estaba copiado aquí, en `publicar.py` y en
# `revisar.py`, las tres veces igual.
from dominio.texto import apodo  # noqa: E402


def aprobados(con):
    """Fragmentos en fase `aprobado` y con fichero. Ni uno mas."""
    return con.execute("""
        select f.id, t.nombre, f.desde, f.hasta, p.fichero,
               v.slug, e.orden, ec.nombre, l.texto,
               (select group_concat(u.texto, ' ') from fragmento_unidad fu
                 join unidad u on u.id = fu.unidad_id
                where fu.fragmento_id = f.id)
          from fragmento f
          join paso p on p.fragmento_id = f.id
          join fase fa on fa.id = p.fase_id
          join toma t on t.id = f.toma_id
          left join eleccion el on el.fragmento_id = f.id
          left join etapa e on e.id = el.etapa_id
          left join video v on v.id = e.video_id
          left join etapa_canonica ec
                 on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
          left join libreto l on l.video_id = v.id and l.orden = e.orden
         where fa.nombre = 'aprobado' and p.fichero is not null
         order by v.slug, e.orden
    """).fetchall()


def listas(con):
    """Piezas entregadas que **pasan el mismo criterio con que se montan**.

    La primera version miraba solo si la verificacion traia un 🛑, y dejaba
    pasar el reel 2 — al que el build le para por faltarle la etapa 10, que es
    obligatoria. Una puerta de publicar mas floja que la de montar no es una
    puerta: es una forma de saltarsela.

    Asi que el criterio es el mismo y sale del mismo sitio: **la unidad de
    analisis es el segmento**. No sale una pieza a la que le falte una etapa
    obligatoria, ni una cuyos segmentos no encajen en lo que el libreto espera
    ahi (C-61). La cifra no decide (falso positivo medido) y la duracion tampoco
    —eso lo decide Jaime al final, con el reel montado—.
    """
    ENCAJE = 0.14
    out = []
    dest = rutas.DESTINO
    for n in rutas.piezas():
        slug, pieza = f"reel-{n:02d}", f"reel-R{n}"
        mp4 = os.path.join(dest, "entrega", f"{pieza}.mp4")
        ver = os.path.join(dest, f"Reel-R{n}.verification.md")
        if not os.path.exists(mp4):
            continue
        pega = []
        edl_p = os.path.join("ads", slug, "edl-sell.json")
        if not os.path.exists(edl_p):
            pega.append("sin EDL")
        else:
            edl = json.load(open(edl_p, encoding="utf-8"))
            # Un tablero ejecuta la etapa: sin_toma con `copy` es una lectura
            # plana trasladada a proposito, no un hueco.
            # **Y lo que el aprobo no se vuelve a discutir aqui.** Regla suya,
            # 1-9-2026: *«lo que ya se aprobo no se vuelve a discutir: se revisa
            # que este como se dijo»*. Las dos comprobaciones de abajo —etapa
            # sin material y segmentos que no encajan— son criterio editorial:
            # existen para que nadie publique una pieza que nadie miro. Cuando
            # el ya la miro y la aprobo, seguir oponiendolas es pedirle una
            # segunda opinion sobre su propia decision.
            #
            # Lo que NO cede es lo mecanico —sin EDL, EDL del proceso anterior,
            # entrega anterior al EDL, verificacion anterior a la entrega—:
            # eso no es opinion, es «¿esta como se dijo?», y una aprobacion de
            # ayer no responde por un fichero que cambio despues.
            #
            # Medido el 14-9-2026: reel-13 aprobada por el, con su musica y su
            # voz limpia, y la puerta la paraba por la etapa 4 —cobertura 0,333
            # sobre 0,889—, que es exactamente lo que el habia decidido dejar
            # como esta. C-499.
            from dominio.segmento import aprobada as _aprobada

            suya = _aprobada(slug)
            faltan = [] if suya else [h for h in edl.get("sin_toma", [])
                                      if h.get("obligatorio") and not h.get("copy")]
            if faltan:
                pega.append("etapa obligatoria sin material: " +
                            ", ".join(f"{h['beat']} ({h['etapa']})" for h in faltan))
            # Mismo criterio que la puerta del montaje: encaja si trae el
            # dato declarado o si se acerca a lo alcanzable en su etapa. La
            # cobertura absoluta medía literalidad contra el libreto, no si el
            # segmento cumple.
            flojos = [] if suya else [
                d["beat"] for d in edl.get("detalle", [])
                if not (d.get("dice")
                        or (d.get("cobertura") or 0)
                        >= max(ENCAJE, 0.5 * (d.get("cubre_max") or 0)))]
            if flojos:
                pega.append(f"segmentos que no encajan: {flojos}")
            # **Un EDL del proceso viejo no puede pasar por la puerta nueva.**
            # R4, R5 y R6 se montaron antes de `seleccionar.py`: su `cobertura`
            # existe pero la calculo otro criterio, asi que el numero se lee
            # igual y no significa lo mismo. Comparar dos escalas distintas es
            # el defecto que este proyecto ya tiene tres veces (19, 28, 47).
            if "seleccionar.py" not in ((edl.get("revision") or {}).get("montaje") or ""):
                pega.append("EDL del proceso anterior: hay que volver a repartir")
            # (Antes aqui se paraba una pieza con material de varias cintas.
            # Ya no: la escena declara su fuente, el ancla se mide por fuente y
            # cada escena abre su bruto. Se quita en vez de dejarla avisando de
            # algo que ya no es cierto — un aviso falso gasta la atencion que
            # hace falta para el que si vale.)
            # Mas viejo que su EDL: se entrego antes del ultimo reparto.
            if os.path.getmtime(edl_p) > os.path.getmtime(mp4):
                pega.append("la entrega es anterior al EDL: hay que remontar")
        if not os.path.exists(ver):
            pega.append("sin fichero de verificacion")
        elif os.path.getmtime(ver) < os.path.getmtime(mp4):
            pega.append("la verificacion es anterior a la entrega (C-60)")
        out.append((pieza, mp4, ver, pega))
    return out


def _verificacion_al_dia(con):
    """Rehace la verificación si alguna entrega es más nueva que la suya (C-650).

    `montar.sh` la deja al runner del lote, y la línea de hoy no pasa por él. Y
    el masterizado reescribe la entrega con la voz limpia, así que R18 y R22,
    aprobadas el 21-10, se quedaron en «la verificación es anterior a la
    entrega» en cada vuelta. La verificación es un documento derivado: si está
    vieja se vuelve a generar, no se para la pieza.
    """
    import subprocess

    if any(any("verificacion es anterior" in x for x in p) for *_, p in listas(con)):
        subprocess.run(["node", os.path.join("scripts", "verificacion.mjs")], check=False)


def anotar(slug, destino, con=None):
    """**Queda escrito que esa pieza salió, y adónde.**

    La tabla `publicacion` estaba declarada desde el principio y **con cero
    filas**: nadie la escribía. `donde.py` tiene una columna que la lee, así que
    preguntaba «¿se publicó?» a un sitio que no podía contestar nunca — un
    consumidor sin productor, que es la avería de C-207 con el signo cambiado.

    Y se nota cuando algo sale por fuera: R-13 se publicó el 15-9 y la línea
    seguía diciendo `aprobado`. Jaime: *«pues ya salió y ya lo publiqué»*. Una
    pieza que está en la calle y que el sistema cree parada es exactamente el
    estado que este proyecto existe para no perder.

    Devuelve la versión anotada, o `None` si la pieza no tiene ninguna.
    """
    cerrar = con is None
    con = con or basedatos.abrir(BASE)
    v = con.execute(
        "select ve.id from version ve join video vi on vi.id = ve.video_id"
        " where vi.slug = ? order by ve.n desc limit 1", (slug,)).fetchone()
    if v:
        con.execute(
            "insert or replace into publicacion (version_id, destino, fecha)"
            " values (?,?,?)",
            (v[0], destino,
             datetime.datetime.now().isoformat(timespec="seconds")))
        con.commit()
    if cerrar:
        con.close()
    return v[0] if v else None


def subir(origen, destino, seco):
    if seco:
        return False
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copy2(origen, destino)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragmentos", action="store_true")
    ap.add_argument("--finales", action="store_true")
    # **Lo que sale por fuera de la linea tambien se anota.** Jaime publica a
    # mano cuando hace falta —R-13, el 15-9— y sin esto la pieza se queda en
    # `aprobado` para siempre: en la calle y el sistema creyendola parada.
    ap.add_argument("--ya-esta", nargs="+", metavar="PIEZA", dest="ya_esta",
                    help="anota que esas piezas ya salieron, sin subir nada")
    ap.add_argument("--en", default="a mano, destino sin declarar",
                    metavar="DONDE", help="adonde salieron")
    ap.add_argument("--revision", action="store_true",
                    help="sube LAS SEIS a FINALES/_revision para verlas montadas."
                         " No es publicar: es enseñar")
    ap.add_argument("--ver", action="store_true", help="dice que haria y no toca nada")
    # **Las piezas se nombran, como las nombra el camino.** `fase.CICLO` llama
    # `publicar.py --finales {n}` y esto no aceptaba el numero: el 20-10-2026
    # el disparador lo intento 362 veces por pieza con «unrecognized arguments»
    # y R18-R22 no salieron. Y sin nombrarlas, `--finales` sube todo lo listo
    # de una vez, cuando Jaime pidio *«sube las nuevas»* y solo esas (C-615).
    ap.add_argument("piezas", nargs="*", type=int,
                    help="solo esas piezas (18 19 …); sin numeros, todas")
    ap.add_argument("--indice", action="store_true",
                    help="rehace FINALES/INDICE.md sin subir nada")
    a = ap.parse_args()
    if a.indice:
        import indice

        print(indice.escribir(rutas.FUENTES["finales"]))
        return
    seco = a.ver or not (a.fragmentos or a.finales or a.revision)

    con = basedatos.abrir(BASE)
    con.execute("PRAGMA foreign_keys = ON")

    if a.ya_esta:
        from dominio import fase as _fa

        fid = con.execute("select id from fase where nombre = 'publicado'"
                          ).fetchone()
        for x in a.ya_esta:
            n = int("".join(c for c in str(x) if c.isdigit()))
            slug = f"reel-{n:02d}"
            v = anotar(slug, a.en, con)
            vid = con.execute("select id from video where slug = ?",
                              (slug,)).fetchone()
            # La etiqueta tambien, que es lo que mira la linea para no volver
            # a trabajar sobre ella.
            if fid and vid:
                _fa.anotar(vid[0], fid[0], f"salio {a.en}"[:400])
            print(f"{slug}: " + (f"anotada como publicada (v{v}) en {a.en}"
                                 if v else "no tiene version que anotar"))
        con.close()
        return

    # **Aquí es donde el motivo pesa, y no antes.**
    #
    # Regla de Jaime: *«pon el bloqueo en el paso final, no acá»*, después de
    # que el montaje se negara a renderizarle reel-01 y él pidiera verla igual:
    # *«el render se necesita, quiero ver lo que va a salir; no importan
    # restricciones, quiero aprobarlo»*.
    #
    # El reparto queda así, y tiene sentido en las dos direcciones: **ver una
    # pieza con un defecto cuesta dos minutos suyos; publicarla cuesta la
    # campaña.** Así que el montaje entrega siempre —con los motivos escritos al
    # lado— y quien para es esto.
    if a.finales and not a.ver:
        import json as _j

        try:
            spec = _j.load(open("src/reels.json", encoding="utf-8"))
        except OSError:
            spec = []
        # **Para la pieza con motivo, no a sus vecinas.** Con todas, una sola
        # pieza con motivo dejaba el lote entero en tierra —el 20-10, R2, que
        # ni estaba en la lista, paraba a R18—. Con piezas nombradas pesa el
        # motivo de esas; sin nombrarlas, el de todas, como siempre (C-615).
        pedidas = {f"Reel-R{n}" for n in a.piezas}
        # **La cifra sin fila se pregunta ahora, no se lee del montaje.** Ese
        # motivo lo escribió `puerta.mjs` al montar, y después corre
        # `respaldado`, que la verifica en red y le pone su fila: leído tal
        # cual, paraba lo ya resuelto. Jaime, con R20 parada por un estudio de
        # JAMA citado en su propio tablero: *«si puedes verificar en red, ¿por
        # qué paras producción?»* (C-616).
        import fuentes

        for r in spec:
            if (pedidas and r["id"] not in pedidas) or not any(
                    SIN_FILA in m for m in r.get("bloqueado") or []):
                continue
            r["bloqueado"] = [m for m in r["bloqueado"] if SIN_FILA not in m] + [
                f"{r['id']}: el beat {b} rotula «{c}» y sigue sin fila en `dato`"
                f" después del respaldo"
                for b, cs in fuentes.pintadas(
                    str(r.get("video") or "").removesuffix(".mp4")).items()
                for c in cs]
        con_motivo = [(r["id"], r.get("bloqueado") or []) for r in spec
                      if r.get("bloqueado")
                      and (not pedidas or r["id"] in pedidas)]
        if con_motivo:
            print(f"NO SE PUBLICA — {len(con_motivo)} pieza(s) con motivos"
                  f" abiertos:")
            for pid, ms in con_motivo:
                print(f"  · {pid}")
                for m in ms:
                    print(f"      {m}")
            print("\n  Verlas y aprobarlas, sí. Soltarlas al mundo, no.")
            raise SystemExit(1)

    if a.revision:
        # **Ver montado no es publicar.** Jaime: *«quiero verlos todos montados;
        # los segmentos sirven como banco de segmentos pero no como videos
        # finales»*. Asi que van los seis, tambien los que no pasan la puerta —
        # con su motivo al lado— y a una carpeta aparte, porque `FINALES` es
        # solo para lo que esta a punto y eso no cambia.
        # **Y se queda en F:.** Jaime, 18-10-2026: *«sigue trabajando en F y
        # los finales ya revisados, no para revision sino los definitivos»*. A
        # Drive (I:) va solo lo definitivo; ver montado es trabajo (C-553).
        raiz = rutas.salida("revision")
        os.makedirs(raiz, exist_ok=True)
        print(f"REVISION -> {raiz}")
        for pieza, mp4, ver, pega in listas(con):
            mb = os.path.getsize(mp4) / 1e6
            # **Y lo que subio a Jaime y sigue abierto.** Un `sube` no para el
            # render —se mira mejor con la pieza delante— pero si para esto:
            # soltar al mundo una pieza con una cifra sin fuente o un dato que
            # contradice al mensaje es exactamente lo que el piso prohibe.
            try:
                import sqlite3 as _s

                _c = _s.connect(BASE)
                abiertos = _c.execute(
                    "select count(*) from revision where video_slug = ?"
                    " and estado = 'sube'", (pieza,)).fetchone()[0]
                _c.close()
            except Exception:                      # noqa: BLE001
                abiertos = 0
            if abiertos:
                pega.append(f"{abiertos} aviso(s) sin resolver que subieron a"
                            f" Jaime — mira `revision.py --ver`")
            estado = "listo" if not pega else "NO pasa: " + "; ".join(pega)
            print(f"  {pieza}  {mb:>4.0f} MB  {estado}")
            shutil.copy2(mp4, os.path.join(raiz, f"{pieza}.mp4"))
            if os.path.exists(ver):
                shutil.copy2(ver, os.path.join(raiz, f"{pieza}.verificacion.md"))
            registro.nota("publicar", "pieza a revision", detalle=pieza)
        con.close()
        return

    if a.fragmentos or seco:
        filas = aprobados(con)
        raiz = rutas.FUENTES["segmentos"]
        print(f"SEGMENTOS -> {raiz}")
        if not filas:
            total = con.execute("select count(*) from fragmento").fetchone()[0]
            enpaso = con.execute("select count(*) from paso").fetchone()[0]
            print(f"  nada que subir: 0 de {total} fragmentos estan aprobados"
                  f" ({enpaso} tienen fase asignada).")
            print("  La puerta es esa a proposito: Drive sincroniza, y lo que se"
                  " copia ahi sale de esta maquina.")
        for (fid, toma, d, h, fich, slug, orden, etapa, libreto, dicho) in filas:
            nombre = f"{slug or 'suelto'}-{orden or 0:02d}-{apodo(etapa)}"
            carpeta = os.path.join(raiz, nombre)
            print(f"  {nombre}  ({d:.2f}-{h:.2f} de {toma})")
            if not seco:
                os.makedirs(carpeta, exist_ok=True)
                shutil.copy2(fich, os.path.join(carpeta, nombre + ".mp4"))
                json.dump({
                    "fragmento_id": fid, "cinta": toma,
                    "desde": d, "hasta": h,
                    "video": slug, "etapa_orden": orden, "etapa": etapa,
                    "esperaba_el_libreto": libreto,
                    "lo_que_dice": (dicho or "").strip(),
                    "subido": datetime.datetime.now().isoformat(timespec="seconds"),
                }, open(os.path.join(carpeta, "identidad.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
                registro.nota("publicar", "fragmento subido", detalle=nombre)

    if a.finales or seco:
        raiz = rutas.FUENTES["finales"]
        print(f"FINALES -> {raiz}")
        hay = False
        salieron = set()
        if not seco:
            _verificacion_al_dia(con)
        from dominio.segmento import aprobada as _aprobada
        for pieza, mp4, ver, pega in listas(con):
            if a.piezas and int(pieza.split("R")[-1]) not in a.piezas:
                continue
            # **Solo lo que el aprobo.** Pasar la puerta no es estar revisado:
            # a FINALES va lo definitivo, ya visto y firmado por Jaime (C-553).
            if not _aprobada(f"reel-{int(pieza.split('R')[-1]):02d}"):
                pega = pega + ["no esta aprobada por Jaime"]
            # **Y no sale sin su portada** (C-618). Jaime: *«eso debe salir
            # siempre con todos los videos»*. La pinta `servicios/portada.py`
            # con lo que declaró el diseñador; en seco sólo se mira si la hay.
            from servicios import portada as _po

            num = int(pieza.split("R")[-1])
            png = None
            if not seco:
                _po.recoger(num)
            if not _po.declarada(f"reel-{num:02d}"):
                # El encargo sale de aquí y no de `disenar`: al diseñar todavía
                # no hay corte del que sacar el fotograma. Va a su buzón y lo
                # contesta el diseñador como cualquier otro pedido.
                pega = pega + ["sin portada" + ("" if seco else
                               f": encargada al diseñador -> {_po.pedido(num)}")]
            elif not seco:
                png = _po.png(num)
                if not png:
                    pega = pega + ["la portada no se pudo pintar"]
            if pega:
                print(f"  {pieza}: NO sale — {'; '.join(pega)}")
                continue
            hay = True
            salieron.add(int(pieza.split("R")[-1]))
            mb = os.path.getsize(mp4) / 1e6
            print(f"  {pieza}  {mb:.0f} MB")
            if not seco:
                subir(mp4, os.path.join(raiz, f"{pieza}.mp4"), seco)
                # La verificación no va suelta: va dentro del índice (C-623).
                subir(png, os.path.join(raiz, f"{pieza}-portada.png"), seco)
                registro.nota("publicar", "pieza subida", detalle=pieza)
                # Y en la base, no solo en el log: el registro se lee con los
                # ojos y la tabla la lee `donde.py`.
                anotar(pieza.lower().replace("reel-r", "reel-").replace(
                    "reel-", "reel-").strip(), raiz, con)
        if not hay:
            print("  nada listo para salir.")
        # **Y el índice de la carpeta, cada vez que entra algo.** Jaime: *«un
        # descriptor de qué video es cada uno, con el script final, todo en un
        # archivo md»*. Se rehace con lo que hay en FINALES (C-617).
        if hay and not seco:
            import indice

            print(f"  indice -> {indice.escribir(raiz)}")
        # **Y la pieza pedida que no sale no sale con exito.** El camino lee el
        # codigo de salida para pasarla a `publicado`: un «NO sale» con 0 la
        # daria por publicada sin estar en Drive (C-615).
        quedan = sorted(set(a.piezas) - salieron)
        if quedan and not seco:
            con.close()
            raise SystemExit(f"\nNO salieron: {', '.join(f'R{n}' for n in quedan)}")

    if seco:
        print("\n(en seco: no se ha copiado nada. Anade --fragmentos o --finales)")
    con.close()


if __name__ == "__main__":
    main()
