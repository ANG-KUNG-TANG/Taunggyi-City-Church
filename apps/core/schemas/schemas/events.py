from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal

from apps.core.schemas.schemas.base import BaseResponseSchema, BaseSchema
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus


class EventBase(BaseSchema):
    """Base event schema with common fields."""
    
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: datetime
    end_date: datetime
    event_type: EventType
    status: EventStatus = EventStatus.UPCOMING
    max_attendees: Optional[int] = None
    cost: Optional[Decimal] = None
    image_url: Optional[str] = None

class EventCreate(EventBase):
    """Schema for creating a new event."""
    
    @field_validator('end_date')
    @classmethod
    def validate_event_duration(cls, v: datetime, info) -> datetime:
        """Validate event duration."""
        data = info.data
        if 'start_date' in data and data['start_date']:
            event_duration = v - data['start_date']
            if event_duration.total_seconds() > 86400:  # 24 hours
                raise ValueError("Event duration cannot exceed 24 hours")
            if event_duration.total_seconds() < 0:
                raise ValueError("End date cannot be before start date")
        return v
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v: datetime) -> datetime:
        """Validate event start date."""
        if v < datetime.now():
            raise ValueError("Event cannot be in the past")
        return v

class EventUpdate(BaseSchema):
    """Schema for updating event information."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[EventType] = None
    status: Optional[EventStatus] = None
    max_attendees: Optional[int] = None
    cost: Optional[Decimal] = None
    image_url: Optional[str] = None

class EventResponse(EventBase, BaseResponseSchema):
    """Schema for event response."""
    
    attendee_count: int = 0
    available_spots: Optional[int] = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
    )

class EventRegistrationCreate(BaseSchema):
    """Schema for event registration."""
    
    event_id: int
    user_id: int
    status: RegistrationStatus = RegistrationStatus.PENDING
    notes: Optional[str] = None

class EventRegistrationResponse(BaseResponseSchema):
    """Schema for event registration response."""
    
    event_id: int
    user_id: int
    status: RegistrationStatus
    notes: Optional[str] = None
    event_title: Optional[str] = None
    user_name: Optional[str] = None