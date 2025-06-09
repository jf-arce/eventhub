import datetime

from django.utils import timezone
from playwright.sync_api import expect

from app.models import Category, Event, Notification, Ticket, User, Venue
from app.test.test_e2e.base import BaseE2ETest


class NotificationBaseE2ETest(BaseE2ETest):
    """Clase base específica para tests de notificaciones"""
    
    def setUp(self):
        super().setUp()
        
        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizertest@gmail.com",
            password="password123",
            is_organizer=True,
        )
        
        # Crear venue y category necesarios para el evento
        self.venue = Venue.objects.create(
            name="Venue de prueba",
            address="123 Calle Falsa, Ciudad, País",
            city="Ciudad de prueba",
            capacity=100,
            contact="Contacto de prueba",
        )
        
        self.category = Category.objects.create(
            name="Categoria de prueba",
            description="Descripción de la categoría de prueba",
        )
        
        # Crear evento de prueba
        event_date = timezone.make_aware(datetime.datetime(2025, 6, 15, 14, 30))
        self.event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=event_date,
            organizer=self.organizer,
            venue=self.venue,
            category=self.category,
        )
        
        # Crear usuarios regulares
        self.user1 = User.objects.create_user(
            username="usuario_test_1",
            email="user1@gmail.com",
            password="password123",
            is_organizer=False,
        )
        
        self.user2 = User.objects.create_user(
            username="usuario_test_2",
            email="user2@gmail.com",
            password="password123",
            is_organizer=False,
        )
        
        # Crear tickets para los usuarios (simular que compraron entradas)
        self.ticket_user1 = Ticket.objects.create(
            user=self.user1,
            event=self.event,
            buy_date=timezone.now(),
            ticket_code="TICKET123",
            quantity=1,
            type="GENERAL"
        )
        
        self.ticket_user2 = Ticket.objects.create(
            user=self.user2,
            event=self.event,
            buy_date=timezone.now(),
            ticket_code="TICKET456",
            quantity=1,
            type="GENERAL",
        )
        
        
class NotificationWhenEventModifiedE2ETest(NotificationBaseE2ETest):
    """Tests E2E para verificar la funcionalidad de notificaciones cuando se modifican eventos"""
    
    def goToEditEventPage(self):
        """Navega a la página de edición del evento y verifica que el formulario está presente"""
        self.page.goto(f"{self.live_server_url}/")
        header = self.page.locator("h1")
        expect(header).to_be_visible()
        
        # Nos logueamos como organizador
        self.login_user(self.organizer.username, "password123")
    
        # Navegamos a la pagina para editar el evento
        self.page.goto(f"{self.live_server_url}/events/{self.event.pk}/edit/")
        edit_header = self.page.locator("h1")
        expect(edit_header).to_have_text("Editar evento")
        expect(edit_header).to_be_visible()
        
        # Verificamos que el formulario de edición está presente
        form = self.page.locator("form[method='POST'][action*='/edit/']")
        expect(form).to_be_visible()
        
        return form

    def test_notification_when_event_date_modified(self):
        """Test completo E2E para notificaciones cuando se modifica la fecha de un evento"""
        
        # Navegamos hasta la página de edición del evento y recuperamos el formulario
        form = self.goToEditEventPage()
            
        # Verificamos que el campo fecha tiene el valor correcto
        date_input = self.page.get_by_label("Fecha")
        expect(date_input).to_have_value("2025-06-15")
        # Modificamos la fecha del evento
        new_date = "2025-07-01"
        date_input.fill(new_date)
        expect(date_input).to_have_value(new_date)
        # Submit del formulario
        submit_button = form.locator("button[type='submit']")
        submit_button.click()
        
        # Verificamos redirección a la lista de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")
        events_header = self.page.locator("h1")
        expect(events_header).to_have_text("Eventos")
        
        # Verificamos que se creó una notificación en la base de datos
        notifications = Notification.objects.filter(event=self.event)
        assert notifications.count() == 1
        
        # Cerramos sesión del organizador
        self.page.get_by_role("button", name="Salir").click()
        
        # Nos logueamos como usuario 1
        self.login_user(self.user1.username, "password123")
        
        # Navegamos a las notificaciones del usuario
        self.page.goto(f"{self.live_server_url}/user/notifications/")
        notifications_header = self.page.locator("h1")
        expect(notifications_header).to_be_visible()
        
        # Verificamos que aparece la notificación
        list_items = self.page.locator(".list-group-item")
        expect(list_items).to_have_count(1)
        first_item = list_items.first
        expect(first_item.locator("span.badge")).to_have_text("Nueva")
        expect(first_item).to_contain_text("Cambios en el evento")
        expect(first_item).to_contain_text("01/07/2025")        
        
        self.page.get_by_role("button", name="Salir").click()
        
        # Nos logueamos como usuario 2 y verificamos que llego la notificación
        self.login_user(self.user2.username, "password123")
        
        # Navegamos a las notificaciones del usuario
        self.page.goto(f"{self.live_server_url}/user/notifications/")
        notifications_header = self.page.locator("h1")
        expect(notifications_header).to_be_visible()
        
        # Verificamos que aparece la notificación
        list_items = self.page.locator(".list-group-item")
        expect(list_items).to_have_count(1)
        first_item = list_items.first
        expect(first_item.locator("span.badge")).to_have_text("Nueva")
        expect(first_item).to_contain_text("Cambios en el evento")
        expect(first_item).to_contain_text("01/07/2025")

    def test_notification_when_event_hour_changed(self):
        """Test completo E2E para notificaciones cuando se modifica la hora de un evento"""

        # Navegamos hasta la página de edición del evento y recuperamos el formulario
        form = self.goToEditEventPage()
        
        # Verificamos que el campo hora tiene el valor correcto
        time_input = self.page.get_by_label("Hora")
        expect(time_input).to_have_value("14:30")
        
        # Modificamos la hora del evento
        new_time = "16:00"
        time_input.fill(new_time)
        expect(time_input).to_have_value(new_time)
        
        # Submit del formulario
        submit_button = form.locator("button[type='submit']")
        submit_button.click()
        
        # Verificamos redirección a la lista de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")
        events_header = self.page.locator("h1")
        expect(events_header).to_have_text("Eventos")
        
        # Verificamos que se creó una notificación en la base de datos
        notifications = Notification.objects.filter(event=self.event)
        assert notifications.count() == 1
        
        # Cerramos sesión del organizador
        self.page.get_by_role("button", name="Salir").click()
        
        # Nos logueamos como usuario 1
        self.login_user(self.user1.username, "password123")
        
        # Navegamos a las notificaciones del usuario
        self.page.goto(f"{self.live_server_url}/user/notifications/")
        notifications_header = self.page.locator("h1")
        expect(notifications_header).to_be_visible()
        
        # Verificamos que aparece la notificación
        list_items = self.page.locator(".list-group-item")
        expect(list_items).to_have_count(1)
        first_item = list_items.first
        expect(first_item.locator("span.badge")).to_have_text("Nueva")
        expect(first_item).to_contain_text("Cambios en el evento")
        expect(first_item).to_contain_text("16:00")
        
        # Cerramos sesión del usuario 1
        self.page.get_by_role("button", name="Salir").click()
       
        # Nos logueamos como usuario 2 y verificamos que llego la notificación
        self.login_user(self.user2.username, "password123")
        # Navegamos a las notificaciones del usuario
        self.page.goto(f"{self.live_server_url}/user/notifications/")
        notifications_header = self.page.locator("h1")
        expect(notifications_header).to_be_visible()
        # Verificamos que aparece la notificación
        list_items = self.page.locator(".list-group-item")
        expect(list_items).to_have_count(1)
        first_item = list_items.first
        expect(first_item.locator("span.badge")).to_have_text("Nueva")
        expect(first_item).to_contain_text("Cambios en el evento")
        expect(first_item).to_contain_text("16:00")
        
    def test_notification_when_event_venue_changed(self):
        """Test completo E2E para notificaciones cuando se modifica el lugar de un evento"""
        
        new_venue = Venue.objects.create(
            name="Nuevo Venue de prueba 2 ",
            address="489 Nueva Calle 2, Ciudad, País",
            city="Nueva Ciudad de prueba 2",
            capacity=200,
            contact="Nuevo Contacto de prueba 2",
        )
        
        # Navegamos hasta la página de edición del evento y recuperamos el formulario
        form = self.goToEditEventPage()
        
        # Verificamos que el campo lugar tiene el valor correcto
        venue_input = self.page.locator("select[id='venue']")
        expect(venue_input).to_have_value(str(self.venue.pk))
        
        # Modificamos el lugar del evento
        venue_input.select_option(str(new_venue.pk))
        expect(venue_input).to_have_value(str(new_venue.pk))
        
        # Submit del formulario
        submit_button = form.locator("button[type='submit']")
        submit_button.click()
        
        # Verificamos redirección a la lista de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")
        events_header = self.page.locator("h1")
        expect(events_header).to_have_text("Eventos")
        
        # Verificamos que se creó una notificación en la base de datos
        notifications = Notification.objects.filter(event=self.event)
        assert notifications.count() == 1
        
        # Cerramos sesión del organizador
        self.page.get_by_role("button", name="Salir").click()
        
        # Nos logueamos como usuario 1
        self.login_user(self.user1.username, "password123")
        
        # Navegamos a las notificaciones del usuario
        self.page.goto(f"{self.live_server_url}/user/notifications/")
        notifications_header = self.page.locator("h1")
        expect(notifications_header).to_be_visible()
        
        # Verificamos que aparece la notificación
        list_items = self.page.locator(".list-group-item")
        expect(list_items).to_have_count(1)
        first_item = list_items.first
        expect(first_item.locator("span.badge")).to_have_text("Nueva")
        expect(first_item).to_contain_text("Cambios en el evento")
        expect(first_item).to_contain_text(new_venue.name)
        
        # Cerramos sesión del usuario 1
        self.page.get_by_role("button", name="Salir").click()
       
        # Nos logueamos como usuario 2 y verificamos que llego la notificación
        self.login_user(self.user2.username, "password123")
        
        # Navegamos a las notificaciones del usuario
        self.page.goto(f"{self.live_server_url}/user/notifications/")
        notifications_header = self.page.locator("h1")
        expect(notifications_header).to_be_visible()
        
        # Verificamos que aparece la notificación
        list_items = self.page.locator(".list-group-item")
        expect(list_items).to_have_count(1)
        first_item = list_items.first
        expect(first_item.locator("span.badge")).to_have_text("Nueva")
        expect(first_item).to_contain_text("Cambios en el evento")
        expect(first_item).to_contain_text(new_venue.name)