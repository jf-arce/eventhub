
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from app.models import Event


class EventModelTest(TestCase):
    
    def test_event_is_future_is_scheduled_today_but_later(self):

        future_time = timezone.now() + timedelta(hours=1)
        event = Event(scheduled_at=future_time)
        assert event.is_future() is True
