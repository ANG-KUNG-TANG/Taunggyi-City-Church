from datetime import datetime
from typing import Optional, List
import re
from apps.core.core_exceptions.domain import DomainValidationException
from apps.core.schemas.input_schemas.users import UserCreateInputSchema
from apps.tcc.models.base.enums import UserRole, UserStatus
from .base_entity import BaseEntity


class UserEntity(BaseEntity):
    """Domain entity for User with business logic and validation"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Core personal info
        self.name = kwargs.get('name', '')
        self.email = kwargs.get('email', '')
        self.phone_number = kwargs.get('phone_number')
        self.password_hash = kwargs.get('password_hash')  
        
        # Demographic info
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
    
    # ============ BUSINESS RULES ============
    
    def can_manage_users(self) -> bool:
        """Business rule: Check if user can manage other users"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF]
    
    def can_manage_events(self) -> bool:
        """Business rule: Check if user can manage events"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.MINISTRY_LEADER]
    
    def can_join_events(self) -> bool:
        """Business rule: Check if user can join events"""
        return self.is_active and self.status == UserStatus.ACTIVE
    
    def is_member(self) -> bool:
        """Business rule: Check if user is a church member"""
        return self.role in [UserRole.MEMBER, UserRole.MINISTRY_LEADER, UserRole.STAFF, UserRole.SUPER_ADMIN]
    
    def get_permissions(self) -> dict:
        """Business rule: Get all permissions for this user"""
        return {
            'manage_users': self.can_manage_users(),
            'manage_events': self.can_manage_events(),
            'join_events': self.can_join_events(),
            'is_member': self.is_member(),
        }
    
    # ============ VALIDATION METHODS ============
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Business rule for email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) if email else False
    
    def validate_and_raise(self):
        """Validate entity and raise domain exceptions"""
        errors = []
        
        # Required fields
        if not self.name or len(self.name.strip()) < 2:
            errors.append("Name must be at least 2 characters")
        
        if not self.email:
            errors.append("Email is required")
        elif not self.is_valid_email(self.email):
            errors.append("Invalid email format")
        
        # Business rule validations
        if self.date_of_birth and self.date_of_birth > datetime.now().date():
            errors.append("Date of birth cannot be in the future")
        
        if errors:
            raise DomainValidationException("; ".join(errors))
    
    def validate_for_creation(self) -> List[str]:
        """Backward compatibility method - returns errors list"""
        try:
            self.validate_and_raise()
            return []
        except DomainValidationException as e:
            return [str(e)]
    
    # ============ DOMAIN METHODS ============
    
    def prepare_for_persistence(self):
        """Prepare entity for database storage"""
        self.sanitize_inputs()
        self.update_timestamps()
    
    def sanitize_inputs(self):
        """Sanitize user data to prevent XSS"""
        self.name = self.sanitize_string(self.name) if self.name else ''
        self.email = self.sanitize_string(self.email).lower() if self.email else ''
        self.phone_number = self.sanitize_string(self.phone_number) if self.phone_number else None
        self.testimony = self.sanitize_string(self.testimony) if self.testimony else ''
    
    # ============ FACTORY METHODS ============
    
    @classmethod
    def from_create_schema(cls, schema: UserCreateInputSchema) -> 'UserEntity':
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
    
    def __str__(self):
        return f"UserEntity(id={self.id}, name='{self.name}', email='{self.email}')"