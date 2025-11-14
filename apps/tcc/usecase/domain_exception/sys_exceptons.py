from typing import Dict, Any, Optional, List
from apps.core.core_exceptions.base import ConfigurationException, CriticalException, ErrorContext
from apps.core.core_exceptions.integration import DatabaseConnectionException, IntegrationException, StorageException, ThirdPartyAPIException


class SystemException(CriticalException):
    """Base class for all system-level exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "SYSTEM_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class InfrastructureException(SystemException):
    """Base class for infrastructure-related exceptions"""
    pass


# Database exceptions using core IntegrationException hierarchy
class DatabasePoolExhaustedException(DatabaseConnectionException):
    def __init__(
        self,
        pool_size: int,
        active_connections: int,
        max_wait_time: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "pool_size": pool_size,
            "active_connections": active_connections,
            "max_wait_time_seconds": max_wait_time
        })
            
        super().__init__(
            message=f"Database connection pool exhausted. Pool size: {pool_size}, Active: {active_connections}",
            database_type="database",
            operation="acquire_connection",
            details=details,
            context=context,
            cause=cause
        )


# Cache System Exceptions
class CacheSystemException(IntegrationException):
    """Cache system exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "CACHE_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            service_name="cache",
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class CacheConnectionException(CacheSystemException):
    def __init__(
        self,
        cache_server: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "cache_server": cache_server,
            "operation": operation,
            "error_type": type(cause).__name__ if cause else "Unknown"
        })
            
        super().__init__(
            message=f"Cache connection failed for {cache_server} during {operation}",
            error_code="CACHE_CONNECTION_ERROR",
            status_code=503,
            details=details,
            context=context,
            cause=cause
        )


class CacheTimeoutException(CacheSystemException):
    def __init__(
        self,
        operation: str,
        timeout_seconds: int,
        key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "key": key
        })
            
        super().__init__(
            message=f"Cache operation '{operation}' timed out after {timeout_seconds} seconds",
            error_code="CACHE_TIMEOUT_ERROR",
            status_code=408,
            details=details,
            context=context,
            cause=cause
        )


# File System Exceptions
class FileSystemException(IntegrationException):
    """File system exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "FILE_SYSTEM_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            service_name="file_system",
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class FileIOException(FileSystemException):
    def __init__(
        self,
        operation: str,
        file_path: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "operation": operation,
            "file_path": file_path,
            "error_type": type(cause).__name__ if cause else "Unknown"
        })
            
        super().__init__(
            message=f"File operation '{operation}' failed for {file_path}",
            error_code="FILE_IO_ERROR",
            details=details,
            context=context,
            cause=cause
        )


class StorageQuotaExceededException(StorageException):
    def __init__(
        self,
        current_usage: int,
        quota_limit: int,
        storage_type: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "storage_type": storage_type
        })
            
        super().__init__(
            message=f"{storage_type} storage quota exceeded. Usage: {current_usage}/{quota_limit}",
            storage_service=storage_type,
            operation="write",
            details=details,
            context=context,
            cause=cause
        )


# External Service Exceptions using core IntegrationException
class ExternalServiceTimeoutException(ThirdPartyAPIException):
    def __init__(
        self,
        service: str,
        operation: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "service": service,
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })
            
        super().__init__(
            message=f"External service {service} operation '{operation}' timed out after {timeout_seconds} seconds",
            api_name=service,
            endpoint=operation,
            details=details,
            context=context,
            cause=cause
        )


class ExternalServiceUnavailableException(ThirdPartyAPIException):
    def __init__(
        self,
        service: str,
        operation: str,
        status_code: int,
        response: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "service": service,
            "operation": operation,
            "service_status_code": status_code,
            "service_response": response
        })
            
        super().__init__(
            message=f"External service {service} is unavailable for operation '{operation}'",
            api_name=service,
            endpoint=operation,
            status_code=status_code,
            response_body=response,
            details=details,
            context=context,
            cause=cause
        )


# Specialized service exceptions using core hierarchy
class SMSServiceException(ThirdPartyAPIException):
    def __init__(
        self,
        operation: str,
        phone_number: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "operation": operation,
            "phone_number": phone_number,
            "error_type": type(cause).__name__ if cause else None
        })
            
        super().__init__(
            message=f"SMS service failed for operation '{operation}' to {phone_number}",
            api_name="sms_service",
            endpoint=operation,
            details=details,
            context=context,
            cause=cause
        )


class PaymentServiceException(ThirdPartyAPIException):
    def __init__(
        self,
        operation: str,
        amount: float,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "operation": operation,
            "amount": amount,
            "error_type": type(cause).__name__ if cause else None
        })
            
        super().__init__(
            message=f"Payment service failed for operation '{operation}' with amount {amount}",
            api_name="payment_service",
            endpoint=operation,
            details=details,
            context=context,
            cause=cause
        )


# Configuration Exceptions using core ConfigurationException
class MissingConfigurationException(ConfigurationException):
    def __init__(
        self,
        config_key: str,
        service: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "config_key": config_key,
            "service": service
        })
            
        super().__init__(
            message=f"Missing configuration '{config_key}' for service '{service}'",
            config_key=config_key,
            details=details,
            context=context,
            cause=cause
        )


class InvalidConfigurationException(ConfigurationException):
    def __init__(
        self,
        config_key: str,
        config_value: Any,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "config_key": config_key,
            "config_value": config_value,
            "reason": reason
        })
            
        super().__init__(
            message=f"Invalid configuration '{config_key}' with value '{config_value}': {reason}",
            config_key=config_key,
            config_value=config_value,
            details=details,
            context=context,
            cause=cause
        )


# Resource Exhausted Exceptions
class ResourceExhaustedException(SystemException):
    """Resource exhaustion exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "RESOURCE_EXHAUSTED",
        status_code: int = 507,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            context=context,
            cause=cause
        )


class MemoryExhaustedException(ResourceExhaustedException):
    def __init__(
        self,
        current_usage: int,
        max_limit: int,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "current_usage_bytes": current_usage,
            "max_limit_bytes": max_limit
        })
            
        super().__init__(
            message=f"Memory exhausted. Usage: {current_usage} bytes, Limit: {max_limit} bytes",
            error_code="MEMORY_EXHAUSTED",
            details=details,
            context=context,
            cause=cause
        )


class CPULoadExceededException(ResourceExhaustedException):
    def __init__(
        self,
        current_load: float,
        max_load: float,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        details.update({
            "current_load_percent": current_load,
            "max_load_percent": max_load
        })
            
        super().__init__(
            message=f"CPU load exceeded. Current: {current_load}%, Max: {max_load}%",
            error_code="CPU_LOAD_EXCEEDED",
            status_code=503,
            details=details,
            context=context,
            cause=cause
        )