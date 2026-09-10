"""¿Está el sistema conectado? Quién produce y quién consume, comprobado.

Jaime, después de una noche entera de correcciones suyas que no llegaban:
*«tu función ha sido sobre todo táctica, y ése es el problema: tu objetivo no es
editar vídeos, es vigilar que el sistema funcione y esté todo conectado. Acá no
está conectado»*.

## La avería tiene una sola forma

Todo lo que costó esa noche es lo mismo escrito de seis maneras — **alguien
produce y nadie consume**, o alguien consume lo que nadie produce:

    la tabla `revision` escribe          la línea no la leía
    el pedido de diseño se escribe       no reabría la etapa del tiquet
    `entrecortado` contesta              `costuras.py` no lo consume
    `version` / `render` declaradas      nadie las llena
    `nivelado` corre                     no comprueba su propia salida
    el despachador espera                nadie iba a contestar

**Ninguna da error.** Cada pieza funciona perfectamente sola: el que escribe
escribe, el que lee lee lo que encuentra, y el fallo sólo aparece cuando Jaime
mira la entrega y echa en falta lo que pidió. Por eso se repite — y por eso hace
falta mirarlo desde fuera de cada paso.

## Lo que comprueba, y por qué son esas tres cosas

1. **Tablas declaradas y vacías.** El esquema promete que ahí vive un estado. Si
   nadie escribió nunca una fila, esa promesa es falsa y lo que dependa de ella
   —reconstruir una entrega, saber qué se renderizó— no se puede cumplir.
2. **Respuestas de servicio que nadie consume.** Un paso pregunta, alguien
   contesta, y la respuesta se queda en el disco. Corrida tras corrida.
3. **Pasos del ciclo que nadie invoca.** `CICLO` declara el camino; si el
   comando de una fase no aparece en ningún sitio que lo llame, esa fase es una
   intención, no un paso.

No mide calidad ni juzga contenido: mira **si los cables están puestos**. Es lo
contrario de las guardas, que comprueban que un mecanismo sigue ahí; esto
comprueba que además está enchufado a algo.

    python scripts/conectado.py
"""
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Tablas que pueden estar vacías sin que signifique nada roto: son historial de
#: cosas que quizá no han pasado todavía. Cada una con su motivo, porque una
#: excepción sin motivo es un agujero con permiso.
VACIAS_OK = {
    "publicacion": "todavía no se ha publicado ninguna pieza",
    "gasto": "sólo se llena si se paga una generación de IA",
}


def _texto(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _fuentes():
    """Todo el código del proyecto, para preguntarle quién nombra qué."""
    fuera = {}
    for base, _d, ficheros in os.walk(os.path.join(RAIZ, "scripts")):
        if "node_modules" in base or "__pycache__" in base:
            continue
        for f in ficheros:
            if f.endswith((".py", ".mjs", ".sh", ".js")):
                r = os.path.join(base, f)
                fuera[os.path.relpath(r, RAIZ)] = _texto(r)
    return fuera


def tablas_muertas():
    """Tablas del esquema sin una sola fila, y si alguien sabe escribirlas."""
    try:
        cx = basedatos.abrir(BASE)
        nombres = [r[0] for r in cx.execute(
            "select name from sqlite_master where type = 'table'"
            " and name not like 'sqlite_%'")]
    except sqlite3.Error as e:
        return [f"no se pudo abrir la base: {e}"]
    codigo = "\n".join(_fuentes().values())
    fuera = []
    for t in nombres:
        try:
            n = cx.execute(f"select count(*) from {t}").fetchone()[0]
        except sqlite3.Error:
            continue
        if n or t in VACIAS_OK:
            continue
        escribe = re.search(rf"insert\s+(?:or\s+\w+\s+)?into\s+{t}\b", codigo,
                            re.I) is not None
        fuera.append(
            f"la tabla «{t}» esta vacia y "
            + ("hay codigo que la escribe, asi que nunca corrio"
               if escribe else "NADIE la escribe: es una promesa sin cumplir"))
    cx.close()
    return fuera


def respuestas_sin_dueno():
    """Respuestas de servicio que se escriben y nadie lee."""
    raiz = os.path.join(RAIZ, "work", "servicio")
    if not os.path.isdir(raiz):
        return []
    codigo = _fuentes()
    fuera = []
    for paso in sorted(os.listdir(raiz)):
        d = os.path.join(raiz, paso)
        if not os.path.isdir(d):
            continue
        hay = [f for f in os.listdir(d) if f.endswith(".respuesta.json")]
        if not hay:
            continue
        # Quien la consume la nombra: por el paso, o leyendo su respuesta.
        lee = any(paso in t and ("respuesta" in t or "leeRespuesta" in t
                                 or "leer_respuesta" in t)
                  for f, t in codigo.items() if paso not in f)
        if not lee:
            fuera.append(
                f"«{paso}» tiene {len(hay)} respuesta(s) escritas y ningun otro"
                f" paso las lee: se contestan y se quedan ahi")
    return fuera


def pasos_sin_quien_los_llame():
    """Fases del ciclo cuyo comando no aparece en ningún sitio que lo invoque."""
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    try:
        from dominio.fase import CICLO
    except Exception as e:                         # noqa: BLE001
        return [f"no se pudo leer el ciclo: {e}"]
    codigo = _fuentes()
    fuera = []
    for _n, nombre, cmd in CICLO:
        if not cmd:
            continue                                # servicio de IA, no un script
        script = cmd.split()[0]
        base = os.path.basename(script)
        quien = [f for f, t in codigo.items()
                 if base in t and os.path.basename(f) != base]
        if not quien:
            fuera.append(
                f"la fase «{nombre}» corre «{base}» y nadie lo invoca:"
                f" hay que acordarse de correrlo, o sea que no es un paso")
    return fuera


def formas_sin_componente():
    """Formas de tablero declaradas que no las dibuja nadie.

    El despachador conocía seis formas; el resto caía en `TableroDeclarado`, que
    las pinta como puede. Eso no da error y en pantalla sale un hueco — y hasta
    hace poco salía con el nombre interno de la forma escrito encima, porque el
    componente lo rotulaba «para que se vea qué falta construir». Se quitó de
    ahí y se dice aquí: un informe se lee cuando toca, un rótulo en el frame se
    publica.

    **Y se pregunta al render entero, no a `Ad.tsx`.** El despachador se mudó a
    `src/components/Tablero.tsx` cuando `Ad.tsx` pasó del techo de 300 líneas, y
    esta comprobación se habría quedado mirando un fichero donde ya no está la
    respuesta: habría dicho que **ninguna** forma se despacha, justo el día en
    que todas se despachan. La pregunta nunca fue «¿está en `Ad.tsx`?» sino
    «¿la dibuja alguien?».
    """
    import json

    if not os.path.exists("src/reels.json"):
        return []
    with open("src/reels.json", encoding="utf-8") as f:
        piezas = json.load(f)
    despacha = "\n".join(
        _texto(os.path.join(base, f))
        for base, _d, ficheros in os.walk(os.path.join(RAIZ, "src"))
        for f in ficheros if f.endswith(".tsx"))
    fuera, vistas = [], set()
    for p in piezas:
        for b in (p.get("boards") or []):
            k = b.get("kind")
            if not k or k in vistas:
                continue
            vistas.add(k)
            if f'cue.kind === "{k}"' in despacha:
                continue
            hay = os.path.exists(os.path.join(RAIZ, "src", "components",
                                              f"{k}.tsx"))
            por = ("no la despacha el render" if hay
                   else "no existe su componente")
            fuera.append(f"la forma «{k}» se declara y {por}: cae en"
                         f" TableroDeclarado y sale un hueco")
    return fuera


#: Columnas que parecen catalogo y no lo son: fechas, huellas, rutas y claves
#: que ya apuntan a su tabla. Se declaran para que la cuenta signifique algo.
NO_SON_ENTIDAD = ("fecha", "cuando", "cerrado", "devuelto", "huella", "commit",
                  "fichero", "virgen", "config", "video_slug", "pieza",
                  "video_id", "etapa_id", "slug", "id")


def columnas_que_son_entidad():
    """Texto libre que se repite: un catalogo sin tabla.

    Jaime, 10-9-2026, despues de encontrarme cuatro seguidas: *«cada paso que
    das en la supuesta normalidad es un paso en donde encuentro entidades»*, y
    *«las estoy encontrando yo; tu las mandas por buenas»*. Tenia razon en las
    dos: yo iba diciendo «ya esta normalizado» y el iba senalando la siguiente.

    Asi que la cuenta deja de ser una opinion mia. Una columna con **pocos
    valores distintos, cortos y repetidos muchas veces** es un catalogo: `trato`
    con cinco valores en 62 filas, `plano` con tres, `remedio` con cuatro. Como
    texto libre no se puede declarar, ni relacionar, ni ver que dos etapas usan
    el mismo — y deja pasar que `primer plano` y `primer_plano` sean dos cosas.

    No es una regla de estilo: es la unica forma de que «esto ya esta ordenado»
    sea una medida y no algo que yo digo.
    """
    import sqlite3

    import basedatos

    cx = basedatos.abrir()
    cx.row_factory = sqlite3.Row
    fuera = []
    for (t,) in cx.execute("select name from sqlite_master where type='table'"
                           " order by name"):
        n = cx.execute(f"select count(*) from {t}").fetchone()[0]
        if n < 20:
            continue
        for c in [d[1] for d in cx.execute(f"pragma table_info({t})")]:
            if any(x in c for x in NO_SON_ENTIDAD):
                continue
            try:
                vals = [r[0] for r in cx.execute(
                    f"select {c} from {t} where {c} is not null")
                    if isinstance(r[0], str) and r[0].strip()[:1] not in "{["]
            except sqlite3.Error:
                continue
            if len(vals) < 20:
                continue
            d = len(set(vals))
            if 1 < d <= 20 and max(len(v) for v in vals) <= 30 and d < len(vals) * 0.4:
                fuera.append(
                    f"«{t}.{c}» es un catalogo escrito a mano: {d} valores en"
                    f" {len(vals)} filas ({', '.join(sorted(set(vals))[:4])}...)"
                    f" — sin tabla no se puede declarar ni relacionar")
    cx.close()
    return fuera


def filas_sin_autor():
    """Filas que dicen `quien` y no dicen **cual** autor.

    La migracion de C-365 dejo las 692 con su `autor_id`. Lo que esto impide es
    que se pudra: un `insert` nuevo que escriba solo el texto deja la columna a
    medias, y una clave foranea a medias es peor que no tenerla — parece que se
    puede preguntar por el tipo y a veces no.
    """
    import sqlite3

    import basedatos

    cx = basedatos.abrir()
    fuera = []
    for (t,) in cx.execute("select name from sqlite_master where type='table'"
                           " order by name"):
        cols = [d[1] for d in cx.execute(f"pragma table_info({t})")]
        if "quien" not in cols or "autor_id" not in cols:
            continue
        try:
            n = cx.execute(f"select count(*) from {t} where quien is not null"
                           f" and autor_id is null").fetchone()[0]
        except sqlite3.Error:
            continue
        if n:
            fuera.append(f"«{t}»: {n} fila(s) con `quien` escrito y sin autor"
                         f" declarado — el que las inserta no lo esta poniendo")
    cx.close()
    return fuera


def main():
    faltas = []
    for titulo, fn in (("estado que no se guarda", tablas_muertas),
                       ("respuestas que nadie consume", respuestas_sin_dueno),
                       ("pasos que nadie llama", pasos_sin_quien_los_llame),
                       ("formas que nadie dibuja", formas_sin_componente),
                       ("columnas que son una entidad", columnas_que_son_entidad),
                       ("filas sin autor", filas_sin_autor)):
        malas = fn()
        if malas:
            print(f"\n{titulo}:")
            for m in malas:
                print(f"  · {m}")
        faltas += malas
    print(f"\nconectado: {len(faltas)} cable(s) sueltos"
          if faltas else "\nconectado: todo lo que se produce tiene quien lo lea.")
    return 1 if faltas else 0


if __name__ == "__main__":
    raise SystemExit(main())
