from django.contrib.auth.models import AbstractUser
from django.db import models


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


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, description, scheduled_at):
        errors = {}

        if title == "":
            errors["title"] = "Por favor ingrese un titulo"

        if description == "":
            errors["description"] = "Por favor ingrese una descripcion"

        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer):
        errors = Event.validate(title, description, scheduled_at)

        if len(errors.keys()) > 0:
            return False, errors

        Event.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,
        )

        return True, None

    def update(self, title, description, scheduled_at, organizer):
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer

        self.save()

class Ticket(models.Model):
    TICKET_TYPES = [
        ("GENERAL", "GENERAL"),
        ("VIP", "VIP"),
    ]
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
    def new(cls, buy_date, ticket_code, quantity, type):
        errors = Ticket.validate(quantity, type)

        if len(errors.keys()) > 0:
            return False, errors

        Ticket.objects.create(
            buy_date=buy_date,
            ticket_code=ticket_code,
            quantity=quantity,
            type=type,
        )

        return True, None

