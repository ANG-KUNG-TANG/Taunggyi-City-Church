#!/usr/bin/env python
import os
import sys


def main():
    """Run administrative tasks."""
    # Try different settings locations
    settings_modules = [
        'config.settings.base',  # Your current structure
        'config.settings',       # If single settings file
        'config.settings.dev',   # If dev settings exist
        'settings'               # Fallback
    ]
    
    # Set default settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
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


if __name__ == '__main__':
    main()