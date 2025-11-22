import html
from datetime import datetime
from decimal import Decimal
from typing import Optional
from apps.core.schemas.schemas.events import EventCreate, EventRegistrationCreate
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus


class EventEntity:
    def __init__(self, event_data: EventCreate = None, **kwargs):
        if event_data:
            self.title = event_data.title
            self.description = event_data.description
            self.location = event_data.location
            self.start_date = event_data.start_date
            self.end_date = event_data.end_date
            self.event_type = event_data.event_type
            self.status = event_data.status
            self.max_attendees = getattr(event_data, 'max_attendees', None)
            self.cost = getattr(event_data, 'cost', None)
            self.image_url = getattr(event_data, 'image_url', None)
        else:
            # For repository conversion
            self.id = kwargs.get('id')
            self.title = kwargs.get('title')
            self.description = kwargs.get('description')
            self.location = kwargs.get('location')
            self.start_date = kwargs.get('start_date')
            self.end_date = kwargs.get('end_date')
            self.event_type = kwargs.get('event_type')
            self.status = kwargs.get('status', EventStatus.UPCOMING)
            self.max_attendees = kwargs.get('max_attendees')
            self.cost = kwargs.get('cost')
            self.image_url = kwargs.get('image_url')
            self.attendee_count = kwargs.get('attendee_count', 0)
            self.created_at = kwargs.get('created_at')
            self.updated_at = kwargs.get('updated_at')
    
    def sanitize_inputs(self):
        """Sanitize event content"""
        self.title = html.escape(self.title.strip())
        if self.description:
            self.description = html.escape(self.description.strip())
        if self.location:
            self.location = html.escape(self.location.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        # Business rules are now in schema validation
    
    @property
    def available_spots(self) -> Optional[int]:
        """Calculate available spots for the event"""
        if self.max_attendees is None:
            return None
        return max(0, self.max_attendees - self.attendee_count)


class EventRegistrationEntity:
    def __init__(self, registration_data: EventRegistrationCreate = None, **kwargs):
        if registration_data:
            self.event_id = registration_data.event_id
            self.user_id = registration_data.user_id
            self.status = registration_data.status
            self.notes = getattr(registration_data, 'notes', None)
        else:
            # For repository conversion
            self.id = kwargs.get('id')
            self.event_id = kwargs.get('event_id')
            self.user_id = kwargs.get('user_id')
            self.status = kwargs.get('status', RegistrationStatus.PENDING)
            self.notes = kwargs.get('notes')
            self.event_title = kwargs.get('event_title')
            self.user_name = kwargs.get('user_name')
            self.created_at = kwargs.get('created_at')
            self.updated_at = kwargs.get('updated_at')
    
    def prepare_for_persistence(self):
        # Additional validation can be added here if needed
        if self.notes:
            self.notes = html.escape(self.notes.strip())