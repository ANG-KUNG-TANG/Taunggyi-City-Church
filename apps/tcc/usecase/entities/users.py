import html
from datetime import datetime
from typing import Optional
from apps.core.schemas.schemas.users import UserCreateSchema
from apps.tcc.models.base.enums import UserRole, UserStatus

class UserEntity:
    def __init__(self, user_data: UserCreateSchema = None, **kwargs):
        if user_data:
            self.name = user_data.name
            self.email = user_data.email
            self.phone_number = user_data.phone_number
            self.age = user_data.age
            self.gender = user_data.gender
            self.marital_status = user_data.marital_status
            self.date_of_birth = user_data.date_of_birth
            self.testimony = user_data.testimony
            self.baptism_date = user_data.baptism_date
            self.membership_date = user_data.membership_date
            self.role = user_data.role
            self.status = user_data.status
            self.email_notifications = user_data.email_notifications
            self.sms_notifications = user_data.sms_notifications
        else:
            # For repository conversion
            self.id = kwargs.get('id')
            self.name = kwargs.get('name')
            self.email = kwargs.get('email')
            self.phone_number = kwargs.get('phone_number')
            self.age = kwargs.get('age')
            self.gender = kwargs.get('gender')
            self.marital_status = kwargs.get('marital_status')
            self.date_of_birth = kwargs.get('date_of_birth')
            self.testimony = kwargs.get('testimony')
            self.baptism_date = kwargs.get('baptism_date')
            self.membership_date = kwargs.get('membership_date')
            self.role = kwargs.get('role', UserRole.MEMBER)
            self.status = kwargs.get('status', UserStatus.ACTIVE)
            self.is_staff = kwargs.get('is_staff', False)
            self.is_superuser = kwargs.get('is_superuser', False)
            self.is_active = kwargs.get('is_active', True)
            self.email_notifications = kwargs.get('email_notifications', True)
            self.sms_notifications = kwargs.get('sms_notifications', False)
            self.created_at = kwargs.get('created_at')
            self.updated_at = kwargs.get('updated_at')
    
    def sanitize_inputs(self):
        """Sanitize user data"""
        if hasattr(self, 'name'):
            self.name = html.escape(self.name.strip())
        if hasattr(self, 'email'):
            self.email = html.escape(self.email.strip())
        if hasattr(self, 'phone_number') and self.phone_number:
            self.phone_number = html.escape(self.phone_number.strip())
        if hasattr(self, 'testimony') and self.testimony:
            self.testimony = html.escape(self.testimony.strip())
    
    def prepare_for_persistence(self):
        self.sanitize_inputs()
    
    @property
    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    @property
    def can_manage_events(self) -> bool:
        """Check if user can manage events"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    @property
    def can_join_events(self) -> bool:
        """Check if user can join events"""
        return self.is_active and self.status == UserStatus.ACTIVE
    
    @property
    def is_member(self) -> bool:
        """Check if user is a church member"""
        return self.role != UserRole.GUEST
    
    @property
    def is_ministry_leader(self) -> bool:
        """Check if user is a ministry leader"""
        return self.role == UserRole.MINISTRY_LEADER
    
    def __str__(self):
        return f"{self.name} ({self.email})"