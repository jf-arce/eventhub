import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count

from .models import Event, User, Category


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
        {
            "events": events, 
            "user_is_organizer": request.user.is_organizer,
        },
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

    error = None

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")
        category_id = request.POST.get("category")

        if not title or not description or not date or not time or not category_id:
            error = "Todos los campos son obligatorios."
            return render(
                request,
                "app/event_form.html",
                {
                    "event": request.POST,
                    "user_is_organizer": user.is_organizer,
                    "categorys": Category.objects.filter(is_active=True),
                    "error": error,
                },
            )

        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")
        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        category = get_object_or_404(Category, pk=category_id)

        if id is None:
            # Crear un nuevo evento
            success, errors = Event.new(title, description, scheduled_at, request.user, category)
            if not success:
                error = errors  # Enviar los errores si hay
        else:
            # Actualizar un evento existente
            event = get_object_or_404(Event, pk=id)
            # event.update(title, description, scheduled_at, request.user, category)

        return redirect("events")

    event = {}
    if id is not None:
        event = get_object_or_404(Event, pk=id)

    categorys = Category.objects.filter(is_active=True)

    return render(
        request,
        "app/event_form.html",
        {
            "event": event,
            "user_is_organizer": request.user.is_organizer,
            "categorys": categorys,
            "error": error,
        },
    )


@login_required
def categorys(request):
    categorys = Category.objects.annotate(num_events=Count('category_event'))

    return render(
        request,
        "app/categorys/categorys.html",
        {
            "categorys": categorys,
        },
    )

@login_required
def category_form(request, id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("categorys")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")

        if id is None:
            Category.new(name, description)
        else:
            category = get_object_or_404(Category, pk=id)
            # category.update(name, description)

        return redirect("categorys")

    category = {}
    if id is not None:
        category = get_object_or_404(Category, pk=id)

    return render(
        request,
        "app/categorys/category_form.html",
        {"category": category, "user_is_organizer": request.user.is_organizer},
    )