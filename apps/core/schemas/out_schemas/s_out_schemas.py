from typing import List, Optional
from datetime import datetime

from .base import BaseResponseSchema
from common.pagination import PaginatedResponse
from apps.tcc.models.base.enums import SermonStatus


class SermonResponseSchema(BaseResponseSchema):
    title: str
    preacher: str
    bible_passage: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    duration_minutes: Optional[int] = None
    sermon_date: datetime
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: SermonStatus

    view_count: int = 0
    like_count: int = 0


class SermonListResponseSchema(PaginatedResponse[SermonResponseSchema]):
    latest_sermon_date: Optional[datetime] = None
    total_views_all_time: int = 0