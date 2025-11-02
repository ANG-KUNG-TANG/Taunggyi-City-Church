from typing import Dict, List
from base_exception import BusinessException, TechnicalException, DjangoORMException, MySQLException

# Django ORM Specific Exceptions
class ObjectNotFoundException(DjangoORMException):
    """Raised when a database object is not found"""
    def __init__(self, model: str, lookup_params: Dict, cause: Exception = None):
        super().__init__(
            message=f"{model} object not found with parameters: {lookup_params}",
            error_code="OBJECT_NOT_FOUND",
            status_code=404,
            details={"model": model, "lookup_params": lookup_params},
            cause=cause
        )

class ObjectValidationException(DjangoORMException):
    """Raised when object validation fails"""
    def __init__(self, model: str, validation_errors: Dict, cause: Exception = None):
        super().__init__(
            message=f"Validation failed for {model}",
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={"model": model, "validation_errors": validation_errors},
            cause=cause
        )

class BulkOperationException(DjangoORMException):
    """Raised when bulk operations fail partially"""
    def __init__(self, model: str, successful: int, failed: int, errors: List):
        super().__init__(
            message=f"Bulk operation on {model} completed with {successful} successes and {failed} failures",
            error_code="BULK_OPERATION_PARTIAL_FAILURE",
            status_code=400,
            details={
                "model": model,
                "successful_count": successful,
                "failed_count": failed,
                "errors": errors
            }
        )

# MySQL Specific Exceptions
class MySQLIntegrityException(MySQLException):
    """MySQL integrity constraint violations"""
    def __init__(self, constraint_type: str, table: str, details: str, cause: Exception):
        super().__init__(
            message=f"MySQL integrity violation in {table}: {constraint_type}",
            error_code=f"MYSQL_{constraint_type.upper()}_VIOLATION",
            status_code=400,
            details={
                "table": table,
                "constraint_type": constraint_type,
                "mysql_details": details
            },
            cause=cause
        )

class MySQLDeadlockException(MySQLException):
    """MySQL deadlock exceptions"""
    def __init__(self, table: str, details: str, cause: Exception):
        super().__init__(
            message=f"MySQL deadlock detected on table {table}",
            error_code="MYSQL_DEADLOCK",
            status_code=409,  # Conflict
            details={"table": table, "mysql_details": details},
            cause=cause
        )

class MySQLTimeoutException(MySQLException):
    """MySQL timeout exceptions"""
    def __init__(self, operation: str, timeout: int, cause: Exception):
        super().__init__(
            message=f"MySQL {operation} timed out after {timeout}s",
            error_code="MYSQL_TIMEOUT",
            status_code=408,  # Request Timeout
            details={"operation": operation, "timeout_seconds": timeout},
            cause=cause
        )

# Django REST Framework Exceptions
class DRFValidationException(BusinessException):
    """DRF serializer validation exceptions"""
    def __init__(self, serializer_errors: Dict, cause: Exception = None):
        super().__init__(
            message="Request validation failed",
            error_code="DRF_VALIDATION_ERROR",
            status_code=400,
            details={"validation_errors": serializer_errors},
            cause=cause
        )

class AuthenticationException(BusinessException):
    """Authentication related exceptions"""
    pass

class PermissionException(BusinessException):
    """Permission denied exceptions"""
    def __init__(self, user: str, permission: str, resource: str):
        super().__init__(
            message=f"User {user} lacks {permission} permission for {resource}",
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={"user": user, "permission": permission, "resource": resource}
        )