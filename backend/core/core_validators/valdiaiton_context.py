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
        self._warnings: List[str] = []
    
    def add_error(self, field: str, message: str) -> None:
        """Add a validation error for a field"""
        if not field or not message:
            return
            
        if field not in self.errors:
            self.errors[field] = []
        
        if message not in self.errors[field]:  # Avoid duplicate messages
            self.errors[field].append(message)
    
    def add_warning(self, message: str) -> None:
        """Add a validation warning"""
        if message and message not in self._warnings:
            self._warnings.append(message)
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors"""
        return bool(self.errors)
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return bool(self._warnings)
    
    def get_errors(self) -> Dict[str, List[str]]:
        """Get all validation errors"""
        return self.errors.copy()
    
    def get_warnings(self) -> List[str]:
        """Get all warnings"""
        return self._warnings.copy()
    
    def set_context(self, key: str, value: Any) -> None:
        """Set context information"""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information"""
        return self.context.get(key, default)
    
    def clear(self) -> None:
        """Clear all errors, warnings and context"""
        self.errors.clear()
        self._warnings.clear()
        self.context.clear()
    
    def merge(self, other: 'ValidationContext') -> None:
        """Merge another validation context into this one"""
        for field, errors in other.errors.items():
            if field not in self.errors:
                self.errors[field] = []
            self.errors[field].extend(
                error for error in errors if error not in self.errors[field]
            )
        
        for warning in other._warnings:
            self.add_warning(warning)
        
        self.context.update(other.context)

@contextmanager
def validation_context():
    """
    Context manager for validation operations
    
    Usage:
        with validation_context() as ctx:
            ctx.add_error('field', 'Error message')
            if ctx.has_errors():
                raise ValidationError("Validation failed", ctx.get_errors())
    """
    ctx = ValidationContext()
    try:
        yield ctx
    finally:
        if ctx.has_errors():
            from .exceptions import ValidationError
            raise ValidationError("Validation failed", ctx.get_errors())