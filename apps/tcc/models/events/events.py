# events.py
from django.db import models
from django.utils import timezone
from apps.tcc.models.base.base import BaseModel
from apps.tcc.models.base.enums import EventType, EventStatus, RegistrationStatus, UserRole
from apps.tcc.models.base.permission import RoleBasedPermissionsMixin

class Event(BaseModel, RoleBasedPermissionsMixin):
    title = models.CharField(max_length=200, help_text="Event title")
    description = models.TextField(blank=True, help_text="Event details")
    start_date_time = models.DateTimeField(help_text="When the event starts")
    end_date_time = models.DateTimeField(help_text="When the event ends")
    location = models.CharField(max_length=200, help_text="Event venue")
    
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.SERVICE)
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.DRAFT)
    
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='events/', null=True, blank=True)
    
    # Many-to-many relationship for attendees
    attendees = models.ManyToManyField('User', through='EventRegistration', related_name='registered_events', blank=True)
    
    class Meta:
        db_table = "events"
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ['-start_date_time']
    
    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()})"
    
    # Permission methods
    def can_create(self, user):
        """Only staff and ministry leaders can create events"""
        return user.can_manage_events
    
    def can_view(self, user):
        """Anyone can view published events, draft events only by creators or admins"""
        if self.status == EventStatus.PUBLISHED:
            return True
        return user.is_authenticated and (self.created_by == user or user.can_manage_events)
    
    def can_edit(self, user):
        """Only creator, staff, or ministry leaders can edit"""
        if not user.is_authenticated:
            return False
        return self.created_by == user or user.can_manage_events
    
    def can_delete(self, user):
        """Only creator, staff, or super admin can delete"""
        if not user.is_authenticated:
            return False
        return self.created_by == user or user.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def is_upcoming(self):
        return self.start_date_time > timezone.now()
    
    @property
    def attendee_count(self):
        return self.registrations.filter(status=RegistrationStatus.REGISTERED).count()

class EventRegistration(BaseModel, RoleBasedPermissionsMixin):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='event_registrations')
    
    status = models.CharField(max_length=20, choices=RegistrationStatus.choices, default=RegistrationStatus.REGISTERED)
    registered_at = models.DateTimeField(default=timezone.now)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = "event_registrations"
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.user.name} - {self.event.title}"
    
    # Permission methods
    def can_create(self, user):
        """Users can register themselves for events"""
        return user.can_join_events and user.is_authenticated
    
    def can_view(self, user):
        """User can view their own registration, event creators and admins can view all"""
        if not user.is_authenticated:
            return False
        return self.user == user or self.event.created_by == user or user.can_manage_events
    
    def can_edit(self, user):
        """Only admins and event creators can edit registrations"""
        if not user.is_authenticated:
            return False
        return self.event.created_by == user or user.can_manage_events
    
    def can_delete(self, user):
        """Users can delete their own registration, admins can delete any"""
        if not user.is_authenticated:
            return False
        return self.user == user or user.can_manage_events