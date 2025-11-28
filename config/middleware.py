import uuid
import logging
import threading
import traceback
from time import time
from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.db import connection

# ──────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────
logger = logging.getLogger("config.middleware")


# ──────────────────────────────────────────────
# 1. Request ID Middleware
# ──────────────────────────────────────────────
class RequestIDMiddleware(MiddlewareMixin):
    """Generates or extracts a request ID for logging purposes."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = self._get_request_id(request)
        request.request_id = request_id
        self._set_request_id(request_id)

        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        self._log_request(request, response)
        return response

    def _get_request_id(self, request: HttpRequest) -> str:
        return (
            request.headers.get('X-Request-ID') or
            request.GET.get('request_id') or
            str(uuid.uuid4())
        )

    def _set_request_id(self, request_id: str):
        try:
            threading.local().request_id = request_id
        except Exception as e:
            logger.warning(f"Failed to set request_id: {e}")

    def _log_request(self, request: HttpRequest, response: HttpResponse):
        log_data = {
            'request_id': getattr(request, 'request_id', 'no-request-id'),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'ip': self._get_client_ip(request),
        }

        if response.status_code >= 500:
            logger.error("Server Error", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Client Error", extra=log_data)
        else:
            logger.info("Request OK", extra=log_data)

    def _get_client_ip(self, request: HttpRequest) -> str:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return (xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR', 'unknown')).strip()


# ──────────────────────────────────────────────
# 2. Request ID Filter for Logging
# ──────────────────────────────────────────────
class RequestIDFilter(logging.Filter):
    """Attach request_id from thread-local to each log record."""

    def filter(self, record):
        try:
            record.request_id = getattr(threading.local(), 'request_id', 'no-request-id')
        except Exception:
            record.request_id = 'no-request-id'
        return True


# ──────────────────────────────────────────────
# 3. Slow Query Logger Middleware
# ──────────────────────────────────────────────
class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """Logs slow database queries and slow requests."""

    SLOW_QUERY_THRESHOLD = 1.0  # seconds
    SLOW_REQUEST_THRESHOLD = 5.0  # seconds

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time()
        response = self.get_response(request)
        total_time = time() - start_time

        # Log slow queries
        for query in connection.queries:
            qtime = float(query.get('time', 0))
            if qtime > self.SLOW_QUERY_THRESHOLD:
                logger.warning(
                    "SLOW QUERY",
                    extra={
                        'request_id': getattr(request, 'request_id', 'unknown'),
                        'sql': query['sql'][:500],
                        'time': qtime,
                        'path': request.path
                    }
                )

        # Log slow requests
        if total_time > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                "SLOW REQUEST",
                extra={
                    'request_id': getattr(request, 'request_id', 'unknown'),
                    'time': total_time,
                    'path': request.path
                }
            )

        return response


# ──────────────────────────────────────────────
# 4. Security Headers Middleware
# ──────────────────────────────────────────────
class SecurityHeadersMiddleware(MiddlewareMixin):
    """Adds common security headers."""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:"
        )
        return response


# ──────────────────────────────────────────────
# 5. Global Exception Middleware
# ──────────────────────────────────────────────
class GlobalExceptionMiddleware(MiddlewareMixin):
    """Catch all unhandled exceptions and log full traceback."""

    def process_exception(self, request, exception):
        tb = traceback.format_exc()
        logger.error("UNCAUGHT EXCEPTION:\n%s", tb, extra={'request_id': getattr(request, 'request_id', 'no-request-id')})
        return None  # Let Django handle the response (500)
