from datetime import datetime
from apps.core.schemas.prayer import PrayerRequestCreateSchema
from apps.tcc.usecase.entities.users import UserEntity
from models.base.enums import PrayerPrivacy, UserRole
import html

class PrayerRequestEntity:
    def __init__(self, prayer_data: PrayerRequestCreateSchema):
        self.title = prayer_data.title
        self.content = prayer_data.content
        self.privacy = prayer_data.privacy
        self.expires_at = prayer_data.expires_at
        self.answer_notes = prayer_data.answer_notes
        self.user_id = prayer_data.user_id
    
    def sanitize_inputs(self):
        """Sanitize prayer content"""
        self.title = html.escape(self.title.strip())
        self.content = html.escape(self.content.strip())
        if self.answer_notes:
            self.answer_notes = html.escape(self.answer_notes.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        # Business rules are now in schema validation
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def can_view(self, user: 'UserEntity') -> bool:
        if not user:
            return False
        
        # User can view their own requests
        if self.user_id == user.id:
            return True
        
        # Public requests can be viewed by anyone
        if self.privacy == PrayerPrivacy.PUBLIC:
            return True
        
        # Congregation requests can be viewed by members
        if self.privacy == PrayerPrivacy.CONGREGATION and user.is_member:
            return True
        
        # Leaders can view all requests
        if self.privacy == PrayerPrivacy.LEADERS_ONLY and user.is_ministry_leader:
            return True
        
        # Staff and super admins can view everything
        if user.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]:
            return True
        
        return False
    
    def __str__(self):
        return f"{self.title} - User {self.user_id}"