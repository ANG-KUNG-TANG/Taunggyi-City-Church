from typing import Optional
from datetime import date
from pydantic import Field, EmailStr, field_validator, model_validator
from .base import BaseSchema
from models.base.enums import UserRole, UserStatus, Gender, MaritalStatus


class UserSchema(BaseSchema):
    """Base user schema with validation rules"""
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

    @model_validator(mode='after')
    def validate_business_constraints(self):
        """Additional business rule validations"""
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError('Date of birth cannot be in the future')
        return self


class UserCreateSchema(UserSchema):
    """Schema for creating users with password"""
    password: str = Field(..., min_length=8)


class UserUpdateSchema(BaseSchema):
    """Schema for updating users"""
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


class UserResponseSchema(UserSchema):
    """Schema for API responses"""
    id: int
    is_staff: bool = False
    is_superuser: bool = False
    is_active: bool = True