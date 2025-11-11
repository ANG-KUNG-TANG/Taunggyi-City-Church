from typing import Dict, Any, Optional, List
from helpers.exceptions.domain.base_exception import TechnicalException, IntegrationException, DataAccessException
from .error_codes import ErrorCode

class SystemException(TechnicalException):
    """Base class for all system-level exceptions"""
    def __init__(self, message: str, error_code: str, status_code: int = 500, 
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, error_code, status_code, details, cause)

class InfrastructureException(SystemException):
    """Base class for infrastructure-related exceptions"""
    pass

class DatabaseSystemException(InfrastructureException):
    """Database system exceptions"""
    pass

class DatabaseConnectionException(DatabaseSystemException):
    def __init__(self, database: str, operation: str, cause: Exception):
        super().__init__(
            message=f"Database connection failed for {database} during {operation}",
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR.value,
            status_code=503,
            details={
                "database": database,
                "operation": operation,
                "error_type": type(cause).__name__,
                "error_details": str(cause)
            },
            cause=cause
        )

class DatabaseTimeoutException(DatabaseSystemException):
    def __init__(self, operation: str, timeout_seconds: int, query: Optional[str] = None):
        super().__init__(
            message=f"Database operation '{operation}' timed out after {timeout_seconds} seconds",
            error_code=ErrorCode.DATABASE_TIMEOUT.value,
            status_code=408,
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                "query": query
            }
        )

class DatabasePoolExhaustedException(DatabaseSystemException):
    def __init__(self, pool_size: int, active_connections: int, max_wait_time: int):
        super().__init__(
            message=f"Database connection pool exhausted. Pool size: {pool_size}, Active: {active_connections}",
            error_code=ErrorCode.CONNECTION_POOL_EXHAUSTED.value,
            status_code=503,
            details={
                "pool_size": pool_size,
                "active_connections": active_connections,
                "max_wait_time_seconds": max_wait_time
            }
        )

class CacheSystemException(InfrastructureException):
    """Cache system exceptions"""
    pass

class CacheConnectionException(CacheSystemException):
    def __init__(self, cache_server: str, operation: str, cause: Exception):
        super().__init__(
            message=f"Cache connection failed for {cache_server} during {operation}",
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR.value,
            status_code=503,
            details={
                "cache_server": cache_server,
                "operation": operation,
                "error_type": type(cause).__name__
            },
            cause=cause
        )

class CacheTimeoutException(CacheSystemException):
    def __init__(self, operation: str, timeout_seconds: int, key: Optional[str] = None):
        super().__init__(
            message=f"Cache operation '{operation}' timed out after {timeout_seconds} seconds",
            error_code=ErrorCode.DATABASE_TIMEOUT.value,
            status_code=408,
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                "key": key
            }
        )

class FileSystemException(InfrastructureException):
    """File system exceptions"""
    pass

class FileIOException(FileSystemException):
    def __init__(self, operation: str, file_path: str, cause: Exception):
        super().__init__(
            message=f"File operation '{operation}' failed for {file_path}",
            error_code=ErrorCode.EXTERNAL_SERVICE_FAILURE.value,
            status_code=500,
            details={
                "operation": operation,
                "file_path": file_path,
                "error_type": type(cause).__name__
            },
            cause=cause
        )

class StorageQuotaExceededException(FileSystemException):
    def __init__(self, current_usage: int, quota_limit: int, storage_type: str):
        super().__init__(
            message=f"{storage_type} storage quota exceeded. Usage: {current_usage}/{quota_limit}",
            error_code=ErrorCode.PAYLOAD_TOO_LARGE.value,
            status_code=413,
            details={
                "current_usage": current_usage,
                "quota_limit": quota_limit,
                "storage_type": storage_type
            }
        )

class ExternalServiceException(IntegrationException):
    """External service integration exceptions"""
    pass

class ExternalServiceTimeoutException(ExternalServiceException):
    def __init__(self, service: str, operation: str, timeout_seconds: int, cause: Exception = None):
        super().__init__(
            message=f"External service {service} operation '{operation}' timed out after {timeout_seconds} seconds",
            error_code=ErrorCode.EXTERNAL_SERVICE_FAILURE.value,
            status_code=408,
            details={
                "service": service,
                "operation": operation,
                "timeout_seconds": timeout_seconds
            },
            cause=cause
        )

class ExternalServiceUnavailableException(ExternalServiceException):
    def __init__(self, service: str, operation: str, status_code: int, response: str = None):
        super().__init__(
            message=f"External service {service} is unavailable for operation '{operation}'",
            error_code=ErrorCode.EXTERNAL_SERVICE_FAILURE.value,
            status_code=502,
            details={
                "service": service,
                "operation": operation,
                "service_status_code": status_code,
                "service_response": response
            }
        )

class EmailServiceException(ExternalServiceException):
    def __init__(self, operation: str, recipient: str, cause: Exception = None):
        super().__init__(
            message=f"Email service failed for operation '{operation}' to {recipient}",
            error_code=ErrorCode.EMAIL_SERVICE_FAILED.value,
            status_code=500,
            details={
                "operation": operation,
                "recipient": recipient,
                "error_type": type(cause).__name__ if cause else None
            },
            cause=cause
        )

class SMSServiceException(ExternalServiceException):
    def __init__(self, operation: str, phone_number: str, cause: Exception = None):
        super().__init__(
            message=f"SMS service failed for operation '{operation}' to {phone_number}",
            error_code=ErrorCode.SMS_SERVICE_FAILED.value,
            status_code=500,
            details={
                "operation": operation,
                "phone_number": phone_number,
                "error_type": type(cause).__name__ if cause else None
            },
            cause=cause
        )

class PaymentServiceException(ExternalServiceException):
    def __init__(self, operation: str, amount: float, cause: Exception = None):
        super().__init__(
            message=f"Payment service failed for operation '{operation}' with amount {amount}",
            error_code=ErrorCode.PAYMENT_SERVICE_UNAVAILABLE.value,
            status_code=502,
            details={
                "operation": operation,
                "amount": amount,
                "error_type": type(cause).__name__ if cause else None
            },
            cause=cause
        )

class ConfigurationException(SystemException):
    """Configuration-related exceptions"""
    pass

class MissingConfigurationException(ConfigurationException):
    def __init__(self, config_key: str, service: str):
        super().__init__(
            message=f"Missing configuration '{config_key}' for service '{service}'",
            error_code=ErrorCode.EXTERNAL_SERVICE_FAILURE.value,
            status_code=500,
            details={
                "config_key": config_key,
                "service": service
            }
        )

class InvalidConfigurationException(ConfigurationException):
    def __init__(self, config_key: str, config_value: Any, reason: str):
        super().__init__(
            message=f"Invalid configuration '{config_key}' with value '{config_value}': {reason}",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=500,
            details={
                "config_key": config_key,
                "config_value": config_value,
                "reason": reason
            }
        )

class ResourceExhaustedException(SystemException):
    """Resource exhaustion exceptions"""
    pass

class MemoryExhaustedException(ResourceExhaustedException):
    def __init__(self, current_usage: int, max_limit: int):
        super().__init__(
            message=f"Memory exhausted. Usage: {current_usage} bytes, Limit: {max_limit} bytes",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
            status_code=507,  # Insufficient Storage
            details={
                "current_usage_bytes": current_usage,
                "max_limit_bytes": max_limit
            }
        )

class CPULoadExceededException(ResourceExhaustedException):
    def __init__(self, current_load: float, max_load: float):
        super().__init__(
            message=f"CPU load exceeded. Current: {current_load}%, Max: {max_load}%",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED.value,
            status_code=503,
            details={
                "current_load_percent": current_load,
                "max_load_percent": max_load
            }
        )