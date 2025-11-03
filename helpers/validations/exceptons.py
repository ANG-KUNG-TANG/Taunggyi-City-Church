from typing import Any, Dict, Optional


class ValidationError(Exception):
    """Fixed spelling: ValdationError -> ValidationError"""
    
    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None):
        self.message = message
        self.errors = errors or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message, 
            "errors": self.errors,
            "type": "VALIDATION_ERROR"
        }
    
    def __str__(self) -> str:
        return f"ValidationError: {self.message}"


class SchemaNotFoundError(Exception):
    """Raised when a schema is not found in registry"""
    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        super().__init__(f"Schema '{schema_name}' not found in registry")


class RuleValidationError(Exception):
    """Raised when custom rule validation fails"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation failed for field '{field}': {message}")