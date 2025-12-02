#!/usr/bin/env python
import os
import sys

def main():
    """Run administrative tasks."""
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
    
    # Allow async in development
    os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
    
    # First, apply Redis patches (these don't need Django)
    try:
        import redis
        import redis.connection
        import importlib.metadata
        
        # Patch 1: Fix get_lib_version
        def patched_get_lib_version():
            try:
                return importlib.metadata.version("redis")
            except Exception:
                return "5.0.1"  # Use your actual version
        
        if hasattr(redis, 'utils'):
            redis.utils.get_lib_version = patched_get_lib_version
        
        # Patch 2: Fix AbstractConnection class variable initialization
        if hasattr(redis.connection, 'AbstractConnection'):
            original_init = redis.connection.AbstractConnection.__init__
            
            def patched_init(self, *args, **kwargs):
                # Ensure lib_version is set before parent __init__
                if not hasattr(self, 'lib_version'):
                    self.lib_version = patched_get_lib_version()
                return original_init(self, *args, **kwargs)
            
            redis.connection.AbstractConnection.__init__ = patched_init
            
        print("✓ Applied Redis patches for Python 3.12")
        
    except ImportError as e:
        print(f"Redis import warning: {e}")
    
    # Now setup Django
    try:
        import django
        django.setup()
        
        # Patch DRF's @api_view decorator for async support
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
        print(f"Django setup warning: {e}")
        # Continue anyway
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()