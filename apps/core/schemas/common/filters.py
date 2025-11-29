from pydantic import field_validator
from datetime import date
from typing import Optional
from enum import Enum
from apps.core.schemas.input_schemas.base import BaseSchema

class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"

class DateRangeFilter(BaseSchema):
    """Date range filter."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    @field_validator('date_to')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info) -> Optional[date]:
        """Validate date range."""
        data = info.data
        if v and 'date_from' in data and data['date_from'] and v < data['date_from']:
            raise ValueError("Date to cannot be before date from")
        return v

class BaseFilterParams(BaseSchema):
    """Base filter parameters with common fields."""
    
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.DESC
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[str] = None
    
    @field_validator('date_to')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info) -> Optional[date]:
        """Validate date range."""
        data = info.data
        if v and 'date_from' in data and data['date_from'] and v < data['date_from']:
            raise ValueError("Date to cannot be before date from")
        return v
    
    @property
    def has_search(self) -> bool:
        return bool(self.search and self.search.strip())
    
    @property
    def has_date_filter(self) -> bool:
        return bool(self.date_from or self.date_to)

class UserFilterParams(BaseFilterParams):
    """User-specific filter parameters."""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None

class SermonFilterParams(BaseFilterParams):
    """Sermon-specific filter parameters."""
    preacher: Optional[str] = None
    bible_passage: Optional[str] = None
    series: Optional[str] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None

class PrayerFilterParams(BaseFilterParams):
    """Prayer-specific filter parameters."""
    privacy: Optional[str] = None
    is_answered: Optional[bool] = None
    user_id: Optional[int] = None
    category: Optional[str] = None

class EventFilterParams(BaseFilterParams):
    """Event-specific filter parameters."""
    event_type: Optional[str] = None
    location: Optional[str] = None
    is_recurring: Optional[bool] = None

class DonationFilterParams(BaseFilterParams):
    """Donation-specific filter parameters."""
    payment_method: Optional[str] = None
    is_recurring: Optional[bool] = None
    fund_type_id: Optional[int] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None