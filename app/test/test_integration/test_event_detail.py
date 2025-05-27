from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from app.models import Event, Category, Venue

User = get_user_model()

class CountdownIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Crear categoria y venue
        self.category = Category.objects.create(name='Test Category')
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='Test Address',
            city='Test City', 
            capacity=100,
            contact='test@venue.com'
        )
        
        # Crear usuarios
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@test.com',
            password='testpass123',
            is_organizer=False
        )
        self.organizer_user = User.objects.create_user(
            username='organizer',
            email='organizer@test.com', 
            password='testpass123',
            is_organizer=True
        )

    def test_countdown_shows_for_non_organizers(self):
        """CA1: Verificar que el countdown se muestra para usuarios NO organizadores"""
        future_date = timezone.now() + timedelta(days=3)
        event = Event.objects.create(
            title='Test Event',
            description='Test event description',
            scheduled_at=future_date,
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue
        )
        
        # Usuario regular - DEBE mostrar countdown
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('event_detail', kwargs={'id': event.pk}))
        self.assertEqual(response.status_code, 200)
        response_content = response.content.decode()
        self.assertIn('countdown-circle', response_content, 
            "El countdown debería aparecer para usuarios regulares")

    def test_event_is_today_shows_correct_message(self):
        """CA2: Si quedan 0 días, debe indicarse 'Es hoy'"""
        # Evento para hoy
        today_event = timezone.now().replace(hour=23, minute=59)
        event = Event.objects.create(
            title='Today Event',
            description='Event happening today',
            scheduled_at=today_event,
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue
        )
        
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('event_detail', kwargs={'id': event.pk}))
        self.assertEqual(response.status_code, 200)
        
        response_content = response.content.decode()
        # Verificar que muestra "Es hoy"
        self.assertIn('Es hoy', response_content,
            "Debería mostrar 'Es hoy' cuando quedan 0 días")
        
        # También verificar que el countdown muestra 0
        self.assertIn('<span class="countdown-number">0</span>', response_content,
                "El countdown debería mostrar 0 para eventos de hoy")

    def test_shows_exact_days_remaining(self):
        """CA3: La cuenta regresiva debe mostrar el número exacto de días restantes"""
        # Evento en exactamente 5 días
        future_date = timezone.now() + timedelta(days=5)
        event = Event.objects.create(
            title='Future Event',
            description='Event in 5 days',
            scheduled_at=future_date,
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue
        )
        
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('event_detail', kwargs={'id': event.pk}))
        self.assertEqual(response.status_code, 200)
        
        response_content = response.content.decode()
        
        # Verificar que aparece el countdown
        self.assertIn('countdown-circle', response_content,
            "Debería mostrar el countdown para eventos futuros")
        
        # Verificar que incluye la palabra 'días' en algún formato
        self.assertIn('días', response_content,
            "Debería incluir la palabra 'días'")