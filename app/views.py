import datetime, uuid
from datetime import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from .models import Event, User, Rating, Ticket, Comment, Category, Venue, RefoundRequest, Notification
from .forms import RatingForm 
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from datetime import timedelta
from django.utils import timezone

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
    date_filter = request.GET.get('date')
    category_filter = request.GET.get('category')
    venue_filter = request.GET.get('venue')

    if request.user.is_organizer:
        events = Event.objects.filter(organizer=request.user)
    else:
        events = Event.objects.all()
    
    if date_filter:
        try:
            date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()
            events = events.filter(scheduled_at__date__gte=date_filter)
        except ValueError:
            pass
    
    if category_filter:
        events = events.filter(category_id=category_filter)
    
    if venue_filter:
        events = events.filter(venue_id=venue_filter)
    
    events = events.order_by("scheduled_at")
    
    categories = Category.objects.filter(is_active=True)
    venues = Venue.objects.all().order_by('name')

    return render(
        request,
        "app/events.html",
        {
            "events": events, 
            "user_is_organizer": request.user.is_organizer,
            "selected_date": date_filter if date_filter else '',
            "selected_category": category_filter,
            "selected_venue": venue_filter,
            "categories": categories,
            "venues": venues
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
    user_has_ticket = Ticket.objects.filter(event=event, user=request.user).exists()
    
    return render(
        request,
        'app/event_detail.html',
        {
            'event': event,
            'form': form,
            'ratings': ratings,
            'user_rated': user_rated,
            'editing': editing,
            'user_has_ticket': user_has_ticket,  
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
            datetime(int(year), int(month), int(day), int(hour), int(minutes))
        )

        errors = {}
        
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            errors["category"] = "La categoría seleccionada no existe"
            category = None

        try:
            venue = Venue.objects.get(pk=venue_id)
        except Venue.DoesNotExist:
            errors["venue"] = "La ubicación seleccionada no existe"
            venue = None
            
        if errors:
            venues = Venue.objects.all().order_by('name')
            categorys = Category.objects.filter(is_active=True)
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
                    "venues": venues,
                    "categorys": categorys,
                },
            )
        
        if id is None:
            success, event_errors = Event.new(title, description, scheduled_at, request.user, category, venue)
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
                        "errors": event_errors,
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
        if request.user == event.organizer:
            user_id = request.POST.get('rating_user_id')
            rating = Rating.objects.filter(event=event, user_id=user_id).first()
            if rating:
                rating.delete()
        else:
            Rating.delete_rating(event=event, user=request.user)
    return redirect('event_detail', id=event.pk)
    
@login_required
def purchase_ticket(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if request.user == event.organizer:
        messages.error(request, "Los organizadores no pueden comprar tickets para sus propios eventos")
        return redirect('event_detail', id=event_id)
    
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
    
    if request.user.is_organizer or request.user.is_superuser:
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
def refound_request(request, id=None):
    user = request.user
    errors = {}
    organizer_events = None
    refound_request_single = {}

    if id is not None:
        refound_request_single = get_object_or_404(RefoundRequest, pk=id)

    if request.method == "POST":
        ticket_code = request.POST.get("ticket_code")
        reason = request.POST.get("reason")

        errors = RefoundRequest.validate(ticket_code, reason)

        if errors:
            return render(
                        request,
                        "app/refound/refound_request.html",
                        {
                            "errors": errors,
                        },
                    )

        if ticket_code:
            try:
                ticket_encontrado = Ticket.objects.get(ticket_code=ticket_code)
                user_enconrtado = ticket_encontrado.user
                evento_asociado = ticket_encontrado.event

                # Valido que el reembolso sea dentro de los 30 dias despues de la fecha del evento
                fecha_limite_reembolso = evento_asociado.scheduled_at + timedelta(days=30)
                ahora = timezone.now()
                if ahora > fecha_limite_reembolso:
                    errors["ticket_code"] = "Han pasado más de 30 días desde la fecha del evento. No se puede solicitar un reembolso."
                    return render(
                        request,
                        "app/refound/refound_request.html",
                        {
                            "errors": errors,
                            "refound_request": {"ticket_code": ticket_code, "reason": reason},
                            "user_is_organizer": user.is_organizer,
                            "organizer_events": organizer_events,
                        },
                    )

                success, possible_errors = RefoundRequest.new(ticket_code, reason, user_enconrtado, evento_asociado)

                if possible_errors is not None:
                    errors.update(possible_errors)
                if not success:
                    return render(
                        request,
                        "app/refound/refound_request.html",
                        {
                            "errors": errors,
                            "refound_request": {"ticket_code": ticket_code, "reason": reason},
                            "user_is_organizer": user.is_organizer,
                            "organizer_events": organizer_events,
                        },
                    )
                return redirect("events")

            except Ticket.DoesNotExist:
                errors["ticket_code"] = "El código del ticket no es válido."
        else:
            errors["ticket_code"] = "Por favor, proporciona el código del ticket."

        return render(
            request,
            "app/refound/refound_request.html",
            {
                "errors": errors,
                "refound_request": {"ticket_code": ticket_code, "reason": reason},
                "user_is_organizer": user.is_organizer,
                "organizer_events": organizer_events,
            },
        )

    if user.is_superuser:
        organizer_events = RefoundRequest.objects.all()
    elif user.is_organizer:
        organizer_events = RefoundRequest.objects.filter(event__organizer=user)

    return render(
        request,
        "app/refound/refound_request.html",
        {
            "refound_request": refound_request_single,
            "user_is_organizer": user.is_organizer,
            "user_is_superuser": user.is_superuser,
            "organizer_events": organizer_events,
        },
    )
    

def notifications(request):
    user = request.user
    events_not_found = not Event.objects.exists()

    if not (user.is_organizer or user.is_superuser):
        return redirect("events")

    search_query = request.GET.get("search", "").strip()
    event_filter = request.GET.get("event", "")
    priority_filter = request.GET.get("priority", "")

    notifications = Notification.objects.all().order_by("-created_at")

    if search_query:
        notifications = notifications.filter(title__icontains=search_query)

    if event_filter:
        notifications = notifications.filter(event__id=event_filter)

    if priority_filter:
        notifications = notifications.filter(priority=priority_filter)

    events = Event.objects.all()

    return render(
        request,
        "app/notifications/notifications.html",
        {
            "notifications": notifications,
            "events_not_found": events_not_found,
            "events": events,
        },
    )

@login_required
def refound_delete(request, refound_id):
    user = request.user
    if(user.is_organizer or user.is_superuser):
        return redirect("refounds")

    refound_request = get_object_or_404(RefoundRequest, pk=refound_id)

    if request.method == "POST":
        refound_request.delete()
        return redirect("refounds")
    
    return render(
        request,
        "app/refound/refounds.html",
        {"refounds": refounds}
    )

@login_required
def accept_reject_refound_request(request, refound_id, action):
    user = request.user

    if not (user.is_organizer or user.is_superuser):
        return redirect("refound_request")
    
    refound_request = get_object_or_404(RefoundRequest, pk=refound_id)

    if action == 'approve':
        refound_request.approved = True
        messages.success(request, f"La solicitud de reembolso para el ticket {refound_request.ticket_code} ha sido aprobada.")
    elif action == 'reject':
        refound_request.approved = False
        messages.success(request, f"La solicitud de reembolso para el ticket {refound_request.ticket_code} ha sido rechazada.")
    else:
        messages.error(request, "Acción inválida.")
        return redirect("refound_request")

    refound_request.save()
    return redirect("refound_request")

@login_required
def refounds(request):
    user = request.user
    if user.is_superuser:
        refounds_by_user = RefoundRequest.objects.all()
    elif user.is_organizer:
        refounds_by_user = RefoundRequest.objects.filter(event__organizer=user)
    else:
        refounds_by_user = RefoundRequest.objects.filter(user=user)

    return render(
        request,
        "app/refound/refounds.html",
        {
            "refounds_by_user": refounds_by_user,
            "user_is_organizer": user.is_organizer,
            "user_is_admin": user.is_superuser,
        },
    )

@login_required
def refound_edit(request, id):

    if request.method == "POST":
        reason = request.POST.get("reason")
        refound = get_object_or_404(RefoundRequest, pk=id)
        
        refound.update(reason)
        
        return redirect("refounds")
    
    comment = get_object_or_404(RefoundRequest, pk=id)
    return redirect("refounds")

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
    
@login_required
def events_users(request, id):
    print("Llamando a events_users con ID:", id)
    event = get_object_or_404(Event, pk=id)
    
    tickets = Ticket.objects.filter(event=event)
    users = [{"id": ticket.user.pk, "username": ticket.user.username} for ticket in tickets]

    return JsonResponse({"usuarios": users})

@login_required
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
        
        
@login_required
def user_notifications(request):
    user = request.user
    notifications = Notification.objects.filter(users=user).order_by("-created_at")
    unread_count = notifications.filter(is_read=False).count()
    
    return render(
        request,
        "app/notifications/user_notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )
    
@login_required
def mark_as_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, users=request.user)
    notif.is_read = True
    notif.save()
    
    return redirect('user_notifications')

@login_required
def mark_all_as_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    
    return redirect('user_notifications')