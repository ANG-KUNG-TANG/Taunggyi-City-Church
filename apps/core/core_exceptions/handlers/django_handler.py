import logging
import json
from typing import Optional, Dict, Any
from django.http import JsonResponse, HttpRequest
from django.core.exceptions import (
    PermissionDenied, 
    ObjectDoesNotExist, 
    ValidationError as DjangoValidationError
)
from django.db import IntegrityError, DatabaseError

from core.core_exceptions.base import BaseAppException, ErrorContext
from core.core_exceptions.http import (
    NotFoundException,
    AuthorizationException,
    ValidationException as HTTPValidationException
)

logger = logging.getLogger(__name__)


class DjangoExceptionHandler:
    """
    Comprehensive exception handler for Django views and middleware.
    Provides consistent error responses and logging for Django applications.
    """
    
    @staticmethod
    def handle_exception(request: HttpRequest, exception: Exception) -> JsonResponse:
        """
        Handle exceptions in Django views and return appropriate JSON responses.
        
        Args:
            request: The Django HTTP request
            exception: The exception that was raised
            
        Returns:
            JsonResponse: Appropriate JSON error response
        """
        # Build error context from request
        context = DjangoExceptionHandler._build_error_context(request)
        
        # Handle custom application exceptions
        if isinstance(exception, BaseAppException):
            return DjangoExceptionHandler._handle_custom_exception(exception, context)
        
        # Handle Django-specific exceptions
        elif isinstance(exception, PermissionDenied):
            return DjangoExceptionHandler._handle_permission_denied(exception, context)
        
        elif isinstance(exception, ObjectDoesNotExist):
            return DjangoExceptionHandler._handle_object_not_found(exception, context)
        
        elif isinstance(exception, DjangoValidationError):
            return DjangoExceptionHandler._handle_validation_error(exception, context)
        
        elif isinstance(exception, IntegrityError):
            return DjangoExceptionHandler._handle_integrity_error(exception, context)
        
        elif isinstance(exception, DatabaseError):
            return DjangoExceptionHandler._handle_database_error(exception, context)
        
        # Handle generic exceptions
        else:
            return DjangoExceptionHandler._handle_unexpected_exception(exception, context)
    
    @staticmethod
    def _handle_custom_exception(exception: BaseAppException, context: ErrorContext) -> JsonResponse:
        """Handle custom application exceptions."""
        # Add request context to the exception
        exception.with_context(**context.__dict__)
        
        # Return the exception as JSON response
        return JsonResponse(
            data=exception.to_dict(),
            status=exception.status_code,
            json_dumps_params={'indent': 2}
        )
    
    @staticmethod
    def _handle_permission_denied(exception: PermissionDenied, context: ErrorContext) -> JsonResponse:
        """Handle Django PermissionDenied exceptions."""
        auth_exception = AuthorizationException(
            message="Access denied",
            context=context
        )
        return JsonResponse(
            data=auth_exception.to_dict(),
            status=auth_exception.status_code
        )
    
    @staticmethod
    def _handle_object_not_found(exception: ObjectDoesNotExist, context: ErrorContext) -> JsonResponse:
        """Handle Django ObjectDoesNotExist exceptions."""
        not_found_exception = NotFoundException(
            resource="Resource",
            context=context
        )
        return JsonResponse(
            data=not_found_exception.to_dict(),
            status=not_found_exception.status_code
        )
    
    @staticmethod
    def _handle_validation_error(exception: DjangoValidationError, context: ErrorContext) -> JsonResponse:
        """Handle Django ValidationError exceptions."""
        # Extract validation errors
        if hasattr(exception, 'message_dict'):
            errors = exception.message_dict
        elif hasattr(exception, 'messages'):
            errors = {'non_field_errors': exception.messages}
        else:
            errors = {'non_field_errors': [str(exception)]}
        
        validation_exception = HTTPValidationException(
            message="Validation failed",
            errors=errors,
            context=context
        )
        return JsonResponse(
            data=validation_exception.to_dict(),
            status=validation_exception.status_code
        )
    
    @staticmethod
    def _handle_integrity_error(exception: IntegrityError, context: ErrorContext) -> JsonResponse:
        """Handle database integrity errors."""
        from core.core_exceptions.integration import DatabaseIntegrityException
        
        integrity_exception = DatabaseIntegrityException(
            message="Database integrity error",
            constraint_type="UNKNOWN",
            table="unknown",
            context=context,
            cause=exception
        )
        return JsonResponse(
            data=integrity_exception.to_dict(),
            status=integrity_exception.status_code
        )
    
    @staticmethod
    def _handle_database_error(exception: DatabaseError, context: ErrorContext) -> JsonResponse:
        """Handle generic database errors."""
        from core.core_exceptions.integration import DatabaseConnectionException
        
        db_exception = DatabaseConnectionException(
            message="Database error occurred",
            context=context,
            cause=exception
        )
        return JsonResponse(
            data=db_exception.to_dict(),
            status=db_exception.status_code
        )
    
    @staticmethod
    def _handle_unexpected_exception(exception: Exception, context: ErrorContext) -> JsonResponse:
        """Handle unexpected exceptions."""
        logger.error(
            f"Unhandled exception in Django view: {str(exception)}",
            exc_info=True,
            extra={'context': context.__dict__}
        )
        
        from core.core_exceptions.base import CriticalException
        critical_exception = CriticalException(
            message="An unexpected error occurred",
            context=context,
            cause=exception
        )
        return JsonResponse(
            data=critical_exception.to_dict(),
            status=critical_exception.status_code
        )
    
    @staticmethod
    def handle_404(request: HttpRequest, exception: Exception) -> JsonResponse:
        """Handle 404 errors."""
        context = DjangoExceptionHandler._build_error_context(request)
        not_found_exception = NotFoundException(
            resource="Endpoint",
            context=context
        )
        return JsonResponse(
            data=not_found_exception.to_dict(),
            status=not_found_exception.status_code
        )
    
    @staticmethod
    def handle_500(request: HttpRequest) -> JsonResponse:
        """Handle 500 errors."""
        context = DjangoExceptionHandler._build_error_context(request)
        from core.core_exceptions.base import CriticalException
        critical_exception = CriticalException(
            message="Internal server error",
            context=context
        )
        return JsonResponse(
            data=critical_exception.to_dict(),
            status=critical_exception.status_code
        )
    
    @staticmethod
    def _build_error_context(request: HttpRequest) -> ErrorContext:
        """Build error context from Django request."""
        context = ErrorContext()
        
        # Extract information from request
        context.endpoint = request.path
        context.method = request.method
        context.ip_address = DjangoExceptionHandler._get_client_ip(request)
        context.user_agent = request.META.get('HTTP_USER_AGENT')
        
        # Extract user information if available
        if hasattr(request, 'user') and request.user.is_authenticated:
            context.user_id = str(request.user.id)
        
        # Extract request ID if available
        context.request_id = request.META.get('HTTP_X_REQUEST_ID')
        
        return context
    
    @staticmethod
    def _get_client_ip(request: HttpRequest) -> Optional[str]:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip