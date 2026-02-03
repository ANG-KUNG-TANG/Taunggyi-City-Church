import re
from typing import Any, Dict, Optional
from pydantic import Field, EmailStr, field_validator, model_validator, validator
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
    """Schema for refresh token - accepts multiple field names."""
    
    refresh_token: str = Field(..., description="Refresh token")
    
    @model_validator(mode='before')
    @classmethod
    def extract_token(cls, data: Any) -> Dict[str, Any]:
        """Extract token from any of the possible field names."""
        if isinstance(data, dict):
            # Try all possible field names
            token = (
                data.get('refresh_token') or 
                data.get('refresh') or 
                data.get('refreshToken')
            )
            
            if not token:
                raise ValueError('Refresh token is required')
            
            # Clean the token immediately
            if isinstance(token, str):
                # Remove any quotes, whitespace
                token = token.strip().strip('"\'').strip()
                
                # Remove any newline characters
                token = re.sub(r'[\n\r]+', '', token)
            
            # Return dict with just refresh_token
            return {'refresh_token': token}
        return data
    
    @field_validator('refresh_token')
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        """Validate that the token looks like a valid JWT."""
        if not v:
            raise ValueError('Refresh token is required')
        
        # Check minimum length
        if len(v) < 10:
            raise ValueError('Token is too short')
        
        # Check if it looks like a JWT (has dots)
        if '.' not in v:
            raise ValueError('Invalid token format')
        
        # Check for exactly 2 dots (3 parts)
        if v.count('.') != 2:
            raise ValueError('Invalid JWT format')
        
        # Check each part for base64url characters
        parts = v.split('.')
        base64url_pattern = r'^[A-Za-z0-9_-]+$'
        for i, part in enumerate(parts):
            if not part:
                raise ValueError(f'JWT part {i+1} is empty')
            if not re.match(base64url_pattern, part):
                raise ValueError(f'JWT part {i+1} contains invalid characters')
        
        return v
    
    # Add the property back for compatibility
    @property
    def actual_refresh_token(self) -> str:
        """Compatibility property - returns the refresh token."""
        return self.refresh_token
    
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Return dict with only refresh_token."""
        d = super().dict(*args, **kwargs)
        return d
    
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
    
class VerifyTokenInputSchema(BaseSchema):
    """Schema for token verification."""
    token: str = Field(..., description="Token to verify")
    