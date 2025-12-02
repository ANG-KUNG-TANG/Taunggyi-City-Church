import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# Import from context.py to avoid duplication
from apps.core.core_exceptions.logging.context import ErrorContext

class BaseAppException(Exception):
    """
    Base exception class for the entire application.
    Does NOT auto-log to avoid duplicate logging.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "APPLICATION_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.context = context  # Can be None - will be set later if needed
        self.cause = cause
        self.user_message = user_message or message
        
        # Generate unique identifiers
        self.exception_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        response = {
            'error': {
                'code': self.error_code,
                'message': self.user_message,
                "context": self.context.to_dict() if self.context else None,
                'type': self.__class__.__name__,
                'exception_id': self.exception_id,
                'timestamp': self.timestamp.isoformat(),
            }
        }
        
        # Add details if available
        if self.details:
            response['error']['details'] = self.details
        
        # Add context information (sanitized)
        if self.context:
            sanitized_context = {
                k: v for k, v in self.context.to_dict().items()
                if v is not None and k not in ['ip_address', 'user_agent']
            }
            if sanitized_context:
                response['error']['context'] = sanitized_context
        
        return response
    
    def with_context(self, **kwargs) -> 'BaseAppException':
        """Add context information to the exception."""
        if not self.context:
            # Create context if it doesn't exist
            self.context = ErrorContext()
            
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                self.context.additional_info[key] = value
        return self
    
    def __str__(self) -> str:
        base_str = f"[{self.error_code}] {self.message} (ID: {self.exception_id})"
        if self.cause:
            base_str += f" Caused by: {type(self.cause).__name__}: {str(self.cause)}"
        return base_str


class CriticalException(BaseAppException):
    """Exception for critical system errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "CRITICAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class ConfigurationException(BaseAppException):
    """Exception for configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        error_code: str = "CONFIGURATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        if config_key:
            details['config_key'] = config_key
        if config_value:
            details['config_value'] = config_value
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )

