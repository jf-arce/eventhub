from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
from django.utils import timezone


class User(AbstractUser):
    is_organizer = models.BooleanField(default=False)

    @classmethod
    def validate_new_user(cls, email, username, password, password_confirm):
        errors = {}

        if email is None:
            errors["email"] = "El email es requerido"
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Ya existe un usuario con este email"

        if username is None:
            errors["username"] = "El username es requerido"
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Ya existe un usuario con este nombre de usuario"

        if password is None or password_confirm is None:
            errors["password"] = "Las contraseñas son requeridas"
        elif password != password_confirm:
            errors["password"] = "Las contraseñas no coinciden"

        return errors

class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    capacity = models.IntegerField()
    contact = models.CharField(max_length=200)

    def __str__(self):
        return self.name
    
    @classmethod
    def validate(cls, name, address, city, capacity, contact):
        errors = {}

        if name == "":
            errors["name"] = "Por favor ingrese un nombre"

        if address == "":
            errors["address"] = "Por favor ingrese una direccion"

        if city == "":
            errors["city"] = "Por favor ingrese una ciudad"

        if capacity <= 0:
            errors["capacity"] = "La capacidad debe ser mayor a 0"

        if contact == "":
            errors["contact"] = "Por favor ingrese un contacto"

        return errors

class Category (models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
   
    @classmethod
    def validate(cls, name, description, exclude_id=None):
        errors = {}

        if name == "":
            errors["name"] = "Por favor ingrese un nombre"

        if len(name) > 200:
            errors["name"] = "El nombre no puede tener más de 200 caracteres"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

        if len(description.strip()) < 10:
           errors["description"] = "La descripción debe tener al menos 10 caracteres"

        if len(description) > 1000:
            errors["description"] = f"La descripción no puede tener más de 1000 caracteres."

        qs = cls.objects.filter(name__iexact=name)
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        if qs.exists():
            errors["name"] = "Ya existe una categoría con este nombre"

        return errors
    
    @classmethod
    def new(cls, name, description):
        errors = cls.validate(name, description)

        if len(errors.keys()) > 0:
            return False, errors

        cls.objects.create(
            name=name,
            description=description,
        )

        return True, None

    def update(self, name, description):
        errors = self.validate(name, description, exclude_id=self.pk)
        if errors:
            return False, errors

        self.name = name or self.name
        self.description = description or self.description
        self.save()
        return True, {}


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="category_event")

    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, description, scheduled_at, venue, category):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"
        
        if venue is None:
            errors["venue"] = "Por favor seleccione una ubicación"

        if category is None:
            errors["category"] = "Por favor seleccione una categoría"
        
        if scheduled_at:
            buenos_aires_tz = timezone.get_fixed_timezone(-3 * 60)
            
            now_in_ba = timezone.now().astimezone(buenos_aires_tz)
            today = now_in_ba.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            scheduled_at_in_ba = scheduled_at.astimezone(buenos_aires_tz)
            
            if scheduled_at_in_ba < tomorrow:
                errors["date"] = "La fecha del evento debe ser posterior al día de hoy"

        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer, category, venue=None):
        errors = Event.validate(title, description, scheduled_at, venue, category)

        if len(errors.keys()) > 0:
            return False, errors

        Event.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,
            category=category,
            venue=venue,
        )

        return True, None

    def update(self, title=None, description=None, scheduled_at=None, organizer=None, category=None, venue=None):
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if scheduled_at is not None:
            self.scheduled_at = scheduled_at
        if organizer is not None:
            self.organizer = organizer
        if category is not None:
            self.category = category
        if venue is not None:
            self.venue = venue

        self.save()

    def is_future(self):
        time_now = timezone.now() - timedelta(hours=3)
        return self.scheduled_at >= time_now     

class Notification(models.Model):
    class Priority(models.TextChoices):
        HIGH = 'high', 'Alta'
        NORMAL = 'normal', 'Normal'
        LOW = 'low', 'Baja'
        
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.LOW,
    )
    is_read = models.BooleanField(default=False)
    users = models.ManyToManyField(User, related_name="notifications")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="notifications")
    
    def __str__(self):
        return self.title
    
    @classmethod
    def validate(cls, title, message, priority, event):
        errors = {}
        
        if message == "":
            errors["message"] = "Por favor ingrese un mensaje"

        if priority not in [cls.Priority.HIGH, cls.Priority.NORMAL, cls.Priority.LOW]:
            errors["priority"] = "Prioridad no válida"
            
        if title is None or not str(title).strip():
            errors["title"] = "El título no puede estar vacío."
        elif len(title.strip()) > 200:
            errors["title"] = "El título no puede superar los 200 caracteres."
            
        if cls.objects.filter(title=title.strip(), message=message.strip(), event=event).exists():
            errors["duplicado"] = "Ya existe una notificación con el mismo título, mensaje y evento."
        
        # El evento debe tener al menos un ticket de usuario vendido
        if event and event.tickets.count() == 0:
            errors["sin_destinatarios"] = "No se puede enviar una notificación a un evento sin personas con entradas."

        return errors
    
    @classmethod
    def notify_users_of_event_update(cls, event, message):
        notification = cls.objects.create(
            title="Cambios en el evento",
            message=message,
            priority= cls.Priority.HIGH,
            event=event
        )
        
        # Encuentra todos los usuarios que tienen entradas para el evento
        tickets = Ticket.objects.filter(event=event)
        users = [ticket.user for ticket in tickets]
        
        notification.users.set(users)
        notification.save()
        return notification

class RefoundRequest(models.Model):
    approved = models.BooleanField(null=True, default=None)
    approval_date = models.DateTimeField(auto_now_add=True)
    ticket_code = models.CharField(max_length=200)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_refund")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="refound_event")


    def __str__(self):
        return self.ticket_code

    @classmethod
    def validate(cls, ticket_code, reason):
        errors = {}

        if ticket_code == "":
            errors["ticket_code"] = "Por favor ingrese su codigo de ticket"

        if cls.objects.filter(ticket_code=ticket_code).exists():
            errors["ticket_code"] = "Ya existe una solicitud de reembolso para este ticket."

        if reason == "":
            errors["reason"] = "Por favor ingrese una razon de reembolso"

        if len(reason) < 10:
            errors["reason"] = "La razón debe tener al menos 10 caracteres."

        if len(reason) > 200:
            errors["reason"] = "La razón es demasiado extensa (máximo 1000 caracteres)."


        return errors

    @classmethod
    def new(cls,ticket_code, reason, user, event):
        errors = RefoundRequest.validate(ticket_code, reason)
        RefoundRequest.objects.create(
            ticket_code=ticket_code,
            reason=reason,
            user=user,
            event=event,
        )

        return True, None

    def update(self, reason):
        self.reason = reason or self.reason
        
        self.save()

class Ticket(models.Model):
    TICKET_TYPES = [
        ("GENERAL", "GENERAL"),
        ("VIP", "VIP"),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    buy_date = models.DateField()
    ticket_code = models.CharField(max_length=100, unique=True)
    quantity = models.IntegerField()
    type = models.CharField(max_length=10, choices=TICKET_TYPES)

    def __str__(self):
        return self.ticket_code
    
    @classmethod
    def validate_event_date(cls, event):
        """
        Valida que el evento no haya ocurrido ya
        """
        if timezone.now() > event.scheduled_at:
            return False, "No se pueden gestionar entradas para eventos que ya ocurrieron"
        return True, None

    @classmethod
    def validate_capacity(cls, event, quantity, exclude_ticket_id=None):
        """
        Valida que haya suficiente capacidad disponible en el evento
        """
        query = cls.objects.filter(event=event)
        if exclude_ticket_id:
            query = query.exclude(id=exclude_ticket_id)
        
        tickets_vendidos = query.aggregate(total=models.Sum('quantity'))['total'] or 0
        disponibles = event.venue.capacity - tickets_vendidos
        
        if quantity > disponibles:
            return False, f"No hay suficientes entradas disponibles (quedan {disponibles})"
        return True, None
        
    @classmethod
    def validate(cls, quantity, type, user=None, event=None):
        errors = {}

        if quantity == "":
            errors["quantity"] = "Por favor ingrese la cantidad de entradas"
        else:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    errors["quantity"] = "La cantidad de entradas debe ser mayor a 0"
                    
                if event and quantity > 0:
                    valid_capacity, error_msg = cls.validate_capacity(event, quantity)
                    if not valid_capacity:
                        errors["capacity"] = error_msg
            except ValueError:
                errors["quantity"] = "La cantidad de entradas debe ser un número válido"

        if type == "":
            errors["type"] = "Por favor ingrese el tipo de entrada"
            
        if event:
            valid_date, error_msg = cls.validate_event_date(event)
            if not valid_date:
                errors["event_date"] = error_msg
    
        if user and event and not errors.get('quantity'):
            limit_errors = cls.validate_ticket_limit(user, event, quantity)
            errors.update(limit_errors)

        return errors
    
    @classmethod
    def new(cls, buy_date, ticket_code, quantity, type, event, user):
        errors = Ticket.validate(quantity, type, user, event)

        if len(errors.keys()) > 0:
            return False, errors

        Ticket.objects.create(
            buy_date=buy_date,
            ticket_code=ticket_code,
            quantity=quantity,
            type=type,
            event=event,
            user=user,
        )

        return True, None

    def update(self, buy_date, ticket_code, quantity, type):
        self.buy_date = buy_date or self.buy_date
        self.ticket_code = ticket_code or self.ticket_code
        self.quantity = quantity or self.quantity
        self.type = type or self.type

        self.save()

    @classmethod
    def validate_ticket_limit(cls, user, event, quantity):
        """
        Valida que un usuario no pueda comprar más de 4 entradas por evento.
        """
        errors = {}
        try:
            quantity = int(quantity)
            
            if quantity > 4:
                errors['quantity'] = "No puedes comprar más de 4 entradas por evento (límite excedido)"
                return errors
            
            current_count = cls.get_user_tickets_count(user, event)
            
            total = current_count + quantity
            if total > 4:
                errors['quantity'] = f"No puedes comprar más de 4 entradas por evento (ya has comprado {current_count}, lo que excedería el límite)"
        except ValueError:
            errors['quantity'] = "La cantidad debe ser un número válido"
        
        return errors

    @classmethod
    def get_user_tickets_count(cls, user, event):
        """
        Calcula el total de tickets que un usuario ya ha comprado para un evento.
        """
        from django.db.models import Sum
        
        result = cls.objects.filter(user=user, event=event).aggregate(
            total=Sum('quantity')
        )
        
        return result['total'] or 0
    
    @classmethod
    def validate_ticket_edit_limit(cls, user, event, new_quantity, ticket_being_edited):
        """
        Valida que al editar un ticket, el usuario no exceda el límite de 4 entradas por evento.
        Excluye el ticket que se está editando del conteo actual.
        """
        errors = {}
        try:
            new_quantity = int(new_quantity)
            
            if new_quantity > 4:
                errors['quantity'] = "No puedes tener más de 4 entradas por evento (límite excedido)"
                return errors
            
            current_count = cls.objects.filter(
                user=user, 
                event=event
            ).exclude(
                id=ticket_being_edited.id
            ).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
            
            total = current_count + new_quantity
            if total > 4:
                errors['quantity'] = f"No puedes tener más de 4 entradas por evento, el total sería {total}"
        except ValueError:
            errors['quantity'] = "La cantidad debe ser un número válido"

            

class Comment(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_comments")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_comments")
    
    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, text, user, event):
        errors = {}
        
        if not title.strip():
            errors["title"] = "Por favor ingrese un título"

        if not text.strip():
            errors["text"] = "Por favor ingrese un comentario"

        if len(title) > 200:
            errors["title"] = "El título no puede tener más de 200 caracteres"

        if len(text) > 1000:
            errors["text"] = "El comentario no puede tener más de 1000 caracteres"
        
        if not isinstance(user, User) or not User.objects.filter(id=user.pk).exists():
            errors["user"] = "El usuario no existe o no es válido"

        if not isinstance(event, Event) or not Event.objects.filter(id=event.pk).exists():
            errors["event"] = "El evento no existe o no es válido"

        return errors
    
    @classmethod
    def new(cls, title, text, user, event):
        error = cls.validate(title, text, user, event)
        
        if len(error.keys()) > 0:
            return False, error
        
        cls.objects.create(
            title=title,
            text=text,
            user=user,
            event=event
        )

        return True, None
    
    def update(self, title, text):
        self.title = title or self.title
        self.text = text or self.text
        
        self.save()
    

class Rating(models.Model):
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    title = models.CharField(max_length=255)
    text = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])  
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')  

    def __str__(self):
        return f"{self.user.username} - {self.rating}★"

    @classmethod
    def create_rating(cls, event, user, title, text, rating):
        if cls.objects.filter(event=event, user=user).exists():
            return False, "Ya has calificado este evento."
        rating = cls.objects.create(
            event=event,
            user=user,
            title=title,
            text=text,
            rating=int(rating)
        )
        return True, rating
    
    @classmethod
    def delete_rating(cls, event, user):
        try:
            rating = cls.objects.get(event=event, user=user)
            rating.delete()
            return True, "Calificación eliminada."
        except cls.DoesNotExist:
            return False, "No se encontró la calificación."
    
    @classmethod
    def update_rating(cls, event, user, title, text, rating):
        try:
            rating_instance = cls.objects.get(event=event, user=user)
            rating_instance.title = title
            rating_instance.text = text
            rating_instance.rating = int(rating)
            rating_instance.save()
            return True, rating_instance
        except cls.DoesNotExist:
            return False, "No se encontró la calificación para actualizar."

    @classmethod
    def filter_events(cls, date_filter=None):
        queryset = cls.objects.all()
        
        if date_filter:
            start_date = datetime.combine(date_filter, datetime.min.time())
            end_date = datetime.combine(date_filter, datetime.max.time())
            
            queryset = queryset.filter(
                scheduled_at__gte=start_date
            )
        
        return queryset.order_by('scheduled_at')
