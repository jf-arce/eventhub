from django.test import TestCase

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Event, User, Category, Venue

class EvenFuturetListView(TestCase):
    def setUp(self):
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



    def test_only_future_events_are_listed(self):
        """Test que verifica que el dashboard de usuario muestre solo los eventos futuros"""
        
        # Creo un evento pasado
        Event.objects.create(
            title="Evento Pasado",
            description="No debería mostrarse",
            scheduled_at=timezone.now() - timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

        # Creo un evento futuro
        Event.objects.create(
            title="Concierto Especial",
            description="Este sí debería mostrarse",
            scheduled_at=timezone.now() + timedelta(days=2),
            organizer=self.organizer,
            venue=self.venue,
            category=self.category
        )

        
        # Login con usuario regular
        self.client.login(username="regular", password="password123")

        url = reverse("events")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("events", response.context)

        event_titles = [event.title for event in response.context["events"]]

        self.assertIn("Concierto Especial", event_titles)
        self.assertNotIn("Evento Pasado", event_titles)