import logging
import uuid
from typing import Any, Optional
import threading


class ContextFilter(logging.Filter):
    """
    Logging filter that adds contextual information to log records.
    Provides request tracking, user context, and custom fields.
    """
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self._local = threading.local()
        self._local.context = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        # Add request ID if not present
        if not hasattr(record, 'request_id'):
            record.request_id = self._get_request_id()
        
        # Add exception ID if not present
        if not hasattr(record, 'exception_id'):
            record.exception_id = str(uuid.uuid4())
        
        # Add session ID if not present
        if not hasattr(record, 'session_id'):
            record.session_id = self._get_session_id()
        
        # Add user ID if not present
        if not hasattr(record, 'user_id'):
            record.user_id = self._get_user_id()
        
        # Add custom context fields
        for key, value in self._local.context.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        
        return True
    
    def set_context(self, **kwargs) -> None:
        """Set context variables for logging."""
        if not hasattr(self._local, 'context'):
            self._local.context = {}
        self._local.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context variables."""
        if hasattr(self._local, 'context'):
            self._local.context.clear()
    
    def get_context(self) -> dict:
        """Get current context variables."""
        if hasattr(self._local, 'context'):
            return self._local.context.copy()
        return {}
    
    def _get_request_id(self) -> str:
        """Get or generate request ID."""
        context = self.get_context()
        return context.get('request_id', str(uuid.uuid4()))
    
    def _get_session_id(self) -> Optional[str]:
        """Get session ID from context."""
        context = self.get_context()
        return context.get('session_id')
    
    def _get_user_id(self) -> Optional[str]:
        """Get user ID from context."""
        context = self.get_context()
        return context.get('user_id')


class CriticalErrorFilter(logging.Filter):
    """
    Filter that only allows critical errors to pass through.
    Useful for alerting and monitoring systems.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Only allow ERROR and CRITICAL level messages."""
        return record.levelno >= logging.ERROR


class DomainFilter(logging.Filter):
    """
    Filter that adds domain context to log records.
    """
    
    def __init__(self, domain: str, name: str = ""):
        super().__init__(name)
        self.domain = domain
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add domain information to log record."""
        if not hasattr(record, 'domain'):
            record.domain = self.domain
        return True