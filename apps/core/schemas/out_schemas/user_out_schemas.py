from typing import List
from datetime import date, datetime
from pydantic import ConfigDict
from apps.core.schemas.out_schemas.base import BaseResponseSchema, BaseSchema
from apps.core.schemas.common.pagination import PaginatedResponse
from apps.tcc.models.base.enums import UserRole, UserStatus, Gender, MaritalStatus

class UserResponseSchema(BaseResponseSchema):
    """Complete user response schema."""
    
    # Personal Information
    name: str
    email: str
    phone_number: str | None = None

    # Demographic Information
    age: int | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    date_of_birth: date | None = None

    # Spiritual Information
    testimony: str | None = None
    baptism_date: date | None = None
    membership_date: date | None = None

    # Account Information
    role: UserRole
    status: UserStatus
    email_notifications: bool = True

    # System Information
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True
    
    # Base Response Fields
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
    
    model_config = ConfigDict(from_attributes=True)

class UserListResponseSchema(PaginatedResponse[UserResponseSchema]):
    """Paginated user list response."""
    pass

class UserProfileResponseSchema(UserResponseSchema):
    """Extended user profile response with additional profile data."""
    
    class Config:
        from_attributes = True

class UserSimpleResponseSchema(BaseResponseSchema):
    """Simplified user response for lists and references."""
    
    id: int
    name: str
    email: str
    role: UserRole
    status: UserStatus
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class UserCountResponseSchema(BaseSchema):
    """User count statistics response."""
    
    total: int
    active: int
    pending: int
    by_role: dict[UserRole, int]
    by_status: dict[UserStatus, int]