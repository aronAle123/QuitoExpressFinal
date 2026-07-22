# Contexto del proyecto QuitoExpress — prompt para Claude

Pega este documento al inicio de una conversación con Claude para darle contexto completo del proyecto antes de pedirle cambios, revisiones o nuevas funcionalidades.

## Qué es QuitoExpress

Simulador de una app de delivery (estilo Uber Eats) para la ciudad de Quito, hecho en Python con Pygame. Corre en un único proceso de interfaz gráfica más N procesos independientes (uno por repartidor) coordinados con `multiprocessing`. El proyecto integra tres unidades de estructuras de datos:

1. **Grafos**: modelo de la ciudad como grafo ponderado no dirigido, con Árbol de Expansión Mínima (Prim) para calcular rutas, y DFS/BFS para verificar cobertura.
2. **Árboles**: dos árboles de decisión (no BST) que deciden lógica real de negocio, con los 4 recorridos clásicos (pre-orden, post-orden, in-orden, por niveles) implementados como métodos reutilizables.
3. **Concurrencia/colas**: cada repartidor es un `multiprocessing.Process` con su propia cola de órdenes; el Dispatcher usa una cola de prioridad (`heapq`) por local para encolar pedidos cuando no hay repartidores libres.

No usa librerías externas de grafos (no networkx) ni Dijkstra: las rutas se obtienen recorriendo el único camino que existe dentro del MST (justificación completa en el docstring de `grafo.py`).

## Archivos y responsabilidades

- **`grafo.py`** — estructura de datos del grafo + algoritmos (Prim, BFS, DFS). No sabe nada de pedidos ni UI.
- **`datos_zonas.py`** — datos estáticos: zonas de Quito con coordenadas, locales, conexiones (calles) con peso. Construye el `GrafoCiudad` ya poblado.
- **`arbol.py`** — árboles de decisión (`NodoArbol` genérico + `ArbolAsignacionLocal` + `ArbolTipoServicio`) y sus recorridos.
- **`dispatcher.py`** — coordina pedidos↔repartidores desde el proceso principal: lanza los `Process`, mantiene colas de prioridad por local, calcula el costo del envío.
- **`repartidor.py`** — la función `proceso_repartidor`, target de cada `multiprocessing.Process`: simula el recorrido zona por zona y reporta eventos.
- **`interfaz.py`** — todo el dibujo con Pygame (mapa, repartidores animados, tarjetas, botones, buscador, historial). No contiene lógica de negocio.
- **`main.py`** — punto de entrada: arma todo, corre el loop principal de Pygame, conecta clicks → grafo/árboles → dispatcher → interfaz.

Cada módulo tiene un bloque `if __name__ == "__main__":` con pruebas de consola independientes (útil para probar lógica sin abrir la ventana de Pygame).

---

## `grafo.py`

### `distancia_a_tiempo_min(distancia_km, factor=2.5) -> float`
Convierte distancia (km) a minutos estimados de viaje (factor fijo ≈ velocidad promedio urbana).

### `class Zona`
Nodo del grafo: `nombre`, `x`, `y` (coordenadas de dibujo, no GPS reales), `es_local` (bool).

### `class GrafoCiudad`
Grafo ponderado no dirigido con diccionario de adyacencia (`self.adyacencia`) más un Árbol de Expansión Mínima calculado aparte (`self.arbol_adyacencia`, `self.arbol_aristas`, `self.arbol_costo_total`) y un set de aristas bloqueadas (`self.aristas_bloqueadas`) para simular accidentes.

- **`agregar_zona(zona)`** — registra una `Zona` en el grafo.
- **`agregar_conexion(zona_a, zona_b, peso)`** — agrega una calle en ambos sentidos.
- **`construir_arbol_expansion_minima()`** — algoritmo de **Prim** con heap de prioridad. Corre Prim por cada componente conexa (arma un *bosque* si hay zonas desconectadas, como la "Zona Aislada" a propósito). Ignora aristas bloqueadas. Se llama una sola vez al construir el grafo, y de nuevo cada vez que se bloquea/repara una calle. Retorna `(arbol_aristas, arbol_costo_total, arbol_adyacencia)`.
- **`camino_en_arbol(origen, destino)`** — BFS simple **dentro del MST** (no Dijkstra: en un árbol solo existe un camino posible entre dos nodos, no hay que comparar alternativas). Retorna `(ruta, costo)` o `(None, None)` si no hay cobertura.
- **`ruta_multi_tramo(puntos: list[str])`** — encadena `camino_en_arbol` tramo por tramo entre puntos consecutivos (ej. Local → Pickup → Parada1 → Dropoff). Retorna `(ruta_completa, costo_total)`.
- **`ruta_encadenada(local, pickup, dropoff)`** — atajo de `ruta_multi_tramo` sin paradas.
- **`zona_mas_cercana(origen, candidatos)`** — de una lista de candidatos (normalmente los locales), cuál está más cerca según el MST. Retorna `(nombre, distancia)`.
- **`dfs(inicio)`** — recorrido en profundidad sobre el **grafo original** (no el MST), recursivo.
- **`bfs(inicio)`** — recorrido en anchura sobre el grafo original, con `deque`.
- **`zonas_con_cobertura(origen)`** — set de zonas alcanzables desde `origen` (usa `bfs`); prueba real de cobertura de entrega.
- **`arista_esta_bloqueada(zona_a, zona_b)`** — bool.
- **`bloquear_arista(zona_a, zona_b)`** — simula un accidente: bloquea la calle y reconstruye el MST excluyéndola.
- **`reparar_arista(zona_a, zona_b)`** — desbloquea y reconstruye el MST; a propósito no recalcula rutas ya en curso.
- **`elegir_arista_para_accidente(ruta_referencia=None)`** — elige al azar una arista sin bloquear, prefiriendo una que esté sobre `ruta_referencia` (el tramo restante del pedido activo) para que el efecto se note en el mapa.

---

## `datos_zonas.py`

- **`ZONAS`** — lista de tuplas `(nombre, x, y, es_local)`, agrupadas por sector (Norte/Centro/Sur) más una `"Zona Aislada"` sin conexiones (a propósito, para demostrar el caso "sin cobertura").
- **`CONEXIONES`** — lista de tuplas `(zona_a, zona_b, peso_km)`.
- **`construir_grafo_quito() -> GrafoCiudad`** — arma el `GrafoCiudad`, agrega zonas y conexiones, y construye el MST una sola vez.
- **`LOCALES`** — `["Local A - Norte", "Local B - Sur"]`.

---

## `arbol.py`

### `class NodoArbol`
Nodo genérico (interno con hijos por rama, u hoja con valor). Hijos guardados como lista de `(rama, nodo)` (no dict) para tener orden fijo entre hermanos.

- **`agregar_hijo(rama, nodo)`**
- **`hijo(rama)`** — busca hijo por etiqueta de rama.
- **`ramas()`** — lista de etiquetas de rama.
- **`nodos_hijos()`**
- **`preorden(fn)`** — nodo actual, luego cada hijo (recursivo).
- **`postorden(fn)`** — todos los hijos primero, nodo actual al final.
- **`inorden(fn)`** — generalización del in-orden binario clásico a N hijos (primera mitad de hijos antes del nodo, segunda mitad después).
- **`por_niveles(fn)`** — BFS sobre el árbol con `deque`.

### `class ArbolAsignacionLocal`
Árbol de 2 niveles que decide qué local (A o B) despacha un pedido. Nivel 1: cuál local está más cerca (según MST). Nivel 2: si ese local tiene repartidor libre; si no, failover al otro local.

- **`decidir(distancia_a, distancia_b, disponible_a, disponible_b) -> str`** — recorre el árbol y devuelve el nombre del local asignado (o `None` si ningún local tiene cobertura).

### `class ArbolTipoServicio`
Árbol de 1 nivel que clasifica el pedido en 3 hojas: Comida (prioridad 1, ×1.0), Documento (prioridad 2, ×1.0), Paquete (prioridad 3, ×1.5).

- **`clasificar(tipo: str) -> dict`** — devuelve `{"tipo", "prioridad", "multiplicador_tiempo"}`; lanza `ValueError` si el tipo no existe.

---

## `dispatcher.py`

- **`calcular_costo(distancia_total_km, multiplicador_tipo, demanda_alta) -> dict`** — tarifa base ($0.50/km × multiplicador del tipo) + recargo del 30% si `demanda_alta` (local sin repartidores libres al crear el pedido). Retorna `{costo_base, recargo_demanda, demanda_alta, total}`.

### `class Dispatcher`
Vive en el proceso principal; coordina pedidos↔repartidores.

- **`__init__(locales, repartidores_por_local, prob_fallo, tiempo_por_zona)`** — crea, por cada local, N `mp.Process` (target `proceso_repartidor`) con su propia `mp.Queue` de órdenes, más una `mp.Queue` de estado compartida (`cola_estado`) que leen todos.
- **`iniciar()`** — arranca todos los procesos.
- **`detener()`** — manda señal de apagado (`None`) a cada cola de órdenes y hace `join`.
- **`nuevo_pedido(local, pedido) -> dict`** — si hay repartidor libre en ese local, despacha inmediato; si no, lo encola en un heap de prioridad (`heapq`) por local, según la prioridad del `ArbolTipoServicio`. Retorna `{despachado_inmediato, pedidos_delante}`.
- **`_despachar_si_hay_libre(local, pedido) -> bool`** — helper interno.
- **`_intentar_vaciar_pendientes(local)`** — al liberarse un repartidor, saca pedidos del heap mientras haya libres.
- **`procesar_eventos() -> list`** — drena (no bloqueante) `cola_estado`, actualiza el estado interno y devuelve los eventos procesados; se llama cada frame desde `main.py`.
- **`_procesar_evento(evento)`** — si el repartidor "cae" (`caido_reasignando`), reencola su pedido pendiente; si queda `libre`, intenta vaciar pendientes.
- **`hay_pendientes() -> bool`**
- **`actualizar_ruta_en_curso(id_repartidor, id_pedido, ruta_restante_nueva)`** — manda un mensaje de control (no un pedido nuevo) a la cola personal del repartidor para que adopte una ruta recalculada (ej. por un accidente) sin reiniciar la entrega.

---

## `repartidor.py`

- **`proceso_repartidor(id_repartidor, nombre_local, cola_ordenes, cola_estado, prob_fallo=0.05, tiempo_por_zona=0.6)`** — target de cada `Process`. Bucle de vida:
  1. Reporta `"libre"`.
  2. Bloquea en `cola_ordenes.get()` esperando un pedido.
  3. Simula el recorrido de `ruta_restante` zona por zona (`time.sleep` por zona), reportando estado a cada paso: `en_camino_a_recoger` → `recogido` (al llegar al pickup) → `en_camino_a_entregar` → `entregado` → `libre`.
  4. Entre paso y paso revisa (no bloqueante, `get_nowait`) si llegó un mensaje de control `{"tipo_mensaje": "actualizar_ruta", ...}` para adoptar una ruta recalculada sin perder `ya_recogido` ni reiniciar el pedido.
  5. Con probabilidad `prob_fallo` (~5%) simula una caída: reporta `"retrasado"` y luego `"caido_reasignando"` con el pedido pendiente (para que el Dispatcher lo reencole a otro repartidor) — tolerancia a fallos real, no solo cosmética.

---

## `interfaz.py`

Solo dibujo (Pygame), sin lógica de negocio. Tema claro con panel oscuro flotante para el pedido en curso.

**Iconos vectoriales** (formas primitivas, sin imágenes externas): `dibujar_icono_moto`, `dibujar_icono_pin`, `dibujar_icono_lupa`, `dibujar_icono_reloj`, `dibujar_icono_advertencia`, `dibujar_spinner`.

**Helpers**: `_dibujar_linea_punteada` (Pygame no trae líneas punteadas nativas), `_superficie_redondeada` (surface con esquinas redondeadas y alpha), `dibujar_tarjeta_blanca`.

### `class VistaMapa`
- **`posicion(nombre_zona)`** — coordenadas en pantalla (aplica offset/escala).
- **`zona_en_click(pos_mouse, radio_click=16)`** — nombre de zona bajo el click, o `None`.
- **`dibujar_calles(pantalla)`** — dibuja todas las aristas; las bloqueadas en rojo con ícono de advertencia.
- **`dibujar_ruta(pantalla, ruta)`** — línea punteada resaltando la ruta activa.
- **`dibujar_zonas(pantalla, fuente, resaltadas)`** — círculos/pines por zona (locales, zonas activas como pin, resto como punto).
- **`dibujar_base(...)`** — orquesta los tres anteriores.

### `class VistaRepartidores`
Traduce eventos discretos del Dispatcher (la zona cambia de golpe) en movimiento animado interpolado.
- **`actualizar(id_repartidor, zona_actual, estado, ahora)`** — arranca una transición lineal de 0.5s cuando cambia la zona destino.
- **`eliminar(id_repartidor)`**
- **`_posicion_actual(anim, ahora)`** — interpola según el progreso de la transición.
- **`dibujar(pantalla, fuente, ahora)`** — dibuja cada repartidor (moto + etiqueta), en rojo si está retrasado/caído.

### Panel de estado del pedido
- **`_dibujar_tarjeta_pedido(...)`** — dibuja (o solo mide, si `pantalla=None`) una tarjeta con título, badge de estado, repartidor/zona, tiempo restante y desglose de costo.
- **`_medir_alto_panel_estado(...)`**, **`calcular_rect_panel_estado(...)`** — calculan tamaño/posición antes de dibujar (para detección de click consistente).
- **`dibujar_panel_estado(...)`** — dibuja el panel oscuro con hasta N tarjetas apiladas.

### Panel de historial
- **`altura_contenido_historial`**, **`clamp_scroll_historial`** — cálculo de scroll.
- **`dibujar_panel_historial(...)`** — lista de pedidos entregados, con scroll por rueda del mouse, usando `set_clip`.

### Otros
- **`medir_alto_resumen`**, **`dibujar_lineas`** — texto apilado genérico.
- **`class Boton`** — botón rectangular reutilizable (`dibujar`, `click_en`); soporta estado `activo`/`seleccionado`.
- **`class CampoBusqueda`** — input de texto simple (Pygame no trae uno nativo): busca coincidencias parciales entre los nombres de zona, muestra sugerencias clickeables, `ENTER` con coincidencia única selecciona directo.

---

## `main.py`

Orquesta todo. La tarjeta de **selección en curso** está organizada en **fases** (como una app de transporte real), derivadas cada frame SOLO del pickup/dropoff que se está armando (no mutadas a mano) por `calcular_fase`:

```
SELECCIONANDO_PICKUP → SELECCIONANDO_DROPOFF → RESUMEN → (confirmar) → vuelve sola a SELECCIONANDO_PICKUP
```

La fase no sabe nada de los pedidos ya confirmados: esos viven en `estado_app.pedidos` y se dibujan aparte, en el panel oscuro de "pedidos activos" (varias tarjetas apiladas, independientes entre sí), hasta que llegan a `entregado` y pasan al historial. Esto es lo que permite tener varios pedidos corriendo en paralelo (cada uno con su propio proceso de repartidor) sin bloquear la posibilidad de armar un pedido nuevo.

### `class EstadoApp`
Guarda selección en curso (`pickup`, `dropoff`, `paradas`), fase actual, todos los pedidos confirmados -activos e históricos- (`self.pedidos: dict`), accidente activo, etc.
- **`mostrar_mensaje(texto, duracion=3.0)`**
- **`reset_seleccion()`**

### Funciones de lógica
- **`calcular_fase(estado_app)`** — deriva la fase actual del estado real (evita desincronización).
- **`seleccionar_zona(estado_app, nombre_zona)`** — aplica un click/selección de zona: primer click fija pickup, el siguiente fija dropoff (o parada, si `modo_parada` está activo), estilo Uber.
- **`calcular_estimado(...)`** — vista previa del local/ruta/costo para la fase RESUMEN, sin despachar de verdad.
- **`crear_pedido(...)`** — repite el cálculo de `calcular_estimado` y esta vez sí llama a `dispatcher.nuevo_pedido`, registra el pedido en `estado_app.pedidos`.
- **`_ruta_restante_desde(ruta_completa, zona_actual)`** — sub-lista desde la última aparición de `zona_actual` (el repartidor puede pasar dos veces por la misma zona en el árbol).
- **`_arista_en_ruta(ruta, zona_a, zona_b)`** — chequea si un tramo consecutivo de la ruta coincide con una arista dada.
- **`_recalcular_ruta_activa_tras_accidente(...)`** — si el pedido activo dependía de la calle recién bloqueada, recalcula su ruta restante desde la posición actual del repartidor (sin saltarse pickup/paradas pendientes) y se la manda al proceso vía `dispatcher.actualizar_ruta_en_curso`.
- **`simular_accidente(estado_app, grafo, dispatcher)`** — bloquea una arista (preferentemente sobre la ruta de algún pedido activo) y dispara el recálculo en cada pedido activo que dependa de ella (pueden ser varios en paralelo).
- **`reparar_calle(estado_app, grafo)`** — desbloquea la arista activa.
- **`_badge_para_estado(estado)`** — mapea estado interno → (texto, colores) del badge visual.
- **`construir_tarjeta_pedido(info, ahora)`** — arma el dict que consume `interfaz.dibujar_panel_estado`.
- **`construir_fila_historial(info)`** — arma una fila para el panel de historial.

### `main()`
Setup de Pygame, construcción del grafo/árboles/dispatcher/vistas, y el **loop principal**:
1. `construir_layout()` — calcula rects/botones según la fase actual (se llama 2 veces por frame: antes y después de procesar eventos, para que el layout usado en detección de click sea el mismo que se dibuja).
2. Procesa eventos de Pygame (click, rueda, teclado — solo ESC como tecla especial).
3. `dispatcher.procesar_eventos()` — aplica eventos de los repartidores al estado de los pedidos.
4. Layout fresco y dibujo (mapa, repartidores, tarjeta de selección + panel de activos, historial). Un pedido "entregado" se archiva solo al historial ~3s después (ver `TIEMPO_ARCHIVAR_ENTREGADO`), calculado cada frame dentro de `construir_layout` (sin timer explícito de app).

`multiprocessing.freeze_support()` se llama al inicio de `if __name__ == "__main__":` por requisito de PyInstaller en Windows.

---

## Constantes de configuración clave (en `main.py`, `dispatcher.py`, `grafo.py`)

- `REPARTIDORES_POR_LOCAL = 3`, `PROB_FALLO = 0.05`, `TIEMPO_POR_ZONA = 1.2`
- `TARIFA_BASE_POR_KM = 0.50`, `RECARGO_DEMANDA_ALTA = 1.3` (+30%)
- `FACTOR_MIN_POR_KM = 2.5`
- `MIN_POR_PEDIDO_EN_COLA = 3`, `TIEMPO_ARCHIVAR_ENTREGADO = 3.0`

## Cosas a tener en cuenta si se pide modificar algo

- El MST se reconstruye completo cada vez que se bloquea/repara una arista (no incremental).
- Las rutas usan el MST, no Dijkstra: pueden no ser la ruta más corta absoluta del grafo original (ver justificación en `grafo.py`).
- El estado de la fase (`fase_actual`) nunca se debe setear a mano; siempre se deriva con `calcular_fase`.
- `interfaz.py` no debe importar lógica de negocio; solo recibe datos ya resueltos.
- Cada módulo tiene pruebas de consola en `if __name__ == "__main__":` — útiles para verificar cambios en `grafo.py`, `arbol.py`, `dispatcher.py`, `repartidor.py` sin abrir Pygame.
