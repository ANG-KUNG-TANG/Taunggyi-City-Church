from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from .base_entity import BaseEntity


@dataclass
class PrayerRequestEntity(BaseEntity):
    """Entity for prayer requests"""
    title: str = ""
    description: str = ""
    is_public: bool = False
    is_anonymous: bool = False
    status: str = "pending"
    priority: str = "normal"
    category: str = "general"
    requested_by: Optional[int] = None
    assigned_to: Optional[int] = None
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    answered_by: Optional[int] = None
    expiration_date: Optional[datetime] = None
    prayer_count: int = 0
    
    def prepare_for_persistence(self):
        """Prepare entity for database operations"""
        self.update_timestamps()
        self.title = self.sanitize_string(self.title)
        self.description = self.sanitize_string(self.description)
        self.answer = self.sanitize_string(self.answer)
    
    @classmethod
    def from_model(cls, model):
        """Create entity from Django model"""
        return cls(
            id=model.id,
            title=model.title,
            description=model.description,
            is_public=model.is_public,
            is_anonymous=model.is_anonymous,
            status=model.status,
            priority=model.priority,
            category=model.category,
            requested_by=model.requested_by_id,
            assigned_to=model.assigned_to_id,
            answer=model.answer,
            answered_at=model.answered_at,
            answered_by=model.answered_by_id,
            expiration_date=model.expiration_date,
            prayer_count=model.prayer_count,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


@dataclass
class PrayerResponseEntity(BaseEntity):
    """Entity for prayer responses"""
    prayer_request_id: int
    responded_by: int
    response: str = ""
    is_public: bool = False
    
    def prepare_for_persistence(self):
        """Prepare entity for database operations"""
        self.update_timestamps()
        self.response = self.sanitize_string(self.response)
    
    @classmethod
    def from_model(cls, model):
        """Create entity from Django model"""
        return cls(
            id=model.id,
            prayer_request_id=model.prayer_request_id,
            responded_by=model.responded_by_id,
            response=model.response,
            is_public=model.is_public,
            created_at=model.created_at,
            updated_at=model.updated_at
        )