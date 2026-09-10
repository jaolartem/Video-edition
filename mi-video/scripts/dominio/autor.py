"""Quien actuo, de que tipo es, y **que tenia derecho a hacer**.

Jaime, 10-9-2026: *«hay autores y hay tipos de autores. Estoy yo como persona
asociada a mi propia imagen de marca, pero si entra otra persona la imagen de
marca deberia cambiar. Tambien estan los agentes de IA, que modifican y definen
pasos y cosas. Quien es al final un declarador de agencia, requiere mas trabajo
que solo declarar una entidad»*. Y precisando: *«el tipo no es jaime sino
persona; la entidad persona tiene nombre e identidad de marca; agencia son los
permisos que hay sobre todo»*.

## Por que no basta con un catalogo

`quien` era texto libre en nueve tablas: quince cadenas para diez actores, la
misma persona escrita de cuatro maneras y dos de ellas con la razon metida
dentro del nombre. Pero el problema no era la ortografia — era que **el permiso
se comprobaba comparando esa cadena**: `segmento.es_suya` miraba si empezaba por
«jaime» para decidir si una aprobacion valia, y `contestado` filtraba las notas
con `que like '%Jaime%'`. Un derecho que se decide por prefijo de cadena no es
un derecho.

## El derecho es de la clase, no del nombre

Por eso la agencia cuelga del **tipo**: «aprobar es de una persona» vale para
cualquier persona, no solo para la que hay hoy. El dia que entre otra, hereda el
permiso por ser persona y trae **su** marca — que no se copia aqui: se apunta,
porque las indicaciones ya son los contratos (`contrato/marca.py`).
"""
from __future__ import annotations


def _con():
    from . import ticket as _t

    return _t._con()


def _sin_el_motivo(quien) -> str:
    """El nombre, sin la razon que alguien le pego detras.

    Las filas viejas traen `jaime · aprobo la pieza el 7-9-2026`: el nombre con
    su motivo dentro, que escribi yo. Eso si es limpiar el dato — lo que **no**
    se hace aqui es adivinar equivalencias recortando articulos y mayusculas:
    `diseno` y `disenador` son el mismo actor porque `autor_alias` lo declara,
    no porque dos cadenas se parezcan. Decidir comparando texto es lo que C-363
    quito de la agencia y no vuelve por la puerta de atras.
    """
    return str(quien or "").split("·")[0].split(" - ")[0].strip()


class Autor:
    """Quien hizo algo. Sabe de que tipo es y que puede hacer ese tipo."""

    __slots__ = ("nombre", "tipo", "id")

    def __init__(self, nombre, tipo, id_=None):
        self.nombre, self.tipo, self.id = nombre, tipo, id_

    @classmethod
    def de(cls, quien) -> "Autor | None":
        """El autor que corresponde a ese `quien`, o `None` si no esta declarado.

        `None` no es un hueco benigno: es **nadie**, y nadie no tiene permisos.
        Un `quien` que no esta en la tabla no puede aprobar por descuido.
        """
        n = _sin_el_motivo(quien)
        if not n:
            return None
        cx = _con()
        r = cx.execute(
            "select a.id, a.nombre, t.nombre tipo from autor a"
            " join tipo_autor t on t.id = a.tipo_id"
            " where a.id = (select autor_id from autor_alias where alias = ?)"
            "    or lower(a.nombre) = lower(?)", (n, n)).fetchone()
        cx.close()
        return cls(r["nombre"], r["tipo"], r["id"]) if r else None

    def puede(self, permiso) -> bool:
        """Si su tipo tiene ese permiso. Se lee de `agencia`, no se supone."""
        cx = _con()
        r = cx.execute(
            "select 1 from agencia ag"
            " join tipo_autor t on t.id = ag.tipo_id"
            " join permiso p on p.id = ag.permiso_id"
            " where t.nombre = ? and p.nombre = ?", (self.tipo, permiso)).fetchone()
        cx.close()
        return bool(r)

    @property
    def marca(self):
        """Que marca le toca, si es persona. Es un puntero al contrato, no prosa."""
        cx = _con()
        r = cx.execute("select nombre, marca from persona where autor_id = ?",
                       (self.id,)).fetchone()
        cx.close()
        return dict(r) if r else None

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


def puede(quien, permiso) -> bool:
    """¿Quien hizo esto tenia derecho a hacerlo? La pregunta corta."""
    a = Autor.de(quien)
    return bool(a) and a.puede(permiso)
