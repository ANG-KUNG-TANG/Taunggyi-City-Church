from asgiref.sync import async_to_sync, sync_to_async
from django.utils.deprecation import MiddlewareMixin
import logging
import time
import uuid
import threading
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Thread local storage for request ID
_request_local = threading.local()

def get_request_id():
    """Get current request ID from thread local"""
    return getattr(_request_local, 'request_id', 'NO_REQUEST_ID')

class RequestIDFilter(logging.Filter):
    """Add request ID to log records"""
    def filter(self, record):
        record.request_id = get_request_id()
        return True

class RequestIDMiddleware:
    """Add unique request ID to each request"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        request.id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        _request_local.request_id = request.id
        
        # Get response
        response = self.get_response(request)
        
        # Add request ID to response header
        response['X-Request-ID'] = request.id
        
        # Clean up
        if hasattr(_request_local, 'request_id'):
            del _request_local.request_id
            
        return response

class SecurityHeadersMiddleware:
    """Add security headers to responses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response

class GlobalExceptionMiddleware:
    """Global exception handler"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.get_response(request)
    
    def process_exception(self, request, exception):
        logger.error(
            f"Unhandled exception: {str(exception)}", 
            exc_info=True,
            extra={'request_id': get_request_id()}
        )
        
        # Return JSON error for API requests
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Internal server error',
                'request_id': get_request_id()
            }, status=500)
        
        return None
    
class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """Log database query performance"""
    
    def process_request(self, request):
        request.db_query_start_time = time.time()
        request.db_query_count = 0
    
    def process_response(self, request, response):
        if hasattr(request, 'db_query_start_time'):
            duration = time.time() - request.db_query_start_time
            if duration > 1.0:  # Log slow requests
                logger.warning(
                    f"Slow database queries: {duration:.2f}s, "
                    f"{getattr(request, 'db_query_count', 0)} queries",
                    extra={'request_id': get_request_id()}
                )
        return response
    
    
    


class AsyncMiddleware(MiddlewareMixin):
    """Middleware to handle async views in WSGI mode"""
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if the view is async
        if hasattr(view_func, '__code__') and view_func.__code__.co_flags & 0x80:  # CO_COROUTINE flag
            # Wrap async view to run in sync context
            request._async_view = True
        return None


