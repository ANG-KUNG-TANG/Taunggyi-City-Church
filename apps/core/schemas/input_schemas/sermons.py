from pydantic import BaseModel, field_validator, ConfigDict, Field
from datetime import datetime
from typing import List, Optional
import re

from apps.core.schemas.input_schemas.base import BaseResponseSchema, BaseSchema
from apps.tcc.models.base.enums import SermonStatus

class SermonBaseSchema(BaseSchema):
    """Base sermon schema with common fields."""
    
    title: str = Field(..., min_length=1, max_length=200)
    preacher: str = Field(..., min_length=1, max_length=120)
    bible_passage: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    sermon_date: datetime
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: SermonStatus = Field(default=SermonStatus.DRAFT)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        return v.strip()
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Validate sermon duration."""
        if v and v > 480:  # 8 hours max
            raise ValueError("Sermon duration too long")
        return v
    
    @field_validator('bible_passage')
    @classmethod
    def validate_bible_reference(cls, v: Optional[str]) -> Optional[str]:
        """Validate bible reference format."""
        if v and not cls.is_valid_bible_reference(v):
            raise ValueError("Invalid bible reference format")
        return v
    
    @staticmethod
    def is_valid_bible_reference(reference: str) -> bool:
        """Basic bible reference validation."""
        pattern = r'^[1-9]?[A-Za-z]+\s+\d+:\d+(-\d+)?(\s*[A-Za-z]+)?$'
        return bool(re.match(pattern, reference.strip()))

class SermonCreateSchema(SermonBaseSchema):
    """Schema for creating a new sermon."""
    pass

class SermonUpdateSchema(BaseSchema):
    """Schema for updating sermon information."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    preacher: Optional[str] = Field(None, min_length=1, max_length=120)
    bible_passage: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    sermon_date: Optional[datetime] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[SermonStatus] = None

class SermonResponseSchema(SermonBaseSchema, BaseResponseSchema):
    """Schema for sermon response."""
    
    view_count: int = 0
    like_count: int = 0
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )
    
    
class SermonListResponseSchema(BaseSchema):
    """Schema for listing multiple sermons with pagination support."""

    sermons: List[SermonResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int