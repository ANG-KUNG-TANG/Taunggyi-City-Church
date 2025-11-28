from typing import Dict, Any, Optional, List
from contextlib import contextmanager

class ValidationContext:
    """
    Context manager for validation operations
    Tracks validation errors and context
    """
    
    def __init__(self):
        self.errors: Dict[str, List[str]] = {}
        self.context: Dict[str, Any] = {}
    
    def add_error(self, field: str, message: str) -> None:
        """Add a validation error for a field"""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors"""
        return bool(self.errors)
    
    def get_errors(self) -> Dict[str, List[str]]:
        """Get all validation errors"""
        return self.errors.copy()
    
    def set_context(self, key: str, value: Any) -> None:
        """Set context information"""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information"""
        return self.context.get(key, default)
    
    def clear(self) -> None:
        """Clear all errors and context"""
        self.errors.clear()
        self.context.clear()

# Global validation context manager
_global_validation_context = ValidationContext()

@contextmanager
def validation_context():
    """
    Context manager for validation operations
    
    Usage:
        with validation_context() as ctx:
            ctx.add_error('field', 'Error message')
            if ctx.has_errors():
                from .exceptions import ValidationError
                raise ValidationError("Validation failed", ctx.get_errors())
    """
    ctx = ValidationContext()
    try:
        yield ctx
    finally:
        if ctx.has_errors():
            from .exceptions import ValidationError
            raise ValidationError("Validation failed", ctx.get_errors())