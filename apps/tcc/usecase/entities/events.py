from schemas.events import EventCreateSchema, EventRegistrationCreateSchema
import html
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from models.base.enums import EventStatus, EventType, RegistrationStatus


class EventEntity(EventCreateSchema):
    def sanitize_inputs(self):
        """Sanitize event content"""
        self.title = html.escape(self.title.strip())
        if self.description:
            self.description = html.escape(self.description.strip())
        if self.location:
            self.location = html.escape(self.location.strip())
    
    def validate_business_rules(self):
        """Event-specific business rules"""
        # Event cannot be in the past
        if self.start_date < datetime.now():
            raise ValueError("Event cannot be in the past")
        
        # Event duration cannot exceed 24 hours
        event_duration = self.end_date - self.start_date
        if event_duration.total_seconds() > 86400:  # 24 hours
            raise ValueError("Event duration cannot exceed 24 hours")
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        self.validate_business_rules()


class EventRegistrationEntity(EventRegistrationCreateSchema):
    def validate_business_rules(self):
        """Registration-specific business rules"""
        # Additional validation can be added here
        pass
    
    def prepare_for_persistence(self):
        self.validate_business_rules()