# In your user schemas file
from typing import Optional, List
from datetime import date
from pydantic import Field, EmailStr, model_validator, validator
from core.schemas.input_schemas.base import BaseSchema
from apps.tcc.models.base.enums import Gender, MaritalStatus, UserRole, UserStatus

class UserBaseInputSchema(BaseSchema):
    """Common fields and validation for user input."""
    
    name: str = Field(..., min_length=2, max_length=120, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")

    gender: Optional[Gender] = Field(None, description="Gender")
    marital_status: Optional[MaritalStatus] = Field(None, description="Marital status")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")

    testimony: Optional[str] = Field(None, description="Personal testimony")
    baptism_date: Optional[date] = Field(None, description="Baptism date")
    membership_date: Optional[date] = Field(None, description="Membership date")

    role: UserRole = Field(default=UserRole.VISITOR, description="User role")
    status: UserStatus = Field(default=UserStatus.PENDING, description="User status")
    email_notifications: bool = Field(default=True, description="Email notifications preference")
    sms_notifications: bool = Field(default=False, description="SMS notifications preference") 
    
    # Passwords for creation
    password: str = Field(..., min_length=8, max_length=100)
    password_confirm: str = Field(..., min_length=8, max_length=100)
    
    @model_validator(mode="after")
    def validate_birthdate(self):
        """Ensure that the birth date respects logical constraints."""
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return self

    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
class UserCreateInputSchema(UserBaseInputSchema):
    """Schema for creating new users."""
    
    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Ensure passwords match - extra validation."""
        # Double-check passwords match
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        
        # Additional business logic if needed
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")
            
        return self
   
class UserUpdateInputSchema(BaseSchema):
    """Schema for updating existing users (all fields optional)."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=120, description="Full name")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")

    age: Optional[int] = Field(None, ge=0, le=120, description="Age")
    gender: Optional[Gender] = Field(None, description="Gender")
    marital_status: Optional[MaritalStatus] = Field(None, description="Marital status")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")

    testimony: Optional[str] = Field(None, description="Personal testimony")
    baptism_date: Optional[date] = Field(None, description="Baptism date")
    membership_date: Optional[date] = Field(None, description="Membership date")

    role: Optional[UserRole] = Field(None, description="User role")
    status: Optional[UserStatus] = Field(None, description="User status")
    email_notifications: Optional[bool] = Field(None, description="Email notifications preference")
    
    # System fields that can be updated
    is_active: Optional[bool] = Field(None, description="Active status")
    
    # ADDED: User-specific update fields
    requires_password_change: Optional[bool] = Field(None, description="Password change required")

class UserQueryInputSchema(BaseSchema):
    """Schema for querying/filtering users - matches repo get_paginated."""
    
    # CHANGE: Use actual database field names
    first_name: Optional[str] = Field(None, description="Search by first name")
    last_name: Optional[str] = Field(None, description="Search by last name")
    # OR if you have full_name field:
    # full_name: Optional[str] = Field(None, description="Search by full name")
    
    email: Optional[str] = Field(None, description="Search by email")
    role: Optional[UserRole] = Field(None, description="Filter by role")
    status: Optional[UserStatus] = Field(None, description="Filter by status")
    is_active: Optional[bool] = Field(default=None, description="Filter by active status")  # Changed to None
    gender: Optional[Gender] = Field(None, description="Filter by gender")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    # Sorting
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field(None, pattern="^(asc|desc)$", description="Sort order: asc or desc")
    
class UserSearchInputSchema(BaseSchema):
    """Schema for searching users - matches repo search_users."""
    
    search_term: str = Field(..., min_length=1, description="Search term for name or email")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class EmailCheckInputSchema(BaseSchema):
    """Schema for email validation - SIMPLIFIED VERSION"""
    email: str = Field(..., min_length=3, max_length=255, description="Email to check")
    
    @validator('email', pre=True)
    def clean_and_validate_email(cls, v):
        """Clean and validate email - handles all edge cases"""
        if not v:
            raise ValueError('Email is required')
        
        # Handle list case (from QueryDict)
        if isinstance(v, list):
            if len(v) > 0:
                v = v[0]
            else:
                raise ValueError('Email is required')
        
        # Convert to string
        if not isinstance(v, str):
            v = str(v)
        
        # Clean the email
        v = v.strip().strip('"').strip("'")
        
        # Remove trailing slash
        if v.endswith('/'):
            v = v[:-1]
        
        # Remove URL encoding
        v = v.replace('%22', '').replace('%27', '').strip()
        
        # Validate format
        if not v:
            raise ValueError('Email cannot be empty')
        
        if '@' not in v:
            raise ValueError('Email must contain @')
        
        parts = v.split('@')
        if len(parts) != 2:
            raise ValueError('Invalid email format')
        
        local_part, domain = parts
        if not local_part or not domain:
            raise ValueError('Invalid email format')
        
        if '.' not in domain:
            raise ValueError('Invalid domain in email')
        
        # Return lowercase
        return v.lower()
    
class PasswordVerificationInputSchema(BaseSchema):
    """Schema for verifying password - matches repo verify_password."""
    
    user_id: int = Field(..., ge=1, description="User ID")
    password: str = Field(..., min_length=1, description="Password to verify")

# ADDED: Missing schemas for common operations

class UserBulkUpdateInputSchema(BaseSchema):
    """Schema for bulk user updates."""
    user_ids: List[int] = Field(..., min_items=1, max_items=100, description="User IDs to update")
    update_data: UserUpdateInputSchema = Field(..., description="Data to apply to all users")

class UserBulkDeleteInputSchema(BaseSchema):
    """Schema for bulk user deletion."""
    user_ids: List[int] = Field(..., min_items=1, max_items=100, description="User IDs to delete")

class UserProfileUpdateInputSchema(BaseSchema):
    """Schema for updating user profile (non-sensitive fields)."""
    name: Optional[str] = Field(None, min_length=2, max_length=120, description="Full name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    testimony: Optional[str] = Field(None, description="Personal testimony")
    email_notifications: Optional[bool] = Field(None, description="Email notifications preference")