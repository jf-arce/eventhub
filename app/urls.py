from django.contrib.auth.views import LogoutView
from django.urls import path
from .models import Event, User, Venue

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", views.login_view, name="login"),
    path("events/", views.events, name="events"),
    path("events/create/", views.event_form, name="event_form"),
    path("events/<int:id>/edit/", views.event_form, name="event_edit"),
    path("events/<int:id>/", views.event_detail, name="event_detail"),
    path("events/<int:id>/delete/", views.event_delete, name="event_delete"),
    path("venues/", views.venues, name="venues"),
    path("venues/create/", views.venue_create, name="venue_create"),
    path("venues/<int:id>/delete/", views.venue_delete, name="venue_delete"),
    path("venues/<int:id>/edit/", views.venue_edit, name="venue_edit"),
]
