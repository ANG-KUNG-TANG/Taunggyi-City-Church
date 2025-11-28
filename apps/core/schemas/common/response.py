from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Generic, TypeVar, Dict, List
from datetime import datetime

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """Standard API response schema."""
    
    success: bool
    message: str
    data: Optional[T] = None
    timestamp: datetime = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)
    
    @classmethod
    def success_response(cls, message: str = "Success", data: Optional[T] = None) -> 'APIResponse[T]':
        """Create a success response."""
        return cls(
            success=True,
            message=message,
            data=data
        )
    
    @classmethod
    def error_response(cls, message: str = "Error", data: Optional[T] = None) -> 'APIResponse[T]':
        """Create an error response."""
        return cls(
            success=False,
            message=message,
            data=data
        )

class ErrorResponse(BaseModel):
    """Error response schema."""
    
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

# ========== AUTHENTICATION RESPONSES ==========

class AuthData(BaseModel):
    """Authentication data structure"""
    user: Dict[str, Any]
    tokens: Dict[str, Any]

class LoginResponse(APIResponse[AuthData]):
    """API response for login"""
    
    @classmethod
    def from_auth_data(cls, 
                      user_data: Dict[str, Any], 
                      tokens_data: Dict[str, Any],
                      message: str = "Login successful") -> 'LoginResponse':
        """Create login response from user and token data"""
        data = AuthData(user=user_data, tokens=tokens_data)
        return cls.success_response(message=message, data=data)

class RegisterResponse(APIResponse[AuthData]):
    """API response for registration"""
    
    @classmethod
    def from_auth_data(cls, 
                      user_data: Dict[str, Any], 
                      tokens_data: Dict[str, Any],
                      message: str = "Registration successful") -> 'RegisterResponse':
        """Create registration response from user and token data"""
        data = AuthData(user=user_data, tokens=tokens_data)
        return cls.success_response(message=message, data=data)

class TokenRefreshResponse(APIResponse[Dict[str, Any]]):
    """API response for token refresh"""
    
    @classmethod
    def from_tokens(cls, 
                   tokens_data: Dict[str, Any],
                   message: str = "Token refreshed successfully") -> 'TokenRefreshResponse':
        """Create token refresh response"""
        return cls.success_response(message=message, data=tokens_data)

class LogoutResponse(APIResponse[None]):
    """API response for logout"""
    pass

class PasswordResetResponse(APIResponse[None]):
    """API response for password reset"""
    pass

class EmailVerificationResponse(APIResponse[None]):
    """API response for email verification"""
    pass

class TwoFactorResponse(APIResponse[Dict[str, Any]]):
    """API response for 2FA operations"""
    pass

class SessionListResponse(APIResponse[List[Dict[str, Any]]]):
    """API response for session list"""
    pass

# Convenience constructors

def make_auth_response(user: Dict[str, Any], 
                      tokens: Dict[str, Any],
                      message: str = "Success") -> LoginResponse:
    """Convenience function to create auth response"""
    return LoginResponse.from_auth_data(user, tokens, message)

def make_token_response(access_token: str,
                       refresh_token: Optional[str] = None,
                       expires_in: Optional[int] = None,
                       message: str = "Success") -> TokenRefreshResponse:
    """Convenience function to create token response"""
    tokens = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": "bearer"
    }
    return TokenRefreshResponse.from_tokens(tokens, message)

def make_simple_response(success: bool = True, 
                        message: str = "Success") -> APIResponse[None]:
    """Convenience function for simple responses"""
    if success:
        return APIResponse.success_response(message=message)
    else:
        return APIResponse.error_response(message=message)
    
class TokenResponseSchema():
    pass