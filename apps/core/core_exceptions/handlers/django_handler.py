from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from core.core_exceptions.http import ValidationException


class DjangoExceptionHandler:

    @staticmethod
    def handle(exc, context):
        response = exception_handler(exc, context)

        # If DRF didn't handle it
        if response is None:
            if isinstance(exc, ValidationException):
                return Response({
                    "error": {
                        "code": "validation_error",
                        "message": str(exc.detail),
                        "field_errors": getattr(exc, "field_errors", {})
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "error": {
                    "code": "server_error",
                    "message": "An unexpected error occurred"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Standard DRF exceptions
        if hasattr(exc, "detail"):
            if isinstance(exc.detail, dict):
                response.data = {
                    "error": {
                        "code": "validation_error",
                        "message": "Validation failed",
                        "field_errors": exc.detail
                    }
                }
            else:
                response.data = {
                    "error": {
                        "code": getattr(exc, "default_code", "error"),
                        "message": str(exc.detail)
                    }
                }

        return response


def django_handler(exc, context):
    """
    DRF requires a function, not a class.
    This wrapper ensures DRF always receives a callable.
    """
    return DjangoExceptionHandler.handle(exc, context)
