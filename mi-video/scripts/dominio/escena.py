"""La descripción de una etapa: qué se guarda, y **quién manda sobre cada campo**.

`escena_desc` la escriben dos pasos distintos. `descrito` (7) planea la escena
—qué pasa, qué emoción, qué encargo— y `disenado` (7.5) contesta ese encargo con
el tablero. Son dos oficios: pedirle al diseñador que reenvíe la descripción
entera para cambiar un campo es invitarle a reescribir lo que no le toca.

**Y la regla de quién manda vivía dentro de un `INSERT`.** Un `UPDATE` que decía
`tablero=excluded.tablero` hacía que re-describir una etapa —lo normal, porque el
compositor no diseña— dejara el tablero en NULL: **borraba en silencio lo que el
diseñador había montado**, y en la siguiente corrida esa etapa salía sin nada. Se
arregló con un `coalesce` escrito a mano campo por campo, o sea con una regla de
propiedad expresada como cadena SQL: quien añada una columna mañana tiene que
acordarse de en cuál de las dos mitades va, y nada se lo dice.

Aquí se declara: dos tuplas, y la sentencia se deriva de ellas. Añadir un campo
es ponerlo en la lista que le toca, que es la pregunta que hay que contestar de
todas formas.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

from .pieza import Pieza  # noqa: E402

TABLA = "escena_desc"
#: Lo que identifica la fila. No se actualiza nunca: es la fila.
CLAVE = ("video_slug", "etapa_orden")

#: **Los campos de quien compone.** Una descripción nueva manda sobre ellos: si
#: los deja vacíos es porque decidió vaciarlos.
MANDA_QUIEN_COMPONE = (
    "que_pasa", "emocion", "grafico", "trato", "trato_porque", "prioridad",
    "integridad", "remedio", "corrige_dice", "corrige_es", "sobre_texto",
    "quien", "fecha",
    # La propuesta de tablero: es suya, y por eso se pisa cuando redescribe.
    "tablero_propuesto",
)

#: **Los campos que otro paso llena, y que el silencio no borra.** `tablero` lo
#: monta el diseño; `componente`, `color`, `sonido` y `plano` pueden venir de una
#: corrida anterior. Que una descripción no los mencione significa «no tengo nada
#: que decir de esto», nunca «bórralo». Vaciarlos a propósito se hace desde el
#: paso que es su dueño.
NO_SE_BORRAN = ("tablero", "componente", "color", "sonido", "plano")

COLUMNAS = CLAVE + MANDA_QUIEN_COMPONE + NO_SE_BORRAN



def _dibujables():
    """Las formas que `src/components/Tablero.tsx` despacha. Sin copiar la lista.

    Es la unica autoridad: si el render no tiene una rama para ese `kind`, la
    forma no se dibuja por mucho que tres ficheros la nombren.
    """
    import re

    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        with open(os.path.join(raiz, "src", "components", "Tablero.tsx"),
                  encoding="utf-8") as h:
            return set(re.findall(r'cue\.kind === "([^"]+)"', h.read()))
    except OSError:
        return set()


class EscenaInvalida(ValueError):
    """Lo que llega no describe una escena. Se dice, no se guarda a medias."""


def _upsert() -> str:
    """La sentencia, derivada de quién manda sobre cada campo."""
    puesta = ", ".join(
        [f"{c}=excluded.{c}" for c in MANDA_QUIEN_COMPONE]
        + [f"{c}=coalesce(excluded.{c}, {TABLA}.{c})" for c in NO_SE_BORRAN])
    return (f"insert into {TABLA} ({', '.join(COLUMNAS)})"
            f" values ({', '.join('?' * len(COLUMNAS))})"
            f" on conflict({', '.join(CLAVE)}) do update set {puesta}")


class Escena:
    """La etapa `orden` de la pieza `slug`, tal y como quedó descrita."""

    __slots__ = ("slug", "orden")

    def __init__(self, slug: str, orden):
        self.slug = str(slug)
        self.orden = int(orden)

    # ── lo que la descripción describe ──────────────────────────────────────
    def sobre_texto(self) -> str | None:
        """El texto que la descripción describe, **leído del montaje**.

        No se recibe: se deriva. Un campo que el llamador puede olvidar es un
        campo que se olvida — `sobre_texto` llevaba 54 filas escritas a mano y
        ninguna línea de código que lo mantuviera, así que la puerta comparaba
        contra lo que alguien tecleó una vez.

        Y sale del montaje, no de la base: la base guarda **lo que se eligió** y
        el montaje es lo que sobrevivió a los recortes posteriores. Describir lo
        elegido y verificar lo montado es como se llegó a tener seis piezas
        descritas contra un texto que ya no existía.
        """
        return (Pieza(int(self.slug.split("-")[1])).texto or {}).get(self.orden)

    # ── guardar ─────────────────────────────────────────────────────────────
    def guardar(self, d: dict) -> dict:
        """Guarda la descripción. `ninguno` se guarda como NULL, no como texto."""
        if not isinstance(d, dict) or not (d.get("que_pasa") or "").strip():
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: una descripción sin `que_pasa` no"
                f" describe nada")
        corrige = d.get("corrige") or {}
        tablero = d.get("tablero")
        valores = {
            "video_slug": self.slug, "etapa_orden": self.orden,
            "que_pasa": d["que_pasa"], "emocion": d.get("emocion"),
            "grafico": d.get("grafico"), "trato": d.get("trato"),
            "trato_porque": d.get("trato_porque"),
            "prioridad": d.get("prioridad"), "integridad": d.get("integridad"),
            "remedio": d.get("remedio"), "corrige_dice": corrige.get("dice"),
            "corrige_es": corrige.get("es"), "sobre_texto": self.sobre_texto(),
            # `quien` decía «gemini» y esa vía se descartó —*«no quiero a
            # Google»*—, así que el campo mentía sobre quién decidió.
            "quien": d.get("quien", "cli"), "fecha": _ahora(),
            # **El tablero NO lo escribe quien describe. Lo escribe quien
            # compone, por `poner_tablero`.**
            #
            # `describir` dice QUÉ tiene que quedar dicho —eso es `grafico`, y es
            # el encargo—; `disenar` decide CÓMO se dibuja y cómo conviven los
            # de la pieza. La separación estaba escrita en el docstring de
            # `disenar` desde el principio y el código la colapsaba aquí.
            #
            # El precio, medido el 1 de septiembre: **`disenar` no había corrido
            # nunca**, cero respuestas en toda la historia del proyecto. Como
            # sólo pide las etapas con el tablero vacío y esto se lo llenaba,
            # quedaba desactivado para siempre. Lo que se veía en pantalla eran
            # siete etapas declarando cada una su componente por su cuenta, sin
            # nadie que mirase la pieza entera — Jaime, viendo el primer render:
            # *«los tableros y paneles están sobrepuestos en todos lados»*, y
            # después, más corto: *«no hay composición»*. Tenía razón literal.
            #
            # Lo que trae quien describe se guarda como **propuesta**, que es lo
            # que es: una sugerencia para quien compone, no una entrega.
            "tablero_propuesto": (json.dumps(tablero, ensure_ascii=False)
                                  if tablero not in (None, "", {}) else None),
            # **Y `tablero` viaja en None a propósito: es lo que el `coalesce`
            # de `NO_SE_BORRAN` necesita para dejarlo como estaba.**
            #
            # Sin esta línea `guardar` no se podía llamar: `COLUMNAS` lo incluye
            # y el `[valores[c] for c in COLUMNAS]` reventaba con `KeyError:
            # 'tablero'` antes de tocar la base. O sea, el paso que describe una
            # etapa llevaba roto desde que se separó la propuesta de la entrega,
            # y no se veía porque el que falla es el llamador y no la consulta.
            "tablero": None,
            "componente": (None if d.get("componente") in (None, "ninguno")
                           else d["componente"]),
            "color": d.get("color"), "sonido": d.get("sonido"),
            "plano": d.get("plano"),
        }
        con = basedatos.abrir()
        con.execute(_upsert(), [valores[c] for c in COLUMNAS])
        self._entidades(con, d)
        con.commit()
        con.close()
        return {"ok": True}

    def _entidades(self, con, d):
        """Cámara, voz y tipo de escena, **escritas por quien describe**.

        Jaime, 10-9-2026: *«tablero es una entidad, no una columna; panel es una
        entidad, no una columna; tipo de escena es una entidad que relaciona
        otras entidades»*. Las tablas se crearon ese día y se llenaron con un
        volcado de una vez — o sea que nacieron **sin autor**: la primera pieza
        que se volviera a describir las dejaba viejas, que es exactamente la
        avería contra la que existen.

        Aquí es donde tienen autor. El mismo sitio que guarda la descripción
        guarda lo que la descripción dice de cada una, y por eso no pueden
        divergir: no hay dos escrituras, hay una.

        Las entidades **se reutilizan** —«pecho / fijo» es una cámara, no
        cincuenta— y por eso se busca antes de insertar: 19 cámaras para 52
        usos y 8 tipos para 62 etapas, que es la normalización enseñándose sola.
        """
        et = con.execute(
            "select e.id from etapa e join video v on v.id = e.video_id"
            " where v.slug = ? and e.orden = ?", (self.slug, self.orden)).fetchone()
        if not et:
            return
        eid = et[0]

        def una(tabla, campos, vals):
            if not any(v is not None for v in vals):
                return None
            donde = " and ".join(f"{c} is ?" for c in campos)
            fila = con.execute(f"select id from {tabla} where {donde}", vals).fetchone()
            if fila:
                return fila[0]
            return con.execute(
                f"insert into {tabla} ({', '.join(campos)})"
                f" values ({', '.join('?' * len(campos))})", vals).lastrowid

        # **`camara` es la seleccion, no la entidad.** Un `encuadre` no es una
        # cadena que se repita 38 veces: es un catalogo, y lo mismo
        # `movimiento` y `virado`. `transicion` ni siquiera es suya —ya tenia
        # tabla— y `detras` es del mundo de la placa, asi que no se decide aqui.
        cam = d.get("camara") or {}

        def cat(tabla, valor):
            """El id de ese valor en su catalogo, creandolo si hace falta.

            **Y si esta retirado, devuelve el que va en su lugar.** Una
            descripcion vieja que nombra `cortinilla` no puede resucitarla: el
            catalogo la lleva marcada con su sustituto y aqui se sigue la
            marca. Sin esto, borrar una retirada duraba hasta el siguiente
            volcado — medido, y lo caso el humo.
            """
            if not valor:
                return None
            f = con.execute(f"select id from {tabla} where nombre = ?",
                            (valor,)).fetchone()
            if not f:
                return con.execute(f"insert into {tabla} (nombre) values (?)",
                                   (valor,)).lastrowid
            cols = {r[1] for r in con.execute(f"pragma table_info({tabla})")}
            if "en_su_lugar" in cols:
                r = con.execute(f"select en_su_lugar from {tabla} where id = ?",
                                (f[0],)).fetchone()
                if r and r[0]:
                    return r[0]
            return f[0]

        cid = una("camara", ["encuadre_id", "movimiento_id", "virado_id"],
                  [cat("encuadre", cam.get("encuadre")),
                   cat("movimiento", cam.get("movimiento")),
                   cat("virado", cam.get("virado"))])
        if cid:
            con.execute("insert or replace into etapa_camara values (?,?)", (eid, cid))
        if cam.get("transicion"):
            con.execute("insert or replace into etapa_transicion values (?,?)",
                        (eid, cat("transicion", cam["transicion"])))
        voz = d.get("voz") or {}
        vid = una("voz", ["trato", "sobre", "dura"],
                  [voz.get("trato"), voz.get("sobre"), voz.get("dura")])
        if vid:
            con.execute("insert or replace into etapa_voz values (?,?)", (eid, vid))
        # **El tipo de escena es una seleccion, como la camara.** `trato`,
        # `plano` y `color` son catalogos —5, 3 y 3 valores en 62 etapas— y no
        # cadenas que se repitan. `remedio` va aparte: no es un tipo, es la
        # decision sobre un problema de integridad.
        tid = una("tipo_escena", ["trato_id", "plano_id", "color_id"],
                  [cat("trato", d.get("trato")), cat("plano", d.get("plano")),
                   cat("color", d.get("color"))])
        if tid:
            con.execute("insert or replace into etapa_tipo values (?,?,?)",
                        (eid, tid, d.get("trato_porque")))
        rid = cat("remedio", d.get("remedio"))
        if rid:
            con.execute("insert or replace into etapa_remedio values (?,?)",
                        (eid, rid))

    def poner_tablero(self, tablero: dict) -> dict:
        """Guarda SOLO el tablero. Es la entrega del paso de diseño.

        `tablero` es `{"kind": …, "props": {…}}`, que es lo que el render sabe
        montar. Si trae `fuente`, entra en `props.source` — el pie de
        cumplimiento.
        """
        if not isinstance(tablero, dict) or not tablero.get("kind"):
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: el tablero necesita `kind`")
        # **Y una forma que el render no sabe dibujar no se guarda.**
        #
        # Cuatro formas declaradas —`FileteCaida`, `AdelantoEstatica`,
        # `tachadura`, `CausalChain`— llegaban al spec y caian en el `return`
        # final de `Tablero.tsx`, que dibuja `TableroDeclarado` con props que no
        # son suyas: un hueco en la pieza y nadie avisado. `describir-esquema`
        # decia tener «la lista de componentes que existen» y tenia seis de las
        # quince, asi que no rechazaba nada.
        #
        # La lista no se copia: **se lee del propio render**, que es quien
        # decide. Copiarla seria la cuarta version de lo mismo. C-353.
        kind = tablero["kind"]
        sabe = _dibujables()
        if sabe and kind not in sabe:
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: el render no sabe dibujar"
                f" «{kind}». Las que dibuja son: {', '.join(sorted(sabe))}.")
        props = tablero.get("props")
        if not isinstance(props, dict) or not props:
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: el tablero necesita `props` con copy")
        fuente = tablero.get("fuente")
        if fuente and fuente != "sin cifra":
            props = {**props, "source": fuente}
        con = basedatos.abrir()
        # **El tablero es una entidad, y aqui es donde deja de ser una columna.**
        #
        # Jaime, 10-9-2026: *«tablero es una entidad, no una columna»*. Vivia en
        # `escena_desc.tablero` y `escena_desc.tablero_propuesto` —dos columnas
        # para lo mismo, distintas en 35 de las 36 filas que tenian las dos—
        # porque no eran dos cosas: eran **una entidad con dos estados**. Ahora
        # el estado esta en la conexion, que es de la relacion y no de la
        # entidad, y por eso no pueden volver a discrepar.
        #
        # `escena_desc.tablero` se sigue escribiendo, y no es escritura doble:
        # es la **proyeccion** que leen los pasos que aun no han cambiado —
        # `escena.mjs`, `llega.py`, `mudo.py`— con un solo autor, este. La misma
        # figura que `estado.json` con la base: manda uno, publica el otro.
        entero = json.dumps({"kind": tablero["kind"], "props": props},
                            ensure_ascii=False)
        et = con.execute(
            "select e.id from etapa e join video v on v.id = e.video_id"
            " where v.slug = ? and e.orden = ?", (self.slug, self.orden)).fetchone()
        if et:
            cur = con.execute(
                "insert into tablero (kind, props, encargo) values (?,?,?)",
                (tablero["kind"], json.dumps(props, ensure_ascii=False),
                 json.dumps(tablero.get("encargo"), ensure_ascii=False)
                 if tablero.get("encargo") else None))
            con.execute(
                "insert or replace into etapa_tablero (etapa_id, tablero_id,"
                " estado, quien, fecha) values (?,?,'aplicado',?,?)",
                (et[0], cur.lastrowid, "disenador", _ahora()))
        n = con.execute(
            f"update {TABLA} set tablero = ?, fecha = ?"
            f" where video_slug = ? and etapa_orden = ?",
            (entero, _ahora(), self.slug, self.orden)).rowcount
        con.commit()
        con.close()
        if not n:
            raise EscenaInvalida(
                f"{self.slug} e{self.orden}: no existe esa escena; descríbela antes")
        return {"ok": True, "slug": self.slug, "etapa": self.orden,
                "kind": tablero["kind"]}

    def __str__(self) -> str:
        return f"{self.slug} e{self.orden}"


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")
