from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import Q
from repo.base.base_repo import ModelRepository
from apps.tcc.models.events.events import Event, EventRegistration
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus
from models.base.permission import PermissionDenied
from utils.audit_logging import AuditLogger


class EventRepository(ModelRepository[Event]):
    
    def __init__(self):
        super().__init__(Event)
    
    def get_upcoming_events(self, user, limit: int = None) -> List[Event]:
        """Get upcoming events"""
        now = timezone.now()
        queryset = Event.objects.filter(
            is_active=True,
            status=EventStatus.PUBLISHED,
            start_date_time__gt=now
        ).order_by('start_date_time')
        
        if limit:
            queryset = queryset[:limit]
        
        # Apply permission filtering
        events = []
        for event in queryset:
            try:
                if event.can_view(user):
                    events.append(event)
            except PermissionDenied:
                continue
        
        return events
    
    def get_events_by_type(self, event_type: EventType, user) -> List[Event]:
        """Get events by type"""
        queryset = Event.objects.filter(
            is_active=True,
            status=EventStatus.PUBLISHED,
            event_type=event_type
        ).order_by('-start_date_time')
        
        events = []
        for event in queryset:
            try:
                if event.can_view(user):
                    events.append(event)
            except PermissionDenied:
                continue
        
        return events
    
    def get_user_events(self, user) -> List[Event]:
        """Get events created by user"""
        if not user.can_manage_events:
            raise PermissionDenied("You don't have permission to view these events")
        
        return Event.objects.filter(
            is_active=True,
            created_by=user
        ).order_by('-start_date_time')
    
    def register_for_event(self, event_id: int, user, request=None) -> Optional[EventRegistration]:
        """Register user for an event"""
        event = self.get_by_id(event_id, user)
        if not event:
            return None
        
        # Check if user can join events
        if not user.can_join_events:
            raise PermissionDenied("You don't have permission to join events")
        
        # Check if event is full
        if event.max_attendees and event.attendee_count >= event.max_attendees:
            raise ValueError("Event is full")
        
        # Check if already registered
        existing_registration = EventRegistration.objects.filter(
            event=event,
            user=user,
            is_active=True
        ).first()
        
        if existing_registration:
            raise ValueError("You are already registered for this event")
        
        # Create registration
        registration_data = {
            'event': event,
            'user': user,
            'status': RegistrationStatus.REGISTERED,
            'registered_at': timezone.now()
        }
        
        registration = EventRegistration(**registration_data)
        
        # Get audit context
        context, ip_address, user_agent = self._get_audit_context(request)
        
        registration.save()
        AuditLogger.log_create(
            user, registration, ip_address, user_agent,
            notes=f"Registered for event: {event.title}"
        )
        
        return registration
    
    def cancel_registration(self, event_id: int, user, request=None) -> bool:
        """Cancel event registration"""
        event = self.get_by_id(event_id, user)
        if not event:
            return False
        
        registration = EventRegistration.objects.filter(
            event=event,
            user=user,
            is_active=True
        ).first()
        
        if not registration:
            return False
        
        # Get audit context
        context, ip_address, user_agent = self._get_audit_context(request)
        
        registration.soft_delete(user=user)
        AuditLogger.log_delete(
            user, registration, ip_address, user_agent,
            notes=f"Cancelled registration for event: {event.title}"
        )
        
        return True
    
    def get_event_attendees(self, event_id: int, user) -> List[EventRegistration]:
        """Get event attendees - only event creators and admins can see"""
        event = self.get_by_id(event_id, user)
        if not event:
            return []
        
        # Check permission
        if event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only view attendees for your own events")
        
        return EventRegistration.objects.filter(
            event=event,
            is_active=True,
            status=RegistrationStatus.REGISTERED
        ).select_related('user')

class EventRegistrationRepository(ModelRepository[EventRegistration]):
    
    def __init__(self):
        super().__init__(EventRegistration)
    
    def get_user_registrations(self, user) -> List[EventRegistration]:
        """Get all event registrations for a user"""
        return EventRegistration.objects.filter(
            user=user,
            is_active=True
        ).select_related('event').order_by('-registered_at')
    
    def check_in_attendee(self, registration_id: int, user, request=None) -> Optional[EventRegistration]:
        """Check in attendee - only event creators and admins can do this"""
        registration = self.get_by_id(registration_id, user)
        if not registration:
            return None
        
        # Check permission
        if registration.event.created_by != user and not user.can_manage_events:
            raise PermissionDenied("You can only check in attendees for your own events")
        
        registration.checked_in = True
        registration.checked_in_at = timezone.now()
        
        context, ip_address, user_agent = self._get_audit_context(request)
        registration.save()
        
        AuditLogger.log_update(
            user, registration, 
            {'checked_in': {'old': False, 'new': True}},
            ip_address, user_agent,
            notes=f"Checked in attendee: {registration.user.name}"
        )
        
        return registration