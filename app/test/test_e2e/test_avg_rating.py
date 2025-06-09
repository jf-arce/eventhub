import datetime

from django.utils import timezone

from app.models import Category, Event, Rating, Ticket, User, Venue
from app.test.test_e2e.base import BaseE2ETest


class AvgRatingE2ETest(BaseE2ETest):
    def setUp(self):
        super().setUp()

        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizador@example.com",
            password="pass1",
            is_organizer=True,
        )

        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass2",
            is_organizer=False,
        )

        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass3",
            is_organizer=False,
        )

        self.category = Category.objects.create(name="General", description="Test")
        self.venue = Venue.objects.create(
            name="Teatro Central",
            address="Calle Falsa 123",
            city="Ciudad",
            capacity=100,
            contact="contacto@teatro.com"
        )
        self.event = Event.objects.create(
            title="Concierto",
            description="Evento con ratings",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
        )

        Ticket.objects.create(
            buy_date="2025-05-20", user=self.user1, event=self.event,
            ticket_code="1111111111111111", quantity="1", type="general"
        )

        Ticket.objects.create(
            buy_date="2025-05-20", user=self.user2, event=self.event,
            ticket_code="2222222222222222", quantity="1", type="general"
        )

        Rating.objects.create(user=self.user1, event=self.event, rating=3)
        Rating.objects.create(user=self.user2, event=self.event, rating=5)

    def test_organizer_sees_average_rating(self):
        """
        Verifica que el organizador puede ver el bloque de promedio de calificaciones
        y que el promedio correcto aparece en el detalle del evento.
        """
        self.login_user("organizer", "pass1")
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}")

        # Espera a que aparezca el bloque de promedio 
        rating_block = self.page.locator("text=Calificación promedio")
        rating_block.wait_for(timeout=5000)

        # Verifica que el promedio correcto aparece (en este ejemplo: 4,0 / 5)
        assert self.page.locator("text=4,0 / 5").is_visible()

    def test_non_organizer_does_not_see_average_rating(self):
        """
        Verifica que un usuario que no es organizador NO puede ver el promedio de calificaciones en el detalle del evento.
        """
        self.login_user("user1", "pass2")
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}")

        # Espera a que cargue la página y verifica que NO aparece el bloque de promedio
        assert self.page.locator("text=Calificación promedio").count() == 0
        assert self.page.locator("text=4,0 / 5").count() == 0

    def test_organizer_sees_no_ratings_message(self):
        """
        Verifica que si no hay calificaciones, el organizador ve el mensaje 'Sin calificaciones aún'.
        """
        # Elimina todas las calificaciones del evento
        Rating.objects.filter(event=self.event).delete()

        self.login_user("organizer", "pass1")
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}")

        # Espera a que aparezca el mensaje de sin calificaciones
        assert self.page.locator("text=Sin calificaciones").is_visible()
