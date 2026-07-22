"""
datos_zonas.py

Datos del mapa de Quito: zonas (con coordenadas para dibujar en Pygame),
los dos locales de despacho, y las conexiones (calles) entre ellas con su
peso (distancia estimada en km).

Mantener los datos separados de grafo.py permite que grafo.py sea
puramente la estructura de datos + el algoritmo, reutilizable con
cualquier conjunto de zonas.
"""

from grafo import Zona, GrafoCiudad

ZONAS = [
    # --- Sector Norte ---
    ("Calderon", 430, 10, False),
    ("Ponceano", 320, 40, False),
    ("Local A - Norte", 400, 60, True),
    ("El Condado", 200, 110, False),
    ("Carcelen", 300, 100, False),
    ("Comite del Pueblo", 570, 120, False),
    ("El Inca", 505, 160, False),
    ("Cotocollao", 380, 150, False),
    ("Kennedy", 610, 190, False),
    ("Iñaquito", 460, 200, False),
    ("El Bosque", 340, 220, False),
    ("La Carolina", 480, 245, False),

    # --- Centro ---
    ("La Mariscal", 430, 280, False),
    ("Guapulo", 520, 300, False),
    ("Cumbaya", 620, 260, False),
    ("La Floresta", 470, 310, False),
    ("Centro Historico", 400, 340, False),
    ("Itchimbia", 490, 375, False),
    ("La Libertad", 330, 355, False),

    # --- Sector Sur ---
    ("La Magdalena", 380, 400, False),
    ("Chimbacalle", 460, 455, False),
    ("Chilibulo", 240, 430, False),
    ("Chillogallo", 300, 460, False),
    ("La Ferroviaria", 410, 495, False),
    ("Solanda", 280, 545, False),
    ("San Rafael", 520, 520, False),
    ("Quitumbe", 410, 560, False),
    ("Turubamba", 340, 600, False),
    ("Local B - Sur", 400, 640, True),
    ("Guamani", 300, 660, False),

    ("Zona Aislada", 700, 500, False),
]

CONEXIONES = [
    # --- conexiones originales ---
    ("Local A - Norte", "Carcelen", 4),
    ("Local A - Norte", "Cotocollao", 3),
    ("Carcelen", "Cotocollao", 3),
    ("Cotocollao", "Iñaquito", 5),
    ("Cotocollao", "El Bosque", 4),
    ("Iñaquito", "El Bosque", 3),
    ("Iñaquito", "La Mariscal", 4),
    ("Iñaquito", "Guapulo", 6),
    ("El Bosque", "La Mariscal", 3),
    ("La Mariscal", "Centro Historico", 5),
    ("La Mariscal", "Guapulo", 4),
    ("Guapulo", "Cumbaya", 5),
    ("Centro Historico", "Guapulo", 6),
    ("Centro Historico", "La Magdalena", 4),
    ("La Magdalena", "Chillogallo", 6),
    ("La Magdalena", "San Rafael", 7),
    ("Chillogallo", "Quitumbe", 4),
    ("Quitumbe", "Local B - Sur", 3),
    ("San Rafael", "Local B - Sur", 5),
    ("Chillogallo", "Local B - Sur", 4),

    # --- Sector Norte (nuevas) ---
    ("Local A - Norte", "Calderon", 5),
    ("Calderon", "Ponceano", 4),
    ("Ponceano", "Carcelen", 3),
    ("Ponceano", "Local A - Norte", 3),
    ("El Condado", "Carcelen", 3),
    ("El Condado", "Cotocollao", 4),
    ("Comite del Pueblo", "Iñaquito", 3),
    ("Comite del Pueblo", "El Inca", 2),
    ("El Inca", "Iñaquito", 2),
    ("El Inca", "Kennedy", 3),
    ("Kennedy", "Guapulo", 3),
    ("La Carolina", "Iñaquito", 2),
    ("La Carolina", "La Mariscal", 2),

    # --- Centro (nuevas) ---
    ("La Floresta", "La Mariscal", 2),
    ("La Floresta", "Centro Historico", 3),
    ("Itchimbia", "Centro Historico", 3),
    ("Itchimbia", "Guapulo", 4),
    ("La Libertad", "Centro Historico", 2),
    ("La Libertad", "La Magdalena", 3),

    # --- Sector Sur (nuevas) ---
    ("Chimbacalle", "La Magdalena", 3),
    ("Chimbacalle", "La Ferroviaria", 2),
    ("Chilibulo", "La Magdalena", 3),
    ("Chilibulo", "Chillogallo", 2),
    ("La Ferroviaria", "Chillogallo", 2),
    ("La Ferroviaria", "Solanda", 3),
    ("Solanda", "Quitumbe", 2),
    ("Solanda", "Chillogallo", 3),
    ("Turubamba", "Quitumbe", 3),
    ("Turubamba", "Local B - Sur", 2),
    ("Guamani", "Turubamba", 3),
    ("Guamani", "Local B - Sur", 4),
]


def construir_grafo_quito() -> GrafoCiudad:
    """Arma y devuelve el GrafoCiudad de Quito ya poblado con zonas y conexiones."""
    grafo = GrafoCiudad()

    for nombre, x, y, es_local in ZONAS:
        grafo.agregar_zona(Zona(nombre, x, y, es_local))

    for zona_a, zona_b, peso in CONEXIONES:
        grafo.agregar_conexion(zona_a, zona_b, peso)

    grafo.construir_arbol_expansion_minima()

    return grafo


LOCALES = ["Local A - Norte", "Local B - Sur"]
