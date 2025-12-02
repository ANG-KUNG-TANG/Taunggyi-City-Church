from typing import Optional
from pydantic import Field, EmailStr, constr, model_validator
from apps.core.schemas.input_schemas.base import BaseSchema

class LoginInputSchema(BaseSchema):
    """Schema for user login."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    remember_me: bool = Field(default=False, description="Remember login session")

class RegisterInputSchema(BaseSchema):
    """Schema for user registration."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    password_confirm: str = Field(..., min_length=8, description="Password confirmation")
    name: str = Field(..., min_length=2, max_length=120, description="Full name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure passwords match."""
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

class ChangePasswordInputSchema(BaseSchema):
    """Schema for changing password."""
    
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure new passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError('New passwords do not match')
        return self

class RefreshTokenInputSchema(BaseSchema):
    """Schema for token refresh."""
    
    refresh_token: str = Field(..., description="Refresh token")

class ForgotPasswordInputSchema(BaseSchema):
    """Schema for password reset request."""
    
    email: EmailStr = Field(..., description="User email address")

class ResetPasswordInputSchema(BaseSchema):
    """Schema for password reset."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """Ensure passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class VerifyEmailInputSchema(BaseSchema):
    """Schema for email verification."""
    
    token: str = Field(..., description="Email verification token")

class ResendVerificationInputSchema(BaseSchema):
    """Schema for resending verification email."""
    
    email: EmailStr = Field(..., description="User email address")

class LogoutInputSchema(BaseSchema):
    """Schema for logout."""
    
    refresh_token: Optional[str] = Field(None, description="Refresh token to invalidate")

class SocialLoginInputSchema(BaseSchema):
    """Schema for social media login."""
    
    provider: str = Field(..., description="Social provider (google, facebook, etc.)")
    access_token: str = Field(..., description="Social provider access token")
    remember_me: bool = Field(default=False, description="Remember login session")

class TwoFactorInputSchema(BaseSchema):
    """Schema for two-factor authentication."""
    
    code: str = Field(..., min_length=6, max_length=6, description="2FA code")
    remember_device: bool = Field(default=False, description="Remember this device")
    
class ForgotPasswordInputSchema(BaseSchema):
    email: EmailStr
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }

class ResetPasswordInputSchema(BaseSchema):
    reset_token: str
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    
    class Config:
        schema_extra = {
            "example": {
                "reset_token": "abc123def456...",
                "new_password": "newSecurePassword123",
                "confirm_password": "newSecurePassword123"
            }
        }
    
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self