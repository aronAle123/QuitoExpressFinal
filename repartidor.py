"""
repartidor.py

Funcion que corre DENTRO de cada proceso repartidor (multiprocessing.Process).
Un repartidor recibe pedidos por su cola de ordenes (mp.Queue personal),
simula el recorrido zona por zona de la ruta, y reporta cada cambio de
estado/posicion a la cola de estado compartida (mp.Queue) que lee el
Dispatcher en el proceso principal.

Estados que puede reportar:
    libre -> en_camino_a_recoger -> recogido -> en_camino_a_entregar -> entregado -> libre
                    \\-> retrasado -> caido_reasignando (fallo simulado, ~5%)

Estructura de un "pedido" (dict) que llega por cola_ordenes:
    {
        "id_pedido": int,
        "pickup": str,               # nombre de zona
        "dropoff": str,               # nombre de zona
        "prioridad": int,             # 1 alta - 3 baja (viene del ArbolTipoServicio)
        "multiplicador_tiempo": float,
        "ruta_restante": [str, ...],  # zonas que faltan por recorrer, empieza en la posicion actual
        "ya_recogido": bool,          # False si aun no ha pasado por "pickup"
    }

Mientras un repartidor esta en plena entrega (dentro del while de abajo) no
llama a cola_ordenes.get() -bloqueante-, asi que el Dispatcher puede usar esa
misma cola personal para mandarle, sin interrumpir la entrega, un mensaje de
CONTROL con una ruta recalculada (ej. por un accidente que bloqueo una calle
de su camino, ver GrafoCiudad.bloquear_arista en grafo.py y
Dispatcher.actualizar_ruta_en_curso):
    {
        "tipo_mensaje": "actualizar_ruta",
        "id_pedido": int,             # debe coincidir con el pedido en curso
        "ruta_restante": [str, ...],  # nuevo camino, ya arranca en la posicion actual
    }
El repartidor la recoge entre paso y paso con un get_nowait() no bloqueante y
adopta la nueva ruta_restante sin perder ya_recogido/estado ni reiniciar el
pedido desde cero.
"""

import queue
import random
import time

_SIN_MENSAJE = object()


def proceso_repartidor(id_repartidor, nombre_local, cola_ordenes, cola_estado,
                        prob_fallo=0.05, tiempo_por_zona=0.6):
    """Target de multiprocessing.Process: bucle de vida de un repartidor."""

    def reportar(estado, zona_actual, pedido=None, pedido_pendiente=None):
        cola_estado.put({
            "id_repartidor": id_repartidor,
            "local": nombre_local,
            "estado": estado,
            "zona_actual": zona_actual,
            "id_pedido": pedido["id_pedido"] if pedido else None,
            "pedido_pendiente": pedido_pendiente,
        })

    reportar("libre", nombre_local)

    while True:
        pedido = cola_ordenes.get()
        if pedido is None:
            break
        if pedido.get("tipo_mensaje") == "actualizar_ruta":
            continue

        ruta_restante = list(pedido["ruta_restante"])
        ya_recogido = pedido["ya_recogido"]
        multiplicador = pedido["multiplicador_tiempo"]
        estado = "en_camino_a_entregar" if ya_recogido else "en_camino_a_recoger"

        posicion_actual = ruta_restante[0]
        cayo = False
        indice = 1

        while indice < len(ruta_restante):
            zona = ruta_restante[indice]
            time.sleep(tiempo_por_zona * multiplicador)

            try:
                mensaje = cola_ordenes.get_nowait()
            except queue.Empty:
                mensaje = _SIN_MENSAJE

            if mensaje is not _SIN_MENSAJE:
                if mensaje is None:
                    cola_ordenes.put(None)
                elif mensaje.get("tipo_mensaje") == "actualizar_ruta" and mensaje.get("id_pedido") == pedido["id_pedido"]:
                    ruta_restante = list(mensaje["ruta_restante"])
                    indice = 1
                    continue
                continue

            if random.random() < prob_fallo:
                reportar("retrasado", posicion_actual, pedido)
                time.sleep(tiempo_por_zona * multiplicador)

                indice_actual = ruta_restante.index(posicion_actual)
                pedido_pendiente = dict(pedido)
                pedido_pendiente["ruta_restante"] = ruta_restante[indice_actual:]
                pedido_pendiente["ya_recogido"] = ya_recogido

                reportar("caido_reasignando", posicion_actual, pedido, pedido_pendiente)
                cayo = True
                break

            posicion_actual = zona

            if zona == pedido["pickup"] and not ya_recogido:
                ya_recogido = True
                reportar("recogido", posicion_actual, pedido)
                estado = "en_camino_a_entregar"
            else:
                reportar(estado, posicion_actual, pedido)

            indice += 1

        if not cayo:
            reportar("entregado", posicion_actual, pedido)
            time.sleep(0.3)
        else:
            time.sleep(1.5)

        reportar("libre", posicion_actual)


if __name__ == "__main__":
    import multiprocessing as mp

    cola_ordenes = mp.Queue()
    cola_estado = mp.Queue()

    proceso = mp.Process(
        target=proceso_repartidor,
        args=("Local A - Norte-R1", "Local A - Norte", cola_ordenes, cola_estado),
        kwargs={"prob_fallo": 0.3, "tiempo_por_zona": 0.2},
    )
    proceso.start()

    pedido_prueba = {
        "id_pedido": 1,
        "pickup": "Cotocollao",
        "dropoff": "Centro Historico",
        "prioridad": 1,
        "multiplicador_tiempo": 1.0,
        "ruta_restante": ["Local A - Norte", "Cotocollao", "El Bosque", "La Mariscal", "Centro Historico"],
        "ya_recogido": False,
    }

    time.sleep(0.3)
    cola_ordenes.put(pedido_prueba)

    fin = time.time() + 8
    while time.time() < fin:
        try:
            evento = cola_estado.get(timeout=0.3)
        except Exception:
            continue
        print(evento)

    cola_ordenes.put(None)
    proceso.join(timeout=2)
