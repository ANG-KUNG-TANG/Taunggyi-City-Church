import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import time
import uuid

logger = logging.getLogger(__name__)

class RequestIDFilter(logging.Filter):
    """Add request ID to log records"""
    def filter(self, record):
        from .middleware import get_request_id
        record.request_id = get_request_id()
        return True

def get_request_id():
    """Get current request ID from thread local"""
    import threading
    return getattr(threading.current_thread(), 'request_id', '')

class RequestIDMiddleware(MiddlewareMixin):
    """Add unique request ID to each request"""
    
    def process_request(self, request):
        request.id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        # Store in thread local for logging
        import threading
        threading.current_thread().request_id = request.id
    
    def process_response(self, request, response):
        response['X-Request-ID'] = getattr(request, 'id', '')
        return response

class GlobalExceptionMiddleware(MiddlewareMixin):
    """Global exception handler"""
    
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