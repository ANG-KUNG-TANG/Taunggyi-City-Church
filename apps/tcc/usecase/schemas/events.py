from datetime import datetime
from typing import Optional
from pydantic import Field, model_validator
from .base import BaseSchema
from models.base.enums import EventStatus, EventType, RegistrationStatus


class EventBaseSchema(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: EventType = Field(default=EventType.SERVICE)
    status: EventStatus = Field(default=EventStatus.DRAFT)
    start_date: datetime = Field(...)
    end_date: datetime = Field(...)
    location: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self):
        if self.start_date >= self.end_date:
            raise ValueError('End date must be after start date')
        return self


class EventCreateSchema(EventBaseSchema):
    pass


class EventUpdateSchema(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    status: Optional[EventStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None


class EventResponseSchema(EventBaseSchema):
    pass


class EventRegistrationBaseSchema(BaseSchema):
    status: RegistrationStatus = Field(default=RegistrationStatus.REGISTERED)
    notes: Optional[str] = None


class EventRegistrationCreateSchema(EventRegistrationBaseSchema):
    event_id: int = Field(...)
    user_id: int = Field(...)
    registered_by_id: Optional[int] = None


class EventRegistrationResponseSchema(EventRegistrationBaseSchema):
    event_id: int
    user_id: int
    registered_by_id: Optional[int] = None
    registered_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None