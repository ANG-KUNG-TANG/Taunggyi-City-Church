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
    AuthorizationException,
    InvalidAuthInputException  
)
from apps.tcc.usecase.domain_exception.u_exceptions import InvalidUserInputException

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
        
        # For InvalidUserInputException or InvalidAuthInputException, add field errors if available
        if isinstance(exception, (InvalidUserInputException, InvalidAuthInputException)):
            if hasattr(exception, 'field_errors') and exception.field_errors:
                error_data['field_errors'] = exception.field_errors
            # Add operation ID if available
            if hasattr(exception, 'details') and isinstance(exception.details, dict):
                if 'operation_id' in exception.details:
                    error_data['operation_id'] = exception.details['operation_id']
        
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
        # Validation errors
        elif isinstance(exception, (InvalidUserInputException, InvalidAuthInputException)):
            logger.info(
                f"Validation error in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_id': getattr(exception, 'user_id', None),
                    'field_errors': getattr(exception, 'field_errors', {}),
                    'event_type': 'validation_error'
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
                
                # Create APIResponse with error status
                return APIResponse(
                    success=False,
                    message=getattr(e, 'message', None) or "Authentication required",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InvalidCredentialsException, AccountInactiveException,
                   TokenExpiredException, InvalidTokenException, InvalidResetTokenException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 401)
                error_data = cls._get_error_data(e)
                
                return APIResponse(
                    success=False,
                    message=getattr(e, 'message', None) or "Authentication failed",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InsufficientPermissionsException, ResourceAccessException,
                   MinistryAccessException, AuthorizationException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 403)
                error_data = cls._get_error_data(e)
                
                return APIResponse(
                    success=False,
                    message=getattr(e, 'message', None) or "Access denied",
                    data=error_data,
                    status_code=status_code
                )
                
            except RateLimitExceededException as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 429)
                error_data = cls._get_error_data(e)
                
                return APIResponse(
                    success=False,
                    message=getattr(e, 'message', None) or "Rate limit exceeded",
                    data=error_data,
                    status_code=status_code
                )
            
            except InvalidAuthInputException as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 400)
                error_data = cls._get_error_data(e)
                
                # Create a user-friendly message
                user_message = getattr(e, 'user_message', None)
                if not user_message:
                    if hasattr(e, 'field_errors') and e.field_errors:
                        # Build message from field errors
                        field_names = ', '.join(e.field_errors.keys())
                        user_message = f"Validation error in fields: {field_names}"
                    else:
                        user_message = "Invalid authentication input"
                
                return APIResponse(
                    success=False,
                    message=user_message,
                    data=error_data,
                    status_code=status_code
                )
            
            except InvalidUserInputException as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 400)
                error_data = cls._get_error_data(e)
                
                # Create a user-friendly message
                user_message = getattr(e, 'user_message', None)
                if not user_message:
                    if hasattr(e, 'field_errors') and e.field_errors:
                        # Build message from field errors
                        field_names = ', '.join(e.field_errors.keys())
                        user_message = f"Validation error in fields: {field_names}"
                    else:
                        user_message = "Invalid input data"
                
                return APIResponse(
                    success=False,
                    message=user_message,
                    data=error_data,
                    status_code=status_code
                )
                
        return wrapper

# Convenience function for direct usage
handle_auth_exceptions = AuthExceptionHandler.handle_auth_exceptions