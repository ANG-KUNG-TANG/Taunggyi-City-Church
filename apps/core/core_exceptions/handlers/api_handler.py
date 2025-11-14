import logging
import json
from typing import Any, Dict, Optional

from django.http import JsonResponse
from rest_framework.views import exception_handler as drf_default_handler
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.request import Request

from core.core_exceptions.base import BaseAppException, ErrorContext

logger = logging.getLogger(__name__)


class APIExceptionHandler:
    """
    Centralized exception handler for Django REST Framework.
    Provides consistent JSON responses and structured error logging.
    """

    @staticmethod
    def handle_exception(exc: Exception, context: Dict[str, Any]) -> JsonResponse:
        """
        Main entry point used by Django REST Framework.
        """

        request: Request = context.get("request")

        # Build context
        error_context = APIExceptionHandler._build_error_context(request)

        # 1. Custom application exceptions
        if isinstance(exc, BaseAppException):
            return APIExceptionHandler._handle_custom_exception(exc, error_context)

        # 2. DRF exceptions (APIException, NotFound, PermissionDenied, etc.)
        if isinstance(exc, APIException):
            return APIExceptionHandler._handle_drf_api_exception(exc, error_context)

        # 3. DRF validation errors
        if isinstance(exc, ValidationError):
            return APIExceptionHandler._handle_validation_error(exc, error_context)

        # 4. Fallback to DRF default handler
        response = drf_default_handler(exc, context)
        if response is not None:
            return response

        # 5. Unexpected error
        return APIExceptionHandler._handle_unexpected_exception(exc, error_context)

    # ----------------------------------------------------------------------

    @staticmethod
    def _handle_custom_exception(exc: BaseAppException, context: ErrorContext) -> JsonResponse:
        exc.with_context(**context.__dict__)
        return JsonResponse(exc.to_dict(), status=exc.status_code)

    @staticmethod
    def _handle_drf_api_exception(exc: APIException, context: ErrorContext) -> JsonResponse:
        """Convert DRF APIException to your custom HTTPException."""
        from core.core_exceptions.http import HTTPException

        http_exc = HTTPException(
            message=str(exc.detail),
            status_code=exc.status_code,
            context=context
        )

        return JsonResponse(http_exc.to_dict(), status=http_exc.status_code)

    @staticmethod
    def _handle_validation_error(exc: ValidationError, context: ErrorContext) -> JsonResponse:
        """Convert DRF ValidationError to your custom ValidationException."""
        from core.core_exceptions.http import ValidationException

        validation_exception = ValidationException(
            message="Validation failed",
            errors=exc.detail,
            context=context
        )

        return JsonResponse(
            validation_exception.to_dict(),
            status=validation_exception.status_code
        )

    # ----------------------------------------------------------------------

    @staticmethod
    def _handle_unexpected_exception(exc: Exception, context: ErrorContext) -> JsonResponse:
        logger.error(
            f"Unhandled exception in API: {str(exc)}",
            exc_info=True,
            extra={'context': context.__dict__}
        )

        from core.core_exceptions.base import CriticalException
        critical = CriticalException(
            message="An unexpected server error occurred",
            context=context,
            cause=exc
        )

        return JsonResponse(critical.to_dict(), status=critical.status_code)

    # ----------------------------------------------------------------------

    @staticmethod
    def _build_error_context(request: Request) -> ErrorContext:
        context = ErrorContext()

        if request:
            context.endpoint = request.path
            context.method = request.method
            context.ip_address = APIExceptionHandler._get_client_ip(request)
            context.user_agent = request.headers.get("User-Agent")

            if hasattr(request, "user") and request.user.is_authenticated:
                context.user_id = str(request.user.id)

            context.request_id = request.headers.get("X-Request-ID")

        return context

    @staticmethod
    def _get_client_ip(request: Request) -> Optional[str]:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

