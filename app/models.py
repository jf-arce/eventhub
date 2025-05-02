from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

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
    def validate(cls, name, description):
        errors = {}

        if name == "":
            errors["name"] = "Por favor ingrese un nombre"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

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
        self.name = name or self.name
        self.description = description or self.description

        self.save()


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
    def validate(cls, title, description, scheduled_at, venue):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"
        
        if venue is None:
            errors["venue"] = "Por favor seleccione una ubicación"
        
        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer, category, venue=None):
        errors = Event.validate(title, description, scheduled_at, venue)

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

    def update(self, title, description, scheduled_at, organizer, venue=None):
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer
        if venue is not None:
            self.venue = venue

        self.save()

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

        if reason == "":
            errors["reason"] = "Por favor ingrese una razon de reembolso"

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
    def validate(cls, quantity, type):
        errors = {}

        if quantity == "":
            errors["quantity"] = "Por favor ingrese la cantidad de entradas"
        else:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    errors["quantity"] = "La cantidad de entradas debe ser mayor a 0"
            except ValueError:
                errors["quantity"] = "La cantidad de entradas debe ser un número válido"

        if type == "":
            errors["type"] = "Por favor ingrese el tipo de entrada"
    
        return errors
    
    @classmethod
    def new(cls, buy_date, ticket_code, quantity, type, event, user):
        errors = Ticket.validate(quantity, type)

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
            

class Comment(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="user_comments")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="event_comments")
    
    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, text):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if text == "":
            errors["text"] = "Por favor ingrese un comentario"

        return errors
    
    @classmethod
    def new(cls, title, text, user, event):
        error = cls.validate(title, text)
        
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
        unique_together = ('event', 'user')  # evita duplicados

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

