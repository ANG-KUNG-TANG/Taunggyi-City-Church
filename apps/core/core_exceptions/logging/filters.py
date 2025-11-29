# filters.py (updated)
import logging
from .context import context_manager


class ContextFilter(logging.Filter):
    """
    Logging filter that adds unified contextual information to log records.
    """
    
    def __init__(self, name: str = ""):
        super().__init__(name)
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add unified context information to log record."""
        context = context_manager.get_context()
        
        # Add context fields to log record
        if not hasattr(record, 'request_id'):
            record.request_id = context.request_id
        
        if not hasattr(record, 'user_id'):
            record.user_id = context.user_id
        
        # Add other context fields
        for key, value in context.to_dict().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        
        return True