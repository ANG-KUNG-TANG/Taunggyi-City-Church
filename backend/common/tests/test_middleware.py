"""
Tests for request ID and global exception middleware.
"""

import json

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from config.middleware import (
    GlobalExceptionMiddleware,
    RequestIDMiddleware,
    get_request_id,
)


class RequestIDMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_request_id_is_preserved_in_response_header(self):
        request = self.factory.get(
            "/api/test/",
            HTTP_X_REQUEST_ID="client-request-123",
        )

        middleware = RequestIDMiddleware(lambda request: HttpResponse("OK"))

        response = middleware(request)

        self.assertEqual(request.id, "client-request-123")
        self.assertEqual(
            response["X-Request-ID"],
            "client-request-123",
        )

    def test_request_id_is_generated_when_header_is_missing(self):
        request = self.factory.get("/api/test/")

        middleware = RequestIDMiddleware(lambda request: HttpResponse("OK"))

        response = middleware(request)

        self.assertTrue(request.id)
        self.assertEqual(
            response["X-Request-ID"],
            request.id,
        )

    def test_request_id_is_cleaned_after_successful_response(self):
        request = self.factory.get(
            "/api/test/",
            HTTP_X_REQUEST_ID="cleanup-success-123",
        )

        middleware = RequestIDMiddleware(lambda request: HttpResponse("OK"))

        middleware(request)

        self.assertEqual(
            get_request_id(),
            "NO_REQUEST_ID",
        )

    def test_request_id_is_cleaned_after_exception(self):
        request = self.factory.get(
            "/api/test/",
            HTTP_X_REQUEST_ID="cleanup-error-123",
        )

        def raise_exception(request):
            raise RuntimeError("Test exception")

        middleware = RequestIDMiddleware(raise_exception)

        with self.assertRaises(RuntimeError):
            middleware(request)

        self.assertEqual(
            get_request_id(),
            "NO_REQUEST_ID",
        )


class GlobalExceptionMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = GlobalExceptionMiddleware(lambda request: HttpResponse("OK"))

    def test_api_exception_returns_standard_error_response(self):
        request = self.factory.get(
            "/api/v1/test/",
            HTTP_X_REQUEST_ID="global-error-123",
        )
        request.id = "global-error-123"

        with self.assertLogs(
            "config.middleware",
            level="ERROR",
        ):
            response = self.middleware.process_exception(
                request,
                RuntimeError("Internal test exception"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            json.loads(response.content),
            {
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                },
                "request_id": "global-error-123",
            },
        )
        self.assertEqual(
            response["X-Request-ID"],
            "global-error-123",
        )

    def test_non_api_exception_returns_none(self):
        request = self.factory.get("/dashboard/")
        request.id = "web-request-123"

        with self.assertLogs(
            "config.middleware",
            level="ERROR",
        ):
            response = self.middleware.process_exception(
                request,
                RuntimeError("Web exception"),
            )

        self.assertIsNone(response)
