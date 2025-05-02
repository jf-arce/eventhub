import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse

from .models import Event, User, Notification


def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        is_organizer = request.POST.get("is-organizer") is not None
        password = request.POST.get("password")
        password_confirm = request.POST.get("password-confirm")

        errors = User.validate_new_user(email, username, password, password_confirm)

        if len(errors) > 0:
            return render(
                request,
                "accounts/register.html",
                {
                    "errors": errors,
                    "data": request.POST,
                },
            )
        else:
            user = User.objects.create_user(
                email=email, username=username, password=password, is_organizer=is_organizer
            )
            login(request, user)
            return redirect("events")

    return render(request, "accounts/register.html", {})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request, "accounts/login.html", {"error": "Usuario o contraseña incorrectos"}
            )

        login(request, user)
        return redirect("events")

    return render(request, "accounts/login.html")


def home(request):
    return render(request, "home.html")


@login_required
def events(request):
    events = Event.objects.all().order_by("scheduled_at")
    return render(
        request,
        "app/events.html",
        {"events": events, "user_is_organizer": request.user.is_organizer},
    )


@login_required
def event_detail(request, id):
    event = get_object_or_404(Event, pk=id)
    return render(request, "app/event_detail.html", {"event": event})


@login_required
def event_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        event = get_object_or_404(Event, pk=id)
        event.delete()
        return redirect("events")

    return redirect("events")


@login_required
def event_form(request, id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")

        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")

        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        if id is None:
            Event.new(title, description, scheduled_at, request.user)
        else:
            event = get_object_or_404(Event, pk=id)
            event.update(title, description, scheduled_at, request.user)

        return redirect("events")

    event = {}
    if id is not None:
        event = get_object_or_404(Event, pk=id)

    return render(
        request,
        "app/event_form.html",
        {"event": event, "user_is_organizer": request.user.is_organizer},
    )

@login_required
def notifications(request):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
    
    notifications = Notification.objects.all().order_by("-created_at")
    
    return render(
        request,
        "app/notifications/notifications.html",
        {
            "notifications": notifications
        },
    )

@login_required
def notification_delete(request, id):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
    
    if request.method == "POST":
        notification = get_object_or_404(Notification, pk=id)
        notification.delete()
        return redirect("notifications")
    
    return redirect("notifications")

@login_required
def notification_detail(request, id):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
    
    notification = get_object_or_404(Notification, pk=id)
    
    return render(
        request,
        "app/notifications/notification_detail.html",
        {
            "notification": notification
        },
    )

@login_required 
def notification_form(request, id=None):
    user = request.user

    if not (user.is_organizer or user.is_superuser):
        return redirect("events")

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        priority = request.POST.get("priority")
        event_id = request.POST.get("event")
        destination = request.POST.get("destination")
        
        Notification.validate(title, message, priority)

        event = get_object_or_404(Event, pk=event_id)
        
        if destination == "all":
            # # Obtener todos los usuarios con tickets para el evento
            # tickets = Ticket.objects.filter(event=event)
            # users = [ticket.user for ticket in tickets]

            # # Crear la notificación para cada usuario
            # for user in users:
            #     notification = Notification.objects.create(
            #         title=title,
            #         message=message,
            #         priority=priority,
            #         event=event,
            #     )
            #     notification.users.add(user)
            return redirect("notifications")

        elif destination == "users":
            user_id = request.POST.get("specific_user")
            specific_user = get_object_or_404(User, pk=user_id)

            notification = Notification.objects.create(
                title=title,
                message=message,
                priority=priority,
                event=event,
            )
            notification.users.add(specific_user)

        return redirect("notifications")

    notification = {}
    if id is not None:
        notification = get_object_or_404(Notification, pk=id)

    events = Event.objects.all()
    users = User.objects.all()

    return render(
        request,
        "app/notifications/notification_form.html",
        {
            "notification": notification,
            "events": events,
            "users": users,
            "priority": Notification.Priority,
        },
    )
    
def events_users(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    # Recuperar todo los usuarios que tienen tickets del evento en cuestión
    # tickets = Ticket.objects.filter(event=event)
    # users = [ticket.user for ticket in tickets]
    
    # retornar la lista de usuarios en formato JSON
    # return JsonResponse({"users": users})
    
    return JsonResponse({"users": []})  # Borrar esto cuando se implemente la funcionalidad
    
def notification_update(request, id):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
    
    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        priority = request.POST.get("priority")
        
        print(title, message, priority)

        Notification.validate(title, message, priority)
        
        notification = get_object_or_404(Notification, pk=id)
        
        notification.title = title or notification.title
        notification.message = message or notification.message
        notification.priority = priority or notification.priority

        notification.save()
        
        return redirect("notifications")

    return redirect("notifications")
        
    
    