import logging
from typing import Dict, Any, Optional
from django.db import DatabaseError, IntegrityError, OperationalError
import re

from domain.django_exceptions import (
    MySQLIntegrityException, MySQLDeadlockException,
    MySQLTimeoutException, DatabaseConnectionException,
    DatabaseTimeoutException, QueryExecutionException
)
from domain.error_codes import ErrorCode

logger = logging.getLogger('db.mapper')


class DatabaseExceptionMapper:
    """
    Maps Django database exceptions to application-specific exceptions
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.mysql_error_map = self._initialize_mysql_error_map()
    
    def _initialize_mysql_error_map(self) -> Dict[int, str]:
        """Initialize MySQL error code to exception mapping"""
        return {
            # Connection errors
            2002: "CANNOT_CONNECT",
            2003: "CANNOT_CONNECT", 
            2006: "CONNECTION_CLOSED",
            2013: "CONNECTION_LOST",
            
            # Integrity violations
            1062: "DUPLICATE_ENTRY",
            1451: "FOREIGN_KEY_VIOLATION",
            1452: "FOREIGN_KEY_VIOLATION",
            
            # Lock and timeout errors
            1205: "LOCK_WAIT_TIMEOUT",
            1213: "DEADLOCK",
        }
    
    def map_django_exception(self, exception: Exception, context: Dict[str, Any]) -> Exception:
        """
        Map Django database exception to application-specific exception
        """
        try:
            if isinstance(exception, IntegrityError):
                return self._handle_integrity_error(exception, context)
            elif isinstance(exception, OperationalError):
                return self._handle_operational_error(exception, context)
            elif isinstance(exception, DatabaseError):
                return self._handle_generic_database_error(exception, context)
            else:
                return exception
                
        except Exception as mapping_error:
            self.logger.error(f"Error mapping database exception: {mapping_error}")
            return exception
    
    def _handle_integrity_error(self, exception: IntegrityError, context: Dict[str, Any]) -> Exception:
        """Handle database integrity errors"""
        error_str = str(exception).lower()
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        if 'duplicate' in error_str or 'unique' in error_str:
            return MySQLIntegrityException(
                constraint_type="UNIQUE",
                table=model,
                details=str(exception),
                cause=exception
            )
        elif 'foreign key' in error_str:
            return MySQLIntegrityException(
                constraint_type="FOREIGN_KEY", 
                table=model,
                details=str(exception),
                cause=exception
            )
        else:
            return MySQLIntegrityException(
                constraint_type="GENERIC",
                table=model,
                details=str(exception),
                cause=exception
            )
    
    def _handle_operational_error(self, exception: OperationalError, context: Dict[str, Any]) -> Exception:
        """Handle database operational errors"""
        error_str = str(exception).lower()
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        # Check for connection errors
        if any(phrase in error_str for phrase in ['connection', 'server has gone away', 'lost connection']):
            return DatabaseConnectionException(
                database='mysql',
                operation=operation,
                cause=exception
            )
        
        # Check for deadlock
        elif 'deadlock' in error_str:
            return MySQLDeadlockException(
                table=model,
                details=str(exception),
                cause=exception
            )
        
        # Check for timeout
        elif 'timeout' in error_str or 'lock wait' in error_str:
            timeout = self._extract_timeout(error_str)
            return MySQLTimeoutException(
                operation=operation,
                timeout=timeout,
                cause=exception
            )
        
        else:
            return DatabaseTimeoutException(
                operation=operation,
                timeout_seconds=30,
                cause=exception
            )
    
    def _handle_generic_database_error(self, exception: DatabaseError, context: Dict[str, Any]) -> Exception:
        """Handle generic database errors"""
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        return QueryExecutionException(
            model=model,
            operation=operation,
            sql=None,
            cause=exception
        )
    
    def is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable"""
        if isinstance(error, (OperationalError, DatabaseError)):
            error_str = str(error).lower()
            retryable_phrases = [
                'deadlock',
                'timeout', 
                'lock wait',
                'connection',
                'server has gone away'
            ]
            return any(phrase in error_str for phrase in retryable_phrases)
        return False
    
    @staticmethod
    def _extract_timeout(error_msg: str) -> int:
        """Extract timeout value from error message"""
        patterns = [
            r"wait timeout (\d+)",
            r"timeout (\d+)", 
            r"(\d+) second"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                return int(match.group(1))
                
        return 30  # Default timeout


# Global instance
db_exception_mapper = DatabaseExceptionMapper(logger)