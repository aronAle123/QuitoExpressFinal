

from collections import deque


class NodoArbol:
    """Nodo generico de arbol: interno (con hijos por rama) u hoja (con valor)."""

    def __init__(self, etiqueta, es_hoja=False, valor=None):
        self.etiqueta = etiqueta
        self.es_hoja = es_hoja
        self.valor = valor
        self.hijos = []

    def agregar_hijo(self, rama: str, nodo: "NodoArbol"):
        self.hijos.append((rama, nodo))

    def hijo(self, rama: str) -> "NodoArbol":
        """Busca un hijo por su etiqueta de rama (ej. 'si', 'A_mas_cerca')."""
        for etiqueta_rama, nodo in self.hijos:
            if etiqueta_rama == rama:
                return nodo
        raise KeyError(rama)

    def ramas(self):
        return [etiqueta_rama for etiqueta_rama, _ in self.hijos]

    def nodos_hijos(self):
        return [nodo for _, nodo in self.hijos]

    def preorden(self, fn):
        """Nodo actual primero, despues cada hijo (izquierda a derecha), recursivo."""
        fn(self)
        for hijo in self.nodos_hijos():
            hijo.preorden(fn)

    def postorden(self, fn):
        """Todos los hijos primero (izquierda a derecha), el nodo actual al final."""
        for hijo in self.nodos_hijos():
            hijo.postorden(fn)
        fn(self)

    def inorden(self, fn):
        """
        In-orden clasico: subarbol izquierdo, raiz, subarbol derecho -
        definido estrictamente para arboles BINARIOS (2 hijos). Aqui se
        generaliza para cualquier cantidad de hijos partiendo la lista de
        hijos a la mitad: la primera mitad se visita antes que el nodo, la
        segunda despues. Con 2 hijos esto coincide exactamente con la
        definicion clasica (hijos[0], self, hijos[1]); con 0 o 1 hijos se
        reduce a visitar primero lo que haya antes de la mitad y despues
        el resto, que para una hoja es simplemente fn(self).
        """
        hijos = self.nodos_hijos()
        mitad = len(hijos) // 2
        for hijo in hijos[:mitad]:
            hijo.inorden(fn)
        fn(self)
        for hijo in hijos[mitad:]:
            hijo.inorden(fn)

    def por_niveles(self, fn):
        """
        Recorrido en amplitud (BFS sobre el arbol): raiz primero, despues
        el resto de nodos ordenados por nivel, de izquierda a derecha
        dentro de cada nivel. A diferencia de los otros 3, necesita una
        cola (no recursion) porque procesa nivel por nivel.
        """
        cola = deque([self])
        while cola:
            nodo = cola.popleft()
            fn(nodo)
            cola.extend(nodo.nodos_hijos())

    def __repr__(self):
        if self.es_hoja:
            return f"Hoja({self.etiqueta!r} -> {self.valor!r})"
        return f"Nodo({self.etiqueta!r}, ramas={self.ramas()})"


class ArbolAsignacionLocal:
    """
    Arbol de decision de 2 niveles para elegir el local que despacha el pedido.

    raiz: "que local esta mas cerca" -> rama A_mas_cerca / B_mas_cerca
      -> nodo interno: "tiene repartidor disponible" -> rama si / no
        -> hoja: nombre del local asignado
    """

    LOCAL_A = "Local A - Norte"
    LOCAL_B = "Local B - Sur"

    def __init__(self):
        self.raiz = NodoArbol("Que local esta mas cerca del pickup")

        nodo_a = NodoArbol("Local A disponible")
        nodo_a.agregar_hijo("si", NodoArbol("Asignar A", es_hoja=True, valor=self.LOCAL_A))
        nodo_a.agregar_hijo("no", NodoArbol("Failover a B", es_hoja=True, valor=self.LOCAL_B))

        nodo_b = NodoArbol("Local B disponible")
        nodo_b.agregar_hijo("si", NodoArbol("Asignar B", es_hoja=True, valor=self.LOCAL_B))
        nodo_b.agregar_hijo("no", NodoArbol("Failover a A", es_hoja=True, valor=self.LOCAL_A))

        self.raiz.agregar_hijo("A_mas_cerca", nodo_a)
        self.raiz.agregar_hijo("B_mas_cerca", nodo_b)

    def decidir(self, distancia_a, distancia_b, disponible_a: bool, disponible_b: bool) -> str:
        """Recorre el arbol y devuelve el nombre del local asignado."""
        if distancia_a is None and distancia_b is None:
            return None

        if distancia_b is None or (distancia_a is not None and distancia_a <= distancia_b):
            rama_nivel1 = "A_mas_cerca"
            disponible_local_cercano = disponible_a
        else:
            rama_nivel1 = "B_mas_cerca"
            disponible_local_cercano = disponible_b

        nodo_nivel2 = self.raiz.hijo(rama_nivel1)
        rama_nivel2 = "si" if disponible_local_cercano else "no"
        hoja = nodo_nivel2.hijo(rama_nivel2)

        return hoja.valor


class ArbolTipoServicio:
    """
    Clasifica el pedido en 3 hojas. Cada hoja trae la prioridad de cola
    (1 = mas alta) y el multiplicador de tiempo de entrega.
    """

    def __init__(self):
        self.raiz = NodoArbol("Tipo de pedido")
        self.raiz.agregar_hijo("comida", NodoArbol(
            "Comida", es_hoja=True,
            valor={"tipo": "Comida", "prioridad": 1, "multiplicador_tiempo": 1.0},
        ))
        self.raiz.agregar_hijo("documento", NodoArbol(
            "Documento", es_hoja=True,
            valor={"tipo": "Documento", "prioridad": 2, "multiplicador_tiempo": 1.0},
        ))
        self.raiz.agregar_hijo("paquete", NodoArbol(
            "Paquete", es_hoja=True,
            valor={"tipo": "Paquete", "prioridad": 3, "multiplicador_tiempo": 1.5},
        ))

    def clasificar(self, tipo: str) -> dict:
        clave = tipo.strip().lower()
        if clave not in self.raiz.ramas():
            opciones = ", ".join(self.raiz.ramas())
            raise ValueError(f"Tipo de pedido desconocido: {tipo!r}. Opciones: {opciones}")
        return self.raiz.hijo(clave).valor


if __name__ == "__main__":
    print("=== Arbol de asignacion de local ===")
    arbol_local = ArbolAsignacionLocal()

    casos = [
        (10, 25, True, True, "A mas cerca y disponible"),
        (10, 25, False, True, "A mas cerca pero SIN repartidores -> debe caer a B"),
        (30, 12, True, True, "B mas cerca y disponible"),
        (30, 12, False, False, "B mas cerca pero ninguno disponible -> failover a A igual"),
    ]
    for distancia_a, distancia_b, disponible_a, disponible_b, descripcion in casos:
        resultado = arbol_local.decidir(distancia_a, distancia_b, disponible_a, disponible_b)
        print(f"- {descripcion}: asignado -> {resultado}")

    print()
    print("=== Arbol de tipo de servicio ===")
    arbol_servicio = ArbolTipoServicio()
    for tipo in ["Comida", "Documento", "Paquete"]:
        info = arbol_servicio.clasificar(tipo)
        print(f"- {tipo}: prioridad={info['prioridad']} multiplicador_tiempo={info['multiplicador_tiempo']}")

    def _demostrar_4_recorridos(nombre_arbol, raiz):
        print()
        print(f"=== Los 4 recorridos sobre: {nombre_arbol} ===")
        for etiqueta, metodo in [
            ("Pre-orden  ", raiz.preorden),
            ("Post-orden ", raiz.postorden),
            ("In-orden   ", raiz.inorden),
            ("Por niveles", raiz.por_niveles),
        ]:
            visitados = []
            metodo(lambda nodo: visitados.append(nodo.etiqueta))
            print(f"{etiqueta}: {visitados}")

    _demostrar_4_recorridos("Arbol de asignacion de local", arbol_local.raiz)
    _demostrar_4_recorridos("Arbol de tipo de servicio", arbol_servicio.raiz)
