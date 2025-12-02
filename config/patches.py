"""
Monkey patches to fix async view support in Django REST Framework
"""
import sys
from functools import wraps

def patch_drf_for_async():
    """Patch DRF's @api_view decorator to support async views"""
    try:
        import rest_framework.decorators
        from asgiref.sync import async_to_sync
        
        # Store original
        original_api_view = rest_framework.decorators.api_view
        
        def patched_api_view(http_method_names=None):
            def decorator(func):
                # Check if function is async
                import inspect
                if inspect.iscoroutinefunction(func):
                    @wraps(func)
                    def sync_wrapper(request, *args, **kwargs):
                        return async_to_sync(func)(request, *args, **kwargs)
                    return original_api_view(http_method_names)(sync_wrapper)
                return original_api_view(http_method_names)(func)
            return decorator
        
        # Apply patch
        rest_framework.decorators.api_view = patched_api_view
        print("✓ Patched DRF @api_view decorator for async support")
        
    except ImportError as e:
        print(f"Warning: Could not patch DRF: {e}")