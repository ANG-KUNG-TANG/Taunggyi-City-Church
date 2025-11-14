import logging
import re
from typing import Dict, Any, Optional
from django.db import DatabaseError, IntegrityError, OperationalError

from apps.core.core_exceptions.domain import BusinessRuleException
from core.core_exceptions.integration import (
    DatabaseConnectionException,
    DatabaseTimeoutException,
    DatabaseIntegrityException,
    StorageException
)

logger = logging.getLogger('core.db.mapper')


class DatabaseExceptionMapper:
    """
    Maps Django database exceptions to application-specific exceptions
    with support for multiple database backends
    """
    
    def __init__(self):
        self.mysql_error_map = self._initialize_mysql_error_map()
        self.postgresql_error_map = self._initialize_postgresql_error_map()
        self.retryable_errors = self._initialize_retryable_errors()
    
    def _initialize_mysql_error_map(self) -> Dict[int, str]:
        """Initialize MySQL error code to exception type mapping"""
        return {
            # Connection errors
            2002: "CANNOT_CONNECT",
            2003: "CANNOT_CONNECT", 
            2006: "CONNECTION_CLOSED",
            2013: "CONNECTION_LOST",
            2017: "CONNECTION_LOST",
            
            # Integrity violations
            1062: "DUPLICATE_ENTRY",  # Duplicate entry
            1451: "FOREIGN_KEY_VIOLATION",  # Cannot delete/update parent row
            1452: "FOREIGN_KEY_VIOLATION",  # Cannot add/update child row
            
            # Lock and timeout errors
            1205: "LOCK_WAIT_TIMEOUT",  # Lock wait timeout
            1213: "DEADLOCK",  # Deadlock found
            1614: "CONNECTION_FAILURE",  # Transaction branch rollback
            
            # Resource errors
            1040: "TOO_MANY_CONNECTIONS",
            1044: "ACCESS_DENIED",
            1045: "ACCESS_DENIED",
            1159: "NETWORK_ERROR",
            1161: "NETWORK_ERROR",
        }
    
    def _initialize_postgresql_error_map(self) -> Dict[str, str]:
        """Initialize PostgreSQL error code to exception type mapping"""
        return {
            '08000': "CONNECTION_EXCEPTION",
            '08003': "CONNECTION_DOES_NOT_EXIST",
            '08006': "CONNECTION_FAILURE",
            '08001': "SQLCLIENT_UNABLE_TO_ESTABLISH_SQLCONNECTION",
            '08004': "SQLSERVER_REJECTED_ESTABLISHMENT_OF_SQLCONNECTION",
            '08007': "TRANSACTION_RESOLUTION_UNKNOWN",
            '23505': "UNIQUE_VIOLATION",
            '23503': "FOREIGN_KEY_VIOLATION",
            '23502': "NOT_NULL_VIOLATION",
            '23514': "CHECK_VIOLATION",
            '40001': "SERIALIZATION_FAILURE",
            '40P01': "DEADLOCK_DETECTED",
            '53300': "TOO_MANY_CONNECTIONS",
            '57P03': "CANNOT_CONNECT_NOW",
        }
    
    def _initialize_retryable_errors(self) -> Dict[str, list]:
        """Initialize retryable error patterns"""
        return {
            'mysql': [
                'deadlock',
                'lock wait',
                'timeout',
                'connection',
                'server has gone away',
                'lost connection',
                'try restarting transaction'
            ],
            'postgresql': [
                'deadlock',
                'timeout',
                'connection',
                'serialization failure',
                'could not connect',
                'terminating connection'
            ],
            'sqlite': [
                'database is locked',
                'disk i/o error'
            ]
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
                # For unknown database exceptions, wrap in generic database exception
                return DatabaseConnectionException(
                    service_name="database",
                    message=f"Database error: {str(exception)}",
                    details=context
                )
                
        except Exception as mapping_error:
            logger.error(
                f"Error mapping database exception: {mapping_error}",
                exc_info=True,
                extra={'original_exception': str(exception), 'context': context}
            )
            # Fallback to generic database exception
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database error: {str(exception)}",
                details=context
            )
    
    def _handle_integrity_error(self, exception: IntegrityError, context: Dict[str, Any]) -> Exception:
        """Handle database integrity errors"""
        error_str = str(exception).lower()
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        # Extract constraint details
        constraint_type = self._extract_constraint_type(error_str)
        constraint_name = self._extract_constraint_name(error_str)
        
        if 'duplicate' in error_str or 'unique' in error_str:
            return DatabaseIntegrityException(
                service_name="database",
                message=f"Duplicate entry violation in {model}",
                details={
                    'constraint_type': 'UNIQUE',
                    'constraint_name': constraint_name,
                    'table': model,
                    'operation': operation,
                    'original_error': str(exception)
                }
            )
        elif 'foreign key' in error_str:
            return DatabaseIntegrityException(
                service_name="database",
                message=f"Foreign key violation in {model}",
                details={
                    'constraint_type': 'FOREIGN_KEY',
                    'constraint_name': constraint_name,
                    'table': model,
                    'operation': operation,
                    'original_error': str(exception)
                }
            )
        elif 'check constraint' in error_str or 'check' in error_str:
            return DatabaseIntegrityException(
                service_name="database",
                message=f"Check constraint violation in {model}",
                details={
                    'constraint_type': 'CHECK',
                    'constraint_name': constraint_name,
                    'table': model,
                    'operation': operation,
                    'original_error': str(exception)
                }
            )
        elif 'not null' in error_str:
            return DatabaseIntegrityException(
                service_name="database",
                message=f"Not null violation in {model}",
                details={
                    'constraint_type': 'NOT_NULL',
                    'table': model,
                    'operation': operation,
                    'original_error': str(exception)
                }
            )
        else:
            return DatabaseIntegrityException(
                service_name="database",
                message=f"Integrity constraint violation in {model}",
                details={
                    'constraint_type': 'GENERIC',
                    'table': model,
                    'operation': operation,
                    'original_error': str(exception)
                }
            )
    
    def _handle_operational_error(self, exception: OperationalError, context: Dict[str, Any]) -> Exception:
        """Handle database operational errors"""
        error_str = str(exception).lower()
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        # Check for connection errors
        if any(phrase in error_str for phrase in ['connection', 'server has gone away', 'lost connection']):
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database connection error during {operation}",
                details={
                    'operation': operation,
                    'model': model,
                    'original_error': str(exception)
                }
            )
        
        # Check for deadlock
        elif 'deadlock' in error_str:
            return BusinessRuleException(
                rule_name="database_deadlock",
                message=f"Database deadlock detected during {operation}",
                details={
                    'operation': operation,
                    'model': model,
                    'original_error': str(exception)
                }
            )
        
        # Check for timeout
        elif 'timeout' in error_str or 'lock wait' in error_str:
            timeout = self._extract_timeout(error_str)
            return DatabaseTimeoutException(
                service_name="database",
                message=f"Database timeout during {operation}",
                details={
                    'operation': operation,
                    'model': model,
                    'timeout_seconds': timeout,
                    'original_error': str(exception)
                }
            )
        
        # Check for resource exhaustion
        elif any(phrase in error_str for phrase in ['too many connections', 'out of memory', 'disk full']):
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database resource exhaustion during {operation}",
                details={
                    'operation': operation,
                    'model': model,
                    'original_error': str(exception)
                }
            )
        
        else:
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database operational error during {operation}",
                details={
                    'operation': operation,
                    'model': model,
                    'original_error': str(exception)
                }
            )
    
    def _handle_generic_database_error(self, exception: DatabaseError, context: Dict[str, Any]) -> Exception:
        """Handle generic database errors"""
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        return DatabaseConnectionException(
            service_name="database",
            message=f"Database error during {operation} on {model}",
            details={
                'operation': operation,
                'model': model,
                'original_error': str(exception)
            }
        )
    
    def is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable based on database backend and error message"""
        if not isinstance(error, (OperationalError, DatabaseError)):
            return False
        
        error_str = str(error).lower()
        
        # Check against retryable error patterns for all database backends
        for patterns in self.retryable_errors.values():
            if any(phrase in error_str for phrase in patterns):
                return True
        
        return False
    
    def _extract_constraint_type(self, error_msg: str) -> str:
        """Extract constraint type from error message"""
        if 'unique' in error_msg or 'duplicate' in error_msg:
            return 'UNIQUE'
        elif 'foreign key' in error_msg:
            return 'FOREIGN_KEY'
        elif 'check' in error_msg:
            return 'CHECK'
        elif 'not null' in error_msg:
            return 'NOT_NULL'
        else:
            return 'UNKNOWN'
    
    def _extract_constraint_name(self, error_msg: str) -> Optional[str]:
        """Extract constraint name from error message"""
        patterns = [
            r"constraint ['\"]([^'\"]+)['\"]",
            r"key ['\"]([^'\"]+)['\"]",
            r"for key ['\"]([^'\"]+)['\"]"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def _extract_timeout(error_msg: str) -> int:
        """Extract timeout value from error message"""
        patterns = [
            r"wait timeout (\d+)",
            r"timeout (\d+)", 
            r"(\d+) second",
            r"(\d+) ms",
            r"(\d+) milliseconds"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                return int(match.group(1))
                
        return 30  # Default timeout in seconds


# Global instance
db_exception_mapper = DatabaseExceptionMapper()