import datetime
from django.test import TestCase
from django.utils import timezone
from app.models import Event, User, Notification, Ticket, Venue, Category

class NotificationModelTest(TestCase):
    
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
        
    def test_create_notification_for_event_update(self):
        """Test que verifica la creación correcta de una notificación con un evento y mensaje"""
       
        notification = Notification.notify_users_of_event_update(
            event=self.event,
            message=self.message,
        )  
        
        self.assertEqual(notification.title, "Cambios en el evento")
        self.assertEqual(notification.message, self.message)
        self.assertEqual(notification.priority, Notification.Priority.HIGH)
        self.assertEqual(notification.event, self.event)
        
    def test_notification_association_with_users(self):
        """Test que verifica la asociación de la notificación con los usuarios del evento"""
        
        notification = Notification.notify_users_of_event_update(
            event=self.event,
            message=self.message,
        )
        
        self.assertEqual(notification.users.count(), 2)
        self.assertIn(self.user1, notification.users.all())
        self.assertIn(self.user2, notification.users.all())
        
        #Verificar que un usuario sin ticket no esté asociado a la notificación
        user_without_ticket = User.objects.create_user(
            username="usuario_sin_ticket",
            email="user_sin_ticket@gmail.com",
            password="password123"
        )
        self.assertNotIn(user_without_ticket, notification.users.all())