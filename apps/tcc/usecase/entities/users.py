from apps.core.schemas.base import UserCreateSchema
from models.base.enums import UserRole, UserStatus
import html
from typing import Dict

class UserEntity:
    def __init__(self, user_data: UserCreateSchema):
        self.name = user_data.name
        self.email = user_data.email
        self.phone_number = user_data.phone_number
        self.date_of_birth = user_data.date_of_birth
        self.age = user_data.age
        self.role = user_data.role
        self.status = user_data.status
        self.testimony = user_data.testimony
    
    def sanitize_inputs(self):
        """Sanitize all inputs to prevent injection attacks"""
        self.name = html.escape(self.name.strip())
        if self.testimony:
            self.testimony = html.escape(self.testimony.strip())
    
    def prepare_for_persistence(self):
        """Final preparation before saving to database"""
        self.sanitize_inputs()
        # Business rules are now in schema validation
    
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