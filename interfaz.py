
import math

import pygame
from recursos import recurso

# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------

COLOR_FONDO_VENTANA = (41, 121, 255)

COLOR_FONDO_MAPA = (237, 239, 243)
COLOR_CALLE = (213, 217, 224)
COLOR_RUTA = (41, 121, 255)
COLOR_CALLE_BLOQUEADA = (214, 40, 40)

COLOR_ZONA_NORMAL = (185, 190, 201)
COLOR_ZONA_TERMINAL = (255, 107, 53)
COLOR_LOCAL = (255, 107, 53)

COLOR_TARJETA_FONDO = (255, 255, 255)
COLOR_TARJETA_SOMBRA = (0, 0, 0)

COLOR_TEXTO_SOBRE_BLANCO = (26, 26, 26)
COLOR_TEXTO_SECUNDARIO_BLANCO = (107, 114, 128)
COLOR_TEXTO_MUTED_BLANCO = (154, 161, 172)
COLOR_ERROR_TEXTO_BLANCO = (196, 60, 45)

COLOR_BOTON_ACENTO = (255, 107, 53)
COLOR_BOTON_ACENTO_TEXTO = (255, 255, 255)
COLOR_BOTON_SECUNDARIO_FONDO = (243, 245, 248)
COLOR_BOTON_SECUNDARIO_TEXTO = (107, 114, 128)

COLOR_PANEL_ESTADO_FONDO = (20, 22, 26)
COLOR_PANEL_ESTADO_BORDE = (44, 46, 51)
COLOR_TARJETA_METRICA_FONDO = (33, 35, 40)

COLOR_TEXTO_SOBRE_NEGRO = (243, 245, 248)
COLOR_TEXTO_SECUNDARIO_NEGRO = (154, 161, 172)

COLOR_BADGE_EXITO_FONDO = (30, 58, 46)
COLOR_BADGE_EXITO_TEXTO = (143, 227, 168)
COLOR_BADGE_ALERTA_FONDO = (69, 47, 15)
COLOR_BADGE_ALERTA_TEXTO = (250, 199, 117)
COLOR_BADGE_ERROR_FONDO = (69, 22, 22)
COLOR_BADGE_ERROR_TEXTO = (240, 149, 149)

COLORES_REPARTIDOR = [
    (230, 126, 34), (155, 89, 182), (52, 152, 219),
    (241, 196, 15), (26, 188, 156), (231, 76, 60),
]

# ---------------------------------------------------------------------------
# Iconos vectoriales (formas primitivas, sin archivos externos)
# ---------------------------------------------------------------------------


def dibujar_icono_moto(superficie, x, y, tamano, color):
    """Cuerpo + manubrio (rects redondeados) + 2 ruedas (circulos)."""
    cuerpo = pygame.Rect(0, 0, int(tamano * 1.3), int(tamano * 0.55))
    cuerpo.center = (int(x), int(y) + int(tamano * 0.05))
    pygame.draw.rect(superficie, color, cuerpo, border_radius=max(2, int(cuerpo.height * 0.4)))

    manubrio = pygame.Rect(0, 0, int(tamano * 0.32), int(tamano * 0.4))
    manubrio.center = (int(x) + int(tamano * 0.38), int(y) - int(tamano * 0.28))
    pygame.draw.rect(superficie, color, manubrio, border_radius=max(2, int(manubrio.width * 0.3)))

    radio_rueda = max(2, int(tamano * 0.22))
    pygame.draw.circle(superficie, color, (int(x) - int(tamano * 0.45), int(y) + int(tamano * 0.32)), radio_rueda)
    pygame.draw.circle(superficie, color, (int(x) + int(tamano * 0.45), int(y) + int(tamano * 0.32)), radio_rueda)


def dibujar_icono_pin(superficie, x, y, tamano, color):
    """Circulo con un punto claro al centro: pickup/dropoff/parada activa."""
    pygame.draw.circle(superficie, color, (int(x), int(y)), tamano)
    pygame.draw.circle(superficie, COLOR_FONDO_MAPA, (int(x), int(y)), max(2, int(tamano * 0.35)))


def dibujar_icono_lupa(superficie, x, y, tamano, color, ancho_linea=2):
    """Circulo sin relleno + una linea diagonal corta: icono de busqueda."""
    radio = tamano * 0.5
    cx, cy = x - tamano * 0.15, y - tamano * 0.15
    pygame.draw.circle(superficie, color, (cx, cy), radio, ancho_linea)
    dx = dy = radio * 0.7071
    inicio = (cx + dx, cy + dy)
    fin = (inicio[0] + tamano * 0.35, inicio[1] + tamano * 0.35)
    pygame.draw.line(superficie, color, inicio, fin, ancho_linea + 1)


def dibujar_icono_reloj(superficie, x, y, tamano, color, ancho_linea=2):
    """Circulo sin relleno + 2 agujas cortas: icono de tiempo."""
    radio = tamano * 0.5
    pygame.draw.circle(superficie, color, (x, y), radio, ancho_linea)
    pygame.draw.line(superficie, color, (x, y), (x, y - radio * 0.55), ancho_linea + 1)
    pygame.draw.line(superficie, color, (x, y), (x + radio * 0.4, y), ancho_linea + 1)


def dibujar_icono_advertencia(superficie, x, y, tamano, color_fondo=COLOR_CALLE_BLOQUEADA, color_texto=(255, 255, 255)):
    """Triangulo de advertencia con '!' adentro: marca el punto medio de una calle bloqueada por un accidente."""
    mitad = tamano * 0.6
    puntos = [(x, y - mitad), (x - mitad, y + mitad * 0.8), (x + mitad, y + mitad * 0.8)]
    pygame.draw.polygon(superficie, color_fondo, puntos)
    pygame.draw.line(superficie, color_texto, (x, y - mitad * 0.15), (x, y + mitad * 0.35), 2)
    pygame.draw.circle(superficie, color_texto, (int(x), int(y + mitad * 0.58)), 1)


def dibujar_spinner(pantalla, centro, radio, angulo, color, ancho=4):
    """Arco que rota (main.py incrementa `angulo` cada frame): spinner de carga simple."""
    rect = pygame.Rect(0, 0, radio * 2, radio * 2)
    rect.center = centro
    pygame.draw.arc(pantalla, color, rect, angulo, angulo + 4.5, ancho)


# ---------------------------------------------------------------------------
# Helpers de dibujo
# ---------------------------------------------------------------------------


def _dibujar_linea_punteada(pantalla, color, punto_a, punto_b, ancho, longitud_segmento=10):
    """Pygame no tiene lineas punteadas nativas: se dibujan segmentos alternados."""
    x0, y0 = punto_a
    x1, y1 = punto_b
    distancia = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    if distancia == 0:
        return
    pasos = max(1, int(distancia // longitud_segmento))
    for i in range(pasos):
        if i % 2 != 0:
            continue
        t0 = i / pasos
        t1 = min(1.0, (i + 1) / pasos)
        inicio = (x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0)
        fin = (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)
        pygame.draw.line(pantalla, color, inicio, fin, ancho)


def _superficie_redondeada(ancho, alto, color, radius, alpha=255, borde_color=None):
    """Surface con esquinas redondeadas y alpha propio, para poder flotar sobre el mapa."""
    ancho, alto = max(1, int(ancho)), max(1, int(alto))
    superficie = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    rect_local = superficie.get_rect()
    pygame.draw.rect(superficie, (*color, alpha), rect_local, border_radius=radius)
    if borde_color:
        pygame.draw.rect(superficie, (*borde_color, 255), rect_local, width=1, border_radius=radius)
    return superficie


def dibujar_tarjeta_blanca(pantalla, rect, radius=14):
    """Tarjeta blanca flotante con una sombra sutil detras (offset + alpha bajo)."""
    sombra = _superficie_redondeada(rect.width, rect.height, COLOR_TARJETA_SOMBRA, radius=radius, alpha=35)
    pantalla.blit(sombra, (rect.x, rect.y + 4))
    pygame.draw.rect(pantalla, COLOR_TARJETA_FONDO, rect, border_radius=radius)


# ---------------------------------------------------------------------------
# Mapa
# ---------------------------------------------------------------------------


class VistaMapa:
    RADIO_ZONA = 7
    RADIO_ZONA_TERMINAL = 11
    RADIO_LOCAL = 15

    def __init__(self, grafo, offset=(175, 60), escala_y=0.72):
        self.grafo = grafo
        self.offset_x, self.offset_y = offset
        self.escala_y = escala_y

        self.mapa2 = pygame.image.load(recurso("assets/Mapa0.png")).convert()
        self.mapa2 = pygame.transform.smoothscale(
            self.mapa2,
            (1100, 780)
        )

        self.mapa = pygame.image.load(recurso("assets/Mapa1.png")).convert()
        self.mapa = pygame.transform.smoothscale(
            self.mapa,
            (550, 590)
        )
    
    def posicion(self, nombre_zona):
        zona = self.grafo.zonas[nombre_zona]
        return zona.x + self.offset_x, zona.y * self.escala_y + self.offset_y

    def zona_en_click(self, pos_mouse, radio_click=16):
        """Devuelve el nombre de la zona bajo el click, o None si no hay ninguna."""
        mx, my = pos_mouse
        for nombre in self.grafo.zonas:
            x, y = self.posicion(nombre)
            if (mx - x) ** 2 + (my - y) ** 2 <= radio_click ** 2:
                return nombre
        return None

    def dibujar_calles(self, pantalla):
        dibujadas = set()
        pendientes_advertencia = []
        for origen, vecinos in self.grafo.adyacencia.items():
            for destino in vecinos:
                clave = tuple(sorted((origen, destino)))
                if clave in dibujadas:
                    continue
                dibujadas.add(clave)

                punto_a, punto_b = self.posicion(origen), self.posicion(destino)
                if self.grafo.arista_esta_bloqueada(origen, destino):
                    pygame.draw.line(pantalla, COLOR_CALLE_BLOQUEADA, punto_a, punto_b, 4)
                    pendientes_advertencia.append(((punto_a[0] + punto_b[0]) / 2, (punto_a[1] + punto_b[1]) / 2))
                else:
                    pygame.draw.line(pantalla, COLOR_CALLE, punto_a, punto_b, 2)

        for x, y in pendientes_advertencia:
            dibujar_icono_advertencia(pantalla, x, y, 9)

    def dibujar_ruta(self, pantalla, ruta):
        if not ruta or len(ruta) < 2:
            return
        for zona_a, zona_b in zip(ruta, ruta[1:]):
            _dibujar_linea_punteada(pantalla, COLOR_RUTA, self.posicion(zona_a), self.posicion(zona_b), ancho=4)

    def dibujar_zonas(self, pantalla, fuente, resaltadas=None):
        """resaltadas: coleccion (set/dict/list) de nombres de zona activas (pickup/paradas/dropoff)."""
        resaltadas = resaltadas or ()
        for nombre, zona in self.grafo.zonas.items():
            x, y = self.posicion(nombre)
            if zona.es_local:
                radio = self.RADIO_LOCAL
                pygame.draw.circle(pantalla, COLOR_LOCAL, (x, y), radio)
                pygame.draw.circle(pantalla, COLOR_FONDO_MAPA, (x, y), max(2, int(radio * 0.35)))
            elif nombre in resaltadas:
                radio = self.RADIO_ZONA_TERMINAL
                dibujar_icono_pin(pantalla, x, y, radio, COLOR_ZONA_TERMINAL)
            else:
                radio = self.RADIO_ZONA
                pygame.draw.circle(pantalla, COLOR_ZONA_NORMAL, (x, y), radio)

            etiqueta = fuente.render(nombre, True, COLOR_TEXTO_SOBRE_BLANCO)
            pantalla.blit(etiqueta, (x - etiqueta.get_width() // 2, y + radio + 2))

    def dibujar_base(self, pantalla, fuente, ruta_resaltada=None, resaltadas=None):
        pantalla.blit(self.mapa2, (0, 0))
        pantalla.blit(self.mapa, (313, 16))
        self.dibujar_calles(pantalla)
        self.dibujar_ruta(pantalla, ruta_resaltada)
        self.dibujar_zonas(pantalla, fuente, resaltadas)


# ---------------------------------------------------------------------------
# Repartidores animados
# ---------------------------------------------------------------------------


class VistaRepartidores:
    """
    Traduce los eventos discretos del Dispatcher (zona_actual cambia de
    golpe) en un movimiento animado: cuando la zona destino cambia, arranca
    una transicion lineal de DURACION_TRANSICION segundos entre la
    posicion anterior y la nueva, e interpola cada frame con el reloj real.
    """

    DURACION_TRANSICION = 0.5

    def __init__(self, vista_mapa: VistaMapa):
        self.vista_mapa = vista_mapa
        self.animaciones = {}
        self._colores = {}
        self._siguiente_color = 0

    def _color_para(self, id_repartidor):
        if id_repartidor not in self._colores:
            self._colores[id_repartidor] = COLORES_REPARTIDOR[self._siguiente_color % len(COLORES_REPARTIDOR)]
            self._siguiente_color += 1
        return self._colores[id_repartidor]

    def actualizar(self, id_repartidor, zona_actual, estado, ahora):
        anim = self.animaciones.get(id_repartidor)
        if anim is None:
            self.animaciones[id_repartidor] = {
                "zona_origen": zona_actual, "zona_destino": zona_actual,
                "inicio": ahora, "estado": estado,
            }
            return

        if anim["zona_destino"] != zona_actual:
            anim["zona_origen"] = anim["zona_destino"]
            anim["zona_destino"] = zona_actual
            anim["inicio"] = ahora
        anim["estado"] = estado

    def eliminar(self, id_repartidor):
        self.animaciones.pop(id_repartidor, None)

    def _posicion_actual(self, anim, ahora):
        x0, y0 = self.vista_mapa.posicion(anim["zona_origen"])
        x1, y1 = self.vista_mapa.posicion(anim["zona_destino"])
        progreso = (ahora - anim["inicio"]) / self.DURACION_TRANSICION
        progreso = max(0.0, min(1.0, progreso))
        return x0 + (x1 - x0) * progreso, y0 + (y1 - y0) * progreso

    def dibujar(self, pantalla, fuente, ahora):
        for id_repartidor, anim in self.animaciones.items():
            x, y = self._posicion_actual(anim, ahora)
            color = COLOR_BADGE_ERROR_FONDO if anim["estado"] in ("retrasado", "caido_reasignando") else self._color_para(id_repartidor)

            pygame.draw.circle(pantalla, COLOR_FONDO_MAPA, (int(x), int(y)), 15)
            pygame.draw.circle(pantalla, COLOR_ZONA_NORMAL, (int(x), int(y)), 15, 1)
            dibujar_icono_moto(pantalla, x, y, 20, color)

            etiqueta = fuente.render(f"{id_repartidor}: {anim['estado']}", True, COLOR_TEXTO_SOBRE_BLANCO)
            pantalla.blit(etiqueta, (x + 16, y - 8))


# ---------------------------------------------------------------------------
# Panel de estado del pedido (fases REPARTIDOR_ASIGNADO / ENTREGADO)
# ---------------------------------------------------------------------------

PADDING_SHEET = 12
GAP_ENTRE_TARJETAS = 10
MAX_PEDIDOS_VISIBLES = 2
ALTO_VACIO = 90
ALTO_NOTA_TRUNCADO = 20

_PAD_TARJETA = 8
_ALTO_FILA_TITULO = 22
_ALTO_FILA_REPARTIDOR = 26
_ALTO_METRICAS = 30

ALTO_TARJETA_COMPACTA = _PAD_TARJETA * 2 + _ALTO_FILA_TITULO + _ALTO_FILA_REPARTIDOR + _ALTO_METRICAS
ALTO_MAX_PANEL_ESTADO = (
    PADDING_SHEET * 2
    + 2 * ALTO_TARJETA_COMPACTA
    + GAP_ENTRE_TARJETAS
    + ALTO_NOTA_TRUNCADO
)


def _dibujar_tarjeta_pedido(pantalla, fuentes, rect, tarjeta):
    """
    Dibuja (o mide, si pantalla es None) una tarjeta compacta con el estado
    del pedido en curso (repartidor, tiempo, costo) sobre el panel oscuro.

    tarjeta: dict con titulo (ya incluye estado/local/tipo/paradas resuelto
    por main.py), badge_texto, badge_fondo, badge_texto_color,
    repartidor_texto, tiempo_valor, costo_base_texto, recargo_texto,
    recargo_activo (bool), total_texto.
    """
    medir_solo = pantalla is None
    x0, y0, ancho = rect.x, rect.y, rect.width
    y = y0 + _PAD_TARJETA

    texto_titulo = fuentes["negrita"].render(tarjeta["titulo"], True, COLOR_TEXTO_SOBRE_NEGRO)
    badge_texto_surf = fuentes["badge"].render(tarjeta["badge_texto"], True, tarjeta["badge_texto_color"])
    badge_w = badge_texto_surf.get_width() + 18
    badge_h = badge_texto_surf.get_height() + 6

    if not medir_solo:
        pantalla.blit(texto_titulo, (x0 + _PAD_TARJETA, y))

        badge_rect = pygame.Rect(0, 0, badge_w, badge_h)
        badge_rect.midright = (x0 + ancho - _PAD_TARJETA, y + texto_titulo.get_height() // 2)
        pygame.draw.rect(pantalla, tarjeta["badge_fondo"], badge_rect, border_radius=badge_h // 2)
        pantalla.blit(badge_texto_surf, (badge_rect.x + 9, badge_rect.y + 3))

    y2 = y + _ALTO_FILA_TITULO
    cy_icono = y2 + 12

    if not medir_solo:
        cx_icono = x0 + _PAD_TARJETA + 11
        pygame.draw.circle(pantalla, COLOR_TARJETA_METRICA_FONDO, (cx_icono, cy_icono), 12)
        dibujar_icono_moto(pantalla, cx_icono, cy_icono, 14, COLOR_TEXTO_SOBRE_NEGRO)

        texto_repartidor = tarjeta["repartidor_texto"] or "Buscando repartidor..."
        superficie_rep = fuentes["normal"].render(texto_repartidor, True, COLOR_TEXTO_SOBRE_NEGRO)
        pantalla.blit(superficie_rep, (cx_icono + 18, cy_icono - superficie_rep.get_height() // 2))

        superficie_tiempo = fuentes["normal"].render(tarjeta["tiempo_valor"], True, COLOR_TEXTO_SOBRE_NEGRO)
        x_tiempo = x0 + ancho - _PAD_TARJETA - superficie_tiempo.get_width()
        pantalla.blit(superficie_tiempo, (x_tiempo, cy_icono - superficie_tiempo.get_height() // 2))
        dibujar_icono_reloj(pantalla, x_tiempo - 14, cy_icono, 14, COLOR_TEXTO_SECUNDARIO_NEGRO)

    y3 = y2 + _ALTO_FILA_REPARTIDOR

    # --- fila de metricas: 3 cajas (tarifa base / recargo / total) ---
    ancho_col = (ancho - 2 * _PAD_TARJETA - 2 * 6) // 3
    columnas = [
        ("Tarifa base", tarjeta["costo_base_texto"], COLOR_TEXTO_SOBRE_NEGRO),
        ("Recargo", tarjeta["recargo_texto"], COLOR_BADGE_ALERTA_TEXTO if tarjeta["recargo_activo"] else COLOR_TEXTO_SECUNDARIO_NEGRO),
        ("Total", tarjeta["total_texto"], COLOR_TEXTO_SOBRE_NEGRO),
    ]
    if not medir_solo:
        x_col = x0 + _PAD_TARJETA
        for etiqueta, valor, color_valor in columnas:
            caja = pygame.Rect(x_col, y3, ancho_col, _ALTO_METRICAS)
            pygame.draw.rect(pantalla, COLOR_TARJETA_METRICA_FONDO, caja, border_radius=7)
            superficie_etq = fuentes["chica"].render(etiqueta, True, COLOR_TEXTO_SECUNDARIO_NEGRO)
            pantalla.blit(superficie_etq, (caja.x + 7, caja.y + 3))
            superficie_val = fuentes["normal"].render(str(valor), True, color_valor)
            pantalla.blit(superficie_val, (caja.x + 7, caja.y + 2 + superficie_etq.get_height()))
            x_col += ancho_col + 6

    return (y3 + _ALTO_METRICAS + _PAD_TARJETA) - y0


def _medir_alto_panel_estado(fuentes, ancho, tarjetas, max_visibles):
    """Misma logica de altura que dibujar_panel_estado, sin dibujar nada (para ubicar botones antes de leer eventos)."""
    visibles = tarjetas[:max_visibles]
    ocultos = len(tarjetas) - len(visibles)

    if not visibles:
        return ALTO_VACIO

    alto_total = PADDING_SHEET
    ancho_tarjeta = ancho - 2 * PADDING_SHEET
    for i, tarjeta in enumerate(visibles):
        alto_total += _dibujar_tarjeta_pedido(None, fuentes, pygame.Rect(0, 0, ancho_tarjeta, 0), tarjeta)
        if i < len(visibles) - 1:
            alto_total += GAP_ENTRE_TARJETAS
    alto_total += PADDING_SHEET
    if ocultos > 0:
        alto_total += ALTO_NOTA_TRUNCADO

    return min(alto_total, ALTO_MAX_PANEL_ESTADO)


def calcular_rect_panel_estado(fuentes, x, ancho, y_fondo, tarjetas, max_visibles=MAX_PEDIDOS_VISIBLES):
    """Rect que va a ocupar el panel este frame, sin dibujar nada todavia."""
    alto_total = _medir_alto_panel_estado(fuentes, ancho, tarjetas, max_visibles)
    return pygame.Rect(x, y_fondo - alto_total, ancho, alto_total)


def dibujar_panel_estado(pantalla, fuentes, x, ancho, y_fondo, tarjetas, max_visibles=MAX_PEDIDOS_VISIBLES):
    """
    Dibuja el panel oscuro de estado del pedido, anclado por su borde
    inferior en `y_fondo`, con hasta `max_visibles` tarjetas apiladas (la
    mas reciente primero). Devuelve el Rect dibujado.
    """
    visibles = tarjetas[:max_visibles]
    ocultos = len(tarjetas) - len(visibles)
    rect = calcular_rect_panel_estado(fuentes, x, ancho, y_fondo, tarjetas, max_visibles)

    superficie = _superficie_redondeada(rect.width, rect.height, COLOR_PANEL_ESTADO_FONDO, radius=16, borde_color=COLOR_PANEL_ESTADO_BORDE)
    pantalla.blit(superficie, rect.topleft)

    if not visibles:
        texto = fuentes["normal"].render("Sin pedidos en curso", True, COLOR_TEXTO_SECUNDARIO_NEGRO)
        pantalla.blit(texto, (rect.centerx - texto.get_width() // 2, rect.centery - texto.get_height() // 2))
        return rect

    y_cursor = rect.y + PADDING_SHEET
    ancho_tarjeta = ancho - 2 * PADDING_SHEET
    for i, tarjeta in enumerate(visibles):
        rect_tarjeta = pygame.Rect(rect.x + PADDING_SHEET, y_cursor, ancho_tarjeta, 0)
        usado = _dibujar_tarjeta_pedido(pantalla, fuentes, rect_tarjeta, tarjeta)
        y_cursor += usado
        if i < len(visibles) - 1:
            y_cursor += GAP_ENTRE_TARJETAS

    if ocultos > 0:
        texto = fuentes["chica"].render(f"+{ocultos} pedido(s) mas en curso", True, COLOR_TEXTO_SECUNDARIO_NEGRO)
        pantalla.blit(texto, (rect.x + PADDING_SHEET, y_cursor + 2))

    return rect


# ---------------------------------------------------------------------------
# Panel de historial (tema claro, con scroll)
# ---------------------------------------------------------------------------

ALTO_FILA_HISTORIAL = 46


def altura_contenido_historial(historial):
    return len(historial) * ALTO_FILA_HISTORIAL


def clamp_scroll_historial(historial, scroll_offset, alto_visible):
    """Mantiene el scroll dentro de [0, maximo desplazable] segun cuanto contenido sobra."""
    maximo = max(0, altura_contenido_historial(historial) - (alto_visible - 20))
    return max(0, min(scroll_offset, maximo))


def dibujar_panel_historial(pantalla, fuentes, rect, historial, scroll_offset):
    """
    Panel de pedidos ya finalizados (tema claro, igual que el resto de la
    interfaz), con scroll por rueda del mouse (`scroll_offset` lo administra
    main.py). Usa set_clip para que las filas no se dibujen fuera de `rect`.
    """
    dibujar_tarjeta_blanca(pantalla, rect, radius=16)

    if not historial:
        texto = fuentes["normal"].render("Todavia no hay pedidos entregados", True, COLOR_TEXTO_SECUNDARIO_BLANCO)
        pantalla.blit(texto, (rect.centerx - texto.get_width() // 2, rect.centery - texto.get_height() // 2))
        return

    clip_anterior = pantalla.get_clip()
    pantalla.set_clip(rect)

    y = rect.y + 10 - scroll_offset
    for i, fila in enumerate(historial):
        fila_rect = pygame.Rect(rect.x, y, rect.width, ALTO_FILA_HISTORIAL)
        if fila_rect.bottom >= rect.y and fila_rect.top <= rect.bottom:
            titulo = fuentes["normal"].render(fila["titulo"], True, COLOR_TEXTO_SOBRE_BLANCO)
            pantalla.blit(titulo, (rect.x + 12, y))
            subtitulo = fuentes["chica"].render(fila["subtitulo"], True, COLOR_TEXTO_SECUNDARIO_BLANCO)
            pantalla.blit(subtitulo, (rect.x + 12, y + titulo.get_height() + 2))

            badge_surf = fuentes["badge"].render(fila["badge_texto"], True, fila["badge_texto_color"])
            badge_rect = pygame.Rect(0, 0, badge_surf.get_width() + 16, badge_surf.get_height() + 6)
            badge_rect.topright = (rect.right - 12, y)
            pygame.draw.rect(pantalla, fila["badge_fondo"], badge_rect, border_radius=badge_rect.height // 2)
            pantalla.blit(badge_surf, (badge_rect.x + 8, badge_rect.y + 3))

            costo_surf = fuentes["chica"].render(fila["costo_texto"], True, COLOR_TEXTO_MUTED_BLANCO)
            pantalla.blit(costo_surf, costo_surf.get_rect(topright=(rect.right - 12, badge_rect.bottom + 4)))

            if i < len(historial) - 1:
                pygame.draw.line(pantalla, COLOR_CALLE, (rect.x + 12, fila_rect.bottom - 4), (rect.right - 12, fila_rect.bottom - 4), 1)

        y += ALTO_FILA_HISTORIAL

    pantalla.set_clip(clip_anterior)


def medir_alto_resumen(fuentes, cantidad_lineas):
    return 16 + cantidad_lineas * (fuentes["chica"].get_height() + 4)


def dibujar_lineas(pantalla, fuentes, x, y, lineas, fuente_clave="chica"):
    """Renderiza una lista de (texto, color) apiladas verticalmente, sin fondo propio (va dentro de una tarjeta ya dibujada). Devuelve el alto usado."""
    y_texto = y
    for texto, color in lineas:
        superficie_linea = fuentes[fuente_clave].render(texto, True, color)
        pantalla.blit(superficie_linea, (x, y_texto))
        y_texto += superficie_linea.get_height() + 4
    return y_texto - y


# ---------------------------------------------------------------------------
# Botones clickeables
# ---------------------------------------------------------------------------


class Boton:
    """Boton rectangular reutilizable: main.py decide texto/color/activo cada frame, esto solo dibuja y detecta click."""

    def __init__(self, rect, texto, color_fondo, color_texto, color_borde=None):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.color_fondo = color_fondo
        self.color_texto = color_texto
        self.color_borde = color_borde
        self.activo = True
        self.seleccionado = False

    def dibujar(self, superficie, fuente):
        if not self.activo:
            color_fondo = COLOR_BOTON_SECUNDARIO_FONDO
            color_texto = COLOR_TEXTO_MUTED_BLANCO
            color_borde = self.color_borde
            ancho_borde = 1
        elif self.seleccionado:
            color_fondo = COLOR_BOTON_ACENTO
            color_texto = COLOR_BOTON_ACENTO_TEXTO
            color_borde = COLOR_BOTON_ACENTO
            ancho_borde = 2
        else:
            color_fondo = self.color_fondo
            color_texto = self.color_texto
            color_borde = self.color_borde
            ancho_borde = 1

        pygame.draw.rect(superficie, color_fondo, self.rect, border_radius=8)
        if color_borde:
            pygame.draw.rect(superficie, color_borde, self.rect, width=ancho_borde, border_radius=8)
        texto_render = fuente.render(self.texto, True, color_texto)
        texto_rect = texto_render.get_rect(center=self.rect.center)
        superficie.blit(texto_render, texto_rect)

    def click_en(self, pos_mouse):
        return self.activo and self.rect.collidepoint(pos_mouse)


# ---------------------------------------------------------------------------
# Barra de busqueda
# ---------------------------------------------------------------------------


class CampoBusqueda:
    """
    Input de texto simple (Pygame no trae uno nativo): un rectangulo que se
    activa con click, acumula texto con eventos KEYDOWN, y al presionar
    ENTER busca coincidencias (parciales, sin distinguir mayusculas) contra
    los nombres de zona del grafo. Convive con la seleccion por click
    directo en el mapa: ambas terminan llamando a la misma funcion
    `seleccionar_zona` en main.py. Pensado para vivir DENTRO de una tarjeta
    blanca ya dibujada por main.py (no tiene fondo translucido propio).
    """

    ALTO_SUGERENCIA = 22
    MAX_SUGERENCIAS = 5

    def __init__(self, rect):
        self.rect = rect
        self.activo = False
        self.texto = ""
        self.sugerencias = []
        self.mensaje = None

    def _buscar(self, grafo):
        texto = self.texto.strip().lower()
        if not texto:
            return []
        return [nombre for nombre in grafo.zonas if texto in nombre.lower()]

    def _armar_sugerencias(self, coincidencias):
        self.sugerencias = []
        y = self.rect.bottom + 4
        for nombre in coincidencias[: self.MAX_SUGERENCIAS]:
            rect_sugerencia = pygame.Rect(self.rect.x, y, self.rect.width, self.ALTO_SUGERENCIA)
            self.sugerencias.append((nombre, rect_sugerencia))
            y += self.ALTO_SUGERENCIA

    def manejar_click(self, pos):
        """Devuelve el nombre de zona elegido si se hizo click en una sugerencia, o None."""
        for nombre, rect_sugerencia in self.sugerencias:
            if rect_sugerencia.collidepoint(pos):
                self.texto = ""
                self.sugerencias = []
                self.activo = False
                return nombre

        self.activo = self.rect.collidepoint(pos)
        if self.activo:
            self.sugerencias = []
            self.mensaje = None
        return None

    def manejar_tecla(self, evento_keydown, grafo):
        """Procesa un KEYDOWN cuando el campo esta activo. Devuelve el nombre de zona si ENTER dio una coincidencia unica."""
        if not self.activo:
            return None

        if evento_keydown.key == pygame.K_BACKSPACE:
            self.texto = self.texto[:-1]
            self.sugerencias = []
            self.mensaje = None

        elif evento_keydown.key == pygame.K_RETURN:
            coincidencias = self._buscar(grafo)
            if len(coincidencias) == 1:
                nombre = coincidencias[0]
                self.texto = ""
                self.sugerencias = []
                self.mensaje = None
                return nombre
            elif len(coincidencias) > 1:
                self._armar_sugerencias(coincidencias)
                self.mensaje = None
            else:
                self.mensaje = "Zona no encontrada"
                self.texto = ""
                self.sugerencias = []

        elif evento_keydown.unicode and evento_keydown.unicode.isprintable():
            self.texto += evento_keydown.unicode
            self.sugerencias = []
            self.mensaje = None

        return None

    def dibujar(self, pantalla, fuente):
        color_fondo = COLOR_TARJETA_FONDO if self.activo else COLOR_BOTON_SECUNDARIO_FONDO
        pygame.draw.rect(pantalla, color_fondo, self.rect, border_radius=8)
        pygame.draw.rect(pantalla, COLOR_BOTON_ACENTO if self.activo else COLOR_CALLE, self.rect, width=1, border_radius=8)

        dibujar_icono_lupa(pantalla, self.rect.x + 18, self.rect.centery, 16, COLOR_TEXTO_SECUNDARIO_BLANCO)

        if self.texto:
            texto_mostrado, color_texto = self.texto, COLOR_TEXTO_SOBRE_BLANCO
        else:
            texto_mostrado, color_texto = "Buscar zona...", COLOR_TEXTO_MUTED_BLANCO
        superficie_txt = fuente.render(texto_mostrado, True, color_texto)
        pantalla.blit(superficie_txt, (self.rect.x + 34, self.rect.y + (self.rect.height - superficie_txt.get_height()) // 2))

        if self.sugerencias:
            primero, ultimo = self.sugerencias[0][1], self.sugerencias[-1][1]
            rect_lista = pygame.Rect(primero.x, primero.y, primero.width, ultimo.bottom - primero.y)
            pygame.draw.rect(pantalla, COLOR_TARJETA_FONDO, rect_lista, border_radius=8)
            pygame.draw.rect(pantalla, COLOR_CALLE, rect_lista, width=1, border_radius=8)

            for i, (nombre, rect_sugerencia) in enumerate(self.sugerencias):
                superficie_s = fuente.render(nombre, True, COLOR_TEXTO_SOBRE_BLANCO)
                pantalla.blit(superficie_s, (rect_sugerencia.x + 8, rect_sugerencia.y + 3))
                if i < len(self.sugerencias) - 1:
                    pygame.draw.line(
                        pantalla, COLOR_CALLE,
                        (rect_sugerencia.x + 8, rect_sugerencia.bottom), (rect_sugerencia.right - 8, rect_sugerencia.bottom), 1,
                    )

        if self.mensaje:
            superficie_m = fuente.render(self.mensaje, True, COLOR_ERROR_TEXTO_BLANCO)
            pantalla.blit(superficie_m, (self.rect.x, self.rect.bottom + 4))


if __name__ == "__main__":
    from datos_zonas import construir_grafo_quito

    pygame.init()
    ANCHO, ALTO = 1100, 780
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("QuitoExpress - prueba de interfaz.py")
    reloj = pygame.time.Clock()
    fuentes = {
        "normal": pygame.font.SysFont("Segoe UI", 14),
        "chica": pygame.font.SysFont("Segoe UI", 12),
        "negrita": pygame.font.SysFont("Segoe UI", 15, bold=True),
        "badge": pygame.font.SysFont("Segoe UI", 11, bold=True),
    }
    campo_busqueda = CampoBusqueda(pygame.Rect(28, 100, 280, 36))

    grafo = construir_grafo_quito()
    vista_mapa = VistaMapa(grafo)
    vista_repartidores = VistaRepartidores(vista_mapa)

    ruta_ejemplo, _ = grafo.ruta_encadenada("Local A - Norte", "Cumbaya", "Centro Historico")

    tarjeta_ejemplo = {
        "titulo": "Local A - Norte · Comida · 1 parada",
        "badge_texto": "En camino",
        "badge_fondo": COLOR_BADGE_EXITO_FONDO,
        "badge_texto_color": COLOR_BADGE_EXITO_TEXTO,
        "repartidor_texto": "Local A - Norte-R1 · Guapulo",
        "tiempo_valor": "12.4 min",
        "costo_base_texto": "$3.50",
        "recargo_texto": "Sin recargo",
        "recargo_activo": False,
        "total_texto": "$3.50",
    }

    indice_actual = 0
    tiempo_ultimo_paso = pygame.time.get_ticks() / 1000.0
    id_falso = "Local A - Norte-R1"
    angulo_spinner = 0.0

    cerrar_automatico_ms = pygame.time.get_ticks() + 6000
    corriendo = True
    while corriendo:
        ahora = pygame.time.get_ticks() / 1000.0
        angulo_spinner += 0.15

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            if evento.type == pygame.MOUSEBUTTONDOWN:
                campo_busqueda.manejar_click(evento.pos)
            if evento.type == pygame.KEYDOWN:
                campo_busqueda.manejar_tecla(evento, grafo)

        if ahora - tiempo_ultimo_paso > 1.0 and indice_actual < len(ruta_ejemplo) - 1:
            indice_actual += 1
            tiempo_ultimo_paso = ahora
            estado = "recogido" if ruta_ejemplo[indice_actual] == "Cumbaya" else "en_camino_a_recoger"
            vista_repartidores.actualizar(id_falso, ruta_ejemplo[indice_actual], estado, ahora)

        vista_mapa.dibujar_base(
            pantalla, fuentes["normal"],
            ruta_resaltada=ruta_ejemplo,
            resaltadas={"Local A - Norte", "Cumbaya", "Centro Historico"},
        )
        vista_repartidores.dibujar(pantalla, fuentes["normal"], ahora)
        dibujar_panel_estado(pantalla, fuentes, 12, ANCHO - 24, ALTO - 12, [tarjeta_ejemplo])

        rect_tarjeta = pygame.Rect(12, 12, 320, 160)
        dibujar_tarjeta_blanca(pantalla, rect_tarjeta)
        dibujar_spinner(pantalla, (rect_tarjeta.centerx, 70), 20, angulo_spinner, COLOR_BOTON_ACENTO)
        campo_busqueda.dibujar(pantalla, fuentes["normal"])

        pygame.display.flip()
        reloj.tick(30)

        if pygame.time.get_ticks() > cerrar_automatico_ms:
            corriendo = False

    pygame.quit()
