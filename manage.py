#!/usr/bin/env python
import os
import sys

# COMPREHENSIVE REDIS PATCH FOR PYTHON 3.12
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

except ImportError as e:
    print(f"Redis import warning: {e}")

def main():
    """Run administrative tasks."""
    # Try different settings locations
    settings_modules = [
        'config.settings.base',  # Your current structure
        'config.settings.prod',       # If single settings file
        'config.settings.dev',   # If dev settings exist
        'settings'               # Fallback
    ]
    
    # Set default settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
    
    # Add project root to Python path
    project_root = os.path.join(os.path.dirname(__file__), 'apps')
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Try to execute with fallback settings
    try:
        execute_from_command_line(sys.argv)
    except ModuleNotFoundError as e:
        if "settings" in str(e):
            print(f"Settings module not found: {e}")
            print("Available settings options:")
            for module in settings_modules:
                try:
                    __import__(module)
                    print(f"✓ {module}")
                except ImportError:
                    print(f"✗ {module}")
            print("\nPlease create the appropriate settings file.")
        raise
    except Exception as e:
        print(f"Error during execution: {e}")
        raise


if __name__ == '__main__':
    main()