"""
Centralized exception handler for Django REST Framework.

Expected application exceptions and framework exceptions are converted
into a consistent API error response.

Unexpected exceptions are logged internally and return a safe response.
"""

import logging

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.http import Http404

from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.exceptions import ApplicationException


logger = logging.getLogger(__name__)


def get_request_id(request):
    """Return the request ID already assigned by middleware."""

    request_id = getattr(request, "id", None)

    if request_id:
        return str(request_id)

    return request.META.get("HTTP_X_REQUEST_ID", "NO_REQUEST_ID")


def get_error_code(exception, status_code):
    """Return a stable error code for framework exceptions."""

    if isinstance(exception, drf_exceptions.ValidationError):
        return "VALIDATION_ERROR"

    if isinstance(exception, DjangoValidationError):
        return "VALIDATION_ERROR"

    if isinstance(exception, drf_exceptions.AuthenticationFailed):
        return "AUTHENTICATION_REQUIRED"

    if isinstance(exception, drf_exceptions.NotAuthenticated):
        return "AUTHENTICATION_REQUIRED"

    if isinstance(exception, (drf_exceptions.PermissionDenied, DjangoPermissionDenied)):
        return "PERMISSION_DENIED"

    if isinstance(exception, (Http404, drf_exceptions.NotFound)):
        return "RESOURCE_NOT_FOUND"

    if isinstance(exception, drf_exceptions.Throttled):
        return "RATE_LIMIT_EXCEEDED"

    if status_code == 400:
        return "INVALID_REQUEST"

    if status_code == 401:
        return "AUTHENTICATION_REQUIRED"

    if status_code == 403:
        return "PERMISSION_DENIED"

    if status_code == 404:
        return "RESOURCE_NOT_FOUND"

    if status_code == 409:
        return "RESOURCE_CONFLICT"

    if status_code == 429:
        return "RATE_LIMIT_EXCEEDED"

    return "APPLICATION_ERROR"


def get_error_message(exception, status_code):
    """Return a safe, client-facing error message."""

    if isinstance(exception, ApplicationException):
        return exception.message

    if isinstance(exception, drf_exceptions.ValidationError):
        return "The request contains invalid data."

    if isinstance(exception, DjangoValidationError):
        return "The request contains invalid data."

    if isinstance(exception, drf_exceptions.AuthenticationFailed):
        return "Authentication failed."

    if isinstance(exception, drf_exceptions.NotAuthenticated):
        return "Authentication is required."

    if isinstance(exception, (drf_exceptions.PermissionDenied, DjangoPermissionDenied)):
        return "You do not have permission to perform this action."

    if isinstance(exception, (Http404, drf_exceptions.NotFound)):
        return "The requested resource was not found."

    if isinstance(exception, drf_exceptions.Throttled):
        return "Too many requests. Please try again later."

    if status_code == 400:
        return "The request is invalid."

    if status_code == 401:
        return "Authentication is required."

    if status_code == 403:
        return "You do not have permission to perform this action."

    if status_code == 404:
        return "The requested resource was not found."

    if status_code == 409:
        return "The request conflicts with existing data."

    if status_code == 429:
        return "Too many requests. Please try again later."

    return "An application error occurred."


def get_error_details(exception, framework_response=None):
    """Return structured details when they are safe and available."""

    if isinstance(exception, ApplicationException):
        return exception.details

    if isinstance(exception, drf_exceptions.ValidationError):
        return exception.detail

    if isinstance(exception, DjangoValidationError):
        return (
            exception.message_dict
            if hasattr(exception, "message_dict")
            else exception.messages
        )

    if framework_response is not None:
        return framework_response.data

    return None


def build_error_response(
    request,
    *,
    code,
    message,
    status_code,
    details=None,
):
    """Build the standard API error response."""

    error = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    request_id = get_request_id(request)

    response = Response(
        {
            "error": error,
            "request_id": request_id,
        },
        status=status_code,
    )

    response["X-Request-ID"] = request_id

    return response


def exception_handler(exception, context):
    """
    Convert exceptions into a consistent response envelope.

    The handler does not suppress exceptions silently. Unexpected errors
    are logged and returned as generic internal-server errors.
    """

    request = context.get("request")

    if request is None:
        return drf_exception_handler(exception, context)

    if isinstance(exception, ApplicationException):
        return build_error_response(
            request,
            code=exception.code,
            message=exception.message,
            status_code=exception.status_code,
            details=exception.details,
        )

    if isinstance(exception, DjangoValidationError):
        return build_error_response(
            request,
            code="VALIDATION_ERROR",
            message="The request contains invalid data.",
            status_code=400,
            details=get_error_details(exception),
        )

    if isinstance(exception, DjangoPermissionDenied):
        return build_error_response(
            request,
            code="PERMISSION_DENIED",
            message="You do not have permission to perform this action.",
            status_code=403,
        )

    if isinstance(exception, Http404):
        return build_error_response(
            request,
            code="RESOURCE_NOT_FOUND",
            message="The requested resource was not found.",
            status_code=404,
        )

    framework_response = drf_exception_handler(exception, context)

    if framework_response is not None:
        status_code = framework_response.status_code

        return build_error_response(
            request,
            code=get_error_code(exception, status_code),
            message=get_error_message(exception, status_code),
            status_code=status_code,
            details=get_error_details(exception, framework_response),
        )

    logger.error(
        "Unhandled API exception",
        exc_info=(
            type(exception),
            exception,
            exception.__traceback__,
        ),
        extra={
            "request_id": get_request_id(request),
            "path": request.path,
        },
    )

    return build_error_response(
        request,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        status_code=500,
    )
