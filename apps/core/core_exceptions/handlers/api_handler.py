import logging
from typing import Any, Dict, Optional

from django.http import JsonResponse
from rest_framework.views import exception_handler as drf_default_handler
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.request import Request

from core.core_exceptions.base import BaseAppException
from core.core_exceptions.domain import ValidationException, AuthenticationException, PermissionException, NotFoundException
from apps.core.core_exceptions.logging.context import context_manager

logger = logging.getLogger(__name__)


class APIExceptionHandler:
    """
    Centralized exception handler for Django REST Framework.
    Uses unified context system.
    """

    @staticmethod
    def handle_exception(exc: Exception, context: Dict[str, Any]) -> JsonResponse:
        """
        Main entry point used by Django REST Framework.
        """
        request: Request = context.get("request")

        # Update global context from request
        if request:
            APIExceptionHandler._update_context_from_request(request)

        # Get current context
        error_context = context_manager.get_context()

        # 1. Custom application exceptions
        if isinstance(exc, BaseAppException):
            return APIExceptionHandler._handle_custom_exception(exc, error_context)

        # 2. DRF validation errors
        if isinstance(exc, ValidationError):
            return APIExceptionHandler._handle_validation_error(exc, error_context)

        # 3. DRF exceptions
        if isinstance(exc, APIException):
            return APIExceptionHandler._handle_drf_api_exception(exc, error_context)

        # 4. Fallback to DRF default handler
        response = drf_default_handler(exc, context)
        if response is not None:
            return APIExceptionHandler._format_drf_response(response)

        # 5. Unexpected error
        return APIExceptionHandler._handle_unexpected_exception(exc, error_context)

    @staticmethod
    def _handle_custom_exception(exc: BaseAppException, context) -> JsonResponse:
        # Use context directly
        exc.with_context(**context.to_dict())
        logger.warning(
            f"Handled application exception: {exc.message}",
            extra={'exception_details': exc.to_dict()}
        )
        return JsonResponse(exc.to_dict(), status=exc.status_code)

    @staticmethod
    def _handle_drf_api_exception(exc: APIException, context) -> JsonResponse:
        """Convert DRF APIException to appropriate domain exception."""
        
        # Map DRF exceptions to domain exceptions
        if exc.status_code == 401:
            domain_exc = AuthenticationException(
                message=str(exc.detail),
                context=context
            )
        elif exc.status_code == 403:
            domain_exc = PermissionException(
                message=str(exc.detail),
                context=context
            )
        elif exc.status_code == 404:
            domain_exc = NotFoundException(
                entity_name="Resource",
                context=context,
                user_message=str(exc.detail)
            )
        else:
            # For other DRF exceptions, create a generic domain exception
            from core.core_exceptions.base import CriticalException
            domain_exc = CriticalException(
                message=str(exc.detail),
                status_code=exc.status_code,
                context=context
            )

        logger.warning(
            f"Handled DRF API exception: {exc.detail}",
            extra={'exception_details': domain_exc.to_dict()}
        )

        return JsonResponse(domain_exc.to_dict(), status=domain_exc.status_code)

    @staticmethod
    def _handle_validation_error(exc: ValidationError, context) -> JsonResponse:
        """Convert DRF ValidationError to domain ValidationException."""
        
        validation_exception = ValidationException(
            message="Validation failed",
            field_errors=exc.detail,
            context=context
        )

        logger.warning(
            "Handled validation error",
            extra={'exception_details': validation_exception.to_dict()}
        )

        return JsonResponse(
            validation_exception.to_dict(),
            status=validation_exception.status_code
        )

    @staticmethod
    def _format_drf_response(response: Any) -> JsonResponse:
        if hasattr(response, 'data'):
            error_data = {
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed",
                    "details": response.data
                }
            }
            return JsonResponse(error_data, status=response.status_code)
        return response

    @staticmethod
    def _handle_unexpected_exception(exc: Exception, context) -> JsonResponse:
        logger.error(
            f"Unhandled exception in API: {str(exc)}",
            exc_info=True,
            extra={'context': context.to_dict()}
        )

        from core.core_exceptions.base import CriticalException
        critical = CriticalException(
            message="An unexpected server error occurred",
            context=context,
            cause=exc
        )

        return JsonResponse(critical.to_dict(), status=critical.status_code)

    @staticmethod
    def _update_context_from_request(request: Request) -> None:
        """Update global context from Django request."""
        context_updates = {
            'endpoint': request.path,
            'method': request.method,
            'ip_address': APIExceptionHandler._get_client_ip(request),
            'user_agent': request.META.get("HTTP_USER_AGENT"),
        }

        # Add request ID from headers if present
        request_id = request.headers.get("X-Request-ID")
        if request_id:
            context_updates['request_id'] = request_id

        # Add user info if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            context_updates['user_id'] = str(request.user.id)

        context_manager.set_context(**context_updates)

    @staticmethod
    def _get_client_ip(request: Request) -> Optional[str]:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")