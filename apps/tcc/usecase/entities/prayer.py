from datetime import datetime
from apps.core.schemas.schemas.prayer import PrayerRequestCreate
from apps.tcc.usecase.entities.users import UserEntity
from apps.tcc.models.base.enums import PrayerPrivacy, UserRole
import html


class PrayerRequestEntity:
    def __init__(self, prayer_data: PrayerRequestCreate = None, **kwargs):
        if prayer_data:
            self.title = prayer_data.title
            self.content = prayer_data.content
            self.privacy = prayer_data.privacy
            self.expires_at = prayer_data.expires_at
            self.answer_notes = prayer_data.answer_notes
            self.user_id = prayer_data.user_id
        else:
            # For repository conversion
            self.id = kwargs.get('id')
            self.user_id = kwargs.get('user_id')
            self.title = kwargs.get('title')
            self.content = kwargs.get('content')
            self.privacy = kwargs.get('privacy', PrayerPrivacy.CONGREGATION)
            self.expires_at = kwargs.get('expires_at')
            self.answer_notes = kwargs.get('answer_notes')
            self.is_answered = kwargs.get('is_answered', False)
            self.prayer_count = kwargs.get('prayer_count', 0)
            self.created_at = kwargs.get('created_at')
            self.updated_at = kwargs.get('updated_at')
    
    def sanitize_inputs(self):
        """Sanitize prayer content"""
        if hasattr(self, 'title'):
            self.title = html.escape(self.title.strip())
        if hasattr(self, 'content'):
            self.content = html.escape(self.content.strip())
        if hasattr(self, 'answer_notes') and self.answer_notes:
            self.answer_notes = html.escape(self.answer_notes.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def can_view(self, user: UserEntity) -> bool:
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