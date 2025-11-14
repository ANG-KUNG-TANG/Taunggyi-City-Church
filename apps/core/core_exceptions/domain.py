from typing import Optional, Dict, Any, List
from .base import BaseAppException, ErrorContext


class DomainException(BaseAppException):
    """
    Base class for domain-specific exceptions.
    These exceptions represent business logic violations.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "DOMAIN_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class BusinessRuleException(DomainException):
    """
    Exception for business rule violations.
    These exceptions occur when business logic constraints are violated.
    """
    
    def __init__(
        self,
        rule_name: str,
        message: str,
        rule_description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'rule_name': rule_name,
            'rule_description': rule_description or message,
        })
            
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VIOLATION",
            status_code=422,
            details=details,
            context=context,
            cause=cause
        )


class EntityNotFoundException(DomainException):
    """
    Exception for entity not found in domain layer.
    """
    
    def __init__(
        self,
        entity_name: str,
        entity_id: Optional[str] = None,
        lookup_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        message = f"{entity_name} not found"
        if entity_id:
            message = f"{entity_name} with ID '{entity_id}' not found"
            
        details = details or {}
        details.update({
            'entity_name': entity_name,
            'entity_id': entity_id,
            'lookup_params': lookup_params,
        })
            
        super().__init__(
            message=message,
            error_code="ENTITY_NOT_FOUND",
            status_code=404,
            details=details,
            context=context,
            cause=cause
        )


class ValidationException(DomainException):
    """
    Exception for domain validation errors.
    """
    
    def __init__(
        self,
        message: str = "Domain validation failed",
        field_errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if field_errors:
            details['field_errors'] = field_errors
            
        super().__init__(
            message=message,
            error_code="DOMAIN_VALIDATION_ERROR",
            status_code=422,
            details=details,
            context=context,
            cause=cause
        )


class ConcurrencyException(DomainException):
    """
    Exception for concurrency conflicts in domain operations.
    """
    
    def __init__(
        self,
        entity_name: str,
        entity_id: str,
        expected_version: Optional[int] = None,
        actual_version: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        message = f"Concurrency conflict for {entity_name} with ID '{entity_id}'"
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
            cause=cause
        )


class DomainOperationException(DomainException):
    """
    Exception for failed domain operations.
    """
    
    def __init__(
        self,
        operation: str,
        entity_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        message = f"Operation '{operation}' failed for {entity_name}: {reason}"
        details = details or {}
        details.update({
            'operation': operation,
            'entity_name': entity_name,
            'reason': reason,
        })
            
        super().__init__(
            message=message,
            error_code="DOMAIN_OPERATION_FAILED",
            status_code=400,
            details=details,
            context=context,
            cause=cause
        )