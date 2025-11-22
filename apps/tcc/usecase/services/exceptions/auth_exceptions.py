from functools import wraps
from typing import Dict, Any, Optional
import logging
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    # Authentication exceptions (401)
    UnauthenticatedException,
    InvalidCredentialsException,
    AccountInactiveException,
    AccountSuspendedException,
    TokenExpiredException,
    InvalidTokenException,
    TokenRevokedException,
    SessionExpiredException,
    
    # Authorization exceptions (403)
    InsufficientPermissionsException,
    RoleBasedAccessException,
    ResourceAccessException,
    OperationNotAllowedException,
    
    # Church domain authorization exceptions (403)
    MinistryAccessException,
    FamilyAccessException,
    SacramentAccessException,
    DonationManagementException,
    EventManagementException,
    
    # Rate limiting exceptions (429)
    RateLimitExceededException,
    ConcurrentRequestLimitException,
    
    # Base exceptions
    UnauthorizedException,
    AuthenticationException,
    AuthorizationException
)

logger = logging.getLogger(__name__)

class AuthExceptionHandler:
    """Production-level authentication and authorization exception handler."""
    
    # Map exceptions to their appropriate HTTP status codes
    STATUS_CODES = {
        # Authentication (401)
        UnauthenticatedException: 401,
        InvalidCredentialsException: 401,
        AccountInactiveException: 401,
        AccountSuspendedException: 401,
        TokenExpiredException: 401,
        InvalidTokenException: 401,
        TokenRevokedException: 401,
        SessionExpiredException: 401,
        AuthenticationException: 401,
        
        # Authorization (403)
        InsufficientPermissionsException: 403,
        RoleBasedAccessException: 403,
        ResourceAccessException: 403,
        OperationNotAllowedException: 403,
        MinistryAccessException: 403,
        FamilyAccessException: 403,
        SacramentAccessException: 403,
        DonationManagementException: 403,
        EventManagementException: 403,
        AuthorizationException: 403,
        
        # Rate limiting (429)
        RateLimitExceededException: 429,
        ConcurrentRequestLimitException: 429,
        
        # Default for base exception
        UnauthorizedException: 401
    }
    
    @classmethod
    def _get_status_code(cls, exception: Exception) -> int:
        """Get appropriate HTTP status code for exception."""
        return cls.STATUS_CODES.get(type(exception), 401)
    
    @classmethod
    def _get_error_data(cls, exception: Exception) -> Dict[str, Any]:
        """Extract structured error data from exception."""
        error_data = {}
        
        # Common attributes across auth exceptions
        if hasattr(exception, 'details'):
            error_data.update(exception.details)
        
        # Add error code if available
        if hasattr(exception, 'error_code'):
            error_data['error_code'] = exception.error_code
        
        # Add retry information for rate limiting
        if isinstance(exception, (RateLimitExceededException, ConcurrentRequestLimitException)):
            if hasattr(exception, 'retry_after') and exception.retry_after:
                error_data['retry_after'] = exception.retry_after
        
        # Add security context
        if hasattr(exception, 'context'):
            error_data['context'] = {
                'timestamp': getattr(exception.context, 'timestamp', None),
                'request_id': getattr(exception.context, 'request_id', None),
                'ip_address': getattr(exception.context, 'ip_address', None),
                'user_agent': getattr(exception.context, 'user_agent', None)
            }
        
        return error_data
    
    @classmethod
    def _log_exception(cls, exception: Exception, func_name: str):
        """Log auth exception with security context."""
        exception_name = type(exception).__name__
        log_level = logging.WARNING  # Most auth exceptions are security-related
        
        # High-security events
        if isinstance(exception, (InvalidCredentialsException, AccountSuspendedException, 
                                TokenRevokedException, InsufficientPermissionsException)):
            logger.warning(
                f"Security violation in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'message': getattr(exception, 'message', None),
                    'user_id': getattr(exception, 'user_id', None),
                    'username': getattr(exception, 'username', None),
                    'ip_address': getattr(getattr(exception, 'context', None), 'ip_address', None),
                    'event_type': 'security_violation'
                }
            )
        # Rate limiting events
        elif isinstance(exception, (RateLimitExceededException, ConcurrentRequestLimitException)):
            logger.warning(
                f"Rate limit exceeded in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_id': getattr(exception, 'user_id', None),
                    'endpoint': getattr(exception, 'endpoint', None),
                    'event_type': 'rate_limit'
                }
            )
        # Other auth exceptions
        else:
            logger.info(
                f"Auth exception in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_id': getattr(exception, 'user_id', None),
                    'event_type': 'auth_exception'
                }
            )
    
    @classmethod
    def handle_auth_exceptions(cls, func):
        """
        Comprehensive decorator for handling auth-domain exceptions.
        
        Features:
        - Security event logging
        - Rate limiting support
        - Structured error responses
        - Automatic retry-after headers for rate limits
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
                
            except UnauthenticatedException as e:
                cls._log_exception(e, func.__name__)
                status_code = cls._get_status_code(e)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.message or "Authentication required",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InvalidCredentialsException, AccountInactiveException, 
                   AccountSuspendedException, TokenExpiredException,
                   InvalidTokenException, TokenRevokedException, 
                   SessionExpiredException) as e:
                cls._log_exception(e, func.__name__)
                status_code = cls._get_status_code(e)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.message or "Authentication failed",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InsufficientPermissionsException, RoleBasedAccessException,
                   ResourceAccessException, OperationNotAllowedException,
                   MinistryAccessException, FamilyAccessException,
                   SacramentAccessException, DonationManagementException,
                   EventManagementException) as e:
                cls._log_exception(e, func.__name__)
                status_code = cls._get_status_code(e)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.message or "Access denied",
                    data=error_data,
                    status_code=status_code
                )
                
            except (RateLimitExceededException, ConcurrentRequestLimitException) as e:
                cls._log_exception(e, func.__name__)
                status_code = cls._get_status_code(e)
                error_data = cls._get_error_data(e)
                
                # Add retry-after header for rate limiting
                headers = {}
                if hasattr(e, 'retry_after') and e.retry_after:
                    headers['Retry-After'] = str(e.retry_after)
                
                return APIResponse.error_response(
                    message=e.message or "Rate limit exceeded",
                    data=error_data,
                    status_code=status_code,
                    headers=headers
                )
                
            except (UnauthorizedException, AuthenticationException, 
                   AuthorizationException) as e:
                cls._log_exception(e, func.__name__)
                status_code = cls._get_status_code(e)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.message or "Authorization failed",
                    data=error_data,
                    status_code=status_code
                )
                
        return wrapper

# Convenience function for direct usage
handle_auth_exceptions = AuthExceptionHandler.handle_auth_exceptions