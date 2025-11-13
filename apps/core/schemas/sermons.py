from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from .base import BaseSchema
from models.base.enums import SermonStatus


class SermonBaseSchema(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    preacher: str = Field(..., min_length=1, max_length=120)
    bible_passage: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    sermon_date: datetime = Field(...)
    status: SermonStatus = Field(default=SermonStatus.DRAFT)
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        return v.strip()


class SermonCreateSchema(SermonBaseSchema):
    pass


class SermonUpdateSchema(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    preacher: Optional[str] = Field(None, min_length=1, max_length=120)
    bible_passage: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    content: Optional[str] = None
    sermon_date: Optional[datetime] = None
    status: Optional[SermonStatus] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)


class SermonResponseSchema(SermonBaseSchema):
    pass