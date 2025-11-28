from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from .base import BaseResponseSchema
from common.pagination import PaginatedResponse
from apps.tcc.models.base.enums import EventStatus, EventType, RegistrationStatus


class EventResponseSchema(BaseResponseSchema):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: datetime
    end_date: datetime
    event_type: EventType
    status: EventStatus
    max_attendees: Optional[int] = None
    cost: Optional[str] = None  # Decimal → str
    image_url: Optional[str] = None

    attendee_count: int = 0
    available_spots: Optional[int] = None


class EventListResponseSchema(PaginatedResponse[EventResponseSchema]):
    upcoming_count: int = 0
    todays_events: int = 0


class EventRegistrationResponseSchema(BaseResponseSchema):
    event_id: int
    user_id: int
    user_name: Optional[str] = None
    event_title: Optional[str] = None
    status: RegistrationStatus
    notes: Optional[str] = None


class EventRegistrationListResponseSchema(PaginatedResponse[EventRegistrationResponseSchema]):
    pending_count: int = 0
    confirmed_count: int = 0