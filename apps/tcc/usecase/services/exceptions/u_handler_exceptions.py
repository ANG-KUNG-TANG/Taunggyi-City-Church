from functools import wraps
from typing import Dict, Any, Optional
import logging
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.domain_exception.u_exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidUserInputException,
    AccountLockedException,
    EmailVerificationException,
    PasswordValidationException,
    UserException
)

logger = logging.getLogger(__name__)

class UserExceptionHandler:
    """Production-level user exception handler."""
    
    @classmethod
    def _get_error_data(cls, exception: Exception) -> Dict[str, Any]:
        """Extract structured error data from exception."""
        error_data = {}
        
        # Common attributes across user exceptions
        if hasattr(exception, 'details') and exception.details:
            error_data.update(exception.details)
        
        # Field errors for validation exceptions
        if hasattr(exception, 'field_errors') and exception.field_errors:
            error_data['field_errors'] = exception.field_errors
        
        # Add error code if available
        if hasattr(exception, 'error_code'):
            error_data['error_code'] = exception.error_code
        
        return error_data
    
    @classmethod
    def _log_exception(cls, exception: Exception, func_name: str):
        """Log exception with appropriate level and context."""
        exception_name = type(exception).__name__
        
        # Log security-related exceptions at warning level
        if isinstance(exception, AccountLockedException):
            logger.warning(
                f"Security exception in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_message': getattr(exception, 'user_message', None),
                    'details': getattr(exception, 'details', {})
                }
            )
        else:
            logger.error(
                f"User exception in {func_name}: {exception_name}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_message': getattr(exception, 'user_message', None),
                    'details': getattr(exception, 'details', {})
                },
                exc_info=True
            )
    
    @classmethod
    def handle_user_exceptions(cls, func):
        """
        Comprehensive decorator for handling user-domain exceptions.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
                
            except UserAlreadyExistsException as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 409)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=getattr(e, 'user_message', None) or "User already exists",
                    data=error_data,
                    status_code=status_code
                )
                
            except AccountLockedException as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 423)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=getattr(e, 'user_message', None) or "Account locked",
                    data=error_data,
                    status_code=status_code
                )
                
            except (InvalidUserInputException, PasswordValidationException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 422)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=getattr(e, 'user_message', None) or "Validation failed",
                    data=error_data,
                    status_code=status_code
                )
                
            except (UserNotFoundException, EmailVerificationException, UserException) as e:
                cls._log_exception(e, func.__name__)
                status_code = getattr(e, 'status_code', 400)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=getattr(e, 'user_message', None) or "Operation failed",
                    data=error_data,
                    status_code=status_code
                )
                            
        return wrapper

# Convenience function for direct usage
handle_user_exceptions = UserExceptionHandler.handle_user_exceptions