
from datetime import timedelta

from django.utils import timezone
from playwright.sync_api import expect

from app.models import Category, Event, User, Venue
from app.test.test_e2e.base import BaseE2ETest


class NoFutureEventsTest(BaseE2ETest):
    

    def setUp(self):
        super().setUp()

        # Crear un usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@test.com",
            password="password123",
            is_organizer=True,
        )

        # Crear un usuario regular
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="password123",
            is_organizer=False,
        )

        # Crea una categoria
        self.category = Category.objects.create(
            name="Conferencia",
            description="Eventos relacionados con conferencias"
        )

        # Crea un venue
        self.venue = Venue.objects.create(
            name="Auditorio Central",
            address="Calle Falsa 123",
            city="Ciudad Gótica",
            capacity=500,
            contact="contacto@auditoriocentral.com"
        )

        # Creo un evento pasado
        Event.objects.create(
            title="Evento Pasado",
            description="No debería mostrarse",
            scheduled_at=timezone.now() - timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

    def test_no_future_events_message(self):
        """Test para verificar el mensaje cuando no hay eventos futuros"""

        # Inicio sesion con usuario regular
        self.login_user(self.regular_user.username, "password123")

        # Ir a la página de eventos
        self.page.goto(self.live_server_url + "/events/")

        # Verificar que se muestra el mensaje de que no hay eventos disponibles
        expect(self.page.get_by_text("No hay eventos disponibles")).to_be_visible()

    def test_future_events_messagge(self):
        """Test para verificar que no se muestre mensaje cuando hay eventos futuros"""

        # Creo un evento futuro
        Event.objects.create(
            title="Concierto Especial",
            description="Este sí debería mostrarse",
            scheduled_at=timezone.now() + timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

        # Inicio sesion con usuario regular
        self.login_user(self.regular_user.username, "password123")

        # Ir a la página de eventos
        self.page.goto(self.live_server_url + "/events/")

        # Verificar que el evento aparece en la página
        expect(self.page.get_by_text("Concierto Especial")).to_be_visible()

        # Verificar que se muestra el mensaje de que no hay eventos disponibles
        expect(self.page.get_by_text("No hay eventos disponibles")).not_to_be_visible()


