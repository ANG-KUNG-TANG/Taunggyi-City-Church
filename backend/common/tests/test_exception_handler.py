"""
Tests for the centralized API exception handler.
"""

from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from common.exceptions import ApplicationException, ZoneNotFound
from common.handlers.exception_handler import exception_handler


class ExceptionHandlerTests(SimpleTestCase):
    def setUp(self):
        self.request = SimpleNamespace(
            id="test-request-123",
            META={},
            path="/api/v1/test/",
        )

        self.context = {
            "request": self.request,
        }

    def test_application_exception_returns_standard_response(self):
        exception = ApplicationException(
            message="Test application error.",
            code="TEST_ERROR",
            details={"field": "name"},
            status_code=400,
        )

        response = exception_handler(exception, self.context)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {
                "error": {
                    "code": "TEST_ERROR",
                    "message": "Test application error.",
                    "details": {"field": "name"},
                },
                "request_id": "test-request-123",
            },
        )

    def test_application_exception_without_details_omits_details(self):
        exception = ApplicationException(
            message="Test application error.",
            code="TEST_ERROR",
        )

        response = exception_handler(exception, self.context)

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("details", response.data["error"])

    def test_domain_exception_preserves_status_and_code(self):
        exception = ZoneNotFound()

        response = exception_handler(exception, self.context)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"]["code"],
            exception.code,
        )
        self.assertEqual(
            response.data["error"]["message"],
            exception.message,
        )

    def test_request_id_is_in_body_and_header(self):
        exception = ApplicationException()

        response = exception_handler(exception, self.context)

        self.assertEqual(
            response.data["request_id"],
            "test-request-123",
        )
        self.assertEqual(
            response["X-Request-ID"],
            "test-request-123",
        )

    def test_request_id_falls_back_to_request_header(self):
        self.request.id = None
        self.request.META["HTTP_X_REQUEST_ID"] = "header-request-456"

        response = exception_handler(
            ApplicationException(),
            self.context,
        )

        self.assertEqual(
            response.data["request_id"],
            "header-request-456",
        )
        self.assertEqual(
            response["X-Request-ID"],
            "header-request-456",
        )

    def test_validation_error_returns_standard_response(self):
        exception = ValidationError({"email": ["Enter a valid email address."]})

        response = exception_handler(exception, self.context)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"]["code"],
            "VALIDATION_ERROR",
        )
        self.assertEqual(
            response.data["error"]["message"],
            "The request contains invalid data.",
        )
        self.assertIn("details", response.data["error"])

    def test_not_authenticated_returns_401(self):
        response = exception_handler(
            NotAuthenticated(),
            self.context,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data["error"]["code"],
            "AUTHENTICATION_REQUIRED",
        )

    def test_permission_denied_returns_403(self):
        response = exception_handler(
            PermissionDenied(),
            self.context,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["error"]["code"],
            "PERMISSION_DENIED",
        )

    def test_not_found_returns_404(self):
        response = exception_handler(
            NotFound(),
            self.context,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"]["code"],
            "RESOURCE_NOT_FOUND",
        )

    def test_unexpected_exception_returns_safe_500(self):
        exception = RuntimeError("Internal database connection details")

        with self.assertLogs(
            "common.handlers.exception_handler",
            level="ERROR",
        ) as captured:
            response = exception_handler(
                exception,
                self.context,
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.data["error"]["code"],
            "INTERNAL_SERVER_ERROR",
        )
        self.assertEqual(
            response.data["error"]["message"],
            "An unexpected error occurred.",
        )
        self.assertNotIn(
            "Internal database connection details",
            str(response.data),
        )
        self.assertTrue(captured.records)
