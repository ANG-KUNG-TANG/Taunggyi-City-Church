import html
from datetime import datetime

from apps.core.schemas.schemas.events import EventCreate, EventRegistrationCreate


class EventEntity:
    def __init__(self, event_data: EventCreate):
        self.title = event_data.title
        self.description = event_data.description
        self.location = event_data.location
        self.start_date = event_data.start_date
        self.end_date = event_data.end_date
        self.event_type = event_data.event_type
        self.status = event_data.status
    
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

class EventRegistrationEntity:
    def __init__(self, registration_data: EventRegistrationCreate):
        self.event_id = registration_data.event_id
        self.user_id = registration_data.user_id
        self.status = registration_data.status
    
    def prepare_for_persistence(self):
        # Additional validation can be added here if needed
        pass