import datetime, uuid
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages

from .models import Event, User, Ticket


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
def purchase_ticket(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == "POST":
        try:
            quantity = request.POST.get("cantidad")
            ticket_type = request.POST.get("tipoEntrada", "GENERAL")
            
            ticket_code = str(uuid.uuid4())[:8].upper()
            
            buy_date = timezone.now().date()
            
            
            success, errors = Ticket.new(
                buy_date=buy_date,
                ticket_code=ticket_code,
                quantity=quantity,
                type=ticket_type,
                event=event,       
                user=request.user  
            )
            
            if success:
                messages.success(request, "Ticket comprado exitosamente!")
                return redirect('view_ticket', event_id=event_id)
            else:
                if errors:
                    for error in errors.values():
                        messages.error(request, error)
                return render(request, 'app/purchase_ticket.html', {
                    'event': event,
                    'errors': errors or {}
                })
                
        except Exception as e:
            messages.error(request, "Error al procesar la compra. Por favor intente nuevamente.")
            return render(request, 'app/purchase_ticket.html', {
                'event': event
            })
            
    return render(request, 'app/purchase_ticket.html', {'event': event})

@login_required
def view_ticket(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        if ticket_id:
            ticket = get_object_or_404(Ticket, id=ticket_id, event_id=event_id)
            ticket.delete()
            return redirect('view_ticket', event_id=event_id)
    
    tickets = Ticket.objects.filter(event=event)
    return render(request, 'app/view_ticket.html', {'tickets': tickets, 'event': event}) 

@login_required
def edit_ticket(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'app/edit_ticket.html', {'event': event})

