from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Generic, TypeVar, Dict
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

# --- User Registration Specific Schemas ---

class UserRegistrationData(BaseModel):
    """Complete user registration response data"""
    user: Dict[str, Any]  # User data as dict
    tokens: Dict[str, Any]  # Token data as dict

class UserRegistrationResponse(APIResponse[UserRegistrationData]):
    """API response for user registration"""
    
    @classmethod
    def from_user_and_tokens(cls, 
                           user_data: Dict[str, Any], 
                           tokens_data: Dict[str, Any],
                           message: str = "User created successfully") -> 'UserRegistrationResponse':
        """Convenience method to create response from user and token data"""
        data = UserRegistrationData(user=user_data, tokens=tokens_data)
        return cls.success_response(message=message, data=data)

# --- Login / Logout related schemas ---

class TokenSchema(BaseModel):
    """Token details returned on login."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None  # seconds

class UserSchema(BaseModel):
    """Basic public user info included in login responses."""
    id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class LoginData(BaseModel):
    """Payload for login response: tokens and optional user info."""
    token: TokenSchema
    user: Optional[UserSchema] = None

class LoginResponse(APIResponse[LoginData]):
    """API response returned after a successful login."""
    pass

class LogoutResponse(APIResponse[None]):
    """API response returned after logout (usually just success/message)."""
    pass

# Convenience constructors

def make_login_response(access_token: str,
                        refresh_token: Optional[str] = None,
                        expires_in: Optional[int] = None,
                        user: Optional[Dict[str, Any]] = None,
                        message: str = "Login successful") -> LoginResponse:
    token = TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    user_obj = UserSchema(**user) if user else None
    data = LoginData(token=token, user=user_obj)
    return LoginResponse.success_response(message=message, data=data)

def make_logout_response(message: str = "Logout successful") -> LogoutResponse:
    return LogoutResponse.success_response(message=message, data=None)