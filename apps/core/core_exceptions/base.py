import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Context information for error tracking and debugging."""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class BaseAppException(Exception):
    """
    Base exception class for the entire application with comprehensive
    error tracking, logging, and monitoring capabilities.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "APPLICATION_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        is_critical: bool = False
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.context = context or ErrorContext()
        self.cause = cause
        self.is_critical = is_critical
        
        # Generate unique identifiers
        self.exception_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        
        # Initialize logging
        self._logger = logging.getLogger(self.__class__.__module__)
        
        # Log the exception
        self._log_exception()
        
        # Capture for monitoring
        self._capture_for_monitoring()
        
        super().__init__(self.message)
    
    def _log_exception(self) -> None:
        """Log the exception with appropriate level and context."""
        log_level = logging.ERROR if self.is_critical else logging.WARNING
        
        log_context = {
            'exception_id': self.exception_id,
            'error_code': self.error_code,
            'status_code': self.status_code,
            'timestamp': self.timestamp.isoformat(),
            'exception_type': self.__class__.__name__,
            'is_critical': self.is_critical,
            'details': self.details,
            'context': asdict(self.context) if self.context else {},
            'cause_type': type(self.cause).__name__ if self.cause else None,
            'cause_message': str(self.cause) if self.cause else None,
        }
        
        self._logger.log(
            log_level,
            f"{self.__class__.__name__}: {self.message}",
            extra=log_context,
            exc_info=self.cause or True
        )
    
    def _capture_for_monitoring(self) -> None:
        """Capture exception for monitoring systems (Sentry, etc.)."""
        try:
            from .monitoring.sentry import capture_exception as sentry_capture
            sentry_capture(self, context=asdict(self.context))
        except ImportError:
            # Sentry not configured, skip silently
            pass
        
        # Increment metrics
        try:
            from .monitoring.metrics import error_counter
            error_counter(
                error_type=self.__class__.__name__,
                error_code=self.error_code,
                is_critical=self.is_critical
            )
        except ImportError:
            # Metrics not configured, skip silently
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        response = {
            'error': {
                'code': self.error_code,
                'message': self.message,
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
                k: v for k, v in asdict(self.context).items()
                if v is not None and k not in ['ip_address', 'user_agent']  # Remove sensitive info
            }
            if sanitized_context:
                response['error']['context'] = sanitized_context
        
        return response
    
    def to_json(self) -> str:
        """Convert exception to JSON string."""
        import json
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    def with_context(self, **kwargs) -> 'BaseAppException':
        """Add context information to the exception."""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                if not self.context.additional_info:
                    self.context.additional_info = {}
                self.context.additional_info[key] = value
        return self
    
    def get_traceback(self) -> str:
        """Get formatted traceback for debugging."""
        import traceback
        if self.cause:
            return ''.join(traceback.format_exception(
                type(self.cause), self.cause, self.cause.__traceback__
            ))
        return ''.join(traceback.format_exception(
            type(self), self, self.__traceback__
        ))
    
    def __str__(self) -> str:
        base_str = f"[{self.error_code}] {self.message} (ID: {self.exception_id})"
        if self.cause:
            base_str += f" Caused by: {type(self.cause).__name__}: {str(self.cause)}"
        return base_str
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', error_code='{self.error_code}', exception_id='{self.exception_id}')"


class CriticalException(BaseAppException):
    """
    Exception for critical system errors that require immediate attention.
    These errors typically indicate system instability or data corruption.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "CRITICAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details,
            context=context,
            cause=cause,
            is_critical=True
        )


class ConfigurationException(BaseAppException):
    """
    Exception for configuration-related errors.
    These errors occur when required configuration is missing or invalid.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        error_code: str = "CONFIGURATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
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
            is_critical=True
        )