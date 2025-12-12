from typing import Optional
from pydantic import Field, EmailStr, model_validator, validator
from apps.core.schemas.input_schemas.base import BaseSchema


class LoginInputSchema(BaseSchema):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    remember_me: bool = Field(default=False, description="Remember login session")
    
    @validator('email', pre=True)
    def validate_email_not_empty(cls, v):
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("Email is required to login")
        return v
    
    @validator('password', pre=True)
    def validate_password_not_empty(cls, v):
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("Password is required to login")
        return v

class RegisterInputSchema(BaseSchema):
    """User registration - authentication operation"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    password_confirm: str = Field(..., min_length=8, description="Password confirmation")
    name: str = Field(..., min_length=2, max_length=120, description="Full name")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
    
class ChangePasswordInputSchema(BaseSchema):
    """Schema for changing password (logged-in user)."""
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure new passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError('New passwords do not match')
        if self.current_password == self.new_password:
            raise ValueError('New password must be different from current password')
        return self


class ForgotPasswordInputSchema(BaseSchema):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User email address")


class ResetPasswordInputSchema(BaseSchema):
    """Schema for password reset with token."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class LogoutInputSchema(BaseSchema):
    """Schema for logout."""
    refresh_token: Optional[str] = Field(None, description="Refresh token to invalidate")


class RefreshTokenInputSchema(BaseSchema):
    """Schema for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")
    
class AdminResetPasswordSchema(BaseSchema):
    """Schema for admin to reset user password (no current password needed)."""
    user_id: int = Field(..., description="User ID to reset password for")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self