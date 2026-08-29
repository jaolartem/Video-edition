"""Sustituye en el Reel 2 los intentos con «al mes» por la toma limpia.

Qué pasa
--------
En el bruto Jaime **se corrige en directo**. El transcript lo enseña cuatro
veces:

    24.90  «se gana 180.000, se gana 180.000 al mes, un»
    41.40  «y factura mas o menos 180.000 al mes, y»
    45.50  «180.000 al mes, y factura 180.000 al año, un»   <- se corrige
    75.98  «gana mas o menos 180 mil al mes, al año.»       <- se corrige
   104.93  «se gana 180.000 al año de los buenos»           <- toma limpia

El EDL montado usa `67.84–76.61` y `79.67–81.60`, o sea **el intento con el
error y su correccion**. En pantalla eso suena a «180 mil al mes… al año», y si
alguien se queda con la primera mitad, la cifra que sale es 2,16 millones al
año: el ejemplo del electricista deja de tener sentido.

La toma limpia de 95.9 a 113.7 dice lo mismo de una vez y sin tropiezo:

    «un electricista en Brampton, tiene dos contratos, trabaja fines de semana,
     se gana 180.000 al año de los buenos. De cada 100 dolares que el recibe, el
     le tiene que dar al CRA 56 y se queda con 44.»

Por que esto SI lo decide el script
-----------------------------------
El aprendizaje 13 dice que las heuristicas limpian pero no eligen, y aqui no se
esta eligiendo: no hay dos candidatos buenos entre los que decidir por gusto.
Hay una cifra mal dicha en un anuncio financiero, y el orden de prioridad del
proyecto pone el cumplimiento por delante de todo lo demas.

Lo que NO toca: el gancho. Va de 67.84 a 72.84 y el «al mes» aparece en 75.98,
asi que el gancho ya estaba limpio.

Ojo aparte, para decidir fuera
------------------------------
La toma limpia dice **«al CRA 56 y se queda con 44»**; el libreto dice que el
gobierno se queda con 54 y le quedan 46. Es una discrepancia entre guion y
grabacion, y —igual que con la fecha— **cual de los dos esta mal lo decide quien
conoce el hecho**, no este script.
"""
import json

EDL = "ads/reel-02/edl-sell.json"
# Los dos tramos que llevan el error y su correccion.
FUERA = [(67.84, 76.61), (79.67, 81.60)]
# La toma limpia, recortada a fronteras de tramo de habla.
DENTRO = [(95.917, 99.983), (100.033, 104.361), (104.571, 107.318)]


def main():
    d = json.load(open(EDL, encoding="utf-8"))
    antes = list(d["segmentos"])
    quitados = [s for s in antes
                if any(abs(s[0] - a) < 0.02 and abs(s[1] - b) < 0.02
                       for a, b in FUERA)]
    if not quitados:
        print("nada que sustituir: el EDL ya no lleva esos tramos")
        return
    resto = [s for s in antes if s not in quitados]
    nuevos = [[a, b] for a, b in DENTRO]
    d["segmentos"] = sorted(nuevos + resto, key=lambda s: s[0])
    d["duracion_montada_s"] = round(sum(b - a for a, b in d["segmentos"]), 2)
    d.setdefault("revision", {})["cifra_180k"] = (
        "Sustituidos los intentos con «al mes» (67.84-76.61, 79.67-81.60) por la "
        "toma limpia 95.92-107.32, que dice «al año». Pendiente aparte: la toma "
        "dice «al CRA 56 / se queda con 44» y el libreto dice 54/46."
    )
    json.dump(d, open(EDL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"fuera:  {quitados}")
    print(f"dentro: {nuevos}")
    print(f"duracion montada -> {d['duracion_montada_s']}s")


if __name__ == "__main__":
    main()
