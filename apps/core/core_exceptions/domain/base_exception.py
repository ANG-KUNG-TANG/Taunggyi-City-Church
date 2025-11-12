from abc import ABC
from typing import Optional, Dict, Any
import datetime

class BaseApplicationException(Exception, ABC):
    def __init__(
        self, 
        message: str, 
        error_code: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.datetime.utcnow()
        self.context = {}
        
    def add_context(self, key: str, value: Any) -> None:
        self.context[key] = value
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'message': self.message,
            'error_code': self.error_code,
            'status_code': self.status_code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.error_code}): {self.message}"

class BusinessException(BaseApplicationException):
    pass

class TechnicalException(BaseApplicationException):
    pass

class IntegrationException(TechnicalException):
    pass

class DataAccessException(TechnicalException):
    pass