from django.conf import settings
from apps.tcc.models.base.base import BaseModel
from django.db import models
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus

class Event(BaseModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.SERVICE
    )
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.TextField(blank=True)
    
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='EventRegistration',
        through_fields=('event', 'user'),
        related_name='events_attended',
        blank=True
    )
    
    class Meta:
        db_table = "events"
    
    def __str__(self):
        return self.title


class EventRegistration(BaseModel):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_registrations'
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_events'
    )
    status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.REGISTERED
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = "event_registrations"
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.user} - {self.event}"