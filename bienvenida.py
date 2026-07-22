

import pygame
from recursos import recurso

# ==========================================================
# Paleta de colores
# ==========================================================

COLOR_FONDO = (242, 245, 250)
COLOR_TARJETA = (255, 255, 255)
COLOR_SOMBRA = (220, 220, 220)

COLOR_AZUL = (32, 74, 135)
COLOR_GRIS = (80, 80, 80)
COLOR_GRIS_CLARO = (120, 120, 120)

COLOR_BOTON = (42, 107, 194)
COLOR_BOTON_HOVER = (58, 125, 214)
COLOR_BLANCO = (255, 255, 255)

# ==========================================================
# Pantalla de bienvenida
# ==========================================================

class PantallaBienvenida:
    """
    Pantalla de presentación del proyecto.

    Muestra el logo, la información académica y los integrantes del
    proyecto antes de acceder al simulador. Mantiene su propio bucle de
    eventos hasta que el usuario decide continuar.
    """

    def __init__(self, pantalla):

        self.pantalla = pantalla
        self.ancho, self.alto = pantalla.get_size()
        self.terminado = False

        # ==================================================
        # Dimensiones generales
        # ==================================================

        self.ANCHO_TARJETA = 760
        self.ALTO_TARJETA = 500
        self.RADIO_BORDES = 18
        self.SOMBRA = (5, 5)

        # ==================================================
        # Tarjeta principal
        # ==================================================

        self.tarjeta = pygame.Rect(
            (self.ancho - self.ANCHO_TARJETA) // 2,
            (self.alto - self.ALTO_TARJETA) // 2,
            self.ANCHO_TARJETA,
            self.ALTO_TARJETA
        )

        self.cx = self.tarjeta.centerx

        # ==================================================
        # Botón
        # ==================================================

        self.ANCHO_BOTON = 300
        self.ALTO_BOTON = 52
        self.boton = pygame.Rect(0, 0, self.ANCHO_BOTON, self.ALTO_BOTON)

        # ==================================================
        # Posiciones verticales
        # ==================================================

        self.y_logo = self.tarjeta.top + 80
        self.y_subtitulo = self.y_logo + 95
        self.y_tecnologias = self.y_subtitulo + 35
        self.y_escuela = self.y_tecnologias + 30
        self.y_proyecto = self.y_escuela + 38
        self.y_linea_superior = self.y_proyecto + 30
        self.y_integrantes = self.y_linea_superior + 25
        self.y_nombre1 = self.y_integrantes + 32
        self.separacion_integrantes = 25
        self.y_linea_inferior = self.y_nombre1 + 60
        self.y_boton = self.y_linea_inferior + 40

        self.boton.center = (
            self.cx,
            self.y_boton
        )

        # ==================================================
        # Fuentes
        # ==================================================

        self.f_subtitulo = pygame.font.SysFont("Segoe UI", 22)
        self.f_texto = pygame.font.SysFont("Segoe UI", 18)
        self.f_pequeno = pygame.font.SysFont("Segoe UI", 16)
        self.f_boton = pygame.font.SysFont("Segoe UI", 20, bold=True)

        # ==================================================
        # Logo
        # ==================================================

        self.logo = pygame.image.load(recurso("assets/Logo.png")).convert_alpha()

        ancho_logo = 280
        alto_logo = int(ancho_logo * self.logo.get_height() / self.logo.get_width())

        self.logo = pygame.transform.smoothscale(
            self.logo,
            (ancho_logo, alto_logo)
        )

        # ==================================================
        # Información mostrada
        # ==================================================

        self.subtitulo = "Simulador Inteligente de Delivery"
        self.tecnologias = ("Grafos  •  Árboles")
        self.universidad = ("Escuela Politécnica Nacional")
        self.proyecto = ("Proyecto Final - Estructuras de Datos")
        self.titulo_integrantes = "Integrantes"
        self.integrantes = [
            "AARON ALEJANDRO PALACIOS ASANZA",
            "ANDERSON JOEL HERRERA PANCHI"
        ]
        self.texto_boton = "Iniciar"


    # ==========================================================
    # Helpers de dibujo
    # ==========================================================

    def _texto_centrado(self, fuente, texto, color, y):
        """
            Renderiza un texto centrado horizontalmente respecto a la tarjeta
            principal, usando la fuente, color y posición vertical.
        """

        superficie = fuente.render(texto, True, color)
        rect = superficie.get_rect(center=(self.cx, y))
        self.pantalla.blit(superficie, rect)

    # ==========================================================

    def _dibujar_tarjeta(self):
        """
           Dibuja la tarjeta principal con una sombra  para separarla
           visualmente del fondo de la ventana.
        """

        pygame.draw.rect(
            self.pantalla,
            COLOR_SOMBRA,
            self.tarjeta.move(
                self.SOMBRA[0],
                self.SOMBRA[1]
            ),
            border_radius=self.RADIO_BORDES
        )

        pygame.draw.rect(
            self.pantalla,
            COLOR_TARJETA,
            self.tarjeta,
            border_radius=self.RADIO_BORDES
        )

    # ==========================================================

    def _dibujar_encabezado(self):
        """
            Dibuja el encabezado de la pantalla: logo, subtítulo e información
            institucional del proyecto.
        """

        rect_logo = self.logo.get_rect(
            center=(self.cx, self.y_logo)
        )

        self.pantalla.blit(
            self.logo,
            rect_logo
        )

        self._texto_centrado(
            self.f_subtitulo,
            self.subtitulo,
            COLOR_GRIS,
            self.y_subtitulo
        )

        self._texto_centrado(
            self.f_texto,
            self.tecnologias,
            COLOR_GRIS_CLARO,
            self.y_tecnologias
        )

        self._texto_centrado(
            self.f_texto,
            self.universidad,
            COLOR_GRIS,
            self.y_escuela
        )

        self._texto_centrado(
            self.f_texto,
            self.proyecto,
            COLOR_GRIS,
            self.y_proyecto
        )

    # ==========================================================

    def _dibujar_integrantes(self):
        """
        Muestra la lista de integrantes del proyecto entre dos líneas divisorias
        para separar visualmente esta sección del resto del contenido.
        """

        pygame.draw.line(
            self.pantalla,
            (220, 220, 220),
            (self.tarjeta.left + 80,
             self.y_linea_superior),
            (self.tarjeta.right - 80,
             self.y_linea_superior),2
        )

        self._texto_centrado(
            self.f_texto,
            self.titulo_integrantes,
            COLOR_AZUL,
            self.y_integrantes
        )

        y = self.y_nombre1

        for integrante in self.integrantes:
            self._texto_centrado(
                self.f_pequeno,
                integrante,
                COLOR_GRIS,y
            )

            y += self.separacion_integrantes

        pygame.draw.line(
            self.pantalla,
            (220, 220, 220),
            (self.tarjeta.left + 80,
             self.y_linea_inferior),
            (self.tarjeta.right - 80,
             self.y_linea_inferior),2
        )

    # ==========================================================

    def _dibujar_boton(self):
        """
        Dibuja el botón principal de la pantalla y aplica un cambio de color
        cuando el cursor del mouse pasa sobre él.
        """

        hover = self.boton.collidepoint(
            pygame.mouse.get_pos()
        )

        color = (
            COLOR_BOTON_HOVER
            if hover
            else COLOR_BOTON
        )

        pygame.draw.rect(
            self.pantalla,color,
            self.boton,
            border_radius=14
        )

        self._texto_centrado(
            self.f_boton,
            self.texto_boton,
            COLOR_BLANCO,
            self.y_boton
        )

    # ==========================================================
    # Renderizado
    # ==========================================================

    def dibujar(self):
        """
            Orquesta el dibujo completo de la pantalla de bienvenida llamando a
            cada uno de los componentes visuales en el orden correspondiente.
        """

        self.pantalla.fill(COLOR_FONDO)
        self._dibujar_tarjeta()
        self._dibujar_encabezado()
        self._dibujar_integrantes()
        self._dibujar_boton()

    # ==========================================================
    # Manejo de eventos
    # ==========================================================

    def manejar_eventos(self, evento):
        """
        Procesa únicamente los eventos propios de esta pantalla.

        Cuando el usuario hace clic sobre el botón "Iniciar", marca la
        pantalla como finalizada para que el flujo continúe con la siguiente
        ventana.
        """

        if evento.type == pygame.MOUSEBUTTONDOWN:
            if evento.button == 1:
                if self.boton.collidepoint(evento.pos):
                    self.terminado = True

    # ==========================================================
    # Bucle principal
    # ==========================================================

    def ejecutar(self):
        """
        Bucle principal de la pantalla de bienvenida.

        Mantiene actualizada la ventana hasta que el usuario presiona el
        botón "Iniciar" o decide cerrar la aplicación.
        """

        reloj = pygame.time.Clock()
        while not self.terminado:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    return False
                self.manejar_eventos(evento)
            self.dibujar()
            pygame.display.flip()

            reloj.tick(60)
        return True
