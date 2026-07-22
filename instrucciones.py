
import pygame
from recursos import recurso

# ==========================================================
# Paleta de colores
# ==========================================================

COLOR_FONDO = (240, 242, 246)
COLOR_PANEL = (255, 255, 255)

COLOR_NEGRO = (40, 40, 40)
COLOR_GRIS = (115, 115, 115)
COLOR_GRIS_CLARO = (230, 230, 230)

COLOR_NARANJA = (255, 102, 45)
COLOR_NARANJA_HOVER = (255, 130, 80)

COLOR_AZUL = (70, 140, 255)
COLOR_BLANCO = (255, 255, 255)

# ==========================================================
# PANTALLA DE INSTRUCCIONES
# ==========================================================

class PantallaInstrucciones:
    """
        Pantalla de ayuda del simulador.

        Presenta los pasos básicos para realizar un pedido y muestra una
        vista previa de la interfaz principal antes de iniciar la
        simulación.
    """

    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.ancho, self.alto = pantalla.get_size()
        self.terminado = False

        # ==================================================
        # Paneles
        # ==================================================

        self.panel_izquierdo = pygame.Rect(25, 25, 490, 730)
        self.panel_derecho = pygame.Rect(530, 25, 545, 730)

        # ==================================================
        # Botón
        # ==================================================

        self.boton = pygame.Rect(795, 690, 260, 55)

        # ==================================================
        # Imagen
        # ==================================================

        self.imagen = pygame.image.load(recurso("assets/Instrucciones.png"))
        self.imagen = pygame.transform.smoothscale(self.imagen,(500, 380))

        # ==================================================
        # Fuentes
        # ==================================================

        self.f_titulo = pygame.font.SysFont("Segoe UI", 33, bold=True)
        self.f_subtitulo = pygame.font.SysFont("Segoe UI", 23, bold=True)
        self.f_texto = pygame.font.SysFont("Segoe UI", 19)
        self.f_pequeno = pygame.font.SysFont("Segoe UI", 17)

        # ==================================================
        # Pasos
        # ==================================================

        self.pasos = [
            ("Selecciona el punto de recogida", "Escribe el nombre de la zona o haz clic en el mapa."),
            ("Agrega una o más paradas (Opcional)", "Puedes añadir una o varias paradas antes del destino."),
            ("Selecciona el destino", "Escribe el nombre de la zona o selecciónala en el mapa."),
            ("Elige el tipo de envío", "Documento, Comida o Paquete."),
            ("Confirma el pedido", "Presiona el botón 'Confirmar pedido'.")
        ]

        # ==================================================
        # Resumen de la simulación
        # ==================================================

        self.lista = [
            "• Ruta del repartidor en tiempo real",
            "• Estado del pedido",
            "• Tiempo estimado",
            "• Costo del envío",
            "• Consulta el historial"
        ]

    # ==========================================================
    # Helpers de dibujo
    # ==========================================================

    def _escribir(self, fuente, texto, color, x, y):
        """
            Renderiza un texto en la posición indicada utilizando la fuente y el
            color especificados.
        """

        superficie = fuente.render(texto,True,color)
        self.pantalla.blit(superficie,(x, y))

    # ==========================================================

    def _dibujar_panel(self, rect):
        """
            Dibuja un panel con esquinas redondeadas que sirve como contenedor de
            las distintas secciones de la pantalla.
        """

        pygame.draw.rect(self.pantalla,COLOR_PANEL,rect,border_radius=18)

    # ==========================================================

    def _dibujar_numero(self, numero, x, y):
        """
           Dibuja un indicador circular numerado para representar visualmente
           cada paso del proceso de creación de un pedido.
        """

        pygame.draw.circle(self.pantalla,COLOR_NARANJA,(x, y),18)
        texto = self.f_texto.render(str(numero),True,COLOR_BLANCO)
        self.pantalla.blit(texto,texto.get_rect(center=(x, y)))

    def _dibujar_panel_izquierdo(self):
        self._dibujar_panel(
            self.panel_izquierdo
        )

        self._escribir(
            self.f_titulo,
            "¿Cómo usar QuitoExpress?",
            COLOR_NEGRO,55,55)

        pygame.draw.line(
            self.pantalla,
            COLOR_NARANJA,(55, 105),(95, 105),3)

        self._escribir(
            self.f_texto,
            "Sigue estos pasos para realizar un envío:",
            COLOR_NEGRO,55,125)

        y = 185

        for i, paso in enumerate(self.pasos):

            self._dibujar_numero(
                i + 1,
                65,
                y + 10
            )

            self._escribir(
                self.f_subtitulo,
                paso[0],
                COLOR_NEGRO,95,y - 8)

            self._escribir(
                self.f_pequeno,
                paso[1],
                COLOR_GRIS,95,y + 24)

            y += 105

        pygame.draw.rect(
            self.pantalla,
            (234, 243, 255),
            (35, 660, 470, 75),
            border_radius=12
        )

        self._escribir(
            self.f_subtitulo,
            "¿Te equivocaste?",
            COLOR_AZUL,55,666
        )

        self._escribir(
            self.f_pequeno,
            "Utiliza el botón Reiniciar para comenzar nuevamente.",
            COLOR_NEGRO,
            55,
            695
        )

    # ==========================================================
    # Panel derecho
    # ==========================================================

    def _dibujar_panel_derecho(self):
        """
            Dibuja el panel informativo con una vista previa de la interfaz y un
            resumen de la información que el usuario observará durante la
            simulación.
        """

        self._dibujar_panel(
            self.panel_derecho
        )

        self._escribir(
            self.f_titulo,
            "¿Qué verás durante la simulación?",
            COLOR_NEGRO,545,55)

        marco = pygame.Rect(545,110,515,390)
        pygame.draw.rect(
            self.pantalla,
            COLOR_GRIS_CLARO,
            marco,
            border_radius=10
        )

        self.pantalla.blit(
            self.imagen,
            (550,115)
        )

        pygame.draw.rect(
            self.pantalla,
            (248,248,248),
            (545,510,515,165),
            border_radius=10
        )

        y = 530

        for item in self.lista:

            self._escribir(
                self.f_texto,item,
                COLOR_NEGRO,565,y)
            y += 25

        hover = self.boton.collidepoint(
            pygame.mouse.get_pos())

        color = (
            COLOR_NARANJA_HOVER
            if hover
            else COLOR_NARANJA
        )

        pygame.draw.rect(
            self.pantalla,
            color,
            self.boton,
            border_radius=12
        )

        texto = self.f_subtitulo.render(
            "Comenzar",
            True,
            COLOR_BLANCO
        )

        self.pantalla.blit(
            texto,
            texto.get_rect(
                center=self.boton.center
            )
        )

    # ==========================================================
    # Renderizado
    # ==========================================================

    def dibujar(self):
        self.pantalla.fill(COLOR_FONDO)
        self._dibujar_panel_izquierdo()
        self._dibujar_panel_derecho()

    # ==========================================================
    # Manejo de eventos
    # ==========================================================

    def manejar_eventos(self, evento):
        """
        Procesa los eventos propios de esta pantalla.

        Cuando el usuario presiona el botón "Comenzar", la pantalla finaliza
        y el control regresa al flujo principal de la aplicación.
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
        Bucle principal de la pantalla de instrucciones.

        Mantiene la ventana activa hasta que el usuario decide continuar con
        el simulador o cierra la aplicación.
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
