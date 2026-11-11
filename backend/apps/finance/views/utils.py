"""Shared utilities for finance API views."""

from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


def raise_service_error(error):
    """Translate Django service exceptions into DRF API exceptions."""

    if isinstance(error, ValidationError):
        detail = (
            error.message_dict if hasattr(error, "message_dict") else error.messages
        )
        raise DRFValidationError(detail)

    if isinstance(error, PermissionDenied):
        from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

        raise DRFPermissionDenied(str(error))

    raise error


def get_correlation_id(request):
    """Read and validate the optional X-Correlation-ID header."""

    value = request.headers.get("X-Correlation-ID")

    if not value:
        return None

    try:
        return UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise DRFValidationError({"X-Correlation-ID": "A valid UUID is required."})
