"""El motor del contrato, aparte de lo que el contrato dice.

Dentro de este paquete hay dos cosas de naturaleza distinta, y separarlas es
todo lo que hace este paquete:

- **El vocabulario** — `Aguja`, `Prompt`, `Campo`, `Clave`, `Bloque`,
  `Momento`, `Repeticion`, `Contrato`, el `Registro` y el parte. Es un motor:
  **no cambia cuando cambia un contrato**.
- **La declaración** — los cuatro contratos con sus campos, sus claves y su
  prosa (`corte.py`, `componer.py`, `respaldo.py`, `diseno.py`, y lo común en
  `comun.py`). Eso son datos, y es lo que crece.

Mezcladas eran 1.157 líneas de código en un fichero, y el precio no era el
tamaño: era que añadir un campo y arreglar el verificador se hacían en el mismo
sitio, así que nadie sabía cuál de los dos había roto el otro.

La puerta sigue siendo `scripts/contratos.py`, que es lo que corre `montar.sh`.
"""
from .aguja import NADIE, Aguja, Prompt, plano
from .parte import bloques, parte
from .piezas import Bloque, Campo, Clave, Contrato, Momento, Repeticion
from .registro import Registro

__all__ = ["Aguja", "Bloque", "Campo", "Clave", "Contrato", "Momento", "NADIE",
           "Prompt", "Registro", "Repeticion", "bloques", "parte", "plano"]
