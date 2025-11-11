from typing import Dict, Any, Optional, List
from usecase.exceptions.ch_exceptions import BusinessException
from .error_codes import ErrorCode

class UnauthorizedException(BusinessException):
    """Base class for all authorization-related exceptions"""
    def __init__(self, message: str, error_code: str, status_code: int = 401, 
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, error_code, status_code, details, cause)

class AuthenticationException(UnauthorizedException):
    """Authentication-related exceptions (401)"""
    pass

class AuthorizationException(UnauthorizedException):
    """Authorization-related exceptions (403)"""
    pass

# ============ AUTHENTICATION EXCEPTIONS (401) ============

class UnauthenticatedException(AuthenticationException):
    def __init__(self, message: str = "Authentication required", details: Dict = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=401,
            details=details
        )

class InvalidCredentialsException(AuthenticationException):
    def __init__(self, username: str = None, reason: str = None):
        details = {}
        if username:
            details["username"] = username
        if reason:
            details["reason"] = reason
            
        super().__init__(
            message="Invalid credentials provided",
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=401,
            details=details
        )

class AccountInactiveException(AuthenticationException):
    def __init__(self, username: str, user_id: int = None):
        details = {"username": username}
        if user_id:
            details["user_id"] = user_id
            
        super().__init__(
            message=f"Account '{username}' is inactive",
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=401,
            details=details
        )

class AccountSuspendedException(AuthenticationException):
    def __init__(self, username: str, suspension_reason: str = None, suspension_end: str = None):
        details = {
            "username": username,
            "suspension_reason": suspension_reason,
            "suspension_end": suspension_end
        }
        
        super().__init__(
            message=f"Account '{username}' is suspended",
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=401,
            details=details
        )

class TokenExpiredException(AuthenticationException):
    def __init__(self, token_type: str = "access"):
        super().__init__(
            message=f"{token_type.capitalize()} token has expired",
            error_code=ErrorCode.TOKEN_EXPIRED.value,
            status_code=401,
            details={"token_type": token_type}
        )

class InvalidTokenException(AuthenticationException):
    def __init__(self, token_type: str = "access", reason: str = None):
        details = {"token_type": token_type}
        if reason:
            details["reason"] = reason
            
        super().__init__(
            message=f"Invalid {token_type} token",
            error_code=ErrorCode.TOKEN_INVALID.value,
            status_code=401,
            details=details
        )

class TokenRevokedException(AuthenticationException):
    def __init__(self, token_type: str = "access"):
        super().__init__(
            message=f"{token_type.capitalize()} token has been revoked",
            error_code=ErrorCode.TOKEN_INVALID.value,
            status_code=401,
            details={"token_type": token_type}
        )

class SessionExpiredException(AuthenticationException):
    def __init__(self, session_id: str = None):
        details = {}
        if session_id:
            details["session_id"] = session_id
            
        super().__init__(
            message="Session has expired",
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=401,
            details=details
        )

# ============ AUTHORIZATION EXCEPTIONS (403) ============

class InsufficientPermissionsException(AuthorizationException):
    def __init__(self, user_id: int, username: str, required_permissions: List[str], 
                 user_permissions: List[str] = None, resource: str = None):
        details = {
            "user_id": user_id,
            "username": username,
            "required_permissions": required_permissions,
            "user_permissions": user_permissions or [],
            "resource": resource
        }
        
        super().__init__(
            message=f"User '{username}' lacks required permissions: {required_permissions}",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class RoleBasedAccessException(AuthorizationException):
    def __init__(self, user_id: int, username: str, user_role: str, 
                 required_roles: List[str], resource: str = None):
        details = {
            "user_id": user_id,
            "username": username,
            "user_role": user_role,
            "required_roles": required_roles,
            "resource": resource
        }
        
        super().__init__(
            message=f"User '{username}' with role '{user_role}' cannot access this resource. Required roles: {required_roles}",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class ResourceAccessException(AuthorizationException):
    def __init__(self, user_id: int, username: str, resource_type: str, 
                 resource_id: Any, action: str):
        details = {
            "user_id": user_id,
            "username": username,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action
        }
        
        super().__init__(
            message=f"User '{username}' cannot {action} {resource_type} with ID {resource_id}",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class OperationNotAllowedException(AuthorizationException):
    def __init__(self, user_id: int, username: str, operation: str, reason: str = None):
        details = {
            "user_id": user_id,
            "username": username,
            "operation": operation,
            "reason": reason
        }
        
        super().__init__(
            message=f"User '{username}' is not allowed to perform operation '{operation}'",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class ChurchDomainAuthorizationException(AuthorizationException):
    """Church domain-specific authorization exceptions"""
    pass

class MinistryAccessException(ChurchDomainAuthorizationException):
    def __init__(self, user_id: int, username: str, ministry_id: int, ministry_name: str):
        details = {
            "user_id": user_id,
            "username": username,
            "ministry_id": ministry_id,
            "ministry_name": ministry_name
        }
        
        super().__init__(
            message=f"User '{username}' does not have access to ministry '{ministry_name}'",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class FamilyAccessException(ChurchDomainAuthorizationException):
    def __init__(self, user_id: int, username: str, family_id: int, family_name: str):
        details = {
            "user_id": user_id,
            "username": username,
            "family_id": family_id,
            "family_name": family_name
        }
        
        super().__init__(
            message=f"User '{username}' does not have access to family '{family_name}'",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class SacramentAccessException(ChurchDomainAuthorizationException):
    def __init__(self, user_id: int, username: str, sacrament_type: str, required_role: str):
        details = {
            "user_id": user_id,
            "username": username,
            "sacrament_type": sacrament_type,
            "required_role": required_role
        }
        
        super().__init__(
            message=f"User '{username}' cannot administer sacrament '{sacrament_type}'. Required role: {required_role}",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class DonationManagementException(ChurchDomainAuthorizationException):
    def __init__(self, user_id: int, username: str, action: str):
        details = {
            "user_id": user_id,
            "username": username,
            "action": action
        }
        
        super().__init__(
            message=f"User '{username}' is not authorized to {action} donations",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

class EventManagementException(ChurchDomainAuthorizationException):
    def __init__(self, user_id: int, username: str, event_id: int, event_name: str, action: str):
        details = {
            "user_id": user_id,
            "username": username,
            "event_id": event_id,
            "event_name": event_name,
            "action": action
        }
        
        super().__init__(
            message=f"User '{username}' is not authorized to {action} event '{event_name}'",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details=details
        )

# ============ RATE LIMITING EXCEPTIONS ============

class RateLimitExceededException(AuthorizationException):
    def __init__(self, user_id: int, username: str, endpoint: str, 
                 limit: int, window_seconds: int, retry_after: int = None):
        details = {
            "user_id": user_id,
            "username": username,
            "endpoint": endpoint,
            "limit": limit,
            "window_seconds": window_seconds,
            "retry_after": retry_after
        }
        
        super().__init__(
            message=f"Rate limit exceeded for endpoint '{endpoint}'. Limit: {limit} requests per {window_seconds} seconds",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
            status_code=429,
            details=details
        )

class ConcurrentRequestLimitException(AuthorizationException):
    def __init__(self, user_id: int, username: str, current_requests: int, max_requests: int):
        details = {
            "user_id": user_id,
            "username": username,
            "current_requests": current_requests,
            "max_requests": max_requests
        }
        
        super().__init__(
            message=f"Concurrent request limit exceeded. Current: {current_requests}, Max: {max_requests}",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
            status_code=429,
            details=details
        )