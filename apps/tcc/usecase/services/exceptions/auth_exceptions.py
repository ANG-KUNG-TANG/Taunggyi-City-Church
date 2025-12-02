from functools import wraps
from typing import Dict, Any
import logging
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.domain_exception.auth_exceptions import (
    UnauthenticatedException,
    InvalidCredentialsException,
    AccountInactiveException,
    TokenExpiredException,
    InvalidTokenException,
    InvalidResetTokenException,
    InsufficientPermissionsException,
    ResourceAccessException,
    MinistryAccessException,
    RateLimitExceededException,
    AuthenticationException,
    AuthorizationException
)

logger = logging.getLogger(__name__)

class AuthExceptionHandler:
    """Production-level authentication and authorization exception handler."""
    
    @classmethod
    def _get_error_data(cls, exception: Exception) -> Dict[str, Any]:
        """Extract structured error data from exception."""
        error_data = {}
        
        # Common attributes across auth exceptions
        if hasattr(exception, 'details') and exception.details:
            error_data.update(exception.details)
        
        # Add error code if available
        if hasattr(exception, 'error_code'):
            error_data['error_code'] = exception.error_code
        
        # Add retry information for rate limiting
        if isinstance(exception, RateLimitExceededException):
            if hasattr(exception, 'retry_after') and exception.retry_after:
                error_data['retry_after'] = exception.retry_after
        
        return error_data
    
    @classmethod
    def _log_exception(cls, exception: Exception, func_name: str):
        """Log auth exception with security context."""
        exception_name = type(exception).__name__
        
        # High-security events
        if isinstance(exception, (InvalidCredentialsException, InsufficientPermissionsException)):
            logger.warning(
                f"Security violation in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_id': getattr(exception, 'user_id', None),
                    'username': getattr(exception, 'username', None),
                    'event_type': 'security_violation'
                }
            )
        # Rate limiting events
        elif isinstance(exception, RateLimitExceededException):
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
        
        Returns: Either domain schema (success) or APIResponse (error)
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
                
            except (UnauthenticatedException, AuthenticationException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 401)
                error_data = cls._get_error_data(e)
                
                # Return APIResponse for errors (controller will handle this)
                return APIResponse.error(
                    message=getattr(e, 'message', None) or "Authentication required",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InvalidCredentialsException, AccountInactiveException,
                   TokenExpiredException, InvalidTokenException, InvalidResetTokenException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 401)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error(
                    message=getattr(e, 'message', None) or "Authentication failed",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InsufficientPermissionsException, ResourceAccessException,
                   MinistryAccessException, AuthorizationException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 403)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error(
                    message=getattr(e, 'message', None) or "Access denied",
                    data=error_data,
                    status_code=status_code
                )
                
            except RateLimitExceededException as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 429)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error(
                    message=getattr(e, 'message', None) or "Rate limit exceeded",
                    data=error_data,
                    status_code=status_code
                )
                
        return wrapper

# Convenience function for direct usage
handle_auth_exceptions = AuthExceptionHandler.handle_auth_exceptions