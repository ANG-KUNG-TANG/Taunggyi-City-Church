"""
Comprehensive Exception Handling System for Church Management System

This module provides a complete exception hierarchy with proper categorization,
logging, monitoring, and domain-specific exceptions.
"""

from .base import BaseAppException, CriticalException, ConfigurationException
from .http import (
    HTTPException,
    NotFoundException,
    ValidationException as HTTPValidationException,
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    RateLimitException
)
from .domain import (
    DomainException,
    BusinessRuleException,
    EntityNotFoundException,
    ValidationException as DomainValidationException
)
from .integration import (
    IntegrationException,
    PaymentGatewayException,
    EmailServiceException,
    StorageException,
    ThirdPartyAPIException,
    DatabaseConnectionException,
    DatabaseTimeoutException,
    DatabaseIntegrityException
)

# from .domains.user_exceptions import (
#     UserException,
#     UserNotFoundException,
#     UserAlreadyExistsException,
#     InvalidCredentialsException,
#     InsufficientPermissionsException
# )
# from .domains.sermon_exceptions import (
#     SermonException,
#     SermonNotFoundException,
#     InvalidBibleReferenceException
# )
# from .domains.prayer_exceptions import (
#     PrayerException,
#     PrayerNotFoundException,
#     PrayerAccessDeniedException
# )
# from .domains.event_exceptions import (
#     EventException,
#     EventNotFoundException,
#     EventRegistrationException,
#     EventConflictException
# )
# from .domains.donation_exceptions import (
#     DonationException,
#     DonationNotFoundException,
#     PaymentProcessingException,
# #     InvalidDonationAmountException
# )

from .handlers import (
    DjangoExceptionHandler,
    APIExceptionHandler,
    BackgroundTaskExceptionHandler
)

from .logging import (
    setup_logging,
    get_logger,
    LogLevel,
    ContextFilter,
    JSONFormatter,
    AsyncLogHandler,
    ErrorMonitoringHandler
)

from .monitoring import (
    setup_sentry,
    capture_exception,
    capture_message,
    MetricsCollector,
    request_counter,
    error_counter,
    HealthCheck,
    health_check_manager
)

__all__ = [
    # Base exceptions
    'BaseAppException',
    'CriticalException',
    'ConfigurationException',
    
    # HTTP exceptions
    'HTTPException',
    'NotFoundException',
    'HTTPValidationException',
    'AuthenticationException',
    'AuthorizationException',
    'ConflictException',
    'RateLimitException',
    
    # Domain exceptions
    'DomainException',
    'BusinessRuleException',
    'EntityNotFoundException',
    'DomainValidationException',
    
    # Integration exceptions
    'IntegrationException',
    'PaymentGatewayException',
    'EmailServiceException',
    'StorageException',
    'ThirdPartyAPIException',
    'DatabaseConnectionException',
    'DatabaseTimeoutException',
    'DatabaseIntegrityException',
    
    # Domain-specific exceptions
    'UserException',
    'UserNotFoundException',
    'UserAlreadyExistsException',
    'InvalidCredentialsException',
    'InsufficientPermissionsException',
    
    'SermonException',
    'SermonNotFoundException',
    'InvalidBibleReferenceException',
    
    'PrayerException',
    'PrayerNotFoundException',
    'PrayerAccessDeniedException',
    
    'EventException',
    'EventNotFoundException',
    'EventRegistrationException',
    'EventConflictException',
    
    'DonationException',
    'DonationNotFoundException',
    'PaymentProcessingException',
    'InvalidDonationAmountException',
    
    # Handlers
    'DjangoExceptionHandler',
    'APIExceptionHandler',
    'BackgroundTaskExceptionHandler',
    
    # Logging
    'setup_logging',
    'get_logger',
    'LogLevel',
    'ContextFilter',
    'JSONFormatter',
    'AsyncLogHandler',
    'ErrorMonitoringHandler',
    
    # Monitoring
    'setup_sentry',
    'capture_exception',
    'capture_message',
    'MetricsCollector',
    'request_counter',
    'error_counter',
    'HealthCheck',
    'health_check_manager',
]