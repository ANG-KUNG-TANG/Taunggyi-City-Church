from typing import Any, List, Optional, Dict
from datetime import date, datetime
from pydantic import Field
from apps.core.schemas.out_schemas.base import BaseResponseSchema
from apps.tcc.models.base.enums import UserRole, UserStatus, Gender, MaritalStatus

class UserResponseSchema(BaseResponseSchema):
    """Complete user response schema - matches UserEntity from repo."""
    
    # Personal Information
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    phone_number: Optional[str] = Field(None, description="Phone number")

    # Demographic Information
    age: Optional[int] = Field(None, description="Age")
    gender: Optional[Gender] = Field(None, description="Gender")
    marital_status: Optional[MaritalStatus] = Field(None, description="Marital status")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")

    # Spiritual Information
    testimony: Optional[str] = Field(None, description="Personal testimony")
    baptism_date: Optional[date] = Field(None, description="Baptism date")
    membership_date: Optional[date] = Field(None, description="Membership date")

    # Account Information
    role: UserRole = Field(..., description="User role")
    status: UserStatus = Field(..., description="User status")
    email_notifications: bool = Field(True, description="Email notifications preference")

    # System Information - required by repo
    is_staff: bool = Field(..., description="Is staff member")
    is_superuser: bool = Field(..., description="Is superuser")
    is_active: bool = Field(..., description="Is active")
    
    # Base Response Fields - required by BaseResponseSchema
    id: int = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[int] = Field(None, description="Creator user ID")
    updated_by: Optional[int] = Field(None, description="Last updater user ID")

class UserProfileResponseSchema(UserResponseSchema):
    """Extended user profile with additional data."""
    
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    bio: Optional[str] = Field(None, description="User biography")
    website: Optional[str] = Field(None, description="Personal website")
    social_links: Optional[Dict[str, str]] = Field(None, description="Social media links")

class UserSimpleResponseSchema(BaseResponseSchema):
    """Simplified user response for lists and references."""
    
    id: int = Field(..., description="User ID")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    role: UserRole = Field(..., description="User role")
    status: UserStatus = Field(..., description="User status")
    is_active: bool = Field(..., description="Is active")
    created_at: datetime = Field(..., description="Creation timestamp")

class UserListResponseSchema(BaseResponseSchema):
    """Paginated user list response - matches repo get_paginated_users return."""
    
    items: List[UserSimpleResponseSchema] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_prev: bool = Field(..., description="Has previous page")

class UserSearchResponseSchema(BaseResponseSchema):
    """User search response - matches repo search_users return."""
    
    items: List[UserSimpleResponseSchema] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    search_term: str = Field(..., description="Search term used")

class UserStatsResponseSchema(BaseResponseSchema):
    """User statistics response."""
    
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    pending_users: int = Field(..., description="Number of pending users")
    users_by_role: Dict[UserRole, int] = Field(..., description="Users count by role")
    users_by_status: Dict[UserStatus, int] = Field(..., description="Users count by status")

class EmailCheckResponseSchema(BaseResponseSchema):
    """Email existence check response - matches repo email_exists."""
    
    email: str = Field(..., description="Email checked")
    exists: bool = Field(..., description="Whether email exists")
    available: bool = Field(..., description="Whether email is available for use")

class PasswordVerificationResponseSchema(BaseResponseSchema):
    """Password verification response - matches repo verify_password."""
    
    user_id: int = Field(..., description="User ID")
    valid: bool = Field(..., description="Whether password is valid")

class UserCreateResponseSchema(UserResponseSchema):
    """User creation response with additional context."""
    
    message: str = Field(default="User created successfully", description="Response message")
    password_set: bool = Field(..., description="Whether password was set")

class UserUpdateResponseSchema(UserResponseSchema):
    """User update response with additional context."""
    
    message: str = Field(default="User updated successfully", description="Response message")
    changes: Dict[str, Any] = Field(..., description="Fields that were changed")

class UserDeleteResponseSchema(BaseResponseSchema):
    """User delete response - matches repo delete return."""
    
    id: int = Field(..., description="User ID")
    deleted: bool = Field(..., description="Whether user was deleted")
    message: str = Field(..., description="Response message")