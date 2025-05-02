from django.contrib import admin
from app.models import User, Event, Notification

class AuthorAdmin(admin.ModelAdmin):
    pass

admin.site.register(User, AuthorAdmin)
admin.site.register(Event, AuthorAdmin)
admin.site.register(Notification, AuthorAdmin)