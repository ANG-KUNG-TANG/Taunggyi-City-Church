from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema

class TokenResponseSchema(BaseModel):
    """Token response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    expires_at: datetime = Field(..., description="Token expiration timestamp")

class AuthSuccessResponseSchema(BaseModel):
    """Authentication success response."""
    
    message: str = Field(default="Authentication successful", description="Response message")
    user: UserResponseSchema = Field(..., description="User information")
    tokens: TokenResponseSchema = Field(..., description="Authentication tokens")

class LoginResponseSchema(AuthSuccessResponseSchema):
    """Login specific response."""
    
    message: str = Field(default="Login successful", description="Login message")
    requires_2fa: bool = Field(default=False, description="Whether 2FA is required")

class RegisterResponseSchema(AuthSuccessResponseSchema):
    """Registration specific response."""
    
    message: str = Field(default="Registration successful", description="Registration message")
    email_verification_required: bool = Field(default=True, description="Whether email verification is required")

class TokenRefreshResponseSchema(BaseModel):
    """Token refresh response."""
    
    message: str = Field(default="Token refreshed successfully", description="Response message")
    tokens: TokenResponseSchema = Field(..., description="New tokens")

class LogoutResponseSchema(BaseModel):
    """Logout response."""
    
    message: str = Field(default="Logout successful", description="Logout message")

class PasswordResetResponseSchema(BaseModel):
    """Password reset response."""
    
    message: str = Field(default="Password reset successful", description="Response message")

class EmailVerificationResponseSchema(BaseModel):
    """Email verification response."""
    
    message: str = Field(default="Email verified successfully", description="Verification message")

class TwoFactorResponseSchema(BaseModel):
    """2FA response."""
    
    message: str = Field(..., description="2FA response message")
    requires_2fa: bool = Field(..., description="Whether 2FA is still required")
    temporary_token: Optional[str] = Field(None, description="Temporary token for 2FA flow")

class SessionResponseSchema(BaseModel):
    """User session response."""
    
    session_id: str = Field(..., description="Session identifier")
    user_id: int = Field(..., description="User ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    expires_at: datetime = Field(..., description="Session expiration")
    is_active: bool = Field(..., description="Whether session is active")
    
    model_config = ConfigDict(from_attributes=True)

class SessionListResponseSchema(BaseModel):
    """List of user sessions."""
    
    sessions: List[SessionResponseSchema] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")

class AuthAuditResponseSchema(BaseModel):
    """Authentication audit log response."""
    
    id: int = Field(..., description="Audit log ID")
    user_id: int = Field(..., description="User ID")
    action: str = Field(..., description="Authentication action")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    status: str = Field(..., description="Success or failure")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)