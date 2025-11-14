import os
from typing import Optional, Dict, Any
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

def setup_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    release: Optional[str] = None,
    sample_rate: float = 1.0,
    max_breadcrumbs: int = 100,
    debug: bool = False
) -> None:
    """
    Initialize Sentry for error monitoring.
    
    Args:
        dsn: Sentry DSN (Data Source Name)
        environment: Environment name (development, staging, production)
        release: Application release version
        sample_rate: Error sampling rate (0.0 to 1.0)
        max_breadcrumbs: Maximum number of breadcrumbs
        debug: Enable Sentry debug mode
    """
    dsn = dsn or os.getenv("SENTRY_DSN")
    if not dsn:
        return
    
    # Configure Sentry logging integration
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        sample_rate=sample_rate,
        max_breadcrumbs=max_breadcrumbs,
        debug=debug,
        integrations=[sentry_logging],
        # Configure context
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
    )

def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter or modify events before sending to Sentry.
    
    Args:
        event: The event dictionary
        hint: Hint dictionary containing original exception
        
    Returns:
        Modified event or None to discard
    """
    # Filter out specific exceptions if needed
    exception = hint.get('exc_info')
    if exception:
        # Example: Don't send specific exception types
        if isinstance(exception[1], SomeSpecificException):
            return None
    
    # Add custom tags or context
    event.setdefault('tags', {}).update({
        'custom_tag': 'value'
    })
    
    return event

def before_breadcrumb(crumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter or modify breadcrumbs before adding them.
    
    Args:
        crumb: Breadcrumb dictionary
        hint: Hint dictionary
        
    Returns:
        Modified breadcrumb or None to discard
    """
    # Filter out noisy breadcrumbs
    if crumb.get('category') in ['http', 'console']:
        return None
    
    return crumb

def capture_exception(exception: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture an exception with additional context.
    
    Args:
        exception: Exception to capture
        context: Additional context information
    """
    if context:
        with sentry_sdk.configure_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
    
    sentry_sdk.capture_exception(exception)

def capture_message(message: str, level: str = "error", context: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture a message with specified level.
    
    Args:
        message: Message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context information
    """
    if context:
        with sentry_sdk.configure_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
    
    sentry_sdk.capture_message(message, level)