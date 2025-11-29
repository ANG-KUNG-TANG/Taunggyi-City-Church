import uuid
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ErrorContext:
    """Unified context for errors and logging."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContextManager:
    """Thread-local context management for both logging and exceptions."""
    
    def __init__(self):
        self._local = threading.local()
        self._local.context = ErrorContext()
    
    def get_context(self) -> ErrorContext:
        """Get current context."""
        if not hasattr(self._local, 'context'):
            self._local.context = ErrorContext()
        return self._local.context
    
    def set_context(self, **kwargs) -> None:
        """Update context with new values."""
        context = self.get_context()
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.additional_info[key] = value
    
    def clear_context(self) -> None:
        """Clear context (useful for request lifecycle)."""
        self._local.context = ErrorContext()


# Global context manager instance
context_manager = ContextManager()