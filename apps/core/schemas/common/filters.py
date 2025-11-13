from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import Optional
from enum import Enum

class SortOrder(str, Enum):
    """Sort order enumeration."""
    
    ASC = "asc"
    DESC = "desc"

class FilterParams(BaseModel):
    """Base filter parameters schema."""
    
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

class UserFilters(FilterParams):
    """User-specific filter parameters."""
    
    role: Optional[str] = None
    status: Optional[str] = None

class SermonFilters(FilterParams):
    """Sermon-specific filter parameters."""
    
    preacher: Optional[str] = None
    bible_passage: Optional[str] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None

class PrayerFilters(FilterParams):
    """Prayer-specific filter parameters."""
    
    privacy: Optional[str] = None
    is_answered: Optional[bool] = None
    user_id: Optional[int] = None

class EventFilters(FilterParams):
    """Event-specific filter parameters."""
    
    event_type: Optional[str] = None
    location: Optional[str] = None

class DonationFilters(FilterParams):
    """Donation-specific filter parameters."""
    
    payment_method: Optional[str] = None
    is_recurring: Optional[bool] = None
    fund_type_id: Optional[int] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None