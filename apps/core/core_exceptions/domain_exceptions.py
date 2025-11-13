from typing import Dict, List, Any, Optional
from .base_exception import TechnicalException, BusinessException, DataAccessException
from .error_codes import ErrorCode

class DjangoORMException(DataAccessException):
    pass

class MySQLException(DataAccessException):
    pass

class DatabaseConnectionException(DataAccessException):
    def __init__(self, database: str, operation: str, cause: Exception):
        super().__init__(
            message=f"Database connection failed for {database} during {operation}",
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR.value,
            status_code=503,
            details={
                "database": database,
                "operation": operation,
                "error_type": type(cause).__name__
            },
            cause=cause
        )

class DatabaseTimeoutException(DataAccessException):
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

class ObjectNotFoundException(DjangoORMException):
    def __init__(self, model: str, lookup_params: Dict, cause: Exception = None):
        super().__init__(
            message=f"{model} object not found with parameters: {lookup_params}",
            error_code=ErrorCode.NOT_FOUND.value,
            status_code=404,
            details={"model": model, "lookup_params": lookup_params},
            cause=cause
        )

class ObjectValidationException(DjangoORMException):
    def __init__(self, model: str, validation_errors: Dict, cause: Exception = None):
        super().__init__(
            message=f"Validation failed for {model}",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=400,
            details={"model": model, "validation_errors": validation_errors},
            cause=cause
        )

class BulkOperationException(DjangoORMException):
    def __init__(self, model: str, successful: int, failed: int, errors: List):
        super().__init__(
            message=f"Bulk operation on {model} completed with {successful} successes and {failed} failures",
            error_code=ErrorCode.CONFLICT.value,
            status_code=400,
            details={
                "model": model,
                "successful_count": successful,
                "failed_count": failed,
                "errors": errors
            }
        )

class TransactionException(DjangoORMException):
    def __init__(self, operation: str, cause: Exception):
        super().__init__(
            message=f"Transaction error during {operation}",
            error_code=ErrorCode.TRANSACTION_ERROR.value,
            status_code=500,
            details={
                "operation": operation,
                "error": str(cause)
            },
            cause=cause
        )

class MySQLIntegrityException(MySQLException):
    def __init__(self, constraint_type: str, table: str, details: str, cause: Exception):
        super().__init__(
            message=f"MySQL integrity violation in {table}: {constraint_type}",
            error_code=ErrorCode.INTEGRITY_VIOLATION.value,
            status_code=400,
            details={
                "table": table,
                "constraint_type": constraint_type,
                "mysql_details": details
            },
            cause=cause
        )

class MySQLDeadlockException(MySQLException):
    def __init__(self, table: str, details: str, cause: Exception):
        super().__init__(
            message=f"MySQL deadlock detected on table {table}",
            error_code=ErrorCode.DEADLOCK_DETECTED.value,
            status_code=409,
            details={"table": table, "mysql_details": details},
            cause=cause
        )

class MySQLConnectionPoolException(MySQLException):
    def __init__(self, operation: str, pool_size: int, active_connections: int, cause: Exception):
        super().__init__(
            message=f"MySQL connection pool exhausted during {operation}",
            error_code=ErrorCode.CONNECTION_POOL_EXHAUSTED.value,
            status_code=503,
            details={
                "operation": operation,
                "pool_size": pool_size,
                "active_connections": active_connections
            },
            cause=cause
        )

class DRFValidationException(BusinessException):
    def __init__(self, serializer_errors: Dict, cause: Exception = None):
        super().__init__(
            message="Request validation failed",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=400,
            details={"validation_errors": serializer_errors},
            cause=cause
        )

class AuthenticationException(BusinessException):
    def __init__(self, message: str = "Authentication failed", details: Dict = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED.value,
            status_code=401,
            details=details
        )

class PermissionException(BusinessException):
    def __init__(self, user: str, permission: str, resource: str):
        super().__init__(
            message=f"User {user} lacks {permission} permission for {resource}",
            error_code=ErrorCode.INSUFFICIENT_PERMISSIONS.value,
            status_code=403,
            details={"user": user, "permission": permission, "resource": resource}
        )
        
             
class MemberNotFoundException(BusinessException):
    def __init__(self, message:str ='Member not found ', details: Dict = None, cause = None):
        super().__init__(message = message, details = details)