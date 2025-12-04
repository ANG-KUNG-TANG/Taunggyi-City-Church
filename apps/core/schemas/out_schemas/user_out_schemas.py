from typing import Any, List, Optional, Dict
from datetime import date, datetime
from pydantic import Field
from apps.core.schemas.out_schemas.base import (
    BaseResponseSchema, 
    DeleteResponseSchema,
    PaginatedResponseSchema )
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

    # System Information - CHANGED to optional with defaults
    is_staff: bool = Field(default=False, description="Is staff member")
    is_superuser: bool = Field(default=False, description="Is superuser")
    is_active: bool = Field(..., description="Is active")
    
    # ADDED: User-specific fields
    requires_password_change: bool = Field(default=False, description="Password change required")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(default=0, description="Number of logins")
    
    # Base Response Fields
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
    
    # ADDED: Optional profile picture for UI
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")

# UPDATED: Use generic paginated response
class UserListResponseSchema(PaginatedResponseSchema[UserSimpleResponseSchema]):
    """Paginated user list response - matches repo get_paginated return."""
    pass

# UPDATED: Use generic paginated response with search term
class UserSearchResponseSchema(PaginatedResponseSchema[UserSimpleResponseSchema]):
    """User search response - matches repo search_users return."""
    search_term: str = Field(..., description="Search term used")

class UserStatsResponseSchema(BaseResponseSchema):
    """User statistics response."""
    
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    pending_users: int = Field(..., description="Number of pending users")
    users_by_role: Dict[UserRole, int] = Field(..., description="Users count by role")
    users_by_status: Dict[UserStatus, int] = Field(..., description="Users count by status")
    users_by_gender: Dict[Gender, int] = Field(default_factory=dict, description="Users count by gender")

class EmailCheckResponseSchema(BaseResponseSchema):
    """Email existence check response - matches repo email_exists."""
    
    email: str = Field(..., description="Email checked")
    exists: bool = Field(..., description="Whether email exists")
    available: bool = Field(..., description="Whether email is available for use")

class PasswordVerificationResponseSchema(BaseResponseSchema):
    """Password verification response - matches repo verify_password."""
    
    user_id: int = Field(..., description="User ID")
    valid: bool = Field(..., description="Whether password is valid")

# REMOVED: UserCreateResponseSchema, UserUpdateResponseSchema - use generic responses instead

# ADDED: Missing response schemas

class UserLoginResponseSchema(BaseResponseSchema):
    """Response for user login."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserSimpleResponseSchema = Field(..., description="User information")

class UserTokenRefreshResponseSchema(BaseResponseSchema):
    """Response for token refresh."""
    
    access_token: str = Field(..., description="New access token")
    expires_in: int = Field(..., description="Token expiration in seconds")

class UserPasswordChangeResponseSchema(BaseResponseSchema):
    """Response for password change."""
    
    success: bool = Field(..., description="Whether password was changed")
    message: str = Field(..., description="Response message")
    requires_login: bool = Field(default=True, description="Whether user needs to login again")

class UserResetPasswordResponseSchema(BaseResponseSchema):
    """Response for password reset."""
    
    success: bool = Field(..., description="Whether reset was successful")
    message: str = Field(..., description="Response message")
    email: str = Field(..., description="User email")

class UserBulkOperationResponseSchema(BaseResponseSchema):
    """Response for bulk operations."""
    
    operation: str = Field(..., description="Operation type")
    total: int = Field(..., description="Total users processed")
    successful: int = Field(..., description="Successfully processed")
    failed: int = Field(..., description="Failed to process")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")

class UserAuditResponseSchema(BaseResponseSchema):
    """User audit trail entry."""
    
    action: str = Field(..., description="Action performed")
    performed_by: Optional[int] = Field(None, description="User who performed action")
    performed_at: datetime = Field(..., description="When action was performed")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    changes: Optional[Dict[str, Any]] = Field(None, description="Field changes")

class UserAuditListResponseSchema(PaginatedResponseSchema[UserAuditResponseSchema]):
    """Paginated user audit trail."""
    user_id: Optional[int] = Field(None, description="User ID filter")