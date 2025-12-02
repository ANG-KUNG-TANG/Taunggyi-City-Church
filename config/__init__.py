"""
Apply patches when Django starts
"""

# Apply patches for async views
try:
    # Patch DRF's @api_view decorator
    import rest_framework.decorators
    from asgiref.sync import async_to_sync
    from functools import wraps
    
    original_api_view = rest_framework.decorators.api_view
    
    def patched_api_view(http_method_names=None):
        def decorator(func):
            import inspect
            if inspect.iscoroutinefunction(func):
                @wraps(func)
                def sync_wrapper(request, *args, **kwargs):
                    return async_to_sync(func)(request, *args, **kwargs)
                return original_api_view(http_method_names)(sync_wrapper)
            return original_api_view(http_method_names)(func)
        return decorator
    
    rest_framework.decorators.api_view = patched_api_view
    print("✓ Patched DRF @api_view decorator for async support")
    
except Exception as e:
    print(f"Warning: Could not patch DRF: {e}")