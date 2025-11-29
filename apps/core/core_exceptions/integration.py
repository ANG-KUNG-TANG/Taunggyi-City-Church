from typing import Optional, Dict, Any
from .base import BaseAppException, ErrorContext

from typing import Optional, Dict, Any
from .base import BaseAppException, ErrorContext


class IntegrationException(BaseAppException):
    """Base class for integration-related exceptions."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        error_code: str = "INTEGRATION_ERROR",
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'service_name': service_name,
        })
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class PaymentGatewayException(IntegrationException):
    """
    Exception for payment gateway failures.
    """
    
    def __init__(
        self,
        message: str,
        gateway_name: str,
        transaction_id: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'gateway_name': gateway_name,
            'transaction_id': transaction_id,
        })
            
        super().__init__(
            message=message,
            service_name=gateway_name,
            error_code=error_code or "PAYMENT_GATEWAY_ERROR",
            status_code=402,  # Payment Required
            details=details,
            context=context,
            cause=cause
        )


class EmailServiceException(IntegrationException):
    """
    Exception for email service failures.
    """
    
    def __init__(
        self,
        message: str,
        email_service: str = "SMTP",
        recipient: Optional[str] = None,
        template: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'email_service': email_service,
            'recipient': recipient,
            'template': template,
        })
            
        super().__init__(
            message=message,
            service_name=email_service,
            error_code="EMAIL_SERVICE_ERROR",
            status_code=502,
            details=details,
            context=context,
            cause=cause
        )


class StorageException(IntegrationException):
    """
    Exception for storage service failures.
    """
    
    def __init__(
        self,
        message: str,
        storage_service: str,
        operation: str,
        file_path: Optional[str] = None,
        bucket: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'storage_service': storage_service,
            'operation': operation,
            'file_path': file_path,
            'bucket': bucket,
        })
            
        super().__init__(
            message=message,
            service_name=storage_service,
            error_code="STORAGE_SERVICE_ERROR",
            status_code=502,
            details=details,
            context=context,
            cause=cause
        )


class ThirdPartyAPIException(IntegrationException):
    """
    Exception for third-party API failures.
    """
    
    def __init__(
        self,
        message: str,
        api_name: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'api_name': api_name,
            'endpoint': endpoint,
            'http_status_code': status_code,
            'response_body': response_body,
        })
            
        super().__init__(
            message=message,
            service_name=api_name,
            error_code="THIRD_PARTY_API_ERROR",
            status_code=502,
            details=details,
            context=context,
            cause=cause
        )


class DatabaseConnectionException(IntegrationException):
    """
    Exception for database connection failures.
    """
    
    def __init__(
        self,
        message: str,
        database_type: str = "database",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'database_type': database_type,
            'operation': operation,
        })
            
        super().__init__(
            message=message,
            service_name=database_type,
            error_code="DATABASE_CONNECTION_ERROR",
            status_code=503,
            details=details,
            context=context,
            cause=cause
        )


class DatabaseTimeoutException(IntegrationException):
    """
    Exception for database timeout failures.
    """
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: Optional[float] = None,
        database_type: str = "database",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'database_type': database_type,
            'operation': operation,
            'timeout_seconds': timeout_seconds,
        })
            
        super().__init__(
            message=message,
            service_name=database_type,
            error_code="DATABASE_TIMEOUT_ERROR",
            status_code=504,
            details=details,
            context=context,
            cause=cause
        )


class DatabaseIntegrityException(IntegrationException):
    """
    Exception for database integrity violations.
    """
    
    def __init__(
        self,
        message: str,
        constraint_type: str,
        table: str,
        database_type: str = "database",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            'database_type': database_type,
            'constraint_type': constraint_type,
            'table': table,
        })
            
        super().__init__(
            message=message,
            service_name=database_type,
            error_code="DATABASE_INTEGRITY_ERROR",
            status_code=409,
            details=details,
            context=context,
            cause=cause
        )