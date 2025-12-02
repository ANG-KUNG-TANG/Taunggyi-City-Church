from asgiref.sync import async_to_sync
from functools import wraps
from rest_framework.decorators import api_view

def async_api_view(http_method_names):
    """Custom decorator to handle async views with DRF"""
    def decorator(async_view_func):
        @wraps(async_view_func)
        def sync_wrapper(request, *args, **kwargs):
            return async_to_sync(async_view_func)(request, *args, **kwargs)
        return api_view(http_method_names)(sync_wrapper)
    return decorator