from schemas.users import UserBaseSchema, UserCreateSchema
from models.base.enums import UserRole, UserStatus
import html
from typing import Dict


class UserEntity(UserCreateSchema):
    """Entity inherits schema validation AND adds business logic"""
    
    def sanitize_inputs(self):
        """Sanitize all inputs to prevent injection attacks"""
        self.name = html.escape(self.name.strip())
        self.email = self.email.lower().strip()
        if self.phone_number:
            self.phone_number = self.sanitize_phone(self.phone_number)
        if self.testimony:
            self.testimony = html.escape(self.testimony.strip())
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """Keep only digits in phone numbers"""
        return ''.join(filter(str.isdigit, phone))
    
    def validate_business_rules(self):
        """Business-specific validation beyond schema"""
        # Check for temporary/disposable emails
        if self.email.endswith(('.tmp', '.temp', 'tempmail.com')):
            raise ValueError("Temporary emails are not allowed")
        
        # Validate age consistency with date of birth
        if self.age and self.date_of_birth:
            from datetime import date
            calculated_age = (date.today() - self.date_of_birth).days // 365
            if abs(calculated_age - self.age) > 1:
                raise ValueError("Age doesn't match date of birth")
    
    def prepare_for_persistence(self):
        """Final preparation before saving to database"""
        self.sanitize_inputs()
        self.validate_business_rules()
    
    # Your existing permission properties and methods
    @property
    def can_manage_users(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def can_manage_events(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_staff_member(self) -> bool:
        return self.role == UserRole.STAFF
    
    @property
    def is_ministry_leader(self) -> bool:
        return self.role == UserRole.MINISTRY_LEADER
    
    @property
    def is_member(self) -> bool:
        return self.role == UserRole.MEMBER
    
    @property
    def is_visitor(self) -> bool:
        return self.role == UserRole.VISITOR
    
    @property
    def can_manage_users(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def can_manage_events(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_manage_sermons(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_manage_donations(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def can_view_all_prayers(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_join_events(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER, 
                           UserRole.MEMBER, UserRole.VISITOR]
    
    @property
    def can_create_prayers(self) -> bool:
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER, 
                           UserRole.MEMBER, UserRole.VISITOR]
    
    def get_permissions(self) -> Dict[str, bool]:
        return {
            'manage_users': self.can_manage_users,
            'manage_events': self.can_manage_events,
            'manage_sermons': self.can_manage_sermons,
            'manage_donations': self.can_manage_donations,
            'view_all_prayers': self.can_view_all_prayers,
            'join_events': self.can_join_events,
            'create_prayers': self.can_create_prayers,
        }
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    
