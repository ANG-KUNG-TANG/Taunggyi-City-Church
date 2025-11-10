from datetime import datetime
from apps.tcc.models.base.enums import PrayerPrivacy, UserRole
from apps.tcc.usecase.entities.users import UserEntity
from schemas.prayer import PrayerRequestCreateSchema
import html


class PrayerRequestEntity(PrayerRequestCreateSchema):
    """Prayer request entity with security"""
    
    def sanitize_inputs(self):
        """Sanitize prayer content"""
        self.title = html.escape(self.title.strip())
        self.content = html.escape(self.content.strip())
        if self.answer_notes:
            self.answer_notes = html.escape(self.answer_notes.strip())
    
    def validate_business_rules(self):
        """Prayer-specific business rules"""
        # Prevent extremely long prayer requests
        if len(self.content) > 10000:
            raise ValueError("Prayer request too long")
        
        # Validate expiration makes sense
        from datetime import datetime, timedelta
        if self.expires_at:
            max_expiry = datetime.now() + timedelta(days=365)  # 1 year max
            if self.expires_at > max_expiry:
                raise ValueError("Prayer request expiration too far in future")
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
        self.validate_business_rules()
    
    # Your existing methods
    @property
    def is_expired(self) -> bool:
        from datetime import datetime
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
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

    

    