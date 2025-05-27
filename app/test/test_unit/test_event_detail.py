from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import zoneinfo
from unittest.mock import patch
from app.models import Event, Category, Venue  

User = get_user_model()


class EventDetailCountdownTest(TestCase):
    
    def setUp(self):
        """Configuración inicial para los tests"""
        self.client = Client()
        
        # Crear usuarios
        self.organizer = User.objects.create_user(
            username='organizer',
            email='organizer@test.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='user@test.com',
            password='testpass123'
        )
        
        # Crear categoría
        self.category = Category.objects.create(name='Test Category')
        
        # Crear venue agregando el campo capacity requerido
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test St',
            city='Test City',
            capacity=100  
        )
        
        # Crear evento base
        self.event = Event.objects.create(
            title='Test Event',
            description='Test Description',
            organizer=self.organizer,
            category=self.category,
            venue=self.venue,
            scheduled_at=timezone.now() + timedelta(days=5)
        )
    
    def test_countdown_not_visible_for_organizer(self):
        """
        CA1: La cuenta regresiva debe mostrarse solo a usuarios que no sean organizadores
        """
        # Login como organizador
        self.client.login(username='organizer', password='testpass123')
        
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user_is_organizer'])
        
        # Verificar que la cuenta regresiva no está 
        response_content = response.content.decode()
        
        # Verificar que no hay elementos HTML específicos de countdown para organizadores
        self.assertNotIn('Faltan', response_content)
        self.assertNotIn('Es hoy', response_content)
    
    def test_countdown_visible_for_regular_user(self):
        """
        CA1: La cuenta regresiva debe mostrarse a usuarios que no sean organizadores
        """
        # Login como usuario regular
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user_is_organizer'])
        
        # Verificar que la cuenta regresiva SÍ está presente
        self.assertContains(response, 'countdown-circle')
        self.assertContains(response, 'countdown-number')
    
    @patch('django.utils.timezone.now')
    def test_countdown_shows_event_is_today(self, mock_now):
        """
        CA2: Si quedan 0 días, debe indicarse "El evento es hoy"
        """
        # Simular fecha actual
        utc = zoneinfo.ZoneInfo('UTC')
        mock_current_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=utc)
        mock_now.return_value = mock_current_time
        
        # Crear evento para hoy
        event_date = datetime(2024, 1, 1, 20, 0, 0, tzinfo=utc)
        self.event.scheduled_at = event_date
        self.event.save()
        
        # Login como usuario regular
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que muestra "Es hoy"
        self.assertContains(response, 'Es hoy')
        self.assertEqual(response.context['days_remaining'], 0)
    
    @patch('django.utils.timezone.now')
    def test_countdown_shows_exact_days_remaining(self, mock_now):
        """
        CA3: La cuenta regresiva debe mostrar el número exacto de días restantes
        """
        # Simular fecha actual
        utc = zoneinfo.ZoneInfo('UTC')
        mock_current_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=utc)
        mock_now.return_value = mock_current_time
        
        # Crear evento para dentro de 3 días
        event_date = datetime(2024, 1, 4, 15, 30, 0, tzinfo=utc)
        self.event.scheduled_at = event_date
        self.event.save()
        
        # Login como usuario regular
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que muestra exactamente 3 días
        self.assertContains(response, 'Faltan 3 días')
        self.assertEqual(response.context['days_remaining'], 3)