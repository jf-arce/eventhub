from django.test import TestCase

from app.models import Category, Event, Rating, User, Venue


class AvgRatingTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass', is_organizer=True)
        self.user2 = User.objects.create_user(username='user2', password='pass', is_organizer=True)
        self.category = Category.objects.create(name='Concierto', description='desc')
        self.venue = Venue.objects.create(
            name='Teatro', address='Av. Libertador 742', city='Buenos Aires',
            capacity=100, contact='contacto@example.com'
        )
        self.event = Event.objects.create(
            title='Recital de prueba',
            description='desc',
            scheduled_at='2030-01-01T20:00:00Z',
            organizer=self.user1,
            category=self.category,
            venue=self.venue
        )

    def test_average_rating_multiple(self):
        """Verifica que el promedio de varias calificaciones se calcule correctamente."""
        Rating.objects.create(event=self.event, user=self.user1, title='Buena', text='Me gustó', rating=4)
        Rating.objects.create(event=self.event, user=self.user2, title='Regular', text='Meh', rating=2)
        self.assertEqual(self.event.average_rating(), 3.0)

    def test_average_rating_single(self):
        """Verifica que el promedio sea igual a la única calificación existente."""
        Rating.objects.create(event=self.event, user=self.user1, title='Excelente', text='Muy bueno', rating=5)
        self.assertEqual(self.event.average_rating(), 5.0)

    def test_average_rating_none(self):
        """Verifica que si no hay calificaciones, el promedio sea None."""
        self.assertIsNone(self.event.average_rating())

    def test_average_rating_rounding(self):
        """Verifica que el promedio se redondee correctamente cuando es decimal."""
        Rating.objects.create(event=self.event, user=self.user1, title='Bueno', text='Ok', rating=3)
        Rating.objects.create(event=self.event, user=self.user2, title='Muy bueno', text='Nice', rating=4)
        self.assertEqual(self.event.average_rating(), 3.5)
