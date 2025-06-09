from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from app.models import Category, Event, Venue


class EventDetailCountdownTest(TestCase):
    
    def setUp(self):
        """Configuración inicial para los tests"""
        self.client = Client()
        
        self.organizer = get_user_model().objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='testpass123'
        )
        
        self.regular_user = get_user_model().objects.create_user(
            username='regular_user',
            email='user@test.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name='Test Category')
        
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            capacity=100  
        )
        
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
            scheduled_at=timezone.now() + timedelta(days=5)
        )

    def test_countdown_future_days(self):
        """Debe mostrar 'Faltan X días' si faltan más de 1 día"""
        event = Event.objects.create(
            title="Futuro",
            description="desc",
            scheduled_at=timezone.now() + timedelta(days=3),
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
        )
        self.assertEqual(event.get_countdown_status(), "Faltan 3 días")

    def test_countdown_one_day(self):
        """Debe mostrar 'Falta 1 día' si falta exactamente un día"""
        event = Event.objects.create(
            title="Mañana",
            description="desc",
            scheduled_at=timezone.now() + timedelta(days=1),
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
        )
        self.assertEqual(event.get_countdown_status(), "Falta 1 día")

    def test_countdown_today(self):
        """Debe mostrar 'Es hoy' si el evento es hoy"""
        event = Event.objects.create(
            title="Hoy",
            description="desc",
            scheduled_at=timezone.now(),
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
        )
        self.assertEqual(event.get_countdown_status(), "Es hoy")

    def test_countdown_past(self):
        """Debe mostrar 'Evento finalizado' si el evento ya pasó"""
        event = Event.objects.create(
            title="Pasado",
            description="desc",
            scheduled_at=timezone.now() - timedelta(days=2),
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
        )
        self.assertEqual(event.get_countdown_status(), "Evento finalizado")


