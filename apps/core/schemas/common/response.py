from typing import Generic, TypeVar, Optional, Any, Dict, List
from datetime import datetime
from apps.core.schemas.out_schemas.base import BaseOutputSchema
from pydantic import ConfigDict
import json

T = TypeVar('T')

class APIResponse(BaseOutputSchema, Generic[T]):
    """Standard API response schema."""
    
    success: bool
    message: str
    data: Optional[T] = None
    timestamp: datetime
    status_code: int = 200
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)
    
    def dict(self, **kwargs):
        """Override dict method to ensure proper serialization"""
        result = super().dict(**kwargs)
        result['status_code'] = self.status_code
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status_code': self.status_code
        }
    
    @classmethod
    def success(cls, message: str = "Success", data: Optional[T] = None, status_code: int = 200) -> 'APIResponse[T]':
        """Create a success response."""
        return cls(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.now(),
            status_code=status_code
        )
    
    @classmethod
    def error(cls, message: str = "Error", data: Optional[T] = None, status_code: int = 400) -> 'APIResponse[T]':
        """Create an error response."""
        return cls(
            success=False,
            message=message,
            data=data,
            timestamp=datetime.now(),
            status_code=status_code
        )

class ErrorResponse(BaseOutputSchema):
    """Error response schema."""
    
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""
    
    def __init__(self, errors: Dict[str, Any], message: str = "Validation failed"):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details=errors
        )

class ListResponse(BaseOutputSchema, Generic[T]):
    """Generic list response."""
    items: List[T]
    total: int
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

class SuccessResponse(BaseOutputSchema):
    """Simple success response."""
    success: bool = True
    message: str
    timestamp: datetime
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    def __init__(self, message: str = "Success", **data):
        data.update({
            'message': message,
            'timestamp': datetime.now()
        })
        super().__init__(**data)