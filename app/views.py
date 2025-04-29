import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Event, User, Venue

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
    return render(request, "app/event_detail.html", {"event": event, "user_is_organizer": request.user.is_organizer})


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
        venue_id = request.POST.get("venue")

        if not venue_id:
            venues = Venue.objects.all().order_by('name')
            errors = {"venue": "Por favor seleccione una ubicación"}
            
            if id is None:
                return render(
                    request,
                    "app/event_form.html",
                    {
                        "event": {
                            "title": title,
                            "description": description,
                            "scheduled_at": f"{date} {time}",
                        }, 
                        "errors": errors,
                        "user_is_organizer": request.user.is_organizer,
                        "venues": venues
                    },
                )
            else:
                event = get_object_or_404(Event, pk=id)
                return render(
                    request,
                    "app/event_form.html",
                    {
                        "event": event, 
                        "errors": errors,
                        "user_is_organizer": request.user.is_organizer,
                        "venues": venues
                    },
                )
            
        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")

        scheduled_at = timezone.make_aware(
            datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        venue = get_object_or_404(Venue, pk=venue_id)
        
        if id is None:
            success, errors = Event.new(title, description, scheduled_at, request.user, venue)
            if not success:
                venues = Venue.objects.all().order_by('name')
                return render(
                    request,
                    "app/event_form.html",
                    {
                        "event": {
                            "title": title,
                            "description": description,
                            "scheduled_at": scheduled_at,
                            "venue": venue,
                        }, 
                        "errors": errors,
                        "user_is_organizer": request.user.is_organizer,
                        "venues": venues
                    },
                )
        else:
            event = get_object_or_404(Event, pk=id)
            event.update(title, description, scheduled_at, request.user, venue)

        return redirect("events")

    event = {}
    if id is not None:
        event = get_object_or_404(Event, pk=id)

    venues = Venue.objects.all().order_by('name')

    return render(
        request,
        "app/event_form.html",
        {
            "event": event, 
            "user_is_organizer": request.user.is_organizer,
            "venues": venues
        },
    )

@login_required
def venues(request):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
    
    venues = Venue.objects.all().order_by('name')
    return render(
        request,
        "app/venues/venues.html",
        {
            "venues": venues,
            "user_is_organizer": request.user.is_organizer or request.user.is_superuser
        },
    )

@login_required
def venue_create(request):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
        
    if request.method == "POST":
        name = request.POST.get("location_name")
        address = request.POST.get("address")
        city = request.POST.get("city")
        capacity = request.POST.get("capacity")
        contact = request.POST.get("contact")
        
        errors = Venue.validate(name, address, city, int(capacity), contact)
        
        if len(errors) > 0:
            return render(
                request,
                "app/venues/add_venues.html",
                {
                    "errors": errors,
                    "data": request.POST,
                    "user_is_organizer": request.user.is_organizer or request.user.is_superuser
                },
            )
        
        Venue.objects.create(
            name=name,
            address=address,
            city=city,
            capacity=int(capacity),
            contact=contact
        )
        
        return redirect("venues")
    
    return render(
        request,
        "app/venues/add_venues.html",
        {"user_is_organizer": request.user.is_organizer or request.user.is_superuser}
    )

@login_required
def venue_delete(request, id):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")

    if request.method == "POST":
        venue = get_object_or_404(Venue, pk=id)
        venue.delete()
        return redirect("venues")

    return redirect("venues")

@login_required
def venue_edit(request, id):
    user = request.user
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
        
    venue = get_object_or_404(Venue, pk=id)
        
    if request.method == "POST":
        name = request.POST.get("location_name")
        address = request.POST.get("address")
        city = request.POST.get("city") 
        capacity = request.POST.get("capacity")
        contact = request.POST.get("contact")
        
        errors = Venue.validate(name, address, city, int(capacity), contact)
        
        if len(errors) > 0:
            return render(
                request,
                "app/venues/edit_venue.html",
                {
                    "errors": errors,
                    "data": request.POST,
                    "venue": venue,
                    "user_is_organizer": request.user.is_organizer or request.user.is_superuser
                },
            )
        
        venue.name = name
        venue.address = address
        venue.city = city
        venue.capacity = capacity
        venue.contact = contact
        venue.save()
        
        return redirect("venues")
    
    return render(
        request,
        "app/venues/edit_venue.html",
        {
            "venue": venue,
            "user_is_organizer": request.user.is_organizer or request.user.is_superuser
        }
    )