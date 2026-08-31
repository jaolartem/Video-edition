"""El respaldo de las cifras: de dónde sale cada número que se rotula.

## Por qué esto es una fase y hasta ahora no lo era

`fuentes.py` existía, tenía su contrato y su tabla, y **no lo llamaba nadie**:
cero filas en `fase`, cero registros aquí, y `sin_respaldo()` —cuyo propio
docstring dice *«es lo que mira la puerta»*— sin un solo llamante fuera de su
`main()`. O sea que la comprobación que el playbook pone como prioridad 1 no
estaba en la línea, y sólo corría si alguien se acordaba de teclearla.

Lo encontró una auditoría en frío, y la consecuencia estaba medida: diez cifras
marcadas `no` en la base —los $14.300 y el «$20 esta semana» entre ellas— sin
que ninguna parara nada.

## Y por qué para la pieza

El piso lo dice sin matices, con las palabras de Jaime: *«queremos ser honestos,
por eso aclaramos los datos y ponemos pies de foto con la info complementaria
que no cabe en el video y las fuentes en cada tablero, legibles y claras»*.

**Un tablero con cifra y sin fuente no pasa.** No es un aviso: es la diferencia
entre publicar algo que se sostiene y publicar algo que parece que se sostiene.
Por eso este servicio devuelve que no pudo cuando queda una cifra sin respaldo,
en vez de imprimirlo y seguir — que es lo que hacía `main()`, saliendo con
código 0 tanto si había un `no` como si el servicio no había contestado.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioRespaldo(Servicio):
    nombre = "respaldado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import fuentes
        import servicio as contrato

        filas = fuentes.dossier(pieza.slug)
        if not filas:
            # Una pieza sin cifras en pantalla no tiene nada que respaldar, y
            # eso es un pase legítimo, no un hueco.
            return Resultado(True, salida="ninguna cifra en pantalla")
        prompt = open(fuentes.PROMPT, encoding="utf-8").read()
        r = contrato.pedir("fuentes", pieza.slug, prompt, filas)
        if r is None:
            return Resultado(
                False,
                motivo="espera el respaldo de las cifras -> "
                       + contrato.ruta_pedido("fuentes", pieza.slug))
        puestas = fuentes.cargar(pieza.slug, r)
        falta = fuentes.sin_respaldo(pieza.slug)
        if falta:
            uno = falta[0]
            resto = f" (+{len(falta) - 1} mas)" if len(falta) > 1 else ""
            return Resultado(
                False,
                motivo=f"cifra sin respaldo: e{uno['etapa_orden']}"
                       f" «{str(uno['cifra'])[:70]}» [{uno['respalda']}]{resto}",
                salida=f"{puestas} dato(s) revisados, {len(falta)} sin respaldo")
        return Resultado(True, salida=f"{puestas} cifra(s), todas con fuente")
