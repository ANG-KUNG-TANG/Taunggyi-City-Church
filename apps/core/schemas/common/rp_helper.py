from typing import List, Dict, Any
from datetime import datetime, timedelta
from apps.core.schemas.common.response import APIResponse
from apps.core.schemas.out_schemas.user_out_schemas import UserResponseSchema, UserListResponseSchema
from apps.core.schemas.out_schemas.aut_out_schemas import (
    TokenResponseSchema, AuthSuccessResponseSchema, LoginResponseSchema,
    RegisterResponseSchema, TokenRefreshResponseSchema, LogoutResponseSchema,
    PasswordResetResponseSchema, EmailVerificationResponseSchema,
    TwoFactorResponseSchema, SessionResponseSchema, SessionListResponseSchema
)

def build_user_response(user_entity: Any) -> UserResponseSchema:
    """Convert user entity to response schema."""
    return UserResponseSchema.model_validate(user_entity)

def build_user_list_response(
    user_entities: List[Any], 
    total: int, 
    page: int, 
    per_page: int
) -> UserListResponseSchema:
    """Build paginated user list response."""
    users = [build_user_response(entity) for entity in user_entities]
    
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1
    
    return UserListResponseSchema(
        items=users,
        total=total,
        page=page,
        page_size=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

def build_token_response(
    access_token: str,
    refresh_token: str = None,
    expires_in: int = 3600
) -> TokenResponseSchema:
    """Build token response."""
    return TokenResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        expires_at=datetime.now() + timedelta(seconds=expires_in)
    )

def build_auth_response(
    user_entity: Any,
    access_token: str,
    refresh_token: str = None,
    expires_in: int = 3600,
    message: str = "Authentication successful"
) -> AuthSuccessResponseSchema:
    """Build authentication response."""
    user_response = build_user_response(user_entity)
    tokens = build_token_response(access_token, refresh_token, expires_in)
    
    return AuthSuccessResponseSchema(
        message=message,
        user=user_response,
        tokens=tokens
    )

def build_login_response(
    user_entity: Any,
    access_token: str,
    refresh_token: str = None,
    expires_in: int = 3600,
    requires_2fa: bool = False
) -> LoginResponseSchema:
    """Build login response."""
    user_response = build_user_response(user_entity)
    tokens = build_token_response(access_token, refresh_token, expires_in)
    
    return LoginResponseSchema(
        message="Login successful",
        user=user_response,
        tokens=tokens,
        requires_2fa=requires_2fa
    )

def build_register_response(
    user_entity: Any,
    access_token: str,
    refresh_token: str = None,
    expires_in: int = 3600,
    email_verification_required: bool = True
) -> RegisterResponseSchema:
    """Build registration response."""
    user_response = build_user_response(user_entity)
    tokens = build_token_response(access_token, refresh_token, expires_in)
    
    return RegisterResponseSchema(
        message="Registration successful",
        user=user_response,
        tokens=tokens,
        email_verification_required=email_verification_required
    )

def build_token_refresh_response(
    access_token: str,
    refresh_token: str = None,
    expires_in: int = 3600
) -> TokenRefreshResponseSchema:
    """Build token refresh response."""
    tokens = build_token_response(access_token, refresh_token, expires_in)
    
    return TokenRefreshResponseSchema(
        message="Token refreshed successfully",
        tokens=tokens
    )

def build_logout_response() -> LogoutResponseSchema:
    """Build logout response."""
    return LogoutResponseSchema(message="Logout successful")

def build_password_reset_response() -> PasswordResetResponseSchema:
    """Build password reset response."""
    return PasswordResetResponseSchema(message="Password reset successful")

def build_email_verification_response() -> EmailVerificationResponseSchema:
    """Build email verification response."""
    return EmailVerificationResponseSchema(message="Email verified successfully")

def build_two_factor_response(
    message: str,
    requires_2fa: bool,
    temporary_token: str = None
) -> TwoFactorResponseSchema:
    """Build 2FA response."""
    return TwoFactorResponseSchema(
        message=message,
        requires_2fa=requires_2fa,
        temporary_token=temporary_token
    )

def build_session_response(session_entity: Any) -> SessionResponseSchema:
    """Convert session entity to response schema."""
    return SessionResponseSchema.model_validate(session_entity)

def build_session_list_response(
    session_entities: List[Any],
    total: int
) -> SessionListResponseSchema:
    """Build session list response."""
    sessions = [build_session_response(entity) for entity in session_entities]
    
    return SessionListResponseSchema(
        sessions=sessions,
        total=total
    )