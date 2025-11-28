import html
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class BaseEntity(ABC):
    """Base entity class with common functionality for all domain entities"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
    
    @abstractmethod
    def prepare_for_persistence(self):
        """Prepare entity for database operations - must be implemented by subclasses"""
        pass
    
    @classmethod
    @abstractmethod
    def from_model(cls, model):
        """Create entity from Django model - must be implemented by subclasses"""
        pass
    
    def sanitize_string(self, value: Optional[str]) -> Optional[str]:
        """Sanitize string input to prevent XSS"""
        if value is None:
            return None
        return html.escape(value.strip())
    
    def update_timestamps(self):
        """Update created_at and updated_at timestamps"""
        now = timezone.now()  # ← Use timezone-aware datetime
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                # Handle datetime objects
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result
    
    def validate_required_fields(self, required_fields: list) -> list:
        """Validate required fields, return list of errors"""
        errors = []
        for field in required_fields:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field} is required")
        return errors
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id is not None and other.id is not None and self.id == other.id
    
    def __hash__(self) -> int:
        return hash((self.__class__, self.id))