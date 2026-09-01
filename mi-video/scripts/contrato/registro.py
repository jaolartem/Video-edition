"""Los cuatro contratos juntos: quién gobierna qué fase, y qué agujas siguen en pie.

Es la mitad del motor que **decide**. No imprime nada —de eso es `parte.py`— y
no declara nada —de eso son los cuatro ficheros de contrato—: sólo indexa lo
declarado y lo contrasta con el disco.

`por_fase` **se deriva de los momentos**, no se escribe al lado. Escrito a mano
era una segunda copia de la misma lista, y una segunda copia es la avería que
este proyecto paga más caro: un momento declarado y no enrutado no falla, se
salta el contrato en silencio.
"""
from __future__ import annotations

from .aguja import NADIE
from .piezas import Campo, Contrato, Momento


class Registro:
    """Los contratos vivos, indexados por paso y por fase."""

    def __init__(self, contratos, bloques):
        self.contratos: dict[str, Contrato] = {c.paso: c for c in contratos}
        self.bloques = {b.nombre: b for b in bloques}
        self.por_fase: dict[str, Contrato] = {
            m.fase: c for c in contratos for m in c.momentos}

    def por_paso(self, paso: str) -> Contrato | None:
        return self.contratos.get(paso)

    def momento(self, fase: str) -> tuple[Contrato, Momento] | None:
        c = self.por_fase.get(fase)
        if not c:
            return None
        m = next((x for x in c.momentos if x.fase == fase), None)
        return (c, m) if m else None

    def campos_del_momento(self, fase: str) -> tuple[Campo, ...]:
        """Los campos que el payload TIENE que llevar en esa fase.

        Es de aquí de donde se arma el pedido, no de un `dict` escrito a mano en
        cada servicio: un campo que se añade al contrato aparece en el payload y
        en la comprobación a la vez, que es lo que hace que no puedan divergir.
        """
        par = self.momento(fase)
        if not par:
            return ()
        c, m = par
        return tuple(x for x in c.campos_todos()
                     if (not x.en or fase in x.en) and x.nombre not in m.no_trae)

    def calladas(self) -> list[str]:
        """Lo declarado y callado. Ver `Campo.deuda`."""
        return [f"{c.paso} · «{x.nombre}» se exige en el prompt y no viaja,"
                f" y no dice por que"
                for c in self.contratos.values()
                for x in c.campos_todos()
                if x.manda is None and x.exige and not x.deuda]

    def revisar(self) -> tuple[list[str], list[str]]:
        """Las agujas que ya no estan. Es lo que separa un contrato de una promesa.

        **Y hasta ahora no lo llamaba nadie.** El parte imprimia cuatro numeros
        que se calculan de la declaracion sola —sin abrir un fichero—, asi que
        la mitad que mira la realidad estaba escrita y muerta. Con las rutas
        rotas por encima, las 83 agujas comprobables daban «no esta» y ninguna
        lo decia.

        Se separan dos cosas que no son lo mismo:

        - **mecanismo perdido** — la linea que hace el trabajo ya no existe con
          esa forma. Para la linea, igual que en `guardas.mjs`: o volvio el
          defecto, o la aguja hay que re-apuntarla, y las dos exigen mirar.
        - **clausula sin escribir** — un campo condicional cuyo prompt todavia
          no dice que hacer cuando falta. Es deuda declarada: avisa y deja
          pasar, porque escribirla es criterio y no le toca al codigo
          inventarla.
        """
        perdidos, sin_clausula = [], []
        for c in self.contratos.values():
            for k in c.campos_todos():
                if k.manda is not None and not k.manda.esta():
                    perdidos.append(f"{c.paso} · campo «{k.nombre}» -> {k.manda}")
                if k.si_falta is not None and not k.si_falta.esta():
                    sin_clausula.append(
                        f"{c.paso} · «{k.nombre}» es condicional y"
                        f" `{k.si_falta.fichero}` no dice que hacer si falta")
            for kv in c.claves_todas():
                for a in kv.dispara:
                    if a is not NADIE and not a.esta():
                        perdidos.append(f"{c.paso} · clave «{kv.nombre}» -> {a}")
        return perdidos, sin_clausula
