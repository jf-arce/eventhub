from django.test import TestCase
from django.urls import reverse
from app.models import Event, User, Category, Venue, Rating


class AvgRatingIntegrationTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username='org', password='pass', is_organizer=True)
        self.attendee = User.objects.create_user(username='user', password='pass', is_organizer=False)
        self.category = Category.objects.create(name='Rock', description='desc')
        self.venue = Venue.objects.create(name='Estadio', address='addr', city='city', capacity=100, contact='x')
        self.event = Event.objects.create(
            title='Concierto',
            description='desc',
            scheduled_at='2030-01-01T20:00:00Z',
            organizer=self.organizer,
            category=self.category,
            venue=self.venue
        )

    def test_avg_rating_in_context_for_organizer(self):
        """Test 1: Verifica que el organizador vea correctamente el promedio de calificaciones en el contexto"""
        Rating.objects.create(event=self.event, user=self.organizer, title='T1', text='Excelente', rating=5)
        Rating.objects.create(event=self.event, user=self.attendee, title='T2', text='Bueno', rating=3)

        self.client.login(username='org', password='pass')
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('avg_rating', response.context)
        self.assertAlmostEqual(response.context['avg_rating'], 4.0, places=1)

    def test_avg_rating_none_when_no_ratings(self):
        """Test 2: Verifica que si no hay calificaciones, el promedio sea None (para luego mostrar "Sin calificaciones")"""
        
        self.client.login(username='org', password='pass')
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('avg_rating', response.context)
        self.assertIsNone(response.context['avg_rating'])

    def test_attendee_sees_context_but_not_avg_rating(self):
        """Test 3: Verifica que un asistente (que no es organizador) recibe el contexto,
        pero en la vista real no debería mostrarse (esto se probaría con un test E2E)"""
        Rating.objects.create(event=self.event, user=self.organizer, title='T1', text='Excelente', rating=4)

        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('event_detail', args=[self.event.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('avg_rating', response.context)
        self.assertEqual(response.context['avg_rating'], 4.0)
