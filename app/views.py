import datetime, uuid
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from .models import Event, User, Rating, Ticket, Comment
from .forms import RatingForm 

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
