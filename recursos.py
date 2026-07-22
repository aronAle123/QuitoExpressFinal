import os
import sys

def recurso(ruta):
    """
    Devuelve la ruta absoluta de un recurso, tanto al ejecutar el
    proyecto desde el código fuente como desde el ejecutable generado
    con PyInstaller.
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, ruta)