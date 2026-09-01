"""Los objetos del dominio: `Pieza` y `Servicio`.

Regla de Jaime: *«buscamos construir y mantener servicios, no un monolito, no
spaghetti — eso significa POO»*.

## Qué había y por qué era spaghetti

Cuarenta scripts sueltos que se hablan por ficheros y por la base. `beats.py`
importado por casi todos, `seleccionar.py` en mil quinientas líneas, y el
conocimiento de qué es una pieza —dónde vive su EDL, cuál es su versión, en qué
fase está— **repetido en cada uno**. Cambiar dónde se guarda un EDL era tocar
once ficheros y acordarse de los once.

Y el motor hablaba con los pasos **por cadena de texto**: `"scripts/depurar.py
{n}"`. Eso funciona y no es un servicio: no hay contrato, no hay forma de
preguntarle si puede correr, y un fallo sólo se distingue por el código de
salida.

## Qué hace esto, y qué NO hace

**No reescribe nada.** Los scripts siguen siendo los que trabajan — esa es la
regla: *«cambias la máquina, no la rehaces»*. Lo que se añade es la costura:

- `Pieza` — lo que una pieza **es**: su slug, su EDL, su versión, su fase, su
  texto. Deja de estar repetido en cada script.
- `Servicio` — lo que un paso **promete**: un nombre, la fase a la que lleva,
  un `puede()` que dice si tiene sentido correr, y un `correr()` que devuelve
  un resultado con motivo, no un código de salida.

Un paso nuevo se escribe heredando de `Servicio`. Un paso viejo se envuelve en
tres líneas con `ServicioScript`. Los dos hablan el mismo idioma con el motor, y
el motor deja de saber que por debajo hay un `subprocess`.
"""
from __future__ import annotations

import dataclasses
import json
import os
import shlex
import subprocess
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "ads/decisiones.db"


@dataclasses.dataclass
class Resultado:
    """Lo que devuelve un servicio. **Motivo siempre, no sólo un código.**

    Un `returncode` dice que algo falló y nada más; el motor necesita poder
    escribirlo en `video_fase.por_que` para que alguien lo desatasque después.
    """

    ok: bool
    motivo: str = ""
    salida: str = ""
    # **Y puede pedir volver.** La linea no es una secuencia —eso quedo cuando
    # las fases pasaron a ser un dato— asi que un paso puede decir «esto cambio
    # lo que ya habiamos dado por bueno, hay que rehacerlo desde ahi».
    #
    # Lo pide el repaso final: si corta algo, el texto ya no es el que se
    # cosio, y componer sobre un texto viejo es justo el fallo que ese paso
    # viene a cerrar. Regla de Jaime: *«asegurate de hacerlo ciclico: si no
    # pasa redundancia, no se compone»*.
    volver_a: str = ""


# **`Pieza` vive en el dominio.** Se importa aquí porque medio proyecto la
# pide como `from servicios import Pieza`, y mover una clase no tiene por
# qué romper a treinta llamadores. Ver `dominio/pieza.py`.
from dominio.pieza import Pieza  # noqa: E402,F401


class Servicio:
    """Lo que un paso promete al motor.

    Tres cosas y ninguna opcional:

    - `nombre` — cómo se llama en el log y en la tabla `fase`.
    - `puede(pieza)` — si tiene sentido correrlo ahora. Un servicio que no puede
      correr **no es un fallo**: es un servicio que espera algo, y el motor
      distingue las dos cosas.
    - `correr(pieza)` — hace el trabajo y devuelve `Resultado` con motivo.
    """

    nombre: str = ""

    #: **Si este paso reescribe una cinta compartida.** Lo declara el paso, no
    #: lo adivina el motor. Es lo único que impide correr dos piezas a la vez:
    #: si las dos afinan `20260825_225808`, una se lleva por delante lo que la
    #: otra acaba de escribir — y además la pregunta de la segunda cambia
    #: debajo de quien la esté contestando, que es C-150.
    #:
    #: Todo lo demás —cortar, medir, coser, describir— trabaja sobre el EDL y
    #: las filas de SU pieza, y con WAL eso ya puede pasar en paralelo.
    escribe_cintas: bool = False

    def puede(self, pieza: Pieza) -> tuple[bool, str]:
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.nombre}>"


class ServicioScript(Servicio):
    """Envuelve un script que ya existe y funciona.

    **Esto es la costura, y es a propósito.** Los cuarenta scripts no se
    reescriben: se envuelven. El motor habla con objetos y por debajo sigue
    habiendo el mismo `depurar.py` que lleva días funcionando.

    Un paso nuevo se escribe heredando de `Servicio` directamente; uno viejo
    entra aquí en una línea. Migrar de golpe sería rehacer la máquina, que es lo
    que la regla prohíbe.
    """

    def __init__(self, nombre: str, plantilla: str):
        self.nombre = nombre
        self.plantilla = plantilla
        # **Se deduce del comando, y por una vez está bien deducirlo.** El
        # script envuelto es el que se conoce a sí mismo, y `transcribir.py` es
        # el único de los cuarenta que reescribe una cinta. Ponerlo a mano en
        # `CICLO` sería una segunda declaración de lo mismo — la avería de
        # siempre — y esto se lee del propio comando que se va a ejecutar.
        self.escribe_cintas = "transcribir.py" in plantilla

    def correr(self, pieza: Pieza) -> Resultado:
        partes = shlex.split(self.plantilla.format(n=pieza.n, slug=pieza.slug))
        if partes[0].endswith(".py"):
            partes = [sys.executable] + partes
        elif partes[0].endswith(".mjs"):
            partes = ["node"] + partes
        elif partes[0].endswith(".sh"):
            partes = ["bash"] + partes
        # **Las dos mitades del mismo acuerdo.** `PYTHONIOENCODING` dice al
        # hijo que escriba UTF-8 y hacia falta la otra: sin `encoding` aqui,
        # el padre decodifica con la pagina de codigos de Windows y **un paso
        # que imprime una tilde mata la linea entera**. Paso al renderizar
        # reel-05: la fuente del umbral traia comillas angulares y el montaje
        # murio con UnicodeDecodeError sin producir un solo fichero.
        #
        # `errors="replace"` porque esto es el canal de diagnostico: perder un
        # caracter de un mensaje es barato, perder el mensaje entero —y con el,
        # el motivo por el que un paso no pudo— es lo que deja una pieza parada
        # sin nadie sepa por que.
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(partes, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        salida = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return Resultado(True, salida=salida)
        # **El motivo sale de lo que el paso dijo, no de lo ultimo que se leyo.**
        #
        # Esto tomaba la ultima linea de `stdout + stderr`, y eso no es «lo
        # ultimo que paso»: es lo ultimo del texto. `entorno.sh` escribe su
        # aviso de disco en stderr **al arrancar**, o sea lo primero de todo, y
        # la concatenacion lo dejaba el ultimo — asi que las siete piezas se
        # quedaron paradas en `montado` con este motivo:
        #
        #     AVISA, no para. De seis piezas con 21 GB libres renderizaron
        #     cuatro, y las dos que cayeron eran las dos mas largas...
        #
        # Un mensaje que **dice de si mismo que no para**, tapando el motivo de
        # verdad —«pedido(s) de IA sin contestar», «1 corte(s) caen en pleno
        # sonido»— que estaba en stdout y nadie llego a ver. Un dia entero
        # diagnosticando el disco por un problema que no era del disco.
        #
        # Los pasos de este proyecto dicen POR QUE no pudieron en stdout, y su
        # ultima linea esta escrita para eso: *«la ULTIMA linea es la que el
        # motor guarda como motivo»*. stderr es el canal del entorno y de los
        # avisos. Asi que manda stdout, y stderr solo cuando el paso no dijo
        # nada — que ahi si es lo unico que hay.
        dicho = (r.stdout or "").strip().splitlines()
        if not dicho:
            dicho = (r.stderr or "").strip().splitlines()
        ultima = dicho[-1] if dicho else "sin salida"
        return Resultado(False, motivo=ultima[:160], salida=salida)


class Espera(Servicio):
    """La fase que no mueve un servicio, sino Jaime.

    `aprobado` es la única, y tiene su propia clase en vez de un `if serv is
    None` en el motor: **una excepción con nombre es una clase; una sin nombre
    es un parche.**
    """

    def __init__(self, nombre: str, quien: str = "Jaime"):
        self.nombre = nombre
        self.quien = quien

    def puede(self, pieza: Pieza):
        return False, f"espera a {self.quien}"

    def correr(self, pieza: Pieza) -> Resultado:
        return Resultado(False, motivo=f"espera a {self.quien}")
