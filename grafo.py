

import heapq
import random
from collections import deque

FACTOR_MIN_POR_KM = 2.5


def distancia_a_tiempo_min(distancia_km: float, factor: float = FACTOR_MIN_POR_KM) -> float:
    """Convierte una distancia total (km) en un tiempo estimado de viaje (minutos)."""
    return distancia_km * factor


class Zona:
    """Un nodo del grafo: una zona/sector de Quito o un local de despacho."""

    def __init__(self, nombre, x, y, es_local=False):
        self.nombre = nombre
        self.x = x
        self.y = y
        self.es_local = es_local

    def __repr__(self):
        tipo = "LOCAL" if self.es_local else "zona"
        return f"Zona({self.nombre!r}, {tipo})"


class GrafoCiudad:
    """
    Grafo ponderado no dirigido.

    self.zonas: dict {nombre: Zona}
    self.adyacencia: dict {nombre: dict {vecino: peso}}  <- grafo original completo

    self.arbol_adyacencia: dict {nombre: dict {vecino: peso}}  <- SOLO las
        aristas del Arbol de Expansion Minima (Prim), calculado una vez por
        construir_arbol_expansion_minima() y usado por todas las busquedas
        de ruta (camino_en_arbol, ruta_multi_tramo, zona_mas_cercana).
    self.arbol_aristas: list [(zona_a, zona_b, peso), ...]  <- aristas del MST
    self.arbol_costo_total: float  <- suma de pesos del MST

    self.aristas_bloqueadas: set(frozenset({zona_a, zona_b}))  <- "accidentes"
        activos (ver bloquear_arista/reparar_arista). Toda arista en este
        set queda excluida de construir_arbol_expansion_minima() hasta que
        se repare, forzando a Prim a reconstruir el arbol evitandola.
    """

    def __init__(self):
        self.zonas = {}
        self.adyacencia = {}
        self.arbol_adyacencia = {}
        self.arbol_aristas = []
        self.arbol_costo_total = 0.0
        self.aristas_bloqueadas = set()

    def agregar_zona(self, zona: Zona):
        self.zonas[zona.nombre] = zona
        self.adyacencia.setdefault(zona.nombre, {})

    def agregar_conexion(self, zona_a: str, zona_b: str, peso: float):
        """Agrega una calle entre dos zonas. No dirigido: se registra en ambos sentidos."""
        if zona_a not in self.zonas or zona_b not in self.zonas:
            raise ValueError(f"No se puede conectar: '{zona_a}' o '{zona_b}' no existen en el grafo")
        self.adyacencia[zona_a][zona_b] = peso
        self.adyacencia[zona_b][zona_a] = peso

    def construir_arbol_expansion_minima(self):
        """
        Construye el Arbol de Expansion Minima (MST) de todo el grafo con el
        algoritmo de Prim, usando un heap de prioridad para elegir siempre
        la arista mas barata que conecte un nodo ya incluido con uno que
        todavia no lo esta. Se calcula UNA sola vez y se guarda en
        self.arbol_adyacencia / self.arbol_aristas / self.arbol_costo_total
        para que el resto del programa lo reutilice sin recalcularlo.

        Si el grafo tiene zonas desconectadas del resto (como la "Zona
        Aislada", que existe a proposito para el caso de "sin cobertura"),
        Prim -corriendo desde una sola semilla- nunca las alcanzaria. Por
        eso aqui se recorre cada componente conexa por separado (se arranca
        Prim de nuevo desde cualquier nodo no visitado que quede) y se arma
        un BOSQUE de expansion minima: cada componente queda conectada con
        costo minimo puertas adentro, y las componentes distintas
        simplemente no quedan conectadas entre si. Eso es correcto y
        esperado, no un error.

        Cualquier arista en self.aristas_bloqueadas (un "accidente" activo,
        ver bloquear_arista) se ignora por completo aqui, en ambos sentidos:
        Prim nunca la ve como candidata, asi que el arbol resultante la
        evita, aunque eso signifique conectar esa zona por un camino mas
        largo/caro (o, en el caso extremo de que fuera la unica conexion de
        una zona, dejarla temporalmente sin cobertura hasta que se repare).

        Retorna (arbol_aristas, arbol_costo_total, arbol_adyacencia).
        """
        self.arbol_adyacencia = {nombre: {} for nombre in self.zonas}
        self.arbol_aristas = []
        self.arbol_costo_total = 0.0

        visitados = set()

        for semilla in self.zonas:
            if semilla in visitados:
                continue

            # --- Prim estandar, para la componente conexa de "semilla" ---
            visitados.add(semilla)
            heap = []
            for vecino, peso in self.adyacencia[semilla].items():
                if not self.arista_esta_bloqueada(semilla, vecino):
                    heapq.heappush(heap, (peso, vecino, semilla))

            while heap:
                peso, nodo_nuevo, nodo_en_arbol = heapq.heappop(heap)
                if nodo_nuevo in visitados:
                    continue

                visitados.add(nodo_nuevo)
                self.arbol_adyacencia[nodo_en_arbol][nodo_nuevo] = peso
                self.arbol_adyacencia[nodo_nuevo][nodo_en_arbol] = peso
                self.arbol_aristas.append((nodo_en_arbol, nodo_nuevo, peso))
                self.arbol_costo_total += peso

                for vecino, peso_vecino in self.adyacencia[nodo_nuevo].items():
                    if vecino not in visitados and not self.arista_esta_bloqueada(nodo_nuevo, vecino):
                        heapq.heappush(heap, (peso_vecino, vecino, nodo_nuevo))

        return self.arbol_aristas, self.arbol_costo_total, self.arbol_adyacencia

    def camino_en_arbol(self, origen: str, destino: str):
        """
        Encuentra el camino entre origen y destino DENTRO del Arbol de
        Expansion Minima (self.arbol_adyacencia), no en el grafo original.

        Importante: esto NO es Dijkstra. No compara ni acumula pesos para
        elegir entre varias rutas posibles, porque dentro de un arbol no
        existen rutas alternativas: un arbol no tiene ciclos, asi que entre
        dos nodos cualesquiera hay exactamente un camino (si hubiera dos,
        se cerraria un ciclo). Por eso alcanza con una busqueda simple
        (BFS) que registre "desde que nodo se llego a cada nodo" y despues
        reconstruya el camino siguiendo ese rastro hacia atras desde el
        destino: no hay ninguna decision de "cual es mejor" que tomar.

        Retorna (ruta, costo) donde ruta es una lista de nombres de zona
        desde origen hasta destino (ambos incluidos).
        Si destino no es alcanzable dentro del arbol (ej. esta en otra
        componente, como la "Zona Aislada"), retorna (None, None):
        "sin cobertura de entrega disponible".
        """
        if origen not in self.zonas or destino not in self.zonas:
            return None, None
        if origen == destino:
            return [origen], 0

        previo = {origen: None}
        cola = deque([origen])

        while cola:
            actual = cola.popleft()
            if actual == destino:
                break
            for vecino in self.arbol_adyacencia.get(actual, {}):
                if vecino not in previo:
                    previo[vecino] = actual
                    cola.append(vecino)

        if destino not in previo:
            return None, None

        ruta = []
        nodo = destino
        while nodo is not None:
            ruta.append(nodo)
            nodo = previo[nodo]
        ruta.reverse()

        costo = sum(self.arbol_adyacencia[a][b] for a, b in zip(ruta, ruta[1:]))
        return ruta, costo

    def ruta_multi_tramo(self, puntos: list[str]):
        """
        Arma una ruta que pasa por todos los puntos en orden (por ejemplo
        Local -> Pickup -> Parada1 -> Parada2 -> Dropoff), siguiendo el
        camino dentro del Arbol de Expansion Minima tramo por tramo entre
        cada par consecutivo y encadenando los caminos.

        Retorna (ruta_completa, costo_total) o (None, None) si algun tramo
        no tiene cobertura.
        """
        ruta_completa = [puntos[0]]
        costo_total = 0

        for origen, destino in zip(puntos, puntos[1:]):
            tramo, costo_tramo = self.camino_en_arbol(origen, destino)
            if tramo is None:
                return None, None
            ruta_completa += tramo[1:]
            costo_total += costo_tramo

        return ruta_completa, costo_total

    def ruta_encadenada(self, local: str, pickup: str, dropoff: str):
        """
        Arma la ruta completa del repartidor: Local -> Pickup -> Dropoff.
        Atajo de ruta_multi_tramo para el caso sin paradas intermedias.
        """
        return self.ruta_multi_tramo([local, pickup, dropoff])

    def zona_mas_cercana(self, origen: str, candidatos: list[str]):
        """
        Busca, dentro del Arbol de Expansion Minima, el camino desde origen
        hacia cada candidato (normalmente los locales) y devuelve
        (nombre_candidato_mas_cercano, distancia). Usado por el arbol de
        asignacion de local.
        Si ningun candidato tiene cobertura, retorna (None, None).
        """
        mejor_candidato = None
        mejor_distancia = float("inf")

        for candidato in candidatos:
            _, distancia = self.camino_en_arbol(origen, candidato)
            if distancia is not None and distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_candidato = candidato

        if mejor_candidato is None:
            return None, None
        return mejor_candidato, mejor_distancia

    def dfs(self, inicio: str) -> list:
        """
        Recorrido en profundidad (DFS) sobre el GRAFO ORIGINAL completo
        (self.adyacencia, no el Arbol de Expansion Minima): parte de
        `inicio` y, por cada vecino, se mete lo mas lejos posible antes de
        retroceder a probar el siguiente. Devuelve la lista de zonas en el
        orden en que fueron visitadas.
        """
        visitadas = []
        vistas = set()

        def _visitar(nodo):
            vistas.add(nodo)
            visitadas.append(nodo)
            for vecino in self.adyacencia.get(nodo, {}):
                if vecino not in vistas:
                    _visitar(vecino)

        if inicio in self.zonas:
            _visitar(inicio)
        return visitadas

    def bfs(self, inicio: str) -> list:
        """
        Recorrido en anchura (BFS) sobre el grafo original: desde `inicio`
        visita primero todos sus vecinos directos, luego los vecinos de
        esos vecinos, y asi sucesivamente, usando una cola (deque).
        Devuelve la lista de zonas en el orden en que fueron visitadas.
        """
        if inicio not in self.zonas:
            return []

        visitadas = [inicio]
        vistas = {inicio}
        cola = deque([inicio])

        while cola:
            actual = cola.popleft()
            for vecino in self.adyacencia.get(actual, {}):
                if vecino not in vistas:
                    vistas.add(vecino)
                    visitadas.append(vecino)
                    cola.append(vecino)

        return visitadas

    def zonas_con_cobertura(self, origen: str) -> set:
        """
        Devuelve el conjunto de zonas alcanzables desde `origen` en el
        grafo original, apoyandose en BFS. Sirve como verificacion real de
        "cobertura de entrega": si una zona (ej. "Zona Aislada") no
        aparece en el resultado partiendo de ningun local, es evidencia de
        un recorrido de verdad -no solo la apariencia visual del mapa- de
        que esa zona nunca podria recibir un pedido.
        """
        return set(self.bfs(origen))

    # -----------------------------------------------------------------
    # "Accidentes": bloqueo/reparacion de calles (aristas) del grafo
    # -----------------------------------------------------------------

    def arista_esta_bloqueada(self, zona_a: str, zona_b: str) -> bool:
        return frozenset((zona_a, zona_b)) in self.aristas_bloqueadas

    def bloquear_arista(self, zona_a: str, zona_b: str):
        """
        Simula un accidente: marca la calle (zona_a, zona_b) como
        bloqueada y reconstruye el Arbol de Expansion Minima con Prim
        excluyendola. Quien llama es responsable de recalcular, si hace
        falta, la ruta de cualquier pedido activo que dependiera de esta
        arista (ver main.py: simular_accidente).
        """
        self.aristas_bloqueadas.add(frozenset((zona_a, zona_b)))
        self.construir_arbol_expansion_minima()

    def reparar_arista(self, zona_a: str, zona_b: str):
        """
        Quita el bloqueo de (zona_a, zona_b) y reconstruye el MST
        incluyendola de nuevo. A proposito NO recalcula ninguna ruta ya en
        curso: reparar una calle no debe forzar que un pedido que ya
        encontro un camino alternativo "regrese" a usar la calle reparada,
        eso seria un recalculo innecesario.
        """
        self.aristas_bloqueadas.discard(frozenset((zona_a, zona_b)))
        self.construir_arbol_expansion_minima()

    def elegir_arista_para_accidente(self, rutas_referencia: list = None):
        """
        Elige al azar una arista todavia no bloqueada para simular un
        accidente. `rutas_referencia` es una lista de rutas (el tramo aun
        no recorrido de cada pedido activo, en orden; puede haber varios
        pedidos corriendo en paralelo); si alguna aporta una arista
        bloqueable, se prefiere una de esas, para que el efecto del
        bloqueo sea visible de inmediato sobre alguna ruta que se esta
        mostrando en el mapa. Si no hay pedidos activos (o ninguno aporta
        una arista bloqueable), se elige cualquier arista del grafo
        original al azar.

        Retorna (zona_a, zona_b) o None si ya no queda ninguna arista sin
        bloquear en todo el grafo.
        """
        candidatas = []
        for ruta in (rutas_referencia or []):
            if ruta and len(ruta) >= 2:
                candidatas.extend(
                    (a, b) for a, b in zip(ruta, ruta[1:])
                    if not self.arista_esta_bloqueada(a, b)
                )

        if not candidatas:
            vistas = set()
            for origen, vecinos in self.adyacencia.items():
                for destino in vecinos:
                    clave = frozenset((origen, destino))
                    if clave in vistas or self.arista_esta_bloqueada(origen, destino):
                        continue
                    vistas.add(clave)
                    candidatas.append((origen, destino))

        if not candidatas:
            return None
        return random.choice(candidatas)


if __name__ == "__main__":
    from datos_zonas import construir_grafo_quito

    grafo = construir_grafo_quito()

    print("=== Prueba 0: Arbol de Expansion Minima (Prim) ===")
    print(f"Zonas en el grafo original: {len(grafo.zonas)}")
    zonas_en_arbol = {nombre for nombre, vecinos in grafo.arbol_adyacencia.items() if vecinos}
    print(f"Zonas conectadas en el MST: {len(zonas_en_arbol)} (+1 si alguna quedo aislada sin vecinos)")
    print(f"Aristas del MST: {len(grafo.arbol_aristas)}")
    print(f"Costo total del MST (km): {grafo.arbol_costo_total}")
    zonas_fuera = set(grafo.zonas) - zonas_en_arbol
    print(f"Zonas sin conexion en el MST (esperado: 'Zona Aislada'): {zonas_fuera}")

    print()
    print("=== Prueba 1: ruta encadenada Local A -> Cumbaya -> Centro Historico ===")
    ruta, costo = grafo.ruta_encadenada("Local A - Norte", "Cumbaya", "Centro Historico")
    if ruta:
        print("Ruta:", " -> ".join(ruta))
        print("Costo total (km):", costo, "-> tiempo estimado (min):", distancia_a_tiempo_min(costo))
    else:
        print("sin cobertura de entrega disponible")

    print()
    print("=== Prueba 1b: ruta multi-tramo con 2 paradas (Local A -> Cotocollao -> Kennedy -> Solanda -> Local B) ===")
    ruta_multi, costo_multi = grafo.ruta_multi_tramo(
        ["Local A - Norte", "Cotocollao", "Kennedy", "Solanda", "Local B - Sur"]
    )
    if ruta_multi:
        print("Ruta:", " -> ".join(ruta_multi))
        print("Costo total (km):", costo_multi)
    else:
        print("sin cobertura de entrega disponible")

    print()
    print("=== Prueba 2: zona mas cercana a Quitumbe entre los dos locales ===")
    local, distancia = grafo.zona_mas_cercana("Quitumbe", ["Local A - Norte", "Local B - Sur"])
    print(f"Local mas cercano: {local} (distancia {distancia})")

    print()
    print("=== Prueba 3: caso sin cobertura (zona aislada) ===")
    ruta, costo = grafo.camino_en_arbol("Local A - Norte", "Zona Aislada")
    if ruta is None:
        print("sin cobertura de entrega disponible")
    else:
        print("Ruta:", " -> ".join(ruta), "Costo:", costo)

    print()
    print("=== Prueba 4: DFS vs BFS desde 'Local A - Norte' (grafo original, no el MST) ===")
    orden_dfs = grafo.dfs("Local A - Norte")
    orden_bfs = grafo.bfs("Local A - Norte")
    print(f"DFS ({len(orden_dfs)} zonas): {orden_dfs}")
    print()
    print(f"BFS ({len(orden_bfs)} zonas): {orden_bfs}")
    print()
    print(f"Mismas zonas visitadas: {set(orden_dfs) == set(orden_bfs)} | Mismo orden: {orden_dfs == orden_bfs}")

    print()
    print("=== Prueba 5: cobertura de entrega real (BFS) desde cada local ===")
    for local in ("Local A - Norte", "Local B - Sur"):
        cobertura = grafo.zonas_con_cobertura(local)
        print(f"{local}: cubre {len(cobertura)} zonas. 'Zona Aislada' cubierta: {'Zona Aislada' in cobertura}")

    print()
    print("=== Prueba 6: accidente (bloqueo de arista) fuerza a Prim a reconstruir el MST ===")
    ruta_previa, costo_previo = grafo.ruta_encadenada("Local A - Norte", "Cotocollao", "Centro Historico")
    print("Ruta ANTES del accidente:", " -> ".join(ruta_previa), "| costo:", costo_previo)

    zona_a, zona_b = "Local A - Norte", "Cotocollao"
    en_mst_antes = zona_b in grafo.arbol_adyacencia.get(zona_a, {})
    print(f"'{zona_a} <-> {zona_b}' estaba en el MST antes de bloquear: {en_mst_antes}")

    grafo.bloquear_arista(zona_a, zona_b)
    en_mst_despues = zona_b in grafo.arbol_adyacencia.get(zona_a, {})
    print(f"'{zona_a} <-> {zona_b}' bloqueada: {grafo.arista_esta_bloqueada(zona_a, zona_b)}")
    print(f"'{zona_a} <-> {zona_b}' sigue en el MST reconstruido: {en_mst_despues} (debe ser False)")

    ruta_nueva, costo_nuevo = grafo.ruta_encadenada("Local A - Norte", "Cotocollao", "Centro Historico")
    print("Ruta DESPUES del accidente:", " -> ".join(ruta_nueva), "| costo:", costo_nuevo)

    grafo.reparar_arista(zona_a, zona_b)
    print(f"'{zona_a} <-> {zona_b}' bloqueada tras reparar: {grafo.arista_esta_bloqueada(zona_a, zona_b)}")
    print(f"'{zona_a} <-> {zona_b}' vuelve a estar en el MST: {zona_b in grafo.arbol_adyacencia.get(zona_a, {})}")

    print()
    print("=== Prueba 7: eleccion de arista para un accidente, con y sin pedido activo ===")
    ruta_activa, _ = grafo.ruta_encadenada("Local A - Norte", "Kennedy", "Solanda")
    arista_con_ruta = grafo.elegir_arista_para_accidente([ruta_activa])
    print(f"Con pedido activo (ruta {len(ruta_activa)} zonas) -> arista elegida: {arista_con_ruta}")
    arista_sin_ruta = grafo.elegir_arista_para_accidente(None)
    print(f"Sin pedido activo -> arista elegida al azar: {arista_sin_ruta}")
