from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator, model_validator
from .base import BaseSchema
from models.base.enums import PrayerCategory, PrayerPrivacy, PrayerStatus


class PrayerRequestBaseSchema(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    privacy: PrayerPrivacy = Field(default=PrayerPrivacy.CONGREGATION)
    category: PrayerCategory = Field(default=PrayerCategory.OTHER)
    status: PrayerStatus = Field(default=PrayerStatus.ACTIVE)
    expires_at: Optional[datetime] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        return v.strip()

    @model_validator(mode='after')
    def validate_expiration(self):
        if self.expires_at and self.expires_at <= datetime.now():
            raise ValueError('Expiration must be in future')
        return self


class PrayerRequestCreateSchema(PrayerRequestBaseSchema):
    user_id: int = Field(...)


class PrayerRequestUpdateSchema(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    privacy: Optional[PrayerPrivacy] = None
    category: Optional[PrayerCategory] = None
    status: Optional[PrayerStatus] = None
    is_answered: Optional[bool] = None
    answer_notes: Optional[str] = None
    expires_at: Optional[datetime] = None


class PrayerRequestResponseSchema(PrayerRequestBaseSchema):
    user_id: int
    is_answered: bool = False
    answered_at: Optional[datetime] = None
    answer_notes: Optional[str] = None


class PrayerResponseBaseSchema(BaseSchema):
    content: str = Field(..., min_length=1)
    is_private: bool = False


class PrayerResponseCreateSchema(PrayerResponseBaseSchema):
    prayer_request_id: int = Field(...)
    user_id: int = Field(...)


class PrayerResponseResponseSchema(PrayerResponseBaseSchema):
    prayer_request_id: int
    user_id: int