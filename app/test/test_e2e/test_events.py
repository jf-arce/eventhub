import datetime
import re

from django.utils import timezone
from playwright.sync_api import expect

from app.models import Category, Event, User, Venue
from app.test.test_e2e.base import BaseE2ETest


class EventBaseTest(BaseE2ETest):
    """Clase base específica para tests de eventos"""

    def setUp(self):
        super().setUp()

        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )

        # Crear usuario regular
        self.regular_user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123",
            is_organizer=False,
        )

        # Crear eventos de prueba
        # Evento 1
        self.category = Category.objects.create(name="General", description="Test")
        self.venue = Venue.objects.create(
            name="Teatro Central",
            address="Calle Falsa 123",
            city="Ciudad",
            capacity=100,
            contact="X")
        event_date1 = timezone.make_aware(datetime.datetime(2025, 9, 10, 10, 10))
        self.event1 = Event.objects.create(
            title="Evento de prueba 1",
            description="Descripción del evento 1",
            scheduled_at=event_date1,
            organizer=self.organizer,
            venue=self.venue,  # Usar el mismo venue del evento 1
            category=self.category,  # Usar la misma categoría del evento 1
        )

        # Evento 2
        event_date2 = timezone.make_aware(datetime.datetime(2025, 10, 15, 14, 30))
        self.event2 = Event.objects.create(
            title="Evento de prueba 2",
            description="Descripción del evento 2",
            scheduled_at=event_date2,
            organizer=self.organizer,
            venue=self.venue,  # Usar el mismo venue del evento 1
            category=self.category,  # Usar la misma categoría del evento 1
        )

    def _table_has_event_info(self):
        """Método auxiliar para verificar que la tabla tiene la información correcta de eventos"""
        # Verificar encabezados de la tabla (ORDEN CORRECTO SEGÚN TU HTML)
        headers = self.page.locator("table thead th")
        expect(headers.nth(0)).to_have_text("Nombre")
        expect(headers.nth(1)).to_have_text("Fecha")
        expect(headers.nth(2)).to_have_text("Categoría")
        expect(headers.nth(3)).to_have_text("Ubicación")
        expect(headers.nth(4)).to_have_text("Organizador")
        expect(headers.nth(5)).to_have_text("Acciones")

        # Verificar que los eventos aparecen en la tabla
        rows = self.page.locator("table tbody tr")
        expect(rows).to_have_count(2)

        # Verificar datos del primer evento
        row0 = rows.nth(0)
        expect(row0.locator("td").nth(0)).to_have_text("Evento de prueba 1")
        expect(row0.locator("td").nth(1)).to_have_text("10 set 2025, 10:10")
        expect(row0.locator("td").nth(2)).to_have_text("General")
        expect(row0.locator("td").nth(3)).to_have_text("Teatro Central")
        expect(row0.locator("td").nth(4)).to_have_text("organizador")

        # Verificar datos del segundo evento
        row1 = rows.nth(1)
        expect(row1.locator("td").nth(0)).to_have_text("Evento de prueba 2")
        expect(row1.locator("td").nth(1)).to_have_text("15 oct 2025, 14:30")
        expect(row1.locator("td").nth(2)).to_have_text("General")
        expect(row1.locator("td").nth(3)).to_have_text("Teatro Central")
        expect(row1.locator("td").nth(4)).to_have_text("organizador")

    def _table_has_correct_actions(self, user_type):
        """Método auxiliar para verificar que las acciones son correctas según el tipo de usuario"""
        row0 = self.page.locator("table tbody tr").nth(0)

        detail_button = row0.get_by_role("link", name="Ver Detalle")
        edit_button = row0.get_by_role("link", name="Editar")
        delete_form = row0.locator("form")

        expect(detail_button).to_be_visible()
        expect(detail_button).to_have_attribute("href", f"/events/{self.event1.id}/")

        if user_type == "organizador":
            expect(edit_button).to_be_visible()
            expect(edit_button).to_have_attribute("href", f"/events/{self.event1.id}/edit/")

            expect(delete_form).to_have_attribute("action", f"/events/{self.event1.id}/delete/")
            expect(delete_form).to_have_attribute("method", "POST")

            delete_button = delete_form.get_by_role("button", name="Eliminar")
            expect(delete_button).to_be_visible()
        else:
            expect(edit_button).to_have_count(0)
            expect(delete_form).to_have_count(0)


class EventAuthenticationTest(EventBaseTest):
    """Tests relacionados con la autenticación y permisos de usuarios en eventos"""

    def test_events_page_requires_login(self):
        """Test que verifica que la página de eventos requiere inicio de sesión"""
        # Cerrar sesión si hay alguna activa
        self.context.clear_cookies()

        # Intentar ir a la página de eventos sin iniciar sesión
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que redirige a la página de login
        expect(self.page).to_have_url(re.compile(r"/accounts/login/"))


class EventDisplayTest(EventBaseTest):
    """Tests relacionados con la visualización de la página de eventos"""

    def test_events_page_display_as_organizer(self):
        """Test que verifica la visualización correcta de la página de eventos para organizadores"""
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar el título de la página
        expect(self.page).to_have_title("EventHub")  # Cambiado de "Eventos" a "EventHub"

        # Verificar que existe un encabezado con el texto "Eventos"
        header = self.page.locator("h1")
        expect(header).to_have_text("Eventos")
        expect(header).to_be_visible()

        # Verificar que existe una tabla
        table = self.page.locator("table")
        expect(table).to_be_visible()

        self._table_has_event_info()
        self._table_has_correct_actions("organizador")

    def test_events_page_regular_user(self):
        """Test que verifica la visualización de la página de eventos para un usuario regular"""

        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        expect(self.page).to_have_title("EventHub")  # Cambiado de "Eventos" a "EventHub"

        # Verificar que existe un encabezado con el texto "Eventos"
        header = self.page.locator("h1")
        expect(header).to_have_text("Eventos")
        expect(header).to_be_visible()

        # Verificar que existe una tabla
        table = self.page.locator("table")
        expect(table).to_be_visible()

        self._table_has_event_info()
        self._table_has_correct_actions("regular")

    def test_events_page_no_events(self):
        """Test que verifica el comportamiento cuando no hay eventos"""
        # Eliminar todos los eventos
        Event.objects.all().delete()

        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que existe un mensaje indicando que no hay eventos
        no_events_message = self.page.locator("text=No hay eventos disponibles")
        expect(no_events_message).to_be_visible()


class EventPermissionsTest(EventBaseTest):
    """Tests relacionados con los permisos de usuario para diferentes funcionalidades"""

    def test_buttons_visible_only_for_organizer(self):
        """Test que verifica que los botones de gestión solo son visibles para organizadores"""
        # Primero verificar como organizador
        self.login_user("organizador", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que existe el botón de crear
        create_button = self.page.get_by_role("link", name="Crear Evento")
        expect(create_button).to_be_visible()

        # Cerrar sesión
        self.page.get_by_role("button", name="Salir").click()

        # Iniciar sesión como usuario regular
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Verificar que NO existe el botón de crear
        create_button = self.page.get_by_role("link", name="Crear Evento")
        expect(create_button).to_have_count(0)


class EventCRUDTest(EventBaseTest):
    """Tests relacionados con las operaciones CRUD (Crear, Leer, Actualizar, Eliminar) de eventos"""

    def test_create_new_event_organizer(self):
        """Test que verifica la funcionalidad de crear un nuevo evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Hacer clic en el botón de crear evento
        self.page.get_by_role("link", name="Crear Evento").click()

        # Verificar que estamos en la página de creación de evento
        expect(self.page).to_have_url(f"{self.live_server_url}/events/create/")

        header = self.page.locator("h1")
        expect(header).to_have_text("Crear evento")
        expect(header).to_be_visible()

        # Completar el formulario
        self.page.get_by_label("Título del Evento").fill("Evento de prueba 2")
        self.page.get_by_label("Descripción").fill("Descripción creada desde prueba 2")
        self.page.get_by_label("Fecha").fill("2025-10-15")
        self.page.get_by_label("Hora").fill("14:30")
        self.page.get_by_label("Categoría").select_option(label="General")
        self.page.get_by_label("Ubicación").select_option(label="Teatro Central (Ciudad)")

        # Enviar el formulario (sin esperar navegación)
        self.page.get_by_role("button", name="Crear Evento").click()

        # Esperar a que el nuevo evento aparezca en la tabla
        self.page.wait_for_selector("table tbody tr:has-text('Evento de prueba 2')")

        # Verificar que ahora hay 3 eventos
        rows = self.page.locator("table tbody tr")
        expect(rows).to_have_count(3)

        row = self.page.locator("table tbody tr").last
        expect(row.locator("td").nth(0)).to_have_text("Evento de prueba 2")
        expect(row.locator("td").nth(1)).to_have_text("15 oct 2025, 14:30")
        expect(row.locator("td").nth(2)).to_have_text("General")
        expect(row.locator("td").nth(3)).to_have_text("Teatro Central")
        expect(row.locator("td").nth(4)).to_have_text("organizador")


    def test_edit_event_organizer(self):
        """Test que verifica la funcionalidad de editar un evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Hacer clic en el botón editar del primer evento
        self.page.get_by_role("link", name="Editar").first.click()

        # Verificar que estamos en la página de edición
        expect(self.page).to_have_url(f"{self.live_server_url}/events/{self.event1.id}/edit/")

        header = self.page.locator("h1")
        expect(header).to_have_text("Editar evento")
        expect(header).to_be_visible()

        # Verificar que el formulario está precargado con los datos del evento y luego los editamos
        title = self.page.get_by_label("Título del Evento")
        expect(title).to_have_value("Evento de prueba 1")
        title.fill("Titulo editado")

        description = self.page.get_by_label("Descripción")
        expect(description).to_have_value("Descripción del evento 1")
        description.fill("Descripcion Editada")

        date = self.page.get_by_label("Fecha")
        expect(date).to_have_value("2025-09-10")
        date.fill("2025-11-20")

        time = self.page.get_by_label("Hora")
        expect(time).to_have_value("10:10")
        time.fill("03:00")

        # Enviar el formulario y esperar la navegación
        with self.page.expect_navigation():
            self.page.get_by_role("button", name="Crear Evento").click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que el título y la fecha del evento han sido actualizados
        row = self.page.locator("table tbody tr").last
        expect(row.locator("td").nth(0)).to_have_text("Titulo editado")           # Nombre
        expect(row.locator("td").nth(1)).to_have_text("20 nov 2025, 03:00")       # Fecha
        expect(row.locator("td").nth(2)).to_have_text("General")                  # Categoría
        expect(row.locator("td").nth(3)).to_have_text("Teatro Central")           # Ubicación
        expect(row.locator("td").nth(4)).to_have_text("organizador")              # Organizador

    def test_delete_event_organizer(self):
        """Test que verifica la funcionalidad de eliminar un evento para organizadores"""
        # Iniciar sesión como organizador
        self.login_user("organizador", "password123")

        # Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")

        # Contar eventos antes de eliminar
        initial_count = len(self.page.locator("table tbody tr").all())

        # Hacer clic en el botón eliminar del primer evento
        self.page.get_by_role("button", name="Eliminar").first.click()

        # Verificar que redirigió a la página de eventos
        expect(self.page).to_have_url(f"{self.live_server_url}/events/")

        # Verificar que ahora hay un evento menos
        rows = self.page.locator("table tbody tr")
        expect(rows).to_have_count(initial_count - 1)

        # Verificar que el evento eliminado ya no aparece en la tabla
        expect(self.page.get_by_text("Evento de prueba 1")).to_have_count(0)
