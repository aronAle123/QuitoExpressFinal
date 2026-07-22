"""
dispatcher.py

El Dispatcher vive en el proceso principal y es el "cerebro" que conecta
los pedidos con los repartidores (procesos independientes):

- Crea los Process de cada repartidor (N por local) y sus colas.
- Mantiene, por local, el conjunto de repartidores libres y una cola de
  PRIORIDAD (heapq) de pedidos pendientes cuando no hay repartidor libre.
  La prioridad viene del ArbolTipoServicio (1 = alta, 3 = baja).
- Lee sin bloquear (get_nowait) la cola de estado compartida donde todos
  los repartidores reportan sus eventos, y con eso decide a quien
  despachar el siguiente pedido pendiente.
- Si un repartidor "cae", reencola su pedido (con la ruta restante) al
  heap de su local para que lo tome otro repartidor libre: asi se
  demuestra tolerancia a fallos real, no solo un print.
"""

import heapq
import itertools
import multiprocessing as mp
import queue

from repartidor import proceso_repartidor

TARIFA_BASE_POR_KM = 0.50
RECARGO_DEMANDA_ALTA = 1.3


def calcular_costo(distancia_total_km, multiplicador_tipo, demanda_alta):
    """
    Costo de envio = tarifa base por km * multiplicador del tipo de pedido
    (el mismo que ya usa ArbolTipoServicio para el tiempo, ej. Paquete x1.5),
    con un recargo adicional si el local asignado esta en "alta demanda"
    (todos sus repartidores ocupados al momento de crear el pedido).

    Retorna un dict con el desglose para mostrar en el panel.
    """
    costo_base = distancia_total_km * TARIFA_BASE_POR_KM * multiplicador_tipo
    recargo = costo_base * (RECARGO_DEMANDA_ALTA - 1) if demanda_alta else 0.0
    return {
        "costo_base": round(costo_base, 2),
        "recargo_demanda": round(recargo, 2),
        "demanda_alta": demanda_alta,
        "total": round(costo_base + recargo, 2),
    }


class Dispatcher:
    def __init__(self, locales, repartidores_por_local=3, prob_fallo=0.05, tiempo_por_zona=0.6):
        self.cola_estado = mp.Queue()
        self.procesos = []
        self.colas_ordenes = {}
        self.estado_repartidores = {}
        self.libres_por_local = {}
        self.pendientes_por_local = {}
        self.contador_pedidos = itertools.count()

        for local in locales:
            self.libres_por_local[local] = set()
            self.pendientes_por_local[local] = []

            for i in range(repartidores_por_local):
                id_repartidor = f"{local}-R{i + 1}"
                cola_ordenes = mp.Queue()
                self.colas_ordenes[id_repartidor] = cola_ordenes

                proceso = mp.Process(
                    target=proceso_repartidor,
                    args=(id_repartidor, local, cola_ordenes, self.cola_estado),
                    kwargs={"prob_fallo": prob_fallo, "tiempo_por_zona": tiempo_por_zona},
                    daemon=True,
                )
                self.procesos.append(proceso)

                self.estado_repartidores[id_repartidor] = {
                    "local": local, "estado": "libre", "zona_actual": local, "id_pedido": None,
                }
                self.libres_por_local[local].add(id_repartidor)

    def iniciar(self):
        for proceso in self.procesos:
            proceso.start()

    def detener(self):
        for cola in self.colas_ordenes.values():
            cola.put(None)
        for proceso in self.procesos:
            proceso.join(timeout=2)

    def nuevo_pedido(self, local, pedido):
        """
        Registra un pedido nuevo para que lo despache el local indicado
        (el local ya fue decidido por ArbolAsignacionLocal en main.py).

        pedido debe traer: id_pedido, pickup, dropoff, prioridad,
        multiplicador_tiempo, ruta_completa (Local -> Pickup -> ... -> Dropoff).

        Retorna un dict {"despachado_inmediato": bool, "pedidos_delante": int}
        para que quien llama (main.py) pueda estimar el tiempo de espera en
        cola antes de que arranque el tiempo de viaje.
        """
        pedido = dict(pedido)
        pedido["ruta_restante"] = pedido["ruta_completa"]
        pedido["ya_recogido"] = False

        if self._despachar_si_hay_libre(local, pedido):
            return {"despachado_inmediato": True, "pedidos_delante": 0}

        pedidos_delante = sum(
            1 for prioridad, _, _ in self.pendientes_por_local[local]
            if prioridad <= pedido["prioridad"]
        )
        heapq.heappush(
            self.pendientes_por_local[local],
            (pedido["prioridad"], next(self.contador_pedidos), pedido),
        )
        return {"despachado_inmediato": False, "pedidos_delante": pedidos_delante}

    def _despachar_si_hay_libre(self, local, pedido) -> bool:
        libres = self.libres_por_local[local]
        if not libres:
            return False
        id_repartidor = libres.pop()
        self.colas_ordenes[id_repartidor].put(pedido)
        self.estado_repartidores[id_repartidor]["estado"] = "asignado"
        self.estado_repartidores[id_repartidor]["id_pedido"] = pedido["id_pedido"]
        return True

    def _intentar_vaciar_pendientes(self, local):
        heap = self.pendientes_por_local[local]
        while heap and self.libres_por_local[local]:
            _, _, pedido = heapq.heappop(heap)
            self._despachar_si_hay_libre(local, pedido)

    def procesar_eventos(self):
        """
        Drena la cola de estado (no bloqueante) y actualiza todo el estado
        interno. Se debe llamar periodicamente (cada tick del loop de
        Pygame en main.py). Devuelve la lista de eventos procesados, util
        para que interfaz.py sepa que redibujar.
        """
        eventos = []
        while True:
            try:
                evento = self.cola_estado.get_nowait()
            except queue.Empty:
                break
            eventos.append(evento)
            self._procesar_evento(evento)
        return eventos

    def _procesar_evento(self, evento):
        id_repartidor = evento["id_repartidor"]
        local = evento["local"]
        estado = evento["estado"]

        self.estado_repartidores[id_repartidor].update({
            "estado": estado,
            "zona_actual": evento["zona_actual"],
            "id_pedido": evento["id_pedido"],
        })

        if estado == "caido_reasignando":
            pedido_pendiente = evento["pedido_pendiente"]
            heapq.heappush(
                self.pendientes_por_local[local],
                (pedido_pendiente["prioridad"], next(self.contador_pedidos), pedido_pendiente),
            )
        elif estado == "libre":
            self.libres_por_local[local].add(id_repartidor)
            self._intentar_vaciar_pendientes(local)

    def hay_pendientes(self) -> bool:
        return any(self.pendientes_por_local.values())

    def actualizar_ruta_en_curso(self, id_repartidor, id_pedido, ruta_restante_nueva):
        """
        Manda al repartidor `id_repartidor` (que debe estar entregando
        `id_pedido` en este momento) un mensaje de CONTROL con la ruta
        restante recalculada -tipicamente por un accidente que bloqueo una
        calle de su camino (ver grafo.py: bloquear_arista / main.py:
        simular_accidente)-. No pasa por pendientes_por_local ni cambia el
        estado "ocupado" del repartidor: el proceso lo recoge sin bloquear
        entre paso y paso (ver repartidor.py) y sigue la entrega desde su
        posicion actual, sin reiniciar el pedido.
        """
        if id_repartidor not in self.colas_ordenes:
            return
        self.colas_ordenes[id_repartidor].put({
            "tipo_mensaje": "actualizar_ruta",
            "id_pedido": id_pedido,
            "ruta_restante": ruta_restante_nueva,
        })


if __name__ == "__main__":
    import time

    from datos_zonas import construir_grafo_quito, LOCALES
    from arbol import ArbolTipoServicio

    grafo = construir_grafo_quito()
    arbol_servicio = ArbolTipoServicio()

    dispatcher = Dispatcher(LOCALES, repartidores_por_local=2, prob_fallo=0.25, tiempo_por_zona=0.25)
    dispatcher.iniciar()

    pedidos_prueba = [
        ("Local A - Norte", "Cotocollao", "Centro Historico", "Comida"),
        ("Local A - Norte", "Iñaquito", "La Mariscal", "Paquete"),
        ("Local A - Norte", "El Bosque", "Guapulo", "Documento"),
        ("Local B - Sur", "Quitumbe", "Chillogallo", "Paquete"),
        ("Local B - Sur", "San Rafael", "Local B - Sur", "Comida"),
        ("Local B - Sur", "Chillogallo", "San Rafael", "Documento"),
    ]

    print(f"=== Lanzando {len(pedidos_prueba)} pedidos contra 2 locales x 2 repartidores (4 en total) ===")
    for i, (local, pickup, dropoff, tipo) in enumerate(pedidos_prueba, start=1):
        info_tipo = arbol_servicio.clasificar(tipo)
        ruta, costo = grafo.ruta_encadenada(local, pickup, dropoff)
        pedido = {
            "id_pedido": i,
            "pickup": pickup,
            "dropoff": dropoff,
            "prioridad": info_tipo["prioridad"],
            "multiplicador_tiempo": info_tipo["multiplicador_tiempo"],
            "ruta_completa": ruta,
        }
        print(f"Pedido {i} ({tipo}, prioridad {info_tipo['prioridad']}) -> {local}: {' -> '.join(ruta)}")
        dispatcher.nuevo_pedido(local, pedido)

    print()
    print("=== Eventos en vivo (12 segundos) ===")
    fin = time.time() + 12
    while time.time() < fin:
        for evento in dispatcher.procesar_eventos():
            print(evento)
        time.sleep(0.1)

    print()
    print("=== Estado final de repartidores ===")
    for id_repartidor, info in dispatcher.estado_repartidores.items():
        print(id_repartidor, info)

    print("Pedidos que quedaron en cola de espera por local:",
          {local: len(heap) for local, heap in dispatcher.pendientes_por_local.items()})

    dispatcher.detener()
