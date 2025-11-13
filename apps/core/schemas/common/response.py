from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Generic, TypeVar
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