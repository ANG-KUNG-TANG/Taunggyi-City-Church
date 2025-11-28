from typing import List, Optional
from datetime import datetime

from .base import BaseResponseSchema
from common.pagination import PaginatedResponse
from apps.tcc.models.base.enums import PrayerPrivacy


class PrayerRequestResponseSchema(BaseResponseSchema):
    user_id: int
    user_name: Optional[str] = None

    title: str
    content: str
    privacy: PrayerPrivacy
    expires_at: Optional[datetime] = None
    answer_notes: Optional[str] = None

    is_answered: bool = False
    is_expired: bool = False
    prayer_count: int = 0


class PrayerRequestListResponseSchema(PaginatedResponse[PrayerRequestResponseSchema]):
    active_count: int = 0
    answered_this_week: int = 0