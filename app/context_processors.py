from .models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        notificaciones_no_leidas = Notification.objects.filter(users=request.user, is_read=False).count()
    else:
        notificaciones_no_leidas = 0

    return {"notificaciones_no_leidas": notificaciones_no_leidas}