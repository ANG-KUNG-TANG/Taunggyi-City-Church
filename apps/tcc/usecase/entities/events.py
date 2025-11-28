from typing import Optional
from decimal import Decimal
from apps.core.schemas.input_schemas.events import EventCreateSchema, EventRegistrationCreateSchema
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus
from .base_entity import BaseEntity


class EventEntity(BaseEntity):
    def __init__(self, event_data: EventCreateSchema = None, **kwargs):
        super().__init__(**kwargs)
        
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
    
    def sanitize_inputs(self):
        """Sanitize event content"""
        self.title = self.sanitize_string(self.title)
        self.description = self.sanitize_string(self.description)
        self.location = self.sanitize_string(self.location)
    
    def prepare_for_persistence(self):
        """Prepare entity for database operations"""
        self.sanitize_inputs()
        self.update_timestamps()
    
    @classmethod
    def from_model(cls, model):
        """Create entity from Django model"""
        return cls(
            id=model.id,
            title=model.title,
            description=model.description,
            location=model.location,
            start_date=model.start_date,
            end_date=model.end_date,
            event_type=model.event_type,
            status=model.status,
            max_attendees=model.max_attendees,
            cost=model.cost,
            image_url=model.image_url,
            attendee_count=model.attendee_count,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    @property
    def available_spots(self) -> Optional[int]:
        """Calculate available spots for the event"""
        if self.max_attendees is None:
            return None
        return max(0, self.max_attendees - self.attendee_count)
    
    def is_full(self) -> bool:
        """Check if event is full"""
        if self.max_attendees is None:
            return False
        return self.attendee_count >= self.max_attendees
    
    def can_register(self) -> bool:
        """Check if registration is still open"""
        return (self.status == EventStatus.UPCOMING and 
                not self.is_full())
    
    def validate_for_creation(self) -> list:
        """Validate event for creation"""
        errors = self.validate_required_fields(['title', 'start_date', 'event_type'])
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors.append("End date cannot be before start date")
        
        if self.max_attendees is not None and self.max_attendees < 1:
            errors.append("Max attendees must be at least 1")
        
        if self.cost is not None and self.cost < Decimal('0.00'):
            errors.append("Cost cannot be negative")
        
        return errors
    
    def __str__(self):
        return f"EventEntity(id={self.id}, title='{self.title}', type='{self.event_type}')"


class EventRegistrationEntity(BaseEntity):
    def __init__(self, registration_data: EventRegistrationCreateSchema = None, **kwargs):
        super().__init__(**kwargs)
        
        if registration_data:
            self.event_id = registration_data.event_id
            self.user_id = registration_data.user_id
            self.status = registration_data.status
            self.notes = getattr(registration_data, 'notes', None)
        else:
            # For repository conversion
            self.event_id = kwargs.get('event_id')
            self.user_id = kwargs.get('user_id')
            self.status = kwargs.get('status', RegistrationStatus.PENDING)
            self.notes = kwargs.get('notes')
            self.event_title = kwargs.get('event_title')
            self.user_name = kwargs.get('user_name')
    
    def prepare_for_persistence(self):
        """Prepare entity for database operations"""
        self.notes = self.sanitize_string(self.notes)
        self.update_timestamps()
    
    @classmethod
    def from_model(cls, model):
        """Create entity from Django model"""
        return cls(
            id=model.id,
            event_id=model.event_id,
            user_id=model.user_id,
            status=model.status,
            notes=model.notes,
            event_title=getattr(model, 'event_title', None),
            user_name=getattr(model, 'user_name', None),
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def can_be_cancelled(self) -> bool:
        """Check if registration can be cancelled"""
        return self.status in [RegistrationStatus.PENDING, RegistrationStatus.CONFIRMED]
    
    def validate_for_creation(self) -> list:
        """Validate registration for creation"""
        return self.validate_required_fields(['event_id', 'user_id'])
    
    def __str__(self):
        return f"EventRegistrationEntity(id={self.id}, event_id={self.event_id}, user_id={self.user_id})"