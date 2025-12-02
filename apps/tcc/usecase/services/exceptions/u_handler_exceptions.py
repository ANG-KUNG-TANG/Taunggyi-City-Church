from functools import wraps
from typing import Dict, Any, Callable
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
    """Enhanced user exception handler that integrates with BaseController"""
    
    @classmethod
    def _get_error_response(cls, exception: Exception, func_name: str) -> APIResponse:
        """Create appropriate error response based on exception type"""
        exception_type = type(exception).__name__
        
        # Map exceptions to appropriate status codes and messages
        exception_mapping = {
            UserAlreadyExistsException: {
                'status_code': 409,
                'default_message': 'User already exists',
                'log_level': 'warning'
            },
            AccountLockedException: {
                'status_code': 423,
                'default_message': 'Account locked',
                'log_level': 'warning'
            },
            InvalidUserInputException: {
                'status_code': 422,
                'default_message': 'Invalid input data',
                'log_level': 'info'
            },
            PasswordValidationException: {
                'status_code': 422,
                'default_message': 'Password validation failed',
                'log_level': 'info'
            },
            UserNotFoundException: {
                'status_code': 404,
                'default_message': 'User not found',
                'log_level': 'info'
            },
            EmailVerificationException: {
                'status_code': 400,
                'default_message': 'Email verification failed',
                'log_level': 'warning'
            },
            UserException: {
                'status_code': 400,
                'default_message': 'User operation failed',
                'log_level': 'error'
            }
        }
        
        config = exception_mapping.get(type(exception), {
            'status_code': 400,
            'default_message': 'Operation failed',
            'log_level': 'error'
        })
        
        # Log the exception
        log_method = getattr(logger, config['log_level'])
        log_method(
            f"User exception in {func_name}: {exception_type}",
            extra={
                'exception_type': exception_type,
                'function': func_name,
                'user_message': getattr(exception, 'user_message', None),
                'details': getattr(exception, 'details', {})
            }
        )
        
        # Build error data
        error_data = {}
        if hasattr(exception, 'details') and exception.details:
            error_data.update(exception.details)
        if hasattr(exception, 'field_errors') and exception.field_errors:
            error_data['field_errors'] = exception.field_errors
        if hasattr(exception, 'error_code'):
            error_data['error_code'] = exception.error_code
        
        return APIResponse.error_response(
            message=getattr(exception, 'user_message', None) or config['default_message'],
            data=error_data,
            status_code=config['status_code']
        )

    @classmethod
    def handle_user_exceptions(cls, func: Callable) -> Callable:
        """
        Decorator for handling user-domain exceptions.
        NOTE: This should be used INSTEAD of BaseController.handle_exceptions for user operations
        to avoid duplicate exception handling.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
                
            except (UserAlreadyExistsException, AccountLockedException,
                   InvalidUserInputException, PasswordValidationException,
                   UserNotFoundException, EmailVerificationException, 
                   UserException) as e:
                return cls._get_error_response(e, func.__name__)
                
        return wrapper

# Convenience function
handle_user_exceptions = UserExceptionHandler.handle_user_exceptions