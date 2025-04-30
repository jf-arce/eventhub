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

        if len(errors.keys()) > 0:
            return False, errors

        RefoundRequest.objects.create(
            ticket_code=ticket_code,
            reason=reason,
            user=user,
            event=event,
        )

        return True, None

    def update(self,approved, approval_date ,ticket_code, reason, created_at, user):
        self.approved = approved or self.approved
        self.approval_date = approval_date or self.approval_date
        self.ticket_code = ticket_code or self.ticket_code
        self.reason = reason or self.reason
        self.created_at = created_at or self.created_at
        self.user = user or self.user

        self.save()