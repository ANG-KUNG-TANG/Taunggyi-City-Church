from pydantic import BaseModel, Field, root_validator, validator, constr, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import re

from apps.core.core_validators.rules import (
    validate_email,
    validate_username,
    validate_phone,
    validate_password,
    validate_baptism_date,
    validate_family_name,
    validate_full_name,
    create_choice_validator
)


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        extra = "forbid"  # Forbid extra fields
        anystr_strip_whitespace = True  # Strip whitespace from strings
        allow_population_by_field_name = True  # Allow field name aliases
        use_enum_values = True  # Use enum values instead of names
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

    def dict_safe(self, *, include=None, exclude=None, by_alias=False) -> Dict[str, Any]:
        """
        Convert to dictionary while masking secret fields
        
        Args:
            include: Fields to include
            exclude: Fields to exclude
            by_alias: Whether to use field aliases
            
        Returns:
            Dictionary with secret fields masked
        """
        raw = self.dict(include=include, exclude=exclude, by_alias=by_alias)
        secrets = getattr(self, "__secret_fields__", [])
        
        for secret_field in secrets:
            if secret_field in raw and raw[secret_field]:
                raw[secret_field] = "******"
        
        return raw
    
    def model_dump_safe(self, **kwargs) -> Dict[str, Any]:
        """Alias for dict_safe for consistency with Pydantic v2"""
        return self.dict_safe(**kwargs)


# ----------------------------
# User Schemas
# ----------------------------
class UserBaseSchema(BaseSchema):
    """Base user schema with common fields"""
    username: str = Field(..., min_length=3, max_length=30, description="Unique username")
    email: str = Field(..., description="User email address")
    phone: Optional[str] = Field(None, description="Phone number")
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Full name")


class UserCreateSchema(UserBaseSchema):
    """Schema for creating new users"""
    password: str = Field(..., min_length=8, description="User password")
    
    # Secret fields that should be masked when serializing
    __secret_fields__ = ["password"]

    # Custom validators
    _validate_username = validator("username", allow_reuse=True)(validate_username)
    _validate_email = validator("email", allow_reuse=True)(validate_email)
    _validate_password = validator("password", allow_reuse=True)(validate_password)
    _validate_phone = validator("phone", allow_reuse=True)(validate_phone)
    _validate_full_name = validator("full_name", allow_reuse=True)(validate_full_name)


class UserUpdateSchema(BaseSchema):
    """Schema for updating existing users"""
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    phone: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    
    __secret_fields__ = ["password"]

    _validate_username = validator("username", allow_reuse=True)(validate_username)
    _validate_email = validator("email", allow_reuse=True)(validate_email)
    _validate_password = validator("password", allow_reuse=True)(validate_password)
    _validate_phone = validator("phone", allow_reuse=True)(validate_phone)
    _validate_full_name = validator("full_name", allow_reuse=True)(validate_full_name)

    @root_validator
    def ensure_non_empty(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure at least one field is provided for update"""
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values


class UserResponseSchema(UserBaseSchema):
    """Schema for user responses (excludes sensitive data)"""
    id: int = Field(..., description="User ID")
    is_active: bool = Field(True, description="Whether user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ----------------------------
# Church Domain Schemas
# ----------------------------
class MemberBaseSchema(BaseSchema):
    """Base schema for church members"""
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    baptism_date: Optional[str] = None
    family_id: Optional[int] = None
    member_type: str = Field("member", description="Type of member")


class MemberCreateSchema(MemberBaseSchema):
    """Schema for creating new members"""
    _validate_email = validator("email", allow_reuse=True)(validate_email)
    _validate_phone = validator("phone", allow_reuse=True)(validate_phone)
    _validate_baptism_date = validator("baptism_date", allow_reuse=True)(validate_baptism_date)
    
    @root_validator
    def validate_member_data(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate member-specific business rules"""
        # Ensure either email or phone is provided
        if not values.get('email') and not values.get('phone'):
            raise ValueError("Either email or phone must be provided")
        
        # Validate baptism date is not in future
        baptism_date = values.get('baptism_date')
        if baptism_date:
            from datetime import date
            try:
                baptism = date.fromisoformat(baptism_date)
                if baptism > date.today():
                    raise ValueError("Baptism date cannot be in the future")
            except ValueError:
                # Date format validation already handled by validator
                pass
        
        return values


class FamilyCreateSchema(BaseSchema):
    """Schema for creating families"""
    surname: str = Field(..., description="Family surname")
    address: Optional[str] = Field(None, max_length=200)
    home_phone: Optional[str] = None
    emergency_contact: Optional[str] = Field(None, max_length=200)
    
    _validate_family_name = validator("surname", allow_reuse=True)(validate_family_name)
    _validate_phone = validator("home_phone", allow_reuse=True)(validate_phone)


# ----------------------------
# Query Parameter Schemas
# ----------------------------
class PaginationSchema(BaseSchema):
    """Schema for pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @validator('page_size')
    def validate_page_size(cls, v):
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class UserQuerySchema(PaginationSchema):
    """Schema for user query parameters"""
    search: Optional[str] = Field(None, description="Search term")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order")
    
    _validate_sort_order = validator("sort_order", allow_reuse=True)(
        create_choice_validator(["asc", "desc"], "sort_order")
    )


# ----------------------------
# Authentication Schemas
# ----------------------------
class LoginSchema(BaseSchema):
    """Schema for user login"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    
    __secret_fields__ = ["password"]


class TokenSchema(BaseSchema):
    """Schema for authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(3600, description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")


# Update registry imports
__all__ = [
    'UserCreateSchema',
    'UserUpdateSchema', 
    'UserResponseSchema',
    'MemberCreateSchema',
    'FamilyCreateSchema',
    'PaginationSchema',
    'UserQuerySchema',
    'LoginSchema',
    'TokenSchema'
]