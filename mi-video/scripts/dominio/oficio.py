"""El oficio que contesta un pedido: quién es, dónde está y cómo se le llama.

Un oficio viajaba como `(paso, ruta)` y su nombre como entrada de un `dict`, que
es exactamente el dato desnudo que este proyecto paga caro: quien lo recibe tiene
que saber que el primero es el buzón y el segundo el pedido, y derivar de ahí la
ruta de la respuesta por su cuenta. Aquí lo sabe el objeto.

## Varios a la vez, que no es un detalle de rendimiento

Jaime, 7-9-2026: *«podemos lanzar varios agentes a la vez, no tenemos que hacer
fila, es una arquitectura por servicios»*. Nada aquí serializa: un `Oficio` es de
su pieza, se le llama y contesta. El único turno de la casa lo reparte
`planificador.permiso`, y sólo a los pasos que reescriben una cinta — los de IA
no la tocan, así que pasan sin candado.

## Y la credencial es la de quien lanza

`claude --agent` usa la credencial de la terminal que lo arranca: desde un shell
abierto dentro de una sesión dice `Not logged in` y no contesta. Eso no es un
fallo que haya que tapar — el pedido se queda escrito y abierto, que es el lado
seguro y ya es lo que hace `servicio.pedir` cuando el CLI no está.
"""
from __future__ import annotations

import json
import os
import subprocess

#: Desde dónde se llama al CLI: `mi-video/`, que es contra lo que están escritas
#: las rutas que el pedido nombra —173 en el de reel-01, 203 en el de reel-05— y
#: contra lo que está declarada `servicio.RAIZ`. Se ancla en vez de heredarse
#: porque a `llama` se entra desde el motor, desde el disparador puesto y desde
#: un worktree, y el `cwd` de cada uno no lo garantiza nadie.
#:
#: **Y no es la raíz del repositorio.** Llamar desde ahí dejaba sin resolver cada
#: fichero que el pedido nombra, así que el oficio recorría el encargo entero
#: encontrándose «no existe» y acababa contándolo en prosa. `--agent` resuelve
#: igual desde aquí: el CLI sube al raíz de git a buscar `.claude/agents/`.
CASA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Cuánto se espera a un oficio antes de darlo por colgado. Es la misma espera
#: que el CLI ya tenía declarada en `servicio._por_cli`, escrita una vez y leída
#: por los dos. Sin ella, la única llamada al CLI que corre dentro del bucle del
#: disparador era también la única sin tope: un CLI colgado paraba la línea
#: entera y se leía igual que «el oficio sigue pensando».
ESPERA = 900

#: Qué oficio contesta cada buzón. Los nombres son los de `.claude/agents/`, y un
#: buzón sin oficio declarado no se llama: existe y lo contesta quien pueda, que
#: es el caso honesto mientras ese agente no esté escrito.
#:
#: **Y la redundancia es del compositor** (Jaime, 11-9-2026: *«deberían ir con
#: contrato del agente de composición»*). Iban por `claude -p` genérico, sin el
#: contrato ni la capa de tiquets: la avería que ya describe `servicio.pedir`.
#: **Un buzon, y las dos cosas que se saben de el: quien lo atiende y que fase
#: mueve.** Estaba escrito tres veces —aqui el oficio, en `avanzar.DE_QUIEN` la
#: fase, y `turno.BUZON` dandole la vuelta a la segunda importando el motor
#: entero para eso—. Ya habian divergido una vez: `revisar` estaba en una y no
#: en la otra, y un oficio suscrito a un paso real se quedaba sin buzon.
#:
#: **Y `fuentes` entra.** Estaba en la tabla de fases y no en la de oficios, asi
#: que su pedido se escribia y no habia a quien llamar: un buzon que nadie
#: atiende es una pieza esperando a nadie. Va al compositor por lo mismo que la
#: redundancia (Jaime, 11-9-2026: *«deberian ir con contrato del agente de
#: composicion»*): lo que se comprueba es de donde sale una cifra del texto, y
#: el texto es suyo.
BUZONES = {
    "describir":   ("compositor", "descrito"),
    "disenar":     ("disenador",  "disenado"),
    "visto":       ("disenador",  "visto"),
    "redundancia": ("compositor", "sin_redundancia"),
    "revisar":     ("compositor", "revisado"),
    "revalidar":   ("compositor", "revalidado"),
    "repaso":      ("compositor", "repasado"),
    "fuentes":     ("compositor", "respaldado"),
}

#: Qué oficio contesta cada buzón. Los nombres son los de `.claude/agents/`.
DE = {b: quien for b, (quien, _f) in BUZONES.items()}

#: Qué fase mueve cada buzón. La misma tabla, leída por la otra columna.
LA_FASE = {b: fase for b, (_q, fase) in BUZONES.items()}


def vigente(buzon, slug) -> bool:
    """**Un pedido espera mientras su pieza no haya pasado su fase** (C-606).

    reel-19, 19-10: el pedido de `describir` de las 11:09 seguía sin respuesta
    con la pieza ya en `verificado`. `Oficio.de` lo encontraba antes que el de
    `disenar`, por orden alfabético, y la línea anunciaba «pedido abierto para
    compositor (describir)»: un agente sobre una pregunta que ya nadie hace.
    Lo que no es una pieza del ciclo (las de prueba) sigue esperando.
    """
    import re
    from .fase import camino
    from .pieza import Pieza

    m = re.fullmatch(r"reel-(\d+)(\.[\w-]+)?", slug or "")
    if not m:
        return True
    ahora = Pieza(int(m.group(1))).fase
    # **Y lo de una pieza publicada ya no espera** (C-658). Los pedidos con
    # sufijo —`reel-09.portada`, de `portada.py`— se piden al publicar, así que
    # la fase del buzón no dice nada de ellos; pero con la pieza en la calle
    # nadie los va a contestar. Dos del 25-9 seguían «en vuelo» el 24-10 y
    # bloqueaban `desplegar.py`.
    # Ni lo de una pieza retirada (`rechazado`): reel-01 a reel-07, depreciadas
    # por Jaime, tenían pedidos de diseño abiertos que nadie iba a contestar.
    if (ahora or {}).get("nombre") in ("publicado", "rechazado"):
        return False
    if m.group(2) or buzon not in LA_FASE:
        return True
    suya = next((f for f in camino() if f["nombre"] == LA_FASE[buzon]), None)
    return not (ahora and suya) or ahora["orden"] < suya["orden"]

#: Si la línea lanza el CLI por bash para contestar. **Encendido desde el
#: 15-9-2026**, que es lo que hace que la línea ande sola: sin esto el pedido
#: se queda escrito y abierto esperando a que un agente de la sesión que vigila
#: lo vea — o sea, esperando a que alguien se acuerde.
#:
#: Estuvo apagado cuatro días por una razón que no era de diseño. Jaime,
#: 11-9-2026: *«me quedé sin tokens, los pasos de los agentes no los mandemos
#: por bash, sino por agentes… **no como algo permanente sino como modificación
#: menor**»*. Y el 15-9: *«ya se puede prender el bash»*.
#:
#: **Se apaga sin tocar código**, que es lo que lo hizo reversible entonces y lo
#: sigue haciendo: `OFICIOS_POR_BASH=0`. El valor por defecto es el estado
#: normal de la línea, no el de la semana pasada.
POR_BASH = os.environ.get("OFICIOS_POR_BASH", "1") not in ("0", "", "no")

#: El encargo es siempre el mismo texto. Lo que hay que contestar viaja DENTRO
#: del pedido —`prompt` es su contrato— y esto sólo dice qué fichero leer y en
#: cuál escribir. Improvisar aquí sería un segundo contrato.
ENCARGO = (
    "Tu turno. Lee entero tu contrato {contrato} y el pedido {pedido} —`datos`"
    " es el encargo— y escribe tu respuesta en {respuesta}, con la forma que"
    " ese contrato define. Si el pedido no basta para contestar, se dice en la"
    " respuesta; no se va a buscar fuera."
)

#: **Y lo que se le dice cuando contesta un agente de la sesion**, con tope.
#: Jaime, 18-10-2026: *«reemplaza la accion del bash con agentes tuyos y limita
#: el tope de tokens, esta gastando demasiados; el proceso es de revision de lo
#: que se hizo automaticamente por codigo»*. El 18-10 una sola llamada leyo el
#: pedido en 20 tandas y gasto 4,3 M tokens de entrada (C-552).
REVISION = (
    " Es una REVISION de lo que el codigo ya hizo, no una composicion desde"
    " cero. Lee el contrato y el pedido una sola vez cada uno, sus hojas de"
    " contacto (`hoja`) y los ficheros de `_comun` que nombre (se leen una"
    " vez); un fotograma suelto, solo de la escena que te haga dudar. Todo con"
    " Read, nunca troceado con Bash (C-662); Bash solo para `python"
    " scripts/consulta.py <verbo>` ante una duda concreta. No abras otros"
    " ficheros ni busques. Si lo hecho cumple, contesta lo minimo que el contrato"
    " admite y cambia solo lo que no cumple. Tope: {lecturas} lecturas y una"
    " escritura; si no basta, dilo en la respuesta y para."
)
#: Las lecturas del tope: el contrato (1), el pedido (1), los comunes (1), las
#: hojas de contacto (2-3, C-584) y un fotograma suelto. Eran 6 cuando el
#: pedido se leia en dos tandas (C-550) y los fotogramas iban de uno en uno.
LECTURAS = 7


def _mata_el_arbol(pid: int) -> None:
    """Mata al CLI y a sus nietos. En Windows hace falta el árbol entero.

    `claude` es node y arranca hijos que heredan el pipe: matando sólo al hijo
    directo, la lectura que viene después se queda esperando a que ese pipe se
    cierre, y el tope de espera no sirve de nada.
    """
    try:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                       capture_output=True, check=False, timeout=30)
    except Exception:                              # noqa: BLE001
        pass


class Oficio:
    """Quien sabe contestar el pedido que una pieza dejó abierto."""

    def __init__(self, nombre: str, buzon: str, pedido: str):
        self.nombre = nombre
        self.buzon = buzon
        self.pedido = pedido.replace("\\", "/")

    @classmethod
    def de(cls, slug: str):
        """El oficio que esa pieza está esperando, o `None` si no espera a nadie.

        La cola sale de `servicio.pendientes`, que es la del servicio y ya
        existía, acotada a una pieza: la que acaba de moverse es la única sobre
        la que hay algo nuevo que decir.
        """
        try:
            import sys

            raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if raiz not in sys.path:
                sys.path.insert(0, raiz)
            import servicio

            for buzon, quien, ruta in servicio.pendientes():
                if quien == slug and DE.get(buzon):
                    return cls(DE[buzon], buzon, ruta)
        except Exception:                          # noqa: BLE001
            return None
        return None

    def encargo(self, sesion: bool = False) -> str:
        """Lo que se le dice, por bash o desde la sesion: un solo texto.

        `sesion` le pone el tope de revision (C-552): quien contesta desde la
        sesion que vigila es un agente de esa sesion, y lo que cuesta lo paga
        la misma cuenta.
        """
        texto = ENCARGO.format(
            pedido=os.path.abspath(self.pedido),
            contrato=os.path.abspath(self.pedido).replace(
                ".pedido.json", ".prompt.md"),
            respuesta=os.path.abspath(self.respuesta))
        return texto + (REVISION.format(lecturas=LECTURAS) if sesion else "")

    @property
    def respuesta(self) -> str:
        """Dónde tiene que dejar su respuesta. La deriva del pedido, no se pasa."""
        return self.pedido.replace(".pedido.json", ".respuesta.json")

    @property
    def huella(self) -> tuple:
        """La pregunta concreta que se le hizo: su pedido y cuándo se escribió.

        Es lo que distingue «no ha contestado todavía» de «hay algo nuevo que
        preguntarle». Con el motor puesto, llamarle otra vez por el mismo
        fichero es despertarle para que conteste lo mismo — el coste que hizo
        retirar la patrulla.
        """
        try:
            return (self.pedido, int(os.path.getmtime(self.pedido)))
        except OSError:
            return (self.pedido, 0)

    def contesto(self) -> bool:
        """Cierto si dejó una respuesta **que se puede leer**.

        Que el fichero exista no basta, y la diferencia es cara: un fichero de
        prosa, con vallas ```json o escrito a medias saca la pieza de la cola
        —`servicio.pendientes` deja de nombrarla— y revienta luego, al parsearlo,
        lejos de aquí. Se exige lo mínimo que hace que eso sea una respuesta.
        """
        try:
            with open(self.respuesta, encoding="utf-8") as h:
                json.load(h)
        except (OSError, ValueError):
            return False
        return True

    def llama(self) -> bool:
        """Lo llama y espera. Cierto si dejó una respuesta legible.

        Cuatro cosas que no son detalles y costaron una noche entera:

        - **Se llama desde `mi-video/`**, que es contra lo que están escritas las
          rutas que el pedido nombra. Ver `CASA`.
        - **Con tope de espera** (`ESPERA`) y matando el árbol, no sólo al hijo:
          `claude` es node y deja nietos con el pipe heredado, así que sin eso la
          segunda espera se cuelga igual y el tope no cura nada.
        - **Sin heredar la consola** (`stdin` cerrado): heredada, el CLI se queda
          tres segundos mirando si hay algo que leer y mete su ruido en la salida
          que luego se registra.
        - **Y si no deja respuesta, queda escrito por qué.** Sin esto la llamada
          fallaba en silencio y no había forma de distinguir «no se le llamó» de
          «no resolvió» o «contestó mal».
        """
        orden = [
            "claude", "--agent", self.nombre,
            # **Y con permiso de escribir, que es la mitad del oficio.** Sin
            # esto el CLI le deniega la escritura y el agente hace el trabajo
            # entero para acabar contandolo en prosa: «leyo el pedido y preparo
            # la respuesta», salida 0 y ningun fichero. Se le dan las dos
            # herramientas que su contrato declara —`docs/caminos.md`: *«lo que
            # ninguno toca: la base, los scripts, el EDL, los ficheros de
            # entrega; trabajan con Read y Write»*— y ninguna mas.
            "--allowedTools", "Read Write",
            # **Y sin poder delegar en si mismo.** `--allowedTools` aprueba,
            # no prohibe: el compositor lanzaba un subagente «compositor» que
            # volvia a leer el pedido entero, dos arranques y dos contextos por
            # respuesta, en todas las llamadas del 17 y el 18-10 (C-549).
            "--disallowedTools", "Agent Task", "-p",
            self.encargo()]
        # **Y sin el CLAUDE.md, que es del operador** (C-587): el contrato es su
        # instruccion completa, y eran ~10 K tokens por llamada. Por la sesion
        # lo quita `omitClaudeMd` en `.claude/agents/`; por el CLI, esto.
        with subprocess.Popen(orden, cwd=CASA, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"}) as p:
            try:
                salida, err = p.communicate(timeout=ESPERA)
            except subprocess.TimeoutExpired:
                _mata_el_arbol(p.pid)
                salida, err = p.communicate()
                return self._sin_respuesta(f"no volvio en {ESPERA} s",
                                           salida, err)
            codigo = p.returncode
        if self.contesto():
            return True
        # **Y si contestó por la salida en vez de por el fichero, se recoge.**
        # El agente hizo el trabajo; tirarlo por dónde lo puso es pagarlo dos
        # veces. Lo que se acepta es lo mismo que acepta quien lo consume.
        if self._rescata(salida):
            return True
        return self._sin_respuesta(f"salida {codigo}", salida, err)

    def _rescata(self, salida) -> bool:
        """Guarda la respuesta si vino por la salida y es JSON. Cierto si valió."""
        txt = (salida or "").strip()
        i = min([k for k in (txt.find("["), txt.find("{")) if k >= 0], default=-1)
        j = max(txt.rfind("]"), txt.rfind("}"))
        if i < 0 or j <= i:
            return False
        try:
            json.loads(txt[i:j + 1])
        except ValueError:
            return False
        with open(self.respuesta, "w", encoding="utf-8", newline="\n") as h:
            h.write(txt[i:j + 1])
        return True

    def _sin_respuesta(self, por_que: str, salida, err) -> bool:
        """Lo deja escrito y devuelve `False`. Es el único camino de fallo."""
        dijo = ((salida or "") + (err or "")).strip()
        detalle = (f"{self} no dejo respuesta ({por_que}):"
                   f" {dijo[-400:] or 'sin salida'}")
        print(f"  {detalle}", flush=True)
        try:
            import registro

            registro.aviso("oficio", "el oficio no contesto", detalle=detalle,
                           eco=False)
        except Exception:                          # noqa: BLE001
            pass
        return False

    def __str__(self) -> str:
        return f"{self.nombre} ({self.buzon})"


# **La cola de la sesion vive en `dominio/cola.py`** (C-564): por pedido o
# en lote por buzon. Aqui queda quien contesta, no cuantos esperan.
