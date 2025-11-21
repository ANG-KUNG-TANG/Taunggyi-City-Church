from typing import Any, Dict, List, Optional
from datetime import date, datetime
from pydantic import Field, EmailStr, model_validator, ConfigDict

from apps.core.schemas.schemas.base import BaseSchema, BaseResponseSchema
from apps.tcc.models.base.enums import Gender, MaritalStatus, UserRole, UserStatus


# -----------------------------
# Base User Schema (Shared Rules)
# -----------------------------
class UserBaseSchema(BaseSchema):
    """Common fields and validation for user objects."""
    
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr = Field(...)
    phone_number: Optional[str] = Field(None, max_length=20)

    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Gender] = None
    marital_status: Optional[MaritalStatus] = None
    date_of_birth: Optional[date] = None

    testimony: Optional[str] = None
    baptism_date: Optional[date] = None
    membership_date: Optional[date] = None

    role: UserRole = Field(default=UserRole.VISITOR)
    status: UserStatus = Field(default=UserStatus.PENDING)

    email_notifications: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_birthdate(self):
        """Ensure that the birth date respects logical constraints."""
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return self


# -----------------------------
# Schema for Create Operations
# -----------------------------
class UserCreateSchema(UserBaseSchema):
    """Schema used for creating new users."""
    password: str = Field(..., min_length=8)


# -----------------------------
# Schema for Update Operations
# -----------------------------
class UserUpdateSchema(BaseSchema):
    """Schema for updating existing users."""
    
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=20)

    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Gender] = None
    marital_status: Optional[MaritalStatus] = None
    date_of_birth: Optional[date] = None

    testimony: Optional[str] = None
    baptism_date: Optional[date] = None
    membership_date: Optional[date] = None

    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None

    email_notifications: Optional[bool] = None


# -----------------------------
# Schema for API Response
# -----------------------------
class UserResponseSchema(UserBaseSchema, BaseResponseSchema):
    """
    Response schema returned by API.
    Extends base user fields with system-level metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None


# -----------------------------
# Schema for List Responses
# -----------------------------
class UserListResponseSchema(BaseSchema):
    """Schema for listing multiple users with pagination support."""
    
    users: List[UserResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int


# -----------------------------
# Schema for Query/Filters
# -----------------------------
class UserQuerySchema(BaseSchema):
    """Schema for querying/filtering users."""
    
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    
    # Pagination
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


# -----------------------------
# Schema for Bulk Operations
# -----------------------------
class UserBulkCreateSchema(BaseSchema):
    """Schema for bulk user creation."""
    
    users: List[UserCreateSchema]


class UserBulkUpdateSchema(BaseSchema):
    """Schema for bulk user updates."""
    
    user_ids: List[int]
    update_data: UserUpdateSchema


# -----------------------------
# Schema for Authentication
# -----------------------------
class UserLoginSchema(BaseSchema):
    """Schema for user login."""
    
    email: EmailStr
    password: str


class UserAuthResponseSchema(BaseSchema):
    """Schema for authentication response."""
    
    user: UserResponseSchema
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# -----------------------------
# Schema for Password Operations
# -----------------------------
class UserChangePasswordSchema(BaseSchema):
    """Schema for changing user password."""
    
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResetPasswordSchema(BaseSchema):
    """Schema for password reset."""
    
    email: EmailStr


class UserSetPasswordSchema(BaseSchema):
    """Schema for setting new password after reset."""
    
    token: str
    new_password: str = Field(..., min_length=8)