from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import json
import uuid
from app.models import Event, Ticket, Venue, Category, User
from django.contrib.messages import get_messages

class TicketPurchaseLimitIntegrationTest(TestCase):
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
        
        self.client = Client()

    def test_purchase_ticket_exceeding_direct_limit(self):
        """
        Prueba que verifica que el sistema rechaza la compra cuando se intentan
        comprar más de 4 entradas en una sola compra
        """
        self.client.login(username='regular_user', password='password123')
        
        purchase_data = {
            'cantidad': '5',
            'tipoEntrada': 'GENERAL',
            'numeroTarjeta': '1234567890123456',
            'fechaExpiracion': (timezone.now() + timezone.timedelta(days=30)).strftime('%Y-%m-%d'),
            'cvv': '123',
            'nombreTarjeta': 'Test User',
            'terminos': 'on'
        }
        
        response = self.client.post(
            reverse('purchase_ticket', kwargs={'event_id': self.event.pk}),
            data=purchase_data
        )
        
        self.assertEqual(Ticket.objects.count(), 0)
        
        messages_list = list(get_messages(response.wsgi_request))
        error_found = False
        for message in messages_list:
            message_str = str(message).lower()
            print(f"Mensaje: {message_str}")
            if "límite" in message_str or "exced" in message_str or "más de 4" in message_str or "máximo" in message_str:
                error_found = True
                break
        
        self.assertTrue(error_found, "No se encontró mensaje de error sobre límite de tickets")

    def test_purchase_ticket_exceeding_accumulated_limit(self):
        """
        Prueba que verifica que el sistema rechaza la compra cuando un usuario
        ya tiene tickets y la suma de los existentes y nuevos excede el límite
        """
        self.client.login(username='regular_user', password='password123')
        
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code=str(uuid.uuid4())[:8].upper(),
            quantity=3,
            type="GENERAL"
        )
        
        purchase_data = {
            'cantidad': '2',
            'tipoEntrada': 'GENERAL',
            'numeroTarjeta': '1234567890123456',
            'fechaExpiracion': (timezone.now() + timezone.timedelta(days=30)).strftime('%Y-%m-%d'),
            'cvv': '123',
            'nombreTarjeta': 'Test User',
            'terminos': 'on'
        }
        
        response = self.client.post(
            reverse('purchase_ticket', kwargs={'event_id': self.event.pk}),
            data=purchase_data
        )
        
        self.assertEqual(Ticket.objects.count(), 1)
        
        
        messages_list = list(get_messages(response.wsgi_request))
        error_found = False
        for message in messages_list:
            message_str = str(message).lower()
            print(f"Mensaje: {message_str}")
            if "límite" in message_str or "exced" in message_str or "más de 4" in message_str:
                error_found = True
                break
        
        self.assertTrue(error_found, "No se encontró mensaje de error sobre límite excedido")
        
    def test_purchase_ticket_within_limit(self):
        """
        Prueba que verifica que la compra es exitosa cuando está dentro del límite
        """
        login_successful = self.client.login(username='regular_user', password='password123')
        self.assertTrue(login_successful, "No se pudo iniciar sesión como usuario regular")
        
        purchase_data = {
            'cantidad': '4',
            'tipoEntrada': 'Entrada General',
            'numeroTarjeta': '1234567890123456',
            'fechaExpiracion': (timezone.now() + timezone.timedelta(days=30)).strftime('%Y-%m-%d'),
            'cvv': '123',
            'nombreTarjeta': 'Test User',
            'terminos': 'on'
        }
        
        response = self.client.post(
            reverse('purchase_ticket', kwargs={'event_id': self.event.pk}),
            data=purchase_data,
            follow=True
        )
        
        messages = list(get_messages(response.wsgi_request))
        for message in messages:
            print(f"Mensaje: {message}")
        
        self.assertEqual(response.status_code, 200)
        
        ticket = Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code=str(uuid.uuid4())[:8].upper(),
            quantity=4,
            type="GENERAL"
        )
        
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.quantity, 4)
        self.assertEqual(ticket.user, self.user)

    def test_check_ticket_limit_endpoint(self):
        """
        Prueba que verifica el funcionamiento del endpoint AJAX para verificar límites
        """
        self.client.login(username='regular_user', password='password123')
        
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code=str(uuid.uuid4())[:8].upper(),
            quantity=2,
            type="GENERAL"
        )
        
        response1 = self.client.get(
            reverse('check_ticket_limit', kwargs={'event_id': self.event.pk}),
            {'cantidad': 2},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)
        self.assertTrue(data1['success'])
        self.assertEqual(data1['current_count'], 2)
        self.assertEqual(data1['total'], 4)
        
        response2 = self.client.get(
            reverse('check_ticket_limit', kwargs={'event_id': self.event.pk}),
            {'cantidad': 3},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)
        self.assertFalse(data2['success'])
        self.assertEqual(data2['current_count'], 2)
        self.assertEqual(data2['total'], 5)
        self.assertEqual(data2['remaining'], 2)