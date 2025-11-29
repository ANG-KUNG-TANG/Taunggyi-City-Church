from typing import Optional, Dict, Any, List
from .base import BaseAppException, ErrorContext


class DomainException(BaseAppException):
    """Base class for domain-specific exceptions."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DOMAIN_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class ValidationException(DomainException):
    """Exception for validation errors (replaces HTTP ValidationException)."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        if field_errors:
            details['field_errors'] = field_errors
            
        if not user_message:
            user_message = "Validation failed. Please check your input."
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class AuthenticationException(DomainException):
    """Authentication failed exception."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=401,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message or "Authentication required"
        )


class PermissionException(DomainException):
    """Permission denied exception."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=403,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message or "You don't have permission to perform this action"
        )


class NotFoundException(DomainException):
    """Resource not found exception."""
    
    def __init__(
        self,
        entity_name: str,
        entity_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        message = f"{entity_name} not found"
        if entity_id:
            message = f"{entity_name} with ID '{entity_id}' not found"
            
        if not user_message:
            user_message = f"{entity_name} not found"
            if entity_id:
                user_message = f"{entity_name} with ID '{entity_id}' not found"
            
        details = details or {}
        details.update({
            'entity_name': entity_name,
            'entity_id': entity_id,
            'lookup_params': lookup_params,
        })
            
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class BusinessRuleException(DomainException):
    """Exception for business rule violations."""
    
    def __init__(
        self,
        rule_name: str,
        message: str,
        rule_description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        details = details or {}
        details.update({
            'rule_name': rule_name,
            'rule_description': rule_description or message,
        })
            
        if not user_message:
            user_message = "A business rule violation occurred."
            
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VIOLATION",
            status_code=422,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )


class ConcurrencyException(DomainException):
    """Exception for concurrency conflicts."""
    
    def __init__(
        self,
        entity_name: str,
        entity_id: str,
        expected_version: Optional[int] = None,
        actual_version: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        message = f"Concurrency conflict for {entity_name} with ID '{entity_id}'"
        
        if not user_message:
            user_message = "The data has been modified by another user. Please refresh and try again."
            
        details = details or {}
        details.update({
            'entity_name': entity_name,
            'entity_id': entity_id,
            'expected_version': expected_version,
            'actual_version': actual_version,
        })
            
        super().__init__(
            message=message,
            error_code="CONCURRENCY_CONFLICT",
            status_code=409,
            details=details,
            context=context,
            cause=cause,
            user_message=user_message
        )