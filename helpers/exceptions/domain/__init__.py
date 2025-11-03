"""
Church Project Exception Handling System
"""

from .base_exception import *
from .error_codes import ErrorCode
from .http_exceptions import *
from .domain_exceptions import *
from helpers.handlers import ErrorHandler
from helpers.error_monitor import ErrorMonitor, AlertManager, ErrorEvent

__all__ = [
    # Base
    'BaseApplicationException', 'BusinessException', 'TechnicalException',
    'IntegrationException', 'DataAccessException',
    
    # Error Codes
    'ErrorCode',
    
    # HTTP Exceptions
    'BadRequestException', 'UnauthorizedException', 'ForbiddenException',
    'NotFoundException', 'ConflictException', 'UnprocessableEntityException',
    'TooManyRequestsException', 'PayloadTooLargeException', 'ExternalServiceException',
    
    # Church Domain
    'UserAlreadyExistsException', 'MemberNotFoundException', 'EventFullException',
    'DonationFailedException', 'InvalidBaptismDateException',
    
    # Domain/Database
    'ObjectNotFoundException', 'ObjectValidationException', 'BulkOperationException',
    'MySQLIntegrityException', 'MySQLDeadlockException', 'MySQLTimeoutException',
    'DRFValidationException', 'AuthenticationException', 'PermissionException',
    
    # Handlers & Monitoring
    'ErrorHandler', 'ErrorMonitor', 'AlertManager', 'ErrorEvent'
]