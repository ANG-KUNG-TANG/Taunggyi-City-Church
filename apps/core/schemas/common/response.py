from typing import Generic, TypeVar, Optional, Any, Dict, List
from datetime import datetime
from apps.core.schemas.out_schemas.base import BaseOutputSchema

T = TypeVar('T')

class APIResponse(BaseOutputSchema, Generic[T]):
    """Standard API response schema."""
    
    success: bool
    message: str
    data: Optional[T] = None
    timestamp: datetime
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)
    
    @classmethod
    def success(cls, message: str = "Success", data: Optional[T] = None) -> 'APIResponse[T]':
        """Create a success response."""
        return cls(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.now()
        )
    
    @classmethod
    def error(cls, message: str = "Error", data: Optional[T] = None) -> 'APIResponse[T]':
        """Create an error response."""
        return cls(
            success=False,
            message=message,
            data=data,
            timestamp=datetime.now()
        )

class ErrorResponse(BaseOutputSchema):
    """Error response schema."""
    
    code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime
    
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

class SuccessResponse(BaseOutputSchema):
    """Simple success response."""
    success: bool = True
    message: str
    timestamp: datetime
    
    def __init__(self, message: str = "Success", **data):
        data.update({
            'message': message,
            'timestamp': datetime.now()
        })
        super().__init__(**data)