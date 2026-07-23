

import multiprocessing as mp
import time

import pygame

from arbol import ArbolAsignacionLocal, ArbolTipoServicio
from datos_zonas import construir_grafo_quito, LOCALES
from dispatcher import Dispatcher, calcular_costo
from grafo import distancia_a_tiempo_min
from bienvenida import PantallaBienvenida
from instrucciones import PantallaInstrucciones
from recursos import recurso
import interfaz as ui

MIN_POR_PEDIDO_EN_COLA = 3
TIEMPO_ARCHIVAR_ENTREGADO = 3.0

ANCHO_VENTANA, ALTO_VENTANA = 1100, 780
MARGEN = 12
GAP = 8
ANCHO_TARJETA = 320
ANCHO_HISTORIAL = 320
ALTO_HISTORIAL = 260
ALTO_BOTON = 32
ALTO_BOTON_CONFIRMAR = 44
ALTO_BOTON_HISTORIAL = 28
ALTO_BUSCADOR = 36
REPARTIDORES_POR_LOCAL = 3
PROB_FALLO = 0.05
TIEMPO_POR_ZONA = 1.2

FASE_SELECCIONANDO_PICKUP = "SELECCIONANDO_PICKUP"
FASE_SELECCIONANDO_DROPOFF = "SELECCIONANDO_DROPOFF"
FASE_RESUMEN = "RESUMEN"


class EstadoApp:
    """Guarda la seleccion en curso del usuario, la fase de la interfaz y el historial de pedidos."""

    def __init__(self):
        self.pickup = None
        self.dropoff = None
        self.paradas = []
        self.modo_parada = False
        self.tipo_servicio = "comida"
        self.mensaje = ""
        self.mensaje_expira = 0.0
        self.siguiente_id_pedido = 1
        self.pedidos = {}
        self.ultima_ruta_calculada = None
        self.mostrar_historial = False
        self.historial_scroll = 0

        self.fase_actual = FASE_SELECCIONANDO_PICKUP

        self.arista_accidente = None

    def mostrar_mensaje(self, texto, duracion=3.0):
        self.mensaje = texto
        self.mensaje_expira = time.time() + duracion

    def reset_seleccion(self):
        self.pickup = None
        self.dropoff = None
        self.paradas = []
        self.modo_parada = False


def calcular_fase(estado_app):
    """
    La fase se deriva solo de la seleccion (pickup/dropoff) que se esta
    armando ahora mismo, sin importar si ya hay pedidos confirmados
    corriendo en paralelo (esos viven en `estado_app.pedidos` y se dibujan
    aparte, en el panel de activos). Esto evita que la fase quede
    desincronizada si algo cambia el pickup/dropoff sin pasar por un
    handler especifico, y permite armar un pedido nuevo sin esperar a que
    los anteriores terminen.
    """
    if estado_app.pickup is None:
        return FASE_SELECCIONANDO_PICKUP
    if estado_app.dropoff is None:
        return FASE_SELECCIONANDO_DROPOFF
    return FASE_RESUMEN


def seleccionar_zona(estado_app, nombre_zona):
    """
    Aplica una zona elegida (click directo en el mapa o buscador) a la
    seleccion en curso, estilo Uber: el primer click fija el pickup;
    despues, un click normal siempre fija (o reemplaza) el dropoff, y si el
    usuario activo el modo parada (boton "+ Agregar parada"), esa zona se
    agrega como parada en vez de tocar el dropoff.
    """
    if estado_app.pickup is None:
        estado_app.pickup = nombre_zona
        return

    if estado_app.modo_parada:
        estado_app.modo_parada = False
        if nombre_zona != estado_app.pickup and nombre_zona != estado_app.dropoff \
                and nombre_zona not in estado_app.paradas:
            estado_app.paradas.append(nombre_zona)
        return

    if nombre_zona != estado_app.pickup:
        estado_app.dropoff = nombre_zona


def calcular_estimado(estado_app, grafo, arbol_local, arbol_servicio, dispatcher):
    """
    Calcula el local/ruta/costo esperado para la fase RESUMEN, SIN tocar el
    Dispatcher (es solo una vista previa; `crear_pedido` repite este mismo
    calculo al confirmar, y ese si despacha de verdad). Devuelve None si no
    hay cobertura para la seleccion actual.
    """
    pickup, dropoff, paradas = estado_app.pickup, estado_app.dropoff, estado_app.paradas
    if pickup is None or dropoff is None:
        return None

    _, distancia_a = grafo.camino_en_arbol(pickup, "Local A - Norte")
    _, distancia_b = grafo.camino_en_arbol(pickup, "Local B - Sur")
    if distancia_a is None and distancia_b is None:
        return None

    disponible_a = len(dispatcher.libres_por_local["Local A - Norte"]) > 0
    disponible_b = len(dispatcher.libres_por_local["Local B - Sur"]) > 0
    local_estimado = arbol_local.decidir(distancia_a, distancia_b, disponible_a, disponible_b)
    demanda_alta = not (disponible_a if local_estimado == "Local A - Norte" else disponible_b)

    puntos = [local_estimado, pickup, *paradas, dropoff]
    ruta, distancia_total = grafo.ruta_multi_tramo(puntos)
    if ruta is None:
        return None

    info_tipo = arbol_servicio.clasificar(estado_app.tipo_servicio)
    costo = calcular_costo(distancia_total, info_tipo["multiplicador_tiempo"], demanda_alta)
    tiempo_viaje_min = distancia_a_tiempo_min(distancia_total) * info_tipo["multiplicador_tiempo"]

    return {"local": local_estimado, "ruta": ruta, "costo": costo, "tiempo_viaje_min": tiempo_viaje_min}


def crear_pedido(estado_app, grafo, arbol_local, arbol_servicio, dispatcher):
    pickup, dropoff, paradas = estado_app.pickup, estado_app.dropoff, list(estado_app.paradas)

    _, distancia_a = grafo.camino_en_arbol(pickup, "Local A - Norte")
    _, distancia_b = grafo.camino_en_arbol(pickup, "Local B - Sur")
    if distancia_a is None and distancia_b is None:
        estado_app.mostrar_mensaje("Sin cobertura de entrega disponible (el pickup no llega a ningun local)")
        estado_app.reset_seleccion()
        return

    disponible_a = len(dispatcher.libres_por_local["Local A - Norte"]) > 0
    disponible_b = len(dispatcher.libres_por_local["Local B - Sur"]) > 0
    local_asignado = arbol_local.decidir(distancia_a, distancia_b, disponible_a, disponible_b)
    demanda_alta = not (disponible_a if local_asignado == "Local A - Norte" else disponible_b)

    puntos = [local_asignado, pickup, *paradas, dropoff]
    ruta_completa, distancia_total = grafo.ruta_multi_tramo(puntos)
    if ruta_completa is None:
        estado_app.mostrar_mensaje("Sin cobertura de entrega disponible (algun tramo de la ruta no tiene camino)")
        estado_app.reset_seleccion()
        return

    info_tipo = arbol_servicio.clasificar(estado_app.tipo_servicio)
    id_pedido = estado_app.siguiente_id_pedido
    estado_app.siguiente_id_pedido += 1

    pedido = {
        "id_pedido": id_pedido, "pickup": pickup, "dropoff": dropoff,
        "prioridad": info_tipo["prioridad"], "multiplicador_tiempo": info_tipo["multiplicador_tiempo"],
        "ruta_completa": ruta_completa,
    }
    resultado_despacho = dispatcher.nuevo_pedido(local_asignado, pedido)

    tiempo_viaje_min = distancia_a_tiempo_min(distancia_total) * info_tipo["multiplicador_tiempo"]
    pedidos_delante = resultado_despacho["pedidos_delante"]
    costo = calcular_costo(distancia_total, info_tipo["multiplicador_tiempo"], demanda_alta)

    ahora = time.time()
    estado_app.pedidos[id_pedido] = {
        "pickup": pickup, "dropoff": dropoff, "paradas": paradas, "tipo": info_tipo["tipo"],
        "local": local_asignado, "estado": "esperando repartidor",
        "repartidor_id": None, "zona_actual": None,
        "ruta_completa": ruta_completa,
        "ya_recogido": False,
        "hora_creacion": ahora,
        "hora_despacho": ahora if resultado_despacho["despachado_inmediato"] else None,
        "hora_entregado": None,
        "pedidos_delante": pedidos_delante,
        "tiempo_espera_min": pedidos_delante * MIN_POR_PEDIDO_EN_COLA,
        "tiempo_viaje_min": tiempo_viaje_min,
        "costo": costo,
    }
    estado_app.ultima_ruta_calculada = ruta_completa
    estado_app.reset_seleccion()


def _ruta_restante_desde(ruta_completa, zona_actual):
    """
    Sub-lista de `ruta_completa` desde la ULTIMA vez que aparece
    `zona_actual` hasta el final: el tramo que el repartidor todavia no ha
    recorrido. Se usa la ultima aparicion (no la primera) porque el camino
    dentro de un arbol puede pasar dos veces por la misma zona al
    "regresar" tras una rama sin salida (ej. una parada), y el repartidor
    avanza en orden por la lista, no por nombre de zona. Devuelve None si
    `zona_actual` no aparece en la ruta.
    """
    indices = [i for i, zona in enumerate(ruta_completa) if zona == zona_actual]
    if not indices:
        return None
    return ruta_completa[indices[-1]:]


def _arista_en_ruta(ruta, zona_a, zona_b):
    """True si (zona_a, zona_b) aparece como un tramo consecutivo de `ruta`, en cualquier sentido."""
    par = frozenset((zona_a, zona_b))
    return any(frozenset((x, y)) == par for x, y in zip(ruta, ruta[1:]))


def _recalcular_ruta_activa_tras_accidente(estado_app, grafo, dispatcher, id_pedido, zona_a, zona_b):
    """
    Si el pedido `id_pedido` sigue en curso y el tramo que le falta por
    recorrer pasaba por la calle recien bloqueada (zona_a, zona_b),
    recalcula el camino desde la posicion ACTUAL del repartidor (no desde
    el inicio del pedido) usando el Arbol de Expansion Minima ya
    reconstruido sin esa arista (grafo.bloquear_arista ya lo reconstruyo
    antes de llamar a esta funcion), y se lo manda al proceso del
    repartidor para que continue sin reiniciar la entrega.

    Importante: si el repartidor todavia no paso por el pickup, el nuevo
    camino tiene que seguir pasando por el (y por las paradas, si las
    hay) antes del dropoff -si se recalculara directo hacia el dropoff se
    saltaria el pickup y el pedido "se entregaria" sin haberse recogido
    nunca-. Por eso se arma con ruta_multi_tramo por las paradas/pickup
    que aun faltan, no con un solo camino directo al dropoff. Una
    simplificacion aceptada: si ya paso el pickup, se asume que ya paso
    tambien todas las paradas (no se rastrea cual individualmente), asi
    que el recalculo despues del pickup va directo al dropoff.

    Devuelve True si de verdad recalculo algo (para que quien llama sepa
    si ya mostro un mensaje explicando el recalculo).
    """
    info = estado_app.pedidos.get(id_pedido)
    if info is None or not info.get("ruta_completa") or not info.get("zona_actual"):
        return False

    ruta_completa = info["ruta_completa"]
    ruta_restante_vieja = _ruta_restante_desde(ruta_completa, info["zona_actual"])
    if ruta_restante_vieja is None or len(ruta_restante_vieja) < 2:
        return False

    if not _arista_en_ruta(ruta_restante_vieja, zona_a, zona_b):
        return False

    dropoff_final = ruta_completa[-1]
    if info.get("ya_recogido"):
        objetivos_pendientes = [dropoff_final]
    else:
        objetivos_pendientes = [info["pickup"], *info.get("paradas", []), dropoff_final]

    ruta_restante_nueva, _ = grafo.ruta_multi_tramo([info["zona_actual"], *objetivos_pendientes])
    if ruta_restante_nueva is None:
        estado_app.mostrar_mensaje("El accidente bloqueo la unica ruta disponible: se mantiene la ruta actual")
        return False

    idx_actual = len(ruta_completa) - len(ruta_restante_vieja)
    ruta_completa_nueva = ruta_completa[:idx_actual] + ruta_restante_nueva
    info["ruta_completa"] = ruta_completa_nueva
    estado_app.ultima_ruta_calculada = ruta_completa_nueva

    repartidor_id = info.get("repartidor_id")
    if repartidor_id is not None:
        dispatcher.actualizar_ruta_en_curso(repartidor_id, id_pedido, ruta_restante_nueva)

    estado_app.mostrar_mensaje("Accidente en el camino: ruta recalculada evitando la calle bloqueada")
    return True


def simular_accidente(estado_app, grafo, dispatcher):
    """
    Bloquea una calle (arista) del grafo -eligiendola preferentemente
    sobre la ruta restante de algun pedido activo (puede haber varios
    corriendo en paralelo), para que el efecto se vea de inmediato- y
    fuerza la reconstruccion del Arbol de Expansion Minima (Prim)
    excluyendola. Cada pedido activo cuya ruta restante dependiera de esa
    calle se recalcula por separado desde la posicion actual de su
    repartidor; los pedidos que no la usan quedan intactos.
    """
    if estado_app.arista_accidente is not None:
        return

    ids_activos = [i for i, info in estado_app.pedidos.items() if info["estado"] != "entregado"]

    rutas_restantes = []
    for id_pedido in ids_activos:
        info = estado_app.pedidos[id_pedido]
        if info.get("ruta_completa") and info.get("zona_actual"):
            ruta_restante = _ruta_restante_desde(info["ruta_completa"], info["zona_actual"])
            if ruta_restante:
                rutas_restantes.append(ruta_restante)

    arista = grafo.elegir_arista_para_accidente(rutas_restantes)
    if arista is None:
        estado_app.mostrar_mensaje("No hay calles disponibles para simular un accidente")
        return

    zona_a, zona_b = arista
    grafo.bloquear_arista(zona_a, zona_b)
    estado_app.arista_accidente = (zona_a, zona_b)

    algun_recalculo = False
    for id_pedido in ids_activos:
        if _recalcular_ruta_activa_tras_accidente(estado_app, grafo, dispatcher, id_pedido, zona_a, zona_b):
            algun_recalculo = True

    if not algun_recalculo:
        estado_app.mostrar_mensaje(f"Accidente simulado: calle {zona_a} <-> {zona_b} bloqueada")


def reparar_calle(estado_app, grafo):
    """Quita el bloqueo de la calle activa y reconstruye el MST; no toca ninguna ruta ya en curso."""
    if estado_app.arista_accidente is None:
        return
    zona_a, zona_b = estado_app.arista_accidente
    grafo.reparar_arista(zona_a, zona_b)
    estado_app.arista_accidente = None
    estado_app.mostrar_mensaje(f"Calle {zona_a} <-> {zona_b} reparada")


def _badge_para_estado(estado):
    """Mapea el estado interno del pedido/repartidor a (texto, color_fondo, color_texto) del badge."""
    if estado in ("libre", "esperando repartidor"):
        return "En cola", ui.COLOR_BADGE_ALERTA_FONDO, ui.COLOR_BADGE_ALERTA_TEXTO
    if estado in ("en_camino_a_recoger", "recogido", "en_camino_a_entregar"):
        return "En camino", ui.COLOR_BADGE_EXITO_FONDO, ui.COLOR_BADGE_EXITO_TEXTO
    if estado == "retrasado":
        return "Retrasado", ui.COLOR_BADGE_ERROR_FONDO, ui.COLOR_BADGE_ERROR_TEXTO
    if estado == "caido_reasignando":
        return "Reasignando", ui.COLOR_BADGE_ERROR_FONDO, ui.COLOR_BADGE_ERROR_TEXTO
    if estado == "entregado":
        return "Entregado", ui.COLOR_BADGE_EXITO_FONDO, ui.COLOR_BADGE_EXITO_TEXTO
    return estado, ui.COLOR_BADGE_ALERTA_FONDO, ui.COLOR_BADGE_ALERTA_TEXTO


def construir_tarjeta_pedido(info, ahora):
    """Traduce el pedido en curso a un dict listo para dibujar_panel_estado."""
    badge_texto, badge_fondo, badge_texto_color = _badge_para_estado(info["estado"])

    titulo = f"{info['local']} · {info['tipo']}"
    if info["paradas"]:
        titulo += f" · {len(info['paradas'])} parada(s)"

    repartidor_texto = f"{info['repartidor_id']} · {info['zona_actual']}" if info["repartidor_id"] else None

    if info["estado"] == "entregado":
        tiempo_valor = "Completado"
    elif info["hora_despacho"] is None:
        transcurrido_min = (ahora - info["hora_creacion"]) / 60
        restante = max(0.0, info["tiempo_espera_min"] - transcurrido_min)
        tiempo_valor = f"Espera {restante:.1f} min"
    else:
        transcurrido_min = (ahora - info["hora_despacho"]) / 60
        restante = max(0.0, info["tiempo_viaje_min"] - transcurrido_min)
        tiempo_valor = f"{restante:.1f} min"

    costo = info["costo"]
    return {
        "titulo": titulo,
        "badge_texto": badge_texto, "badge_fondo": badge_fondo, "badge_texto_color": badge_texto_color,
        "repartidor_texto": repartidor_texto,
        "tiempo_valor": tiempo_valor,
        "costo_base_texto": f"${costo['costo_base']:.2f}",
        "recargo_texto": "+30%" if costo["demanda_alta"] else "Sin recargo",
        "recargo_activo": costo["demanda_alta"],
        "total_texto": f"${costo['total']:.2f}",
    }


def construir_fila_historial(info):
    """Traduce un pedido ya finalizado a una fila para el panel de historial."""
    if info["estado"] == "entregado":
        badge_texto, badge_fondo, badge_texto_color = "Entregado", ui.COLOR_BADGE_EXITO_FONDO, ui.COLOR_BADGE_EXITO_TEXTO
    else:
        badge_texto, badge_fondo, badge_texto_color = "Reasignado", ui.COLOR_BADGE_ERROR_FONDO, ui.COLOR_BADGE_ERROR_TEXTO

    return {
        "titulo": f"{info['local']} · {info['tipo']}",
        "subtitulo": f"{info['pickup']} -> {info['dropoff']}",
        "badge_texto": badge_texto, "badge_fondo": badge_fondo, "badge_texto_color": badge_texto_color,
        "costo_texto": f"${info['costo']['total']:.2f}",
    }


def main():
    pygame.init()
    icono = pygame.image.load(recurso("assets/Logo.png"))
    pygame.display.set_icon(icono)
    pantalla = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
    pygame.display.set_caption("QuitoExpress")

    if not PantallaBienvenida(pantalla).ejecutar():
        pygame.quit()
        return

    if not PantallaInstrucciones(pantalla).ejecutar():
        pygame.quit()
        return
    
    reloj = pygame.time.Clock()
    fuentes = {
        "normal": pygame.font.SysFont("Segoe UI", 14),
        "chica": pygame.font.SysFont("Segoe UI", 12),
        "negrita": pygame.font.SysFont("Segoe UI", 14, bold=True),
        "badge": pygame.font.SysFont("Segoe UI", 11, bold=True),
    }

    grafo = construir_grafo_quito()
    arbol_local = ArbolAsignacionLocal()
    arbol_servicio = ArbolTipoServicio()

    vista_mapa = ui.VistaMapa(grafo)
    vista_repartidores = ui.VistaRepartidores(vista_mapa)

    dispatcher = Dispatcher(
        LOCALES, repartidores_por_local=REPARTIDORES_POR_LOCAL,
        prob_fallo=PROB_FALLO, tiempo_por_zona=TIEMPO_POR_ZONA,
    )
    dispatcher.iniciar()

    estado_app = EstadoApp()
    campo_busqueda = ui.CampoBusqueda(pygame.Rect(0, 0, 10, 10))
    ancho_disponible = ANCHO_VENTANA - 2 * MARGEN

    TIPOS = [("comida", "Comida"), ("documento", "Documento"), ("paquete", "Paquete")]
    ancho_col_tipo = (ANCHO_TARJETA - 32 - 2 * GAP) // 3
    ancho_col_medio = (ANCHO_TARJETA - 32 - GAP) // 2

    botones_tipo = [
        ui.Boton((0, 0, ancho_col_tipo, ALTO_BOTON), etiqueta, ui.COLOR_BOTON_SECUNDARIO_FONDO, ui.COLOR_BOTON_SECUNDARIO_TEXTO)
        for _, etiqueta in TIPOS
    ]
    boton_parada = ui.Boton((0, 0, ancho_col_medio, ALTO_BOTON), "+ Agregar parada", ui.COLOR_BOTON_SECUNDARIO_FONDO, ui.COLOR_BOTON_SECUNDARIO_TEXTO)
    boton_reiniciar = ui.Boton((0, 0, ancho_col_medio, ALTO_BOTON), "Reiniciar", ui.COLOR_BOTON_SECUNDARIO_FONDO, ui.COLOR_BOTON_SECUNDARIO_TEXTO)
    boton_confirmar = ui.Boton((0, 0, ANCHO_TARJETA - 32, ALTO_BOTON_CONFIRMAR), "Confirmar pedido", ui.COLOR_BOTON_ACENTO, ui.COLOR_BOTON_ACENTO_TEXTO)
    boton_historial = ui.Boton((0, 0, 10, ALTO_BOTON_HISTORIAL), "Ver historial (0)", ui.COLOR_BOTON_SECUNDARIO_FONDO, ui.COLOR_BOTON_SECUNDARIO_TEXTO)
    boton_accidente = ui.Boton((0, 0, 10, ALTO_BOTON_HISTORIAL), "Simular accidente", ui.COLOR_BOTON_SECUNDARIO_FONDO, ui.COLOR_BOTON_SECUNDARIO_TEXTO)

    def construir_layout():
        """
        Todo lo que depende del estado actual: rects de la tarjeta blanca de
        seleccion / panel oscuro de activos / historial, que botones estan
        activos este frame y donde, y el contenido a dibujar. Se llama dos
        veces por frame (antes y despues de procesar eventos) para que nunca
        se dibuje con un rect viejo -mismo patron que ya se uso para corregir
        el bug del historial-.

        La tarjeta blanca (fase de seleccion) y el panel oscuro de pedidos
        activos se calculan por separado y de forma independiente: puede
        haber varios pedidos activos corriendo en paralelo mientras el
        usuario arma uno nuevo, asi que ninguno bloquea al otro.
        """
        fase = calcular_fase(estado_app)
        estado_app.fase_actual = fase
        ahora = time.time()

        ids_ordenados = sorted(estado_app.pedidos.keys(), reverse=True)
        ids_historial = []
        ids_activos = []
        for i in ids_ordenados:
            info = estado_app.pedidos[i]
            entregado_hace_rato = (
                info["estado"] == "entregado" and info["hora_entregado"] is not None
                and ahora - info["hora_entregado"] > TIEMPO_ARCHIVAR_ENTREGADO
            )
            (ids_historial if entregado_hace_rato else ids_activos).append(i)

        filas_historial = [construir_fila_historial(estado_app.pedidos[i]) for i in ids_historial]
        tarjetas_activas = [construir_tarjeta_pedido(estado_app.pedidos[i], ahora) for i in ids_activos]

        layout = {
            "fase": fase, "rect_tarjeta": None, "rect_panel_estado": None,
            "mostrar_buscador": False, "botones": [], "contenido": {},
            "filas_historial": filas_historial, "tarjetas_activas": tarjetas_activas,
        }

        # --- panel oscuro de pedidos activos: siempre visible si hay alguno, sin importar la fase de seleccion ---
        if tarjetas_activas:
            layout["rect_panel_estado"] = ui.calcular_rect_panel_estado(
                fuentes, MARGEN, ancho_disponible, ALTO_VENTANA - MARGEN, tarjetas_activas,
            )

        # --- boton + panel de historial: siempre en la esquina superior derecha ---
        texto_hist = f"{'Ocultar' if estado_app.mostrar_historial else 'Ver'} historial ({len(filas_historial)})"
        boton_historial.texto = texto_hist
        boton_historial.seleccionado = estado_app.mostrar_historial
        ancho_hist_boton = fuentes["chica"].size(texto_hist)[0] + 24
        boton_historial.rect = pygame.Rect(ANCHO_VENTANA - MARGEN - ancho_hist_boton, MARGEN, ancho_hist_boton, ALTO_BOTON_HISTORIAL)
        layout["botones"].append((boton_historial, lambda: _alternar_historial()))

        # --- boton de accidentes (panel de control): siempre visible, junto al de historial ---
        hay_accidente = estado_app.arista_accidente is not None
        texto_accidente = "Reparar calle" if hay_accidente else "Simular accidente"
        boton_accidente.texto = texto_accidente
        boton_accidente.seleccionado = hay_accidente
        ancho_accidente_boton = fuentes["chica"].size(texto_accidente)[0] + 24
        boton_accidente.rect = pygame.Rect(
            ANCHO_VENTANA - MARGEN - ancho_hist_boton - GAP - ancho_accidente_boton,
            MARGEN, ancho_accidente_boton, ALTO_BOTON_HISTORIAL,
        )
        layout["botones"].append((boton_accidente, lambda: _alternar_accidente()))

        rect_historial = None
        if estado_app.mostrar_historial:
            rect_historial = pygame.Rect(ANCHO_VENTANA - MARGEN - ANCHO_HISTORIAL, MARGEN + ALTO_BOTON_HISTORIAL + GAP, ANCHO_HISTORIAL, ALTO_HISTORIAL)
            estado_app.historial_scroll = ui.clamp_scroll_historial(filas_historial, estado_app.historial_scroll, ALTO_HISTORIAL)
        layout["rect_historial"] = rect_historial

        boton_parada.texto = "Toca una zona en el mapa..." if estado_app.modo_parada else "+ Agregar parada"
        boton_parada.seleccionado = estado_app.modo_parada

        # --- contenido especifico de cada fase ---
        if fase == FASE_SELECCIONANDO_PICKUP:
            alto = 16 + 22 + 8 + ALTO_BUSCADOR + 16
            rect = pygame.Rect(MARGEN, MARGEN, ANCHO_TARJETA, alto)
            layout["rect_tarjeta"] = rect
            layout["mostrar_buscador"] = True
            campo_busqueda.rect = pygame.Rect(rect.x + 16, rect.y + 16 + 22 + 8, ANCHO_TARJETA - 32, ALTO_BUSCADOR)
            layout["contenido"]["titulo"] = "¿Dónde recoges?"

        elif fase == FASE_SELECCIONANDO_DROPOFF:
            alto = 16 + 22 + 6 + 18 + 6 + 18 + 6 + ALTO_BUSCADOR + 8 + ALTO_BOTON + 16
            rect = pygame.Rect(MARGEN, MARGEN, ANCHO_TARJETA, alto)
            layout["rect_tarjeta"] = rect
            layout["mostrar_buscador"] = True

            y = rect.y + 16 + 22 + 6 + 18 + 6 + 18 + 6
            campo_busqueda.rect = pygame.Rect(rect.x + 16, y, ANCHO_TARJETA - 32, ALTO_BUSCADOR)
            y += ALTO_BUSCADOR + 8

            boton_parada.rect = pygame.Rect(rect.x + 16, y, ancho_col_medio, ALTO_BOTON)
            boton_reiniciar.rect = pygame.Rect(rect.x + 16 + ancho_col_medio + GAP, y, ancho_col_medio, ALTO_BOTON)
            layout["botones"].append((boton_parada, lambda: _activar_modo_parada()))
            layout["botones"].append((boton_reiniciar, lambda: estado_app.reset_seleccion()))

            layout["contenido"]["titulo"] = "¿Dónde entregas?"

        elif fase == FASE_RESUMEN:
            alto = 16 + 22 + 6 + 18 + 8 + ALTO_BOTON + 8 + 40 + 8 + ALTO_BOTON + 8 + ALTO_BOTON_CONFIRMAR + 16
            rect = pygame.Rect(MARGEN, MARGEN, ANCHO_TARJETA, alto)
            layout["rect_tarjeta"] = rect

            y = rect.y + 16 + 22 + 6 + 18 + 8

            x_col = rect.x + 16
            for boton_tipo, (valor, _etiqueta) in zip(botones_tipo, TIPOS):
                boton_tipo.rect = pygame.Rect(x_col, y, ancho_col_tipo, ALTO_BOTON)
                layout["botones"].append((boton_tipo, (lambda v=valor: setattr(estado_app, "tipo_servicio", v))))
                x_col += ancho_col_tipo + GAP
            y += ALTO_BOTON + 8 + 40 + 8

            boton_parada.rect = pygame.Rect(rect.x + 16, y, ancho_col_medio, ALTO_BOTON)
            boton_reiniciar.rect = pygame.Rect(rect.x + 16 + ancho_col_medio + GAP, y, ancho_col_medio, ALTO_BOTON)
            layout["botones"].append((boton_parada, lambda: _activar_modo_parada()))
            layout["botones"].append((boton_reiniciar, lambda: estado_app.reset_seleccion()))
            y += ALTO_BOTON + 8

            estimado = calcular_estimado(estado_app, grafo, arbol_local, arbol_servicio, dispatcher)
            boton_confirmar.rect = pygame.Rect(rect.x + 16, y, ANCHO_TARJETA - 32, ALTO_BOTON_CONFIRMAR)
            boton_confirmar.activo = estimado is not None
            layout["botones"].append((boton_confirmar, lambda: crear_pedido(estado_app, grafo, arbol_local, arbol_servicio, dispatcher)))

            layout["contenido"]["titulo"] = "Confirmar pedido"
            layout["contenido"]["estimado"] = estimado

        return layout

    def _alternar_historial():
        estado_app.mostrar_historial = not estado_app.mostrar_historial
        estado_app.historial_scroll = 0

    def _activar_modo_parada():
        estado_app.modo_parada = True
        estado_app.mostrar_mensaje("Selecciona la zona de la proxima parada...")

    def _alternar_accidente():
        if estado_app.arista_accidente is not None:
            reparar_calle(estado_app, grafo)
        else:
            simular_accidente(estado_app, grafo, dispatcher)

    try:
        corriendo = True
        while corriendo:
            ahora = time.time()

            # --- 1. layout con el estado de inicio de frame (para la deteccion de click) ---
            layout = construir_layout()

            # --- 2. eventos ---
            for evento_pygame in pygame.event.get():
                if evento_pygame.type == pygame.QUIT:
                    corriendo = False

                elif evento_pygame.type == pygame.MOUSEBUTTONDOWN:
                    pos = evento_pygame.pos
                    manejado = False

                    if layout["mostrar_buscador"]:
                        nombre = campo_busqueda.manejar_click(pos)
                        if nombre:
                            seleccionar_zona(estado_app, nombre)
                            manejado = True
                        elif campo_busqueda.rect.collidepoint(pos):
                            manejado = True

                    if not manejado:
                        for boton, callback in layout["botones"]:
                            if boton.click_en(pos):
                                callback()
                                manejado = True
                                break

                    if not manejado and layout["rect_historial"] is not None and layout["rect_historial"].collidepoint(pos):
                        manejado = True

                    if not manejado and layout["rect_tarjeta"] is not None and layout["rect_tarjeta"].collidepoint(pos):
                        manejado = True

                    if not manejado and layout["rect_panel_estado"] is not None and layout["rect_panel_estado"].collidepoint(pos):
                        manejado = True

                    if not manejado:
                        if layout["mostrar_buscador"]:
                            campo_busqueda.activo = False
                        zona = vista_mapa.zona_en_click(pos)
                        if zona:
                            seleccionar_zona(estado_app, zona)

                elif evento_pygame.type == pygame.MOUSEWHEEL:
                    if layout["rect_historial"] is not None and layout["rect_historial"].collidepoint(pygame.mouse.get_pos()):
                        estado_app.historial_scroll -= evento_pygame.y * 20

                elif evento_pygame.type == pygame.KEYDOWN:
                    if layout["mostrar_buscador"] and campo_busqueda.activo:
                        nombre = campo_busqueda.manejar_tecla(evento_pygame, grafo)
                        if nombre:
                            seleccionar_zona(estado_app, nombre)
                    elif evento_pygame.key == pygame.K_ESCAPE:
                        corriendo = False

            # --- 3. eventos del dispatcher (repartidores) ---
            for evento_dispatcher in dispatcher.procesar_eventos():
                id_repartidor = evento_dispatcher["id_repartidor"]
                zona_actual = evento_dispatcher["zona_actual"]
                estado = evento_dispatcher["estado"]
                id_pedido = evento_dispatcher["id_pedido"]

                if estado == "libre":
                    vista_repartidores.eliminar(id_repartidor)
                else:
                    vista_repartidores.actualizar(id_repartidor, zona_actual, estado, ahora)

                if id_pedido is not None and id_pedido in estado_app.pedidos:
                    info_pedido = estado_app.pedidos[id_pedido]
                    info_pedido["estado"] = estado
                    info_pedido["repartidor_id"] = id_repartidor
                    info_pedido["zona_actual"] = zona_actual
                    if estado in ("recogido", "en_camino_a_entregar"):
                        info_pedido["ya_recogido"] = True
                    if info_pedido["hora_despacho"] is None:
                        info_pedido["hora_despacho"] = ahora
                    if estado == "entregado" and info_pedido["hora_entregado"] is None:
                        info_pedido["hora_entregado"] = ahora

            # --- 4. layout fresco (con el estado ya al dia) para dibujar; el archivado al historial
            #        tras ~3s en "entregado" ya se recalcula solo dentro de construir_layout ---
            layout = construir_layout()

            # --- 5. dibujar ---
            zonas_activas = set(estado_app.paradas)
            if estado_app.pickup:
                zonas_activas.add(estado_app.pickup)
            if estado_app.dropoff:
                zonas_activas.add(estado_app.dropoff)

            vista_mapa.dibujar_base(
                pantalla, fuentes["normal"],
                ruta_resaltada=estado_app.ultima_ruta_calculada,
                resaltadas=zonas_activas,
            )
            vista_repartidores.dibujar(pantalla, fuentes["normal"], ahora)

            rect = layout["rect_tarjeta"]
            if rect is not None:
                ui.dibujar_tarjeta_blanca(pantalla, rect)
                fase = layout["fase"]

                if fase == FASE_SELECCIONANDO_PICKUP:
                    titulo = fuentes["negrita"].render(layout["contenido"]["titulo"], True, ui.COLOR_TEXTO_SOBRE_BLANCO)
                    pantalla.blit(titulo, (rect.x + 16, rect.y + 16))
                    campo_busqueda.dibujar(pantalla, fuentes["normal"])

                elif fase == FASE_SELECCIONANDO_DROPOFF:
                    titulo = fuentes["negrita"].render(layout["contenido"]["titulo"], True, ui.COLOR_TEXTO_SOBRE_BLANCO)
                    pantalla.blit(titulo, (rect.x + 16, rect.y + 16))
                    y_texto = rect.y + 16 + 22 + 6
                    pygame.draw.circle(pantalla, ui.COLOR_ZONA_TERMINAL, (rect.x + 20, y_texto + 7), 5)
                    linea_pickup = fuentes["chica"].render(f"Pickup: {estado_app.pickup}", True, ui.COLOR_TEXTO_SECUNDARIO_BLANCO)
                    pantalla.blit(linea_pickup, (rect.x + 32, y_texto))
                    y_texto += 18 + 6
                    texto_paradas = ", ".join(estado_app.paradas) if estado_app.paradas else "-"
                    linea_paradas = fuentes["chica"].render(f"Paradas: {texto_paradas}", True, ui.COLOR_TEXTO_SECUNDARIO_BLANCO)
                    pantalla.blit(linea_paradas, (rect.x + 16, y_texto))
                    campo_busqueda.dibujar(pantalla, fuentes["normal"])
                    boton_parada.dibujar(pantalla, fuentes["normal"])
                    boton_reiniciar.dibujar(pantalla, fuentes["normal"])

                elif fase == FASE_RESUMEN:
                    titulo = fuentes["negrita"].render(layout["contenido"]["titulo"], True, ui.COLOR_TEXTO_SOBRE_BLANCO)
                    pantalla.blit(titulo, (rect.x + 16, rect.y + 16))
                    paradas_txt = f" (+{len(estado_app.paradas)} parada(s))" if estado_app.paradas else ""
                    resumen_txt = f"{estado_app.pickup} -> {estado_app.dropoff}{paradas_txt}"
                    linea = fuentes["chica"].render(resumen_txt, True, ui.COLOR_TEXTO_SECUNDARIO_BLANCO)
                    pantalla.blit(linea, (rect.x + 16, rect.y + 16 + 22 + 6))

                    for boton_tipo, (valor, _etiqueta) in zip(botones_tipo, TIPOS):
                        boton_tipo.seleccionado = estado_app.tipo_servicio == valor
                        boton_tipo.dibujar(pantalla, fuentes["normal"])

                    y_costo = botones_tipo[0].rect.bottom + 8
                    estimado = layout["contenido"]["estimado"]
                    if estimado is None:
                        lineas_costo = [("Sin cobertura de entrega disponible", ui.COLOR_ERROR_TEXTO_BLANCO)]
                    else:
                        costo = estimado["costo"]
                        lineas_costo = [
                            (f"Costo estimado: ${costo['total']:.2f}", ui.COLOR_TEXTO_SOBRE_BLANCO),
                            (f"Recargo por demanda: {'Si (+30%)' if costo['demanda_alta'] else 'No'}", ui.COLOR_TEXTO_SECUNDARIO_BLANCO),
                        ]
                    ui.dibujar_lineas(pantalla, fuentes, rect.x + 16, y_costo, lineas_costo, fuente_clave="chica")

                    boton_parada.dibujar(pantalla, fuentes["normal"])
                    boton_reiniciar.dibujar(pantalla, fuentes["normal"])
                    boton_confirmar.dibujar(pantalla, fuentes["normal"])

            if layout["tarjetas_activas"]:
                ui.dibujar_panel_estado(pantalla, fuentes, MARGEN, ancho_disponible, ALTO_VENTANA - MARGEN, layout["tarjetas_activas"])

            if estado_app.mostrar_historial and layout["rect_historial"] is not None:
                ui.dibujar_panel_historial(pantalla, fuentes, layout["rect_historial"], layout["filas_historial"], estado_app.historial_scroll)
            boton_historial.dibujar(pantalla, fuentes["chica"])
            boton_accidente.dibujar(pantalla, fuentes["chica"])

            pygame.display.flip()
            reloj.tick(30)
    finally:
        dispatcher.detener()
        pygame.quit()


if __name__ == "__main__":
    mp.freeze_support()
    main()
