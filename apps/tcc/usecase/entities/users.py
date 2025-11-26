import html
from datetime import datetime
from typing import Optional
from apps.core.schemas.schemas.users import UserCreateSchema
from apps.tcc.models.base.enums import UserRole, UserStatus

class UserEntity:
    """Domain entity for User with business logic"""
    
    def __init__(self, **kwargs):
        # Core personal info
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', '')
        self.email = kwargs.get('email', '')
        self.phone_number = kwargs.get('phone_number')
        
        # Demographic info
        self.age = kwargs.get('age')
        self.gender = kwargs.get('gender')
        self.marital_status = kwargs.get('marital_status')
        self.date_of_birth = kwargs.get('date_of_birth')
        
        # Spiritual info
        self.testimony = kwargs.get('testimony')
        self.baptism_date = kwargs.get('baptism_date')
        self.membership_date = kwargs.get('membership_date')
        
        # Role & status
        self.role = kwargs.get('role', UserRole.VISITOR)
        self.status = kwargs.get('status', UserStatus.PENDING)
        
        # System fields
        self.is_staff = kwargs.get('is_staff', False)
        self.is_superuser = kwargs.get('is_superuser', False)
        self.is_active = kwargs.get('is_active', True)
        
        # Preferences
        self.email_notifications = kwargs.get('email_notifications', True)
        self.sms_notifications = kwargs.get('sms_notifications', False)
        
        # Timestamps
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
    
    @classmethod
    def from_create_schema(cls, schema: UserCreateSchema) -> 'UserEntity':
        """Create entity from creation schema"""
        data = schema.model_dump()
        return cls(**data)
    
    @classmethod
    def from_model(cls, model) -> 'UserEntity':
        """Create entity from Django model"""
        return cls(
            id=model.id,
            name=model.name,
            email=model.email,
            phone_number=model.phone_number,
            age=model.age,
            gender=model.gender,
            marital_status=model.marital_status,
            date_of_birth=model.date_of_birth,
            testimony=model.testimony,
            baptism_date=model.baptism_date,
            membership_date=model.membership_date,
            role=model.role,
            status=model.status,
            is_staff=model.is_staff,
            is_superuser=model.is_superuser,
            is_active=model.is_active,
            email_notifications=model.email_notifications,
            sms_notifications=model.sms_notifications,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by
        )
    
    def sanitize_inputs(self):
        """Sanitize user data to prevent XSS"""
        if self.name:
            self.name = html.escape(self.name.strip())
        if self.email:
            self.email = html.escape(self.email.strip()).lower()
        if self.phone_number:
            self.phone_number = html.escape(self.phone_number.strip())
        if self.testimony:
            self.testimony = html.escape(self.testimony.strip())
    
    def prepare_for_persistence(self):
        """Prepare entity for database storage"""
        self.sanitize_inputs()
        self.updated_at = datetime.now()
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    def can_manage_events(self) -> bool:
        """Check if user can manage events"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    def can_join_events(self) -> bool:
        """Check if user can join events"""
        return self.is_active and self.status == UserStatus.ACTIVE
    
    def is_member(self) -> bool:
        """Check if user is a church member"""
        return self.role in [UserRole.MEMBER, UserRole.MINISTRY_LEADER, UserRole.STAFF, UserRole.SUPER_ADMIN]
    
    def validate_for_creation(self) -> list:
        """Validate entity for creation, return list of errors"""
        errors = []
        
        if not self.name or len(self.name.strip()) < 2:
            errors.append("Name must be at least 2 characters")
        
        if not self.email or '@' not in self.email:
            errors.append("Valid email is required")
        
        if self.date_of_birth and self.date_of_birth > datetime.now().date():
            errors.append("Date of birth cannot be in the future")
        
        return errors
    
    def __str__(self):
        return f"{self.name} ({self.email})"