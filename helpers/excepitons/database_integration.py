# db/mysql_error_handler.py
import logging
from typing import Callable, Any, TypeVar, Optional
from functools import wraps
from django.db import transaction, DatabaseError
from mysql.connector import Error as MySQLError
from mysql.connector.errors import (
    IntegrityError, OperationalError, 
    DatabaseError as MySQLDatabaseError
)

from django_exceptions import (
    MySQLIntegrityException, MySQLDeadlockException,
    MySQLTimeoutException, ObjectNotFoundException,
    ObjectValidationException, BulkOperationException
)

T = TypeVar('T')
logger = logging.getLogger('db.mysql')

class MySQLErrorHandler:
    """MySQL specific error handler for Django ORM operations"""
    
    @classmethod
    def handle_orm_operation(cls, operation: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to handle Django ORM operations with MySQL specific error handling
        """
        @wraps(operation)
        def wrapper(*args, **kwargs) -> T:
            try:
                return operation(*args, **kwargs)
            
            except DatabaseError as e:
                cls._handle_database_error(e, operation.__name__, args, kwargs)
                
            except Exception as e:
                logger.error(
                    f"Unexpected error in ORM operation {operation.__name__}",
                    exc_info=True,
                    extra={
                        'operation': operation.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }
                )
                raise
                
        return wrapper

    @classmethod
    def _handle_database_error(cls, error: DatabaseError, operation: str, args: tuple, kwargs: dict):
        """Handle Django DatabaseError and map to custom exceptions"""
        
        # Extract original MySQL error if available
        original_error = getattr(error, '__cause__', error)
        
        if isinstance(original_error, IntegrityError):
            cls._handle_integrity_error(original_error, operation)
        elif isinstance(original_error, OperationalError):
            cls._handle_operational_error(original_error, operation)
        else:
            logger.error(
                f"Unhandled database error in {operation}",
                exc_info=True,
                extra={
                    'operation': operation,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'mysql_error_code': getattr(original_error, 'errno', None)
                }
            )
            raise MySQLException(
                message=f"Database operation failed: {str(error)}",
                error_code="MYSQL_GENERIC_ERROR",
                cause=error
            )

    @classmethod
    def _handle_integrity_error(cls, error: IntegrityError, operation: str):
        """Handle MySQL integrity constraint violations"""
        error_msg = str(error).lower()
        
        if 'foreign key constraint fails' in error_msg:
            raise MySQLIntegrityException(
                constraint_type="foreign_key",
                table=cls._extract_table_name(error_msg),
                details=str(error),
                cause=error
            )
        elif 'duplicate entry' in error_msg:
            raise MySQLIntegrityException(
                constraint_type="unique",
                table=cls._extract_table_name(error_msg),
                details=str(error),
                cause=error
            )
        else:
            raise MySQLIntegrityException(
                constraint_type="generic",
                table="unknown",
                details=str(error),
                cause=error
            )

    @classmethod
    def _handle_operational_error(cls, error: OperationalError, operation: str):
        """Handle MySQL operational errors"""
        error_code = getattr(error, 'errno', None)
        
        if error_code == 1213:  # Deadlock
            raise MySQLDeadlockException(
                table=cls._extract_table_name(str(error)),
                details=str(error),
                cause=error
            )
        elif error_code == 1205:  # Lock wait timeout
            raise MySQLTimeoutException(
                operation=operation,
                timeout=cls._extract_timeout(str(error)),
                cause=error
            )
        else:
            raise MySQLException(
                message=f"MySQL operational error: {str(error)}",
                error_code="MYSQL_OPERATIONAL_ERROR",
                cause=error
            )

    @staticmethod
    def _extract_table_name(error_msg: str) -> str:
        """Extract table name from MySQL error message"""
        # Simple extraction - can be enhanced based on MySQL error format
        import re
        match = re.search(r"table ['\"]([^'\"]+)['\"]", error_msg)
        return match.group(1) if match else "unknown"

    @staticmethod
    def _extract_timeout(error_msg: str) -> int:
        """Extract timeout value from MySQL error message"""
        import re
        match = re.search(r"wait timeout (\d+)", error_msg)
        return int(match.group(1)) if match else 0

    @classmethod
    def execute_with_retry(
        cls, 
        operation: Callable[..., T],
        max_retries: int = 3,
        retry_delay: float = 0.1
    ) -> T:
        """
        Execute operation with retry logic for transient MySQL errors
        """
        import time
        from django.db import transaction
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    return operation()
                    
            except MySQLDeadlockException as e:
                if attempt == max_retries - 1:
                    logger.warning(
                        f"Max retries exceeded for deadlock in {operation.__name__}",
                        extra={'attempt': attempt + 1, 'max_retries': max_retries}
                    )
                    raise
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                
            except MySQLTimeoutException as e:
                if attempt == max_retries - 1:
                    logger.warning(
                        f"Max retries exceeded for timeout in {operation.__name__}",
                        extra={'attempt': attempt + 1, 'max_retries': max_retries}
                    )
                    raise
                time.sleep(retry_delay)