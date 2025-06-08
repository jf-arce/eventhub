import os
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from django.utils import timezone
from app.models import User, Event, Category, Venue, Ticket
from .base import BaseE2ETest

class TicketPurchaseE2ETestCase(BaseE2ETest):
    def setUp(self):
        super().setUp()
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

    def login_as_regular_user(self):
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.fill("input[name='username']", "regular_user")
        self.page.fill("input[name='password']", "password123")
        self.page.click("button[type='submit']")
        self.page.wait_for_url(f"{self.live_server_url}/events/")

    def fill_purchase_form(self):
        self.page.select_option("select#tipoEntrada", "GENERAL")
        self.page.fill("input#numeroTarjeta", "1234567890123456")
        self.page.fill("input#fechaExpiracion", (timezone.now() + timezone.timedelta(days=30)).strftime('%Y-%m-%d'))
        self.page.fill("input#cvv", "123")
        self.page.fill("input#nombreTarjeta", "Test User")
        self.page.check("input#terminos")

    def test_ticket_purchase_exceeding_limit_client_side(self):
        """Prueba que verifica que la validación del lado del cliente impide superar el límite de entradas"""
        self.login_as_regular_user()
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/purchase/")
        self.page.evaluate("""
            document.getElementById("purchaseForm").addEventListener = function() {};
            const form = document.getElementById("purchaseForm");
            const newForm = form.cloneNode(true);
            form.parentNode.replaceChild(newForm, form);
            document.getElementById("cantidad").max = "10";
        """)
        self.page.fill("input#cantidad", "5")
        self.fill_purchase_form()
        self.page.click("button:has-text('Confirmar compra')")
        self.assertIn("purchase", self.page.url)
        self.assertNotIn("viewTickets", self.page.url)

    def test_ticket_purchase_accumulation_exceeds_limit(self):
        """Prueba que verifica que la suma de entradas previas más nuevas excede el límite permitido"""
        Ticket.objects.create(
            event=self.event,
            user=self.user,
            buy_date=timezone.now().date(),
            ticket_code="ABC123",
            quantity=3,
            type="GENERAL"
        )
        self.login_as_regular_user()
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/purchase/")
        self.page.click("button:has-text('+')")
        self.assertEqual(self.page.input_value("input#cantidad"), "2")
        self.fill_purchase_form()
        self.page.click("button:has-text('Confirmar compra')")
        self.assertIn("purchase", self.page.url)
        self.assertNotIn("viewTickets", self.page.url)

    def test_ticket_purchase_within_limit(self):
        """Prueba que verifica que la compra se realiza correctamente si está dentro del límite permitido"""
        self.login_as_regular_user()
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/purchase/")
        for _ in range(2):
            self.page.click("button:has-text('+')")
        self.assertEqual(self.page.input_value("input#cantidad"), "3")
        self.fill_purchase_form()
        self.page.click("button:has-text('Confirmar compra')")
        self.page.wait_for_selector(".swal2-popup:has-text('¡Pago Exitoso!')")
        self.page.click(".swal2-confirm")
        self.page.wait_for_url(f"**/events/{self.event.pk}/viewTickets/")
        self.page.wait_for_selector("table")
        self.assertGreater(self.page.locator("table tr").count(), 1)

    def test_javascript_validation_prevents_exceeding_limit(self):
        """Prueba que verifica que la validación JavaScript impide seleccionar más de 4 entradas"""
        self.login_as_regular_user()
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/purchase/")
        for _ in range(3):
            self.page.click("button:has-text('+')")
        self.assertEqual(self.page.input_value("input#cantidad"), "4")
        self.page.click("button:has-text('+')")
        self.assertEqual(self.page.input_value("input#cantidad"), "4")
        self.page.fill("input#cantidad", "5")
        self.assertEqual(self.page.input_value("input#cantidad"), "4")
        self.page.evaluate("document.getElementById('cantidad').value = '5'")
        self.fill_purchase_form()
        self.page.click("button:has-text('Confirmar compra')")
        self.assertIn("purchase", self.page.url)

    def test_input_quantity_validation(self):
        """Prueba que verifica que el input de cantidad se corrige si se excede el valor máximo permitido"""
        self.login_as_regular_user()
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/purchase/")
        self.page.fill("input#cantidad", "7")
        self.assertLessEqual(int(self.page.input_value("input#cantidad")), 4)
