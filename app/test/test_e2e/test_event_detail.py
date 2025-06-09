import importlib.util
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from app.models import Category, Event, Venue

from .base import BaseE2ETest

PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None



@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
@pytest.mark.django_db
class EventCountdownE2ETest(BaseE2ETest): 
    
    def setUp(self):
        super().setUp()
        
        self.organizer_user = get_user_model().objects.create_user(
            username='organizer_test',
            email='organizer@test.com',
            password='password123',
            is_organizer=True
        )
        
        self.regular_user = get_user_model().objects.create_user(
            username='regular_test',
            email='regular@test.com',
            password='password123',
            is_organizer=False
        )
        
        self.category = Category.objects.create(name='Conferencia')
        self.venue = Venue.objects.create(
            name='Centro de Convenciones',
            address='Av. Principal 123',
            city='Ciudad Test',
            capacity=100
        )

    def tearDown(self):
        super().tearDown()

    def create_event_with_date(self, days_from_now):
        """Crea un evento con fecha específica basada en días desde hoy"""
        event_date = timezone.now() + timedelta(days=days_from_now)
        return Event.objects.create(
            title='Evento Test',
            description='Descripción del evento',
            scheduled_at=event_date,
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue
        )

    def set_playwright_session_for_user(self, user):
        """Usar el método de login de base.py"""
        self.login_user(user.username, "password123")

    def test_criterio_1_countdown_no_visible_para_organizador(self):
        """CA1: La cuenta regresiva NO debe mostrarse a organizadores"""
        event = self.create_event_with_date(5)
        
        self.set_playwright_session_for_user(self.organizer_user)
        
        self.page.goto(f'{self.live_server_url}/events/{event.pk}/')
        
        countdown_elements = self.page.locator('.countdown-circle')
        self.assertEqual(countdown_elements.count(), 0, 
                "El organizador NO debe ver countdown")

    def test_criterio_1_countdown_visible_para_usuario_regular(self):
        """CA1: La cuenta regresiva SÍ debe mostrarse a usuarios regulares"""
        event = self.create_event_with_date(5)
        
        self.set_playwright_session_for_user(self.regular_user)
        
        self.page.goto(f'{self.live_server_url}/events/{event.pk}/')
        
        countdown_circle = self.page.locator('.countdown-circle')
        countdown_circle.wait_for(state='visible', timeout=10000)
        
        self.assertTrue(countdown_circle.is_visible(), 
                "El usuario regular debe ver countdown")

    def test_criterio_2_muestra_dias_exactos(self):
        """CA2: Debe mostrar número exacto de días (sin horas/minutos/segundos)"""
        event = self.create_event_with_date(7)
        
        self.set_playwright_session_for_user(self.regular_user)
        self.page.goto(f'{self.live_server_url}/events/{event.pk}/')
        
        # Verificar número exacto de días
        countdown_number = self.page.locator('.countdown-number')
        countdown_number.wait_for(state='visible', timeout=10000)
        
        self.assertEqual(countdown_number.text_content(), '7',
                "Debe mostrar exactamente '7' días")

    def test_criterio_3_evento_es_hoy(self):
        """CA3: Si quedan 0 días, debe indicar 'El evento es hoy'"""
        event = self.create_event_with_date(0)
        
        self.set_playwright_session_for_user(self.regular_user)
        self.page.goto(f'{self.live_server_url}/events/{event.pk}/')
        
        # Verificar que muestra 0 días
        countdown_number = self.page.locator('.countdown-number')
        countdown_number.wait_for(state='visible', timeout=10000)
        
        self.assertEqual(countdown_number.text_content(), '0',
                " Debe mostrar '0' cuando es hoy")
        
        # Validar el texto "Es hoy"
        countdown_text = self.page.locator('h6:has-text("Es hoy")')
        self.assertTrue(countdown_text.is_visible(),
                "Debe mostrar texto 'Es hoy'")


if __name__ == '__main__':
    pytest.main([__file__])