import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Category, Event, Notification, Ticket, User, Venue


class BaseNotificationTest(TestCase):
    
     def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizertest@gmail.com",
            password="password123",
            is_organizer=True,
        )
        venue = Venue.objects.create(
            name="Venue de prueba",
            address="123 Calle Falsa, Ciudad, País",
            city="Ciudad de prueba",
            capacity=100,
            contact="Contacto de prueba",
        )
        category = Category.objects.create(
            name="Categoria de prueba",
            description="Descripción de la categoría de prueba",
        )
        
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue= venue,
            category=category,
        )
        self.user1 = User.objects.create_user(
            username="usuario_test_1",
            email="user1@gmail.com",
            password="password123",
            is_organizer=False,
        )
        self.user2 = User.objects.create_user(
            username="usuario_test_2",
            email="user2@gmail.com",
            password="password123",
            is_organizer=False,
        )
        self.ticketUser1 = Ticket.objects.create(
            user=self.user1,
            event=self.event,
            buy_date=timezone.now(),
            ticket_code="TICKET123",
            quantity=1,
            type="GENERAL"
        )
        self.ticketUser2 = Ticket.objects.create(
            user=self.user2,
            event=self.event,
            buy_date=timezone.now(),
            ticket_code="TICKET456",
            quantity=1,
            type="GENERAL",
        )
        self.message = "Descripcion de la Notificación de prueba"
        
        
class NotifyUsersWhenEventModifiedTest(BaseNotificationTest):
      
    def verify_users_notifications(self, expected_user_count=2):
        eventUpdated = Event.objects.get(pk=self.event.pk)
        notifications = Notification.objects.filter(event=eventUpdated)
        self.assertEqual(notifications.count(), 1, "Se esperaba 1 notificación para el evento.")
        
        notification = notifications.first()
        self.assertIsNotNone(notification, "No se creó ninguna notificación para el evento.")
        
        if notification:
            self.assertEqual(notification.users.count(), expected_user_count, f"La notificación debe estar asociada a {expected_user_count} usuarios.")
            self.assertIn(self.user1, notification.users.all(), "user1 debe estar en la notificación")
            self.assertIn(self.user2, notification.users.all(), "user2 debe estar en la notificación")
    
    def test_notify_users_when_date_is_modified(self):
        """Test que verifica que se notifique a los usuarios cuando se modifica la fecha del evento."""
        self.client.login(
            username=self.organizer.username,
            password="password123"
        )
        
        new_date = self.event.scheduled_at + datetime.timedelta(days=2)
        date_str = new_date.strftime("%Y-%m-%d")
        time_str = new_date.strftime("%H:%M")

        response = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": self.event.title,
            "description": self.event.description,
            "date": date_str,
            "time": time_str,
            "category": self.event.category.pk,
            "venue": self.event.venue.pk,
        })
        
        self.assertEqual(response.status_code, 302, "Se esperaba una redirección después de la modificación del evento.")
        self.verify_users_notifications()

    def test_notify_users_when_hour_is_modified(self):
        """Test que verifica que se notifique a los usuarios cuando se modifica la hora del evento."""
        self.client.login(
            username=self.organizer.username,
            password="password123"
        )
        
        new_time = (self.event.scheduled_at + datetime.timedelta(hours=2)).strftime("%H:%M")
        
        response = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": self.event.title,
            "description": self.event.description,
            "date": self.event.scheduled_at.strftime("%Y-%m-%d"),
            "time": new_time,
            "category": self.event.category.pk,
            "venue": self.event.venue.pk,
        })
        
        self.assertEqual(response.status_code, 302, "Se esperaba una redirección después de la modificación del evento.")
        self.verify_users_notifications()

    def test_notify_users_when_venue_is_modified(self):
        """Test que verifica que se notifique a los usuarios cuando se modifica el lugar del evento."""
        self.client.login(
            username=self.organizer.username,
            password="password123"
        )
        
        new_venue = Venue.objects.create(
            name="Nuevo Venue de prueba",
            address="456 Calle Nueva, Ciudad, País",
            city="Nueva Ciudad de prueba",
            capacity=200,
            contact="Nuevo Contacto de prueba",
        )
        
        response = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": self.event.title,
            "description": self.event.description,
            "date": self.event.scheduled_at.strftime("%Y-%m-%d"),
            "time": self.event.scheduled_at.strftime("%H:%M"),
            "category": self.event.category.pk,
            "venue": new_venue.pk,
        })
        
        self.assertEqual(response.status_code, 302, "Se esperaba una redirección después de la modificación del evento.")
        self.verify_users_notifications()
        
    def test_notify_users_when_date_time_and_venue_modified(self):
        """Test que verifica que se notifique a los usuarios cuando se modifican fecha, hora y lugar juntos."""
        self.client.login(
            username=self.organizer.username,
            password="password123"
        )
        
        new_datetime = self.event.scheduled_at + datetime.timedelta(days=2, hours=3)
        date_str = new_datetime.strftime("%Y-%m-%d")
        time_str = new_datetime.strftime("%H:%M")
        
        new_venue = Venue.objects.create(
            name="Venue combinado prueba",
            address="789 Calle Combinada, Ciudad, País",
            city="Ciudad Combinada",
            capacity=300,
            contact="Contacto Combinado",
        )
        
        response = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": self.event.title,
            "description": self.event.description,
            "date": date_str,
            "time": time_str,
            "category": self.event.category.pk,
            "venue": new_venue.pk,
        })
        
        self.assertEqual(response.status_code, 302, "Se esperaba una redirección después de la modificación del evento.")
        self.verify_users_notifications()
        
    def test_notification_non_significant_change(self):
        """Test que verifica que no se notifique a los usuarios si el cambio no es significativo."""
        self.client.login(
            username=self.organizer.username,
            password="password123"
        )
        
        category = Category.objects.create(
            name="Nueva Categoria de prueba",
            description="Descripción de la nueva categoría de prueba",
        )
        
        response = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": "Evento de prueba (Actualizado)",
            "description": "Descripción del evento de prueba (Actualizado)",
            "date": self.event.scheduled_at.strftime("%Y-%m-%d"),
            "time": self.event.scheduled_at.strftime("%H:%M"),
            "category": category.pk,
            "venue": self.event.venue.pk,
        })
        
        self.assertEqual(response.status_code, 302, "Se esperaba una redirección después de la modificación del evento.")
        notifications = Notification.objects.filter(event=self.event)
        self.assertEqual(notifications.count(), 0, "No se esperaba ninguna notificación para el evento.")
        
    def test_no_notification_when_event_not_modified(self):
        """Test que verifica que no se notifique a los usuarios si no se modifica el evento."""
        self.client.login(
            username=self.organizer.username,
            password="password123"
        )
        
        response = self.client.post(reverse("event_edit", args=[self.event.pk]), {
            "title": self.event.title,
            "description": self.event.description,
            "date": self.event.scheduled_at.strftime("%Y-%m-%d"),
            "time": self.event.scheduled_at.strftime("%H:%M"),
            "category": self.event.category.pk,
            "venue": self.event.venue.pk,
        })
        
        self.assertEqual(response.status_code, 302, "Se esperaba una redirección después de la modificación del evento.")
        notifications = Notification.objects.filter(event=self.event)
        self.assertEqual(notifications.count(), 0, "No se esperaba ninguna notificación para el evento.")


    