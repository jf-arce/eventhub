from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from app.models import Category, Event, Ticket, User, Venue


class TicketLimitTestCase(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizer",
            email="organizer@test.com",
            password="password123",
            is_organizer=True
        )
        
        self.user = User.objects.create_user(
            username="regular_user",
            email="user@test.com",
            password="password123",
            is_organizer=False
        )
        
        self.venue = Venue.objects.create(
            name="Test Venue",
            address="Test Address",
            city="Test City",
            capacity=100,
            contact="123456789"
        )
        
        self.category = Category.objects.create(
            name="Test Category",
            description="Test Description",
            is_active=True
        )
        
        self.event = Event.objects.create(
            title="Test Event",
            description="Test Description",
            scheduled_at=timezone.now() + timezone.timedelta(days=10),
            organizer=self.organizer,
            category=self.category,
            venue=self.venue
        )

    def test_validate_ticket_quantity_limit(self):
        """Test que valida que la función de validación rechace compras mayores a 4 tickets"""
        with patch.object(Ticket, 'validate', return_value={}):
            errors = Ticket.validate_ticket_limit(user=self.user, event=self.event, quantity=5)
            self.assertIn('quantity', errors)
            self.assertIn('límite', errors['quantity'].lower())
    
    def test_validate_ticket_accumulative_limit(self):
        """Test que valida que la suma de tickets previos y actuales no supere 4"""
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code="ABC123",
            quantity=2,
            type="GENERAL"
        )
        
        with patch.object(Ticket, 'validate', return_value={}):
            errors = Ticket.validate_ticket_limit(user=self.user, event=self.event, quantity=3)
            self.assertIn('quantity', errors)
            self.assertIn('límite', errors['quantity'].lower())
    
    def test_validate_ticket_within_limit(self):
        """Test que valida que se permita comprar tickets cuando no se supera el límite"""
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code="ABC123",
            quantity=2,
            type="GENERAL"
        )
        
        with patch.object(Ticket, 'validate', return_value={}):
            errors = Ticket.validate_ticket_limit(user=self.user, event=self.event, quantity=2)
            self.assertEqual(errors, {})
    
    def test_get_user_tickets_count(self):
        """Test que verifica el cálculo correcto del total de tickets que un usuario ya tiene"""
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code="ABC123",
            quantity=1,
            type="GENERAL"
        )
        
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code="DEF456",
            quantity=2,
            type="VIP"
        )
        
        count = Ticket.get_user_tickets_count(user=self.user, event=self.event)
        self.assertEqual(count, 3)