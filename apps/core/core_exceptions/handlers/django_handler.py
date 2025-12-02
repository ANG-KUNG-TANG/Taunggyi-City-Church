"""
Django-specific exception handler
"""
from apps.core.core_exceptions.handlers.api_handler import APIExceptionHandler

class DjangoExceptionHandler:
    """
    Django-specific exception handler that wraps the API handler
    """
    
    @staticmethod
    def handle_exception(exc, context):
        """
        Main entry point for Django exception handling
        """
        return APIExceptionHandler.handle_exception(exc, context)

# For backward compatibility
django_handler = DjangoExceptionHandler.handle_exception