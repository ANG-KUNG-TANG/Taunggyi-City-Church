from typing import Optional, List
from datetime import date
from pydantic import Field, EmailStr, model_validator
from apps.core.schemas.input_schemas.base import BaseSchema
from apps.tcc.models.base.enums import Gender, MaritalStatus, UserRole, UserStatus

class UserBaseInputSchema(BaseSchema):
    """Common fields and validation for user input."""
    
    name: str = Field(..., min_length=2, max_length=120, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")

    age: Optional[int] = Field(None, ge=0, le=120, description="Age")
    gender: Optional[Gender] = Field(None, description="Gender")
    marital_status: Optional[MaritalStatus] = Field(None, description="Marital status")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")

    testimony: Optional[str] = Field(None, description="Personal testimony")
    baptism_date: Optional[date] = Field(None, description="Baptism date")
    membership_date: Optional[date] = Field(None, description="Membership date")

    role: UserRole = Field(default=UserRole.VISITOR, description="User role")
    status: UserStatus = Field(default=UserStatus.PENDING, description="User status")
    email_notifications: bool = Field(default=True, description="Email notifications preference")
    
    # Required system fields based on repo
    is_active: bool = Field(default=True, description="Active status")
    is_staff: bool = Field(default=False, description="Staff status")
    is_superuser: bool = Field(default=False, description="Superuser status")

    @model_validator(mode="after")
    def validate_birthdate(self):
        """Ensure that the birth date respects logical constraints."""
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return self

class UserCreateInputSchema(UserBaseInputSchema):
    """Schema for creating new users."""
    
    password: str = Field(..., min_length=8, description="Password")
    password_confirm: str = Field(..., min_length=8, description="Password confirmation")

    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Ensure passwords match."""
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
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

class UserQueryInputSchema(BaseSchema):
    """Schema for querying/filtering users - matches repo get_paginated_users."""
    
    name: Optional[str] = Field(None, description="Search by name")
    email: Optional[str] = Field(None, description="Search by email")
    role: Optional[UserRole] = Field(None, description="Filter by role")
    status: Optional[UserStatus] = Field(None, description="Filter by status")
    is_active: Optional[bool] = Field(default=True, description="Filter by active status")
    
    # Pagination - matches repo parameters
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

class UserSearchInputSchema(BaseSchema):
    """Schema for searching users - matches repo search_users."""
    
    search_term: str = Field(..., min_length=1, description="Search term for name or email")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

class UserChangePasswordInputSchema(BaseSchema):
    """Schema for changing user password - matches repo verify_password."""
    
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

    @model_validator(mode="after")
    def validate_passwords(self):
        """Validate password change."""
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self

class UserResetPasswordRequestInputSchema(BaseSchema):
    """Schema for password reset request."""
    
    email: EmailStr = Field(..., description="User email address")

class UserResetPasswordInputSchema(BaseSchema):
    """Schema for setting new password after reset."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Ensure passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class EmailCheckInputSchema(BaseSchema):
    """Schema for checking email existence - matches repo email_exists."""
    
    email: EmailStr = Field(..., description="Email to check")

class PasswordVerificationInputSchema(BaseSchema):
    """Schema for verifying password - matches repo verify_password."""
    
    user_id: int = Field(..., ge=1, description="User ID")
    password: str = Field(..., min_length=1, description="Password to verify")