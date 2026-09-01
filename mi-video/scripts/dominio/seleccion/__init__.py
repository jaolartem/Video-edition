"""Los sustantivos de **elegir qué trozo de cinta es cada etapa**.

`seleccionar.py` eran 1.599 líneas y 28 funciones sueltas, y dentro convivían
tres trabajos que no son el mismo: **medir** una ventana, **decidir** cuál se
queda y **escribir** lo decidido. Mezclados, un peso mal puesto puede estar
diez veces por debajo de lo debido sin que nadie lo vea — pasó con
`PESO_CUELGA`, y `PESO_REPE` llegó a estar declarado y nunca aplicado.

Aquí cada uno tiene su sitio:

| Fichero | De qué es dueño |
|---|---|
| `pesos.py`    | los números con los que se corta, juntos y a la vista |
| `ventana.py`  | la ventana y **lo que se mide sobre ella** |
| `corpus.py`   | las ventanas de todas las cintas, y las palabras de cada una |
| `tijeras.py`  | lo que sobra de la elegida: extremos, repetición y costura |
| `reparto.py`  | quién se queda con qué trozo, y la última palabra de Jaime |
| `entrega.py`  | entre las que dicen lo mismo, gana la que lo dice con más voz |
| `edl.py`      | el corte, escrito donde el montaje lo lee |
| `eleccion.py` | la decisión, escrita en el modelo |
| `informe.py`  | lo que se cuenta por pantalla |
| `pieza.py`    | la corrida entera de una pieza, paso a paso |

**Por qué es un subpaquete y no diez ficheros en `dominio/`.** Porque `pesos`,
`ventana` o `corpus` son nombres que cualquier otra parte del proyecto querría,
y dos módulos distintos con el mismo nombre no chocan: **uno se lleva al otro
por delante**. Lo que aquí se llama `Ventana` es la candidata de la selección, y
el nombre dice de qué selección habla.
"""
