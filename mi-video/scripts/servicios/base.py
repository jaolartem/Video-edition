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

import rutas  # noqa: E402

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


def devuelve(pieza, marca: str, por_que: str,
             atiende: str = "descrito") -> Resultado:
    """**Un «no» se le dice a quien lo arregla: es un tiquet.**

    Lo usan los dos oficios que pueden parar una pieza: `visto` —«no se
    enseña»— y `disenar` —«la escena no cuadra»—. Jaime, 11-9-2026: *«lo que
    el compositor decide es la escena; si la escena no cuadra y el diseñador lo
    nota, la devuelve»*. Parar sin decírselo a nadie era dejar la pieza
    esperando a un paso que no sabía que tenía trabajo (C-381, C-387).

    `atiende` es el paso que lo arregla, como en cualquier tiquet; la pieza se
    coloca justo antes (`antes_de`). Uno abierto por pieza y por `marca`.
    """
    from dominio import ticket
    from dominio.fase import antes_de, camino

    if atiende not in {f["nombre"] for f in camino()}:
        atiende = "descrito"
    if not any((t.get("dijo") or "").startswith(marca)
               for t in ticket.abiertos(pieza.slug)):
        ticket.abrir(pieza.slug, f"{marca} {por_que}", etapa="pieza",
                     tipo="objecion", vuelve_a=atiende)
    return Resultado(False, motivo=f"{marca} {por_que}"[:300],
                     volver_a=antes_de(atiende), salida=por_que[:200])


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

    @staticmethod
    def _tomar(turno: str) -> bool:
        """Toma el turno. `False` si lo tiene otro proceso que sigue vivo."""
        for _ in range(2):
            try:
                fd = os.open(turno, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return True
            except FileExistsError:
                try:
                    duenyo = int(open(turno).read().strip() or 0)
                except (OSError, ValueError):
                    duenyo = 0
                if _vive(duenyo):
                    return False
                try:
                    os.remove(turno)
                except OSError:
                    return False
        return False

    def correr(self, pieza: Pieza) -> Resultado:
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__} {self.nombre}>"


def _vive(pid: int) -> bool:
    """Si ese proceso sigue corriendo. En Windows no vale `os.kill(pid, 0)`.

    Ahi `os.kill` **mata** en vez de preguntar —solo entiende los dos eventos de
    consola—, asi que la comprobacion inocente de POSIX seria aqui la forma mas
    rapida de tirar el render que se queria respetar. Se pregunta por la API:
    `OpenProcess` puede abrir un proceso ya terminado y todavia sin recoger, asi
    que el que contesta de verdad es `GetExitCodeProcess` con `STILL_ACTIVE`.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)   # QUERY_LIMITED_INFORMATION
        if not h:
            return False
        codigo = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(codigo))
        k.CloseHandle(h)
        return bool(ok) and codigo.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


#: La marca con la que un script pide volver. La escriben `describir.mjs` y
#: `montar.sh`; la lee `ServicioScript._correr`. C-548.
VOLVER_A = "volver_a: "


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
        # **Un paso no corre dos veces sobre la misma pieza a la vez.**
        #
        # Paso el 1 de septiembre: con el despachador encendido corri
        # `montar.sh 2` a mano y **los dos renderizaron reel-02**, once minutos
        # de maquina para producir el mismo fichero dos veces. La culpa fue mia
        # —Jaime: *«tu no toques el proceso, tu estas afuera del proceso»*— pero
        # que se pueda hacer es del codigo: el mismo choque lo produce un segundo
        # despachador, o una prueba lanzada mientras la linea trabaja.
        #
        # Un fichero de turno por paso y pieza. Si esta tomado, el paso no falla:
        # dice que ya se esta haciendo, que es la verdad, y la pieza se queda
        # donde esta hasta la vuelta siguiente.
        turno = os.path.join("work", "turnos", f"{self.nombre}.{pieza.slug}")
        os.makedirs(os.path.dirname(turno), exist_ok=True)
        #
        # **Y el turno caduca con su dueño.** Guardaba el PID y no lo miraba
        # nunca, asi que un montaje que no llega al `finally` —lo mata el techo
        # de tamaño, lo corta una guarda, se cierra la consola— deja la pieza
        # bloqueada **para siempre**, y el mensaje que sale dice «ya se esta
        # haciendo», que es exactamente lo contrario de lo que pasa. Hoy dejo
        # reel-02 y reel-07 paradas con nadie trabajando en ellas.
        #
        # Se comprueba si el proceso vive. No se borra por antiguedad: un render
        # legitimo tarda veinte minutos y un umbral de tiempo lo atropellaria.
        if not self._tomar(turno):
            return Resultado(False, motivo=f"«{self.nombre}» ya se esta"
                                           f" haciendo sobre esta pieza")
        try:
            return self._correr(pieza)
        finally:
            try:
                os.remove(turno)
            except OSError:
                pass

    def _correr(self, pieza: Pieza) -> Resultado:
        partes = shlex.split(self.plantilla.format(n=pieza.n, slug=pieza.slug))
        if partes[0].endswith(".py"):
            partes = [sys.executable] + partes
        elif partes[0].endswith(".mjs"):
            partes = ["node"] + partes
        elif partes[0].endswith(".sh"):
            # El interprete se resuelve y no se hereda del PATH de quien
            # arranco la linea. Ver `rutas.interprete` y C-349.
            partes = [rutas.interprete()] + partes
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
        # Tomaba la ultima linea de `stdout + stderr`, y eso no es «lo ultimo
        # que paso»: es lo ultimo del texto. El aviso de disco de `entorno.sh`
        # sale en stderr **al arrancar** y la concatenacion lo dejaba el
        # ultimo, tapando el motivo de verdad. Los pasos de aqui dicen POR QUE
        # no pudieron en stdout y su ultima linea esta escrita para eso; stderr
        # es el canal del entorno. Manda stdout, y stderr solo si no dijo nada.
        dicho = (r.stdout or "").strip().splitlines()
        if not dicho:
            dicho = (r.stderr or "").strip().splitlines()
        ultima = dicho[-1] if dicho else "sin salida"
        # **Un script tambien puede pedir volver**, como un servicio con
        # `Resultado.volver_a`: su ultima linea dice `volver_a: <fase>` y la
        # pieza se coloca desde donde ese paso se vuelve a correr. Sin esto un
        # «no se puede porque falta lo de atras» se contaba como espera o como
        # fallo, y ninguna de las dos lleva la pieza atras (C-548).
        if ultima.startswith(VOLVER_A):
            from dominio.fase import antes_de
            fase = ultima[len(VOLVER_A):].split()[0]
            return Resultado(False, motivo=ultima[:160], salida=ultima[:200],
                             volver_a=antes_de(fase))
        # **Y lo que dijo el paso no se tira.** Una etiqueta no es un
        # diagnostico: `montar.sh` muere con `set -e` dentro de `render.mjs`,
        # su ultima linea de stdout es «bundle listo en 13.0 s» —progreso
        # guardado como causa— y el error de node se perdia aqui. `salida` ya
        # trae las dos mitades y nadie la guardaba. Va en este punto porque los
        # que llaman son dos y este es el unico por el que pasa entera. C-371.
        import registro
        registro.aviso(self.nombre, "el paso no pudo, y esto es lo que dijo",
                       toma=pieza.slug, eco=False,
                       detalle=chr(10).join(salida.strip().splitlines()[-25:]))
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
