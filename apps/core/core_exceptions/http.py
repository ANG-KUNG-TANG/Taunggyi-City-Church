from typing import Optional, Dict, Any, List, Union
from .base import BaseAppException, ErrorContext


class HTTPException(BaseAppException):
    """
    Base class for HTTP-related exceptions.
    These exceptions correspond to standard HTTP status codes.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "HTTP_ERROR",
        status_code: int = 500,
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


class NotFoundException(HTTPException):
    """
    Exception for resource not found errors (404).
    """
    
    def __init__(
        self,
        resource: str,
        resource_id: Optional[Union[str, int]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
            
        details = details or {}
        details.update({
            'resource': resource,
            'resource_id': resource_id,
        })
            
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details,
            context=context,
            cause=cause
        )


class ValidationException(HTTPException):
    """
    Exception for request validation errors (400).
    """
    
    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[Dict[str, List[str]]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if errors:
            details['validation_errors'] = errors
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details,
            context=context,
            cause=cause
        )


class AuthenticationException(HTTPException):
    """
    Exception for authentication failures (401).
    """
    
    def __init__(
        self,
        message: str = "Authentication required",
        auth_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if auth_type:
            details['auth_type'] = auth_type
            
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=401,
            details=details,
            context=context,
            cause=cause
        )


class AuthorizationException(HTTPException):
    """
    Exception for authorization failures (403).
    """
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permissions: Optional[List[str]] = None,
        user_permissions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if required_permissions:
            details['required_permissions'] = required_permissions
        if user_permissions:
            details['user_permissions'] = user_permissions
            
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            status_code=403,
            details=details,
            context=context,
            cause=cause
        )


class ConflictException(HTTPException):
    """
    Exception for resource conflicts (409).
    """
    
    def __init__(
        self,
        message: str = "Resource conflict",
        resource: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        conflict_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'resource': resource,
            'resource_id': resource_id,
            'conflict_type': conflict_type,
        })
            
        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            status_code=409,
            details=details,
            context=context,
            cause=cause
        )


class RateLimitException(HTTPException):
    """
    Exception for rate limiting (429).
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'retry_after': retry_after,
            'limit': limit,
            'window': window,
        })
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            context=context,
            cause=cause
        )


class MethodNotAllowedException(HTTPException):
    """
    Exception for HTTP method not allowed (405).
    """
    
    def __init__(
        self,
        method: str,
        allowed_methods: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        message = f"Method {method} not allowed"
        details = details or {}
        if allowed_methods:
            details['allowed_methods'] = allowed_methods
            
        super().__init__(
            message=message,
            error_code="METHOD_NOT_ALLOWED",
            status_code=405,
            details=details,
            context=context,
            cause=cause
        )


class UnsupportedMediaTypeException(HTTPException):
    """
    Exception for unsupported media type (415).
    """
    
    def __init__(
        self,
        content_type: str,
        supported_types: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        message = f"Unsupported media type: {content_type}"
        details = details or {}
        if supported_types:
            details['supported_types'] = supported_types
            
        super().__init__(
            message=message,
            error_code="UNSUPPORTED_MEDIA_TYPE",
            status_code=415,
            details=details,
            context=context,
            cause=cause
        )