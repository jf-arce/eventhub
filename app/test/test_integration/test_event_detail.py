from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import Category, Event, Venue

User = get_user_model()

class CountdownIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Test Category')
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='Test Address',
            city='Test City', 
            capacity=100,
            contact='test@venue.com'
        )
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

    def test_countdown_context_for_regular_user(self):
        event = Event.objects.create(
            title='Evento Futuro',
            description='desc',
            scheduled_at=timezone.now() + timedelta(days=2),
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue,
        )
        self.client.login(username='regularuser', password='testpass123')
        url = reverse('event_detail', args=[event.pk])
        response = self.client.get(url)
        self.assertIn('user_is_organizer', response.context)
        self.assertFalse(response.context['user_is_organizer'])
        self.assertIn('days_remaining', response.context)
        self.assertEqual(response.context['days_remaining'], 2)

    def test_countdown_context_for_organizer(self):
        event = Event.objects.create(
            title='Evento Futuro',
            description='desc',
            scheduled_at=timezone.now() + timedelta(days=2),
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue,
        )
        self.client.login(username='organizer', password='testpass123')
        url = reverse('event_detail', args=[event.pk])
        response = self.client.get(url)
        self.assertIn('user_is_organizer', response.context)
        self.assertTrue(response.context['user_is_organizer'])

    def test_countdown_context_today(self):
        event = Event.objects.create(
            title='Evento Hoy',
            description='desc',
            scheduled_at=timezone.now(),
            organizer=self.organizer_user,
            category=self.category,
            venue=self.venue,
        )
        self.client.login(username='regularuser', password='testpass123')
        url = reverse('event_detail', args=[event.pk])
        response = self.client.get(url)
        self.assertIn('days_remaining', response.context)
        self.assertEqual(response.context['days_remaining'], 0)

