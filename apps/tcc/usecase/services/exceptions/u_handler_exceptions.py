from functools import wraps
from typing import Dict, Any, Callable
import logging

# Domain exceptions from user domain
from apps.tcc.usecase.domain_exception.u_exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidUserInputException,
    AccountLockedException,
    EmailVerificationException,
    PasswordValidationException,
    UserException
)

# Core domain exceptions for proper hierarchy
from apps.core.core_exceptions.domain import (
    BusinessRuleException,
    EntityNotFoundException,
    DomainValidationException,
    DomainException
)

logger = logging.getLogger(__name__)


class UserExceptionHandler:
    """User exception handler that integrates with Clean Architecture."""
    
    # Map user exceptions to core domain exceptions for proper handling
    _EXCEPTION_MAPPING = {
        UserNotFoundException: EntityNotFoundException,
        InvalidUserInputException: DomainValidationException,
        PasswordValidationException: DomainValidationException,
        UserAlreadyExistsException: BusinessRuleException,
        AccountLockedException: BusinessRuleException,
        EmailVerificationException: BusinessRuleException,
        UserException: DomainException
    }
    
    @classmethod
    def _log_exception(cls, exception: Exception, func_name: str) -> None:
        """Log user exception with appropriate level."""
        exception_type = type(exception)
        
        # Define log levels for different exception types
        log_levels = {
            UserAlreadyExistsException: 'warning',
            AccountLockedException: 'warning',
            InvalidUserInputException: 'info',
            PasswordValidationException: 'info',
            UserNotFoundException: 'info',
            EmailVerificationException: 'warning',
            UserException: 'error'
        }
        
        log_level = log_levels.get(exception_type, 'error')
        log_method = getattr(logger, log_level)
        
        log_method(
            f"[USER DOMAIN] {func_name}: {exception_type.__name__}",
            extra={
                'exception_type': exception_type.__name__,
                'function': func_name,
                'user_message': getattr(exception, 'user_message', None),
                'details': getattr(exception, 'details', {})
            }
        )
    
    @classmethod
    def handle_user_exceptions(cls, func: Callable) -> Callable:
        """
        Decorator for handling user-domain exceptions.
        Converts user exceptions to core domain exceptions for Clean Architecture.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
                
            except tuple(cls._EXCEPTION_MAPPING.keys()) as e:
                # Log the user exception
                cls._log_exception(e, func.__name__)
                
                # Map to core domain exception
                core_exception_class = cls._EXCEPTION_MAPPING[type(e)]
                
                # Preserve message and details
                message = getattr(e, 'user_message', None) or str(e)
                details = getattr(e, 'details', {})
                
                # Add any additional error metadata
                error_data = {}
                if hasattr(e, 'field_errors') and e.field_errors:
                    error_data['field_errors'] = e.field_errors
                if hasattr(e, 'error_code'):
                    error_data['error_code'] = e.error_code
                
                if error_data:
                    details.update(error_data)
                
                # Raise core domain exception for the view layer to handle
                raise core_exception_class(
                    message=message,
                    context=details
                )
                
        return wrapper

# Convenience function
handle_user_exceptions = UserExceptionHandler.handle_user_exceptions