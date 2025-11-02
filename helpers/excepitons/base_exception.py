from abc import ABC
from typing import Optional, Dict, Any
import datetime


class BaseApplicaitonException(Exception, ABC):
    
    def __init__(
        self, message: str, error_code:str, status_code: int= 500,details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.datetime.utcnow()
        self.contex = {}
        
    def add_context(self, key: str, value: Any) -> None:
        self.contex[key] = value
    
class BusinessException(BaseApplicaitonException):
    pass

class TechnicalException(BaseApplicaitonException):
    pass

class IntegratonException(TechnicalException):
    ...
    
class DataAccessException(TechnicalException):
    ...

class DjangoORMException(TechnicalException):
    """Base exception for Django ORM related errors"""
    pass

class MySQLException(TechnicalException):
    """MySQL specific database exceptions"""
    pass
    
class ValdationException(BusinessException):
    def __init__(self, message: str, validation_errors: Dict[str, Any]):
        super().__init__(
            message = message, 
            error_code= "VALIDATION_ERROR", 
            status_code=400, 
            details={
            'validation_errors': validation_errors
            }
            )