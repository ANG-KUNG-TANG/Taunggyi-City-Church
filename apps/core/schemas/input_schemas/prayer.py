from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from typing import List, Optional

from apps.core.schemas.input_schemas.base import BaseResponseSchema, BaseSchema
from apps.tcc.models.base.enums import PrayerPrivacy

class PrayerRequestBase(BaseSchema):
    """Base prayer request schema with common fields."""
    
    title: str
    content: str
    privacy: PrayerPrivacy = PrayerPrivacy.CONGREGATION
    expires_at: Optional[datetime] = None
    answer_notes: Optional[str] = None

class PrayerRequestCreate(PrayerRequestBase):
    """Schema for creating a new prayer request."""
    
    user_id: int
    
    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Validate prayer request content length."""
        if len(v) > 10000:
            raise ValueError("Prayer request too long")
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expiration(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate prayer request expiration date."""
        if v:
            from datetime import timedelta
            max_expiry = datetime.now() + timedelta(days=365)  # 1 year max
            if v > max_expiry:
                raise ValueError("Prayer request expiration too far in future")
        return v

class PrayerRequestUpdate(BaseSchema):
    """Schema for updating prayer request information."""
    
    title: Optional[str] = None
    content: Optional[str] = None
    privacy: Optional[PrayerPrivacy] = None
    expires_at: Optional[datetime] = None
    answer_notes: Optional[str] = None
    is_answered: Optional[bool] = None

class PrayerRequestResponseSchema(PrayerRequestBase, BaseResponseSchema):
    """Schema for prayer request response."""
    
    user_id: int
    is_answered: bool = False
    is_expired: bool = False
    prayer_count: int = 0
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )

class PrayerRequestListResponseSchema(BaseSchema):
    """Schema for listing multiple prayer requests with pagination support."""
    
    prayer_requests: List[PrayerRequestResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int