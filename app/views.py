import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Event, User, RefoundRequest


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
def refound_request(request, id=None):
    user = request.user
    errors = {}
    organizer_events = None  # Inicializamos organizer_events fuera del bloque POST

    if request.method == "POST":
        ticket_code = request.POST.get("ticket_code")
        reason = request.POST.get("reason")

        if id is None:
            event_id = request.POST.get("event")
            if event_id:
                try:
                    event = Event.objects.get(pk=event_id)
                    success, errors = RefoundRequest.new(ticket_code, reason, user, event) # Ahora pasamos el 'event'
                except Event.DoesNotExist:
                    errors["event"] = "El evento seleccionado no es válido."
                    success = False
            else:
                errors["event"] = "Por favor, selecciona el evento del ticket."
                success = False

            if not success:
                return render(
                    request,
                    "app/refound/refound_request.html",
                    {
                        "errors": errors,
                        "refound_request": {},
                        "user_is_organizer": user.is_organizer,
                        "organizer_events": organizer_events,
                    },
                )
        else:
            organizer_events = RefoundRequest.objects.filter(event__organizer=user) # Filtra directamente por el organizador del evento
            refound_request_list = RefoundRequest.objects.all() # Esto parece innecesario aquí, ¿quizás querías otra cosa?

        return redirect("events") # Rediriges después del POST, así que el render de abajo se ejecutará en una petición GET posterior

    refound_request_single = {}
    if id is not None:
        refound_request_single = get_object_or_404(Event, pk=id)

    if user.is_organizer:
        organizer_events = RefoundRequest.objects.filter(event__organizer=user) # Obtener las solicitudes para los eventos del organizador
    else:
        organizer_events = None # Aseguramos que sea None para usuarios no organizadores

    return render(
        request,
        "app/refound/refound_request.html",
        {
            "refound_request": refound_request_single,
            "user_is_organizer": user.is_organizer,
            "organizer_events": organizer_events,
        },
    )

