# config/middleware.py
import uuid
import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 1. Request ID Middleware
# ──────────────────────────────────────────────
class RequestIDMiddleware(MiddlewareMixin):
    def __init__(self, get_response: Callable):
        self.get_response = get_response

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
            import threading
            threading.local().request_id = request_id
        except Exception as e:
            logger.warning(f"Failed to set request_id: {e}")

    def _log_request(self, request: HttpRequest, response: HttpResponse):
        log_data = {
            'request_id': request.request_id,
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
# 2. Request ID Filter (FOR LOGGING)
# ──────────────────────────────────────────────
class RequestIDFilter(logging.Filter):
    def filter(self, record):
        try:
            import threading
            record.request_id = getattr(threading.local(), 'request_id', 'no-request-id')
        except Exception:
            record.request_id = 'no-request-id'
        return True


# ──────────────────────────────────────────────
# 3. Slow Query Logger
# ──────────────────────────────────────────────
class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.logger = logging.getLogger('db.performance')

    def __call__(self, request: HttpRequest) -> HttpResponse:
        from django.db import connection
        from time import time

        start = time()
        response = self.get_response(request)
        total_time = time() - start

        for query in connection.queries:
            qtime = float(query.get('time', 0))
            if qtime > 1.0:
                self.logger.warning(
                    "SLOW QUERY",
                    extra={
                        'request_id': getattr(request, 'request_id', 'unknown'),
                        'sql': query['sql'][:500],
                        'time': qtime,
                        'path': request.path
                    }
                )

        if total_time > 5.0:
            self.logger.warning(
                "SLOW REQUEST",
                extra={
                    'request_id': getattr(request, 'request_id', 'unknown'),
                    'time': total_time,
                    'path': request.path
                }
            )

        return response


# ──────────────────────────────────────────────
# 4. Security Headers
# ──────────────────────────────────────────────
class SecurityHeadersMiddleware(MiddlewareMixin):
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