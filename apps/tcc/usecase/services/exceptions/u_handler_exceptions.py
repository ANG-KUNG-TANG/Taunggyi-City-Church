from functools import wraps
from typing import Dict, Any, Optional
import logging
from apps.core.schemas.common.response import APIResponse
from apps.tcc.usecase.domain_exception.u_exceptions import ( 
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidUserInputException,
    InvalidCredentialsException,
    AccountLockedException,
    InsufficientPermissionsException,
    EmailVerificationException,
    PasswordValidationException,
    UserException
)

logger = logging.getLogger(__name__)

class UserExceptionHandler:
    """Production-level user exception handler with comprehensive error handling."""
    
    # Map exceptions to their appropriate HTTP status codes
    STATUS_CODES = {
        UserAlreadyExistsException: 409,  # Conflict
        UserNotFoundException: 404,       # Not Found
        InvalidUserInputException: 422,   # Unprocessable Entity
        InvalidCredentialsException: 401, # Unauthorized
        AccountLockedException: 423,      # Locked
        InsufficientPermissionsException: 403,  # Forbidden
        EmailVerificationException: 400,  # Bad Request
        PasswordValidationException: 422, # Unprocessable Entity
        UserException: 400                # Bad Request (default for UserException)
    }
    
    @classmethod
    def _get_status_code(cls, exception: Exception) -> int:
        """Get appropriate HTTP status code for exception."""
        return cls.STATUS_CODES.get(type(exception), 400)
    
    @classmethod
    def _get_error_data(cls, exception: Exception) -> Dict[str, Any]:
        """Extract structured error data from exception."""
        error_data = {}
        
        # Common attributes across user exceptions
        if hasattr(exception, 'details'):
            error_data.update(exception.details)
        
        # Field errors for validation exceptions
        if hasattr(exception, 'field_errors'):
            error_data['field_errors'] = exception.field_errors
        
        # Add error code if available
        if hasattr(exception, 'error_code'):
            error_data['error_code'] = exception.error_code
        
        # Add context information if available
        if hasattr(exception, 'context'):
            error_data['context'] = {
                'timestamp': getattr(exception.context, 'timestamp', None),
                'request_id': getattr(exception.context, 'request_id', None),
                'user_id': getattr(exception.context, 'user_id', None)
            }
        
        return error_data
    
    @classmethod
    def _log_exception(cls, exception: Exception, func_name: str):
        """Log exception with appropriate level and context."""
        exception_name = type(exception).__name__
        
        # Log security-related exceptions at warning level
        if isinstance(exception, (InvalidCredentialsException, AccountLockedException, 
                                InsufficientPermissionsException)):
            logger.warning(
                f"Security exception in {func_name}: {exception_name} - {str(exception)}",
                extra={
                    'exception_type': exception_name,
                    'function': func_name,
                    'user_message': getattr(exception, 'user_message', None),
                    'details': getattr(exception, 'details', {})
                }
            )
        else:
            logger.error(
                f"User exception in {func_name}: {exception_name} - {str(exception)}",
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
                # Execute the function
                return await func(*args, **kwargs)
                
            except UserAlreadyExistsException as e:
                cls._log_exception(e, func.__name__)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.user_message or "User already exists",
                    data=error_data
                )
                
            except (InvalidCredentialsException, AccountLockedException) as e:
                cls._log_exception(e, func.__name__)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.user_message or "Authentication failed",
                    data=error_data
                )
                
            except (InvalidUserInputException, PasswordValidationException) as e:
                cls._log_exception(e, func.__name__)
                error_data = cls._get_error_data(e)
                
                # Ensure field_errors is included
                if hasattr(e, 'field_errors') and 'field_errors' not in error_data:
                    error_data['field_errors'] = e.field_errors
                
                return APIResponse.error_response(
                    message=e.user_message or "Validation failed",
                    data=error_data
                )
                
            except (UserNotFoundException, EmailVerificationException, 
                   InsufficientPermissionsException, UserException) as e:
                cls._log_exception(e, func.__name__)
                error_data = cls._get_error_data(e)
                
                return APIResponse.error_response(
                    message=e.user_message or "Operation failed",
                    data=error_data
                )
                            
        return wrapper

# Convenience function for direct usage
handle_user_exceptions = UserExceptionHandler.handle_user_exceptions