import datetime, uuid
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from .models import Event, User, Rating, Ticket, Comment, Category, Venue, Notification
from .forms import RatingForm 
from django.db.models import Count
from django.db.models.deletion import ProtectedError

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
    event = get_object_or_404(Event, id=id)
    ratings = Rating.objects.filter(event=event)
    user_rating = Rating.objects.filter(event=event, user=request.user).first()
    comments = Comment.objects.all().filter(event=event).order_by("created_at")
    
    user_rated = user_rating is not None
    editing = False
    form = RatingForm()
    
    return render(
        request,
        'app/event_detail.html',
        {
            'event': event,
            'form': form,
            'ratings': ratings,
            'user_rated': user_rated,
            'editing': editing,
            "comments": comments,
            "user_is_organizer": request.user.is_organizer,
            "user_is_admin": request.user.is_superuser,
        }
    )

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
        venue_id = request.POST.get("venue")

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

        category = get_object_or_404(Category, pk=category_id)
        venue = get_object_or_404(Venue, pk=venue_id)
        
        if id is None:
            success, errors = Event.new(title, description, scheduled_at, request.user, category, venue)
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
                        "venues": venues,
                        "categorys": Category.objects.filter(is_active=True),
                    },
                )
        else:
            event = get_object_or_404(Event, pk=id)
            event.update(title, description, scheduled_at, request.user, venue)

        return redirect("events")

    event = {}
    if id is not None:
        event = get_object_or_404(Event, pk=id)

    categorys = Category.objects.filter(is_active=True)
    venues = Venue.objects.all().order_by('name')

    return render(
        request,
        "app/event_form.html",
        {
            "event": event,
            "user_is_organizer": request.user.is_organizer,
            "categorys": categorys,
            "error": error,
            "venues": venues
        },
    )

@login_required
def add_rating(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            success, result = Rating.create_rating(
                event=event,
                user=request.user,
                title=form.cleaned_data['title'],
                text=form.cleaned_data['text'],
                rating=form.cleaned_data['rating'],
            )
            if success:
                return redirect('event_detail', id=event.pk)
            else:
                form.add_error(None, str(result))
    return redirect('event_detail', id=event.pk)

@login_required
def edit_rating(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_rating = Rating.objects.filter(event=event, user=request.user).first()
    form = RatingForm(instance=user_rating)
    ratings = Rating.objects.filter(event=event)
    return render(
        request,
        'app/event_detail.html',
        {
            'event': event,
            'form': form,
            'ratings': ratings,
            'user_rated': True,
            'editing': True,
        }
    )
    
@login_required
def update_rating(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_rating = Rating.objects.filter(event=event, user=request.user).first()
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=user_rating)
        if form.is_valid():
            success, result = Rating.update_rating(
                event=event,
                user=request.user,
                title=form.cleaned_data['title'],
                text=form.cleaned_data['text'],
                rating=form.cleaned_data['rating'],
            )
            if success:
                return redirect('event_detail', id=event.pk)
            else:
                form.add_error(None, str(result))
    return redirect('event_detail', id=event.pk)

@login_required
def delete_rating(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        # Si es el organizador, puede borrar cualquier reseña de su evento
        if request.user == event.organizer:
            user_id = request.POST.get('rating_user_id')
            rating = Rating.objects.filter(event=event, user_id=user_id).first()
            if rating:
                rating.delete()
        else:
            # Si no es organizador, solo puede borrar su propia reseña
            Rating.delete_rating(event=event, user=request.user)
    return redirect('event_detail', id=event.pk)
    
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
            if request.user.is_organizer:
                ticket = get_object_or_404(Ticket, id=ticket_id, event_id=event_id)
            else:
                ticket = get_object_or_404(Ticket, id=ticket_id, event_id=event_id, user=request.user)
            ticket.delete()
            return redirect('view_ticket', event_id=event_id)
    
    if request.user.is_organizer:
        tickets = Ticket.objects.filter(event=event)
    else:
        tickets = Ticket.objects.filter(event=event, user=request.user)
    
    return render(request, 'app/view_ticket.html', {
        'tickets': tickets, 
        'event': event,
        'user_is_organizer': request.user.is_organizer
    })

from django.shortcuts import render, get_object_or_404, redirect
from .models import Event, Ticket

def edit_ticket(request, event_id, ticket_id):
    event = get_object_or_404(Event, id=event_id)
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if not (request.user == ticket.user or request.user == event.organizer):
        return redirect('events')
    
    if request.method == 'POST':
        ticket_type = request.POST.get('ticket_type')
        quantity = request.POST.get('quantity')
        
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError("La cantidad debe ser mayor a 0")
                
            ticket.type = ticket_type
            ticket.quantity = quantity
            ticket.save()
            return redirect('view_ticket', event_id=event_id)
            
        except ValueError:
            pass
    
    return render(request, 'app/edit_ticket.html', {
        'event': event,
        'ticket': ticket
    })

def comments(request):
    comments = Comment.objects.all().order_by("created_at")
    return render(
        request,
        "app/comments/comments.html",
        {
            "comments": comments, 
        },
    )
    
@login_required
def comment_delete(request, id):
    user = request.user
    if not (user.is_organizer or user.is_superuser):
        return redirect("comments")

    if request.method == "POST":
        comment = get_object_or_404(Comment, pk=id)
        comment.delete()
        return redirect("comments")

    return redirect("comments")

@login_required
def add_comment(request, event_id):
    user= request.user
    
    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text")
        event = get_object_or_404(Event, pk=event_id)
        
        print(title, text, event)
        
        success, errors = Comment.new(title, text, user, event)

        if not success:
            return render(
                request,
                "app/event_detail.html",
                {
                    "event": event,
                    "comments": Comment.objects.all().filter(event=event).order_by("created_at"),
                    "errors": errors,
                    "form_data": {"title": title, "text": text},
                },
            )
        
        return redirect("event_detail", event_id) 
    
    return redirect("event_detail", event_id)

@login_required
def comment_update(request, id):

    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text")
        comment = get_object_or_404(Comment, pk=id)
        
        comment.update(title, text)
        
        return redirect("event_detail", comment.event.pk)
    
    comment = get_object_or_404(Comment, pk=id)
    return redirect("event_detail", comment.event.pk)

@login_required
def event_comment_delete(request, id):
    comment = get_object_or_404(Comment, pk=id)

    if request.method == "POST":
        comment = get_object_or_404(Comment, pk=id)
        comment.delete()
        return redirect("event_detail", comment.event.pk)

    return redirect("event_detail", comment.event.pk)

@login_required
def categorys(request):
    categorys = Category.objects.annotate(num_events=Count('category_event'))

    return render(
        request,
        "app/categorys/categorys.html",
        {
            "categorys": categorys,
            "user_is_organizer": request.user.is_organizer,
        },
    )

@login_required
def category_form(request, id=None):
    print("Llamando a category_form con ID:", id)
    user = request.user

    if not (user.is_organizer or user.is_superuser):
        return redirect("categorys")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")

        if id is None:
            Category.new(name, description)
        else:
            category = get_object_or_404(Category, pk=id)
            category.update(name, description)

        return redirect("categorys")

    category = {}
    if id is not None:
        category = get_object_or_404(Category, pk=id)

    return render(
        request,
        "app/categorys/category_form.html",
        {"category": category, 
        "user_is_organizer": request.user.is_organizer},
    )

@login_required
def category_delete(request, category_id):
    user = request.user
    if not (user.is_organizer or user.is_superuser):
        return redirect("categorys")

    category = get_object_or_404(Category, pk=category_id)

    if request.method == "POST":
        category.delete()
        return redirect("categorys")

    return render(
        request,
        "app/categorys/category_confirm_delete.html",
        {"category": category},
    )

@login_required
def category_detail(request, id):
    category = get_object_or_404(Category, pk=id)
    return render(request, "app/categorys/category_detail.html", {"category": category})
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
        try:
            venue.delete()
            messages.success(request, "Ubicación eliminada exitosamente")
        except ProtectedError:
            related_events = Event.objects.filter(venue=venue)
            event_names = ", ".join([event.title for event in related_events])
            
            error_message = f"No se puede eliminar esta ubicación porque está siendo utilizada por los siguientes eventos: {event_names}"
            messages.error(request, error_message)
        
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

@login_required
def notifications(request):
    user = request.user
    events_not_found = False
    
    if not (user.is_organizer or user.is_superuser):
        return redirect("events")
    
    notifications = Notification.objects.all().order_by("-created_at")
    
    events = Event.objects.all()
    if len(notifications) == 0:
        events_not_found = True
        
    return render(
        request,
        "app/notifications/notifications.html",
        {
            "notifications": notifications,
            "events_not_found": events_not_found,
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
    
    if not Event.objects.exists():
        messages.error(request, "No hay eventos disponibles para enviar notificaciones.")
        return redirect("notifications")

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")
        priority = request.POST.get("priority")
        event_id = request.POST.get("event")
        destination = request.POST.get("destination")
        
        Notification.validate(title, message, priority)

        event = get_object_or_404(Event, pk=event_id)
        
        if destination == "all":
            # Obtener todos los usuarios con tickets para el evento
            tickets = Ticket.objects.filter(event=event)
            users = [ticket.user for ticket in tickets]

            notification = Notification.objects.create(
                title=title,
                message=message,
                priority=priority,
                event=event,
            )
            notification.users.set(users)
            

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
    
def events_users(request, id):
    print("Llamando a events_users con ID:", id)
    event = get_object_or_404(Event, pk=id)
    
    tickets = Ticket.objects.filter(event=event)
    users = [{"id": ticket.user.pk, "username": ticket.user.username} for ticket in tickets]

    return JsonResponse({"usuarios": users})
    
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
        
    
    