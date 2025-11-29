from typing import Dict, Any, Optional, List
from apps.core.core_exceptions.base import BaseAppException, ErrorContext


class UnauthorizedActionException(BaseAppException):
    """Base class for all authorization-related exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNAUTHORIZED_ERROR",
        status_code: int = 401,
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


class AuthenticationException(UnauthorizedActionException):
    """Authentication-related exceptions (401)"""
    pass


class AuthorizationException(UnauthorizedActionException):
    """Authorization-related exceptions (403)"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "AUTHORIZATION_ERROR",
        status_code: int = 403,
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


# ============ AUTHENTICATION EXCEPTIONS (401) ============

class UnauthenticatedException(AuthenticationException):
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_REQUIRED",
            status_code=401,
            details=details,
            context=context,
            cause=cause
        )


class InvalidCredentialsException(AuthenticationException):
    def __init__(
        self,
        username: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if username:
            details["username"] = username
        if reason:
            details["reason"] = reason
            
        super().__init__(
            message="Invalid credentials provided",
            error_code="INVALID_CREDENTIALS",
            status_code=401,
            details=details,
            context=context,
            cause=cause
        )


class AccountInactiveException(AuthenticationException):
    def __init__(
        self,
        username: str,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "username": username,
            "reason": "Account is inactive"
        })
        if user_id:
            details["user_id"] = user_id
            
        super().__init__(
            message=f"Account '{username}' is inactive",
            error_code="ACCOUNT_INACTIVE",
            status_code=401,
            details=details,
            context=context,
            cause=cause
        )


class TokenExpiredException(AuthenticationException):
    def __init__(
        self,
        token_type: str = "access",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({"token_type": token_type})
            
        super().__init__(
            message=f"{token_type.capitalize()} token has expired",
            error_code="TOKEN_EXPIRED",
            status_code=401,
            details=details,
            context=context,
            cause=cause
        )


class InvalidTokenException(AuthenticationException):
    def __init__(
        self,
        token_type: str = "access",
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({"token_type": token_type})
        if reason:
            details["reason"] = reason
            
        super().__init__(
            message=f"Invalid {token_type} token",
            error_code="INVALID_TOKEN",
            status_code=401,
            details=details,
            context=context,
            cause=cause
        )


# ============ AUTHORIZATION EXCEPTIONS (403) ============

class InsufficientPermissionsException(AuthorizationException):
    def __init__(
        self,
        user_id: int,
        username: str,
        required_permissions: List[str],
        user_permissions: Optional[List[str]] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "username": username,
            "required_permissions": required_permissions,
            "user_permissions": user_permissions or [],
            "resource": resource
        })
        
        super().__init__(
            message=f"User '{username}' lacks required permissions: {required_permissions}",
            error_code="INSUFFICIENT_PERMISSIONS",
            status_code=403,
            details=details,
            context=context,
            cause=cause
        )


class ResourceAccessException(AuthorizationException):
    def __init__(
        self,
        user_id: int,
        username: str,
        resource_type: str,
        resource_id: Any,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "username": username,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action
        })
        
        super().__init__(
            message=f"User '{username}' cannot {action} {resource_type} with ID {resource_id}",
            error_code="RESOURCE_ACCESS_DENIED",
            status_code=403,
            details=details,
            context=context,
            cause=cause
        )


# Church Domain Authorization Exceptions
class ChurchDomainAuthorizationException(AuthorizationException):
    """Church domain-specific authorization exceptions"""
    pass


class MinistryAccessException(ChurchDomainAuthorizationException):
    def __init__(
        self,
        user_id: int,
        username: str,
        ministry_id: int,
        ministry_name: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "username": username,
            "ministry_id": ministry_id,
            "ministry_name": ministry_name
        })
        
        super().__init__(
            message=f"User '{username}' does not have access to ministry '{ministry_name}'",
            error_code="MINISTRY_ACCESS_DENIED",
            status_code=403,
            details=details,
            context=context,
            cause=cause
        )


# ============ RATE LIMITING EXCEPTIONS ============

class RateLimitExceededException(AuthorizationException):
    def __init__(
        self,
        user_id: int,
        username: str,
        endpoint: str,
        limit: int,
        window_seconds: int,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "user_id": user_id,
            "username": username,
            "endpoint": endpoint,
            "limit": limit,
            "window_seconds": window_seconds,
            "retry_after": retry_after
        })
        
        super().__init__(
            message=f"Rate limit exceeded for endpoint '{endpoint}'. Limit: {limit} requests per {window_seconds} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            context=context,
            cause=cause
        )