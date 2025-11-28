import logging
import re
from typing import Dict, Any, Optional, Tuple, Set
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
    Enhanced database exception mapper with better pattern matching and context
    """
    
    # Database-specific error patterns
    CONNECTION_ERROR_PATTERNS = {
        'mysql': ['connection', 'server has gone away', 'lost connection', 'cannot connect'],
        'postgresql': ['connection', 'could not connect', 'terminating connection'],
        'sqlite': ['unable to open database file', 'database is locked']
    }
    
    RETRYABLE_ERROR_PATTERNS = {
        'mysql': ['deadlock', 'lock wait', 'timeout', 'try restarting transaction'],
        'postgresql': ['deadlock', 'serialization failure', 'could not serialize'],
        'sqlite': ['database is locked', 'disk i/o error']
    }
    
    INTEGRITY_ERROR_PATTERNS = {
        'unique': ['unique', 'duplicate'],
        'foreign_key': ['foreign key'],
        'check': ['check constraint'],
        'not_null': ['not null']
    }
    
    def __init__(self):
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile regex patterns for efficient matching"""
        compiled = {}
        
        for category, patterns in self.CONNECTION_ERROR_PATTERNS.items():
            compiled[f'connection_{category}'] = re.compile(
                '|'.join(patterns), re.IGNORECASE
            )
        
        for category, patterns in self.RETRYABLE_ERROR_PATTERNS.items():
            compiled[f'retryable_{category}'] = re.compile(
                '|'.join(patterns), re.IGNORECASE
            )
            
        for constraint_type, patterns in self.INTEGRITY_ERROR_PATTERNS.items():
            compiled[f'integrity_{constraint_type}'] = re.compile(
                '|'.join(patterns), re.IGNORECASE
            )
        
        return compiled
    
    def map_django_exception(self, exception: Exception, context: Dict[str, Any]) -> Exception:
        """
        Map Django database exception to application-specific exception
        with enhanced context and pattern matching
        """
        try:
            error_str = str(exception).lower()
            operation = context.get('operation', 'unknown')
            model = context.get('model', 'unknown')
            
            # Build enhanced context
            enhanced_context = {
                **context,
                'original_exception_type': type(exception).__name__,
                'original_error_message': str(exception),
                'timestamp': getattr(exception, 'timestamp', None)
            }
            
            if isinstance(exception, IntegrityError):
                return self._handle_integrity_error(exception, enhanced_context)
            elif isinstance(exception, OperationalError):
                return self._handle_operational_error(exception, enhanced_context)
            elif isinstance(exception, DatabaseError):
                return self._handle_generic_database_error(exception, enhanced_context)
            else:
                return DatabaseConnectionException(
                    service_name="database",
                    message=f"Unexpected database error during {operation}",
                    details=enhanced_context
                )
                
        except Exception as mapping_error:
            logger.error(
                f"Error mapping database exception: {mapping_error}",
                exc_info=True,
                extra={
                    'original_exception': str(exception),
                    'mapping_error': str(mapping_error),
                    'context': context
                }
            )
            # Fallback with maximum context
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database error: {str(exception)}",
                details={
                    'operation': context.get('operation', 'unknown'),
                    'model': context.get('model', 'unknown'),
                    'mapping_failed': True,
                    'original_error': str(exception)
                }
            )
    
    def _handle_integrity_error(self, exception: IntegrityError, context: Dict[str, Any]) -> Exception:
        """Handle database integrity errors with pattern matching"""
        error_str = str(exception).lower()
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        # Extract constraint information
        constraint_info = self._extract_constraint_info(error_str)
        
        # Build detailed context
        integrity_context = {
            **context,
            'constraint_type': constraint_info['type'],
            'constraint_name': constraint_info['name'],
            'table': model,
            'violation_details': constraint_info.get('details', {})
        }
        
        if constraint_info['type'] == 'UNIQUE':
            message = f"Duplicate entry violation in {model} during {operation}"
        elif constraint_info['type'] == 'FOREIGN_KEY':
            message = f"Foreign key violation in {model} during {operation}"
        elif constraint_info['type'] == 'CHECK':
            message = f"Check constraint violation in {model} during {operation}"
        elif constraint_info['type'] == 'NOT_NULL':
            message = f"Not null violation in {model} during {operation}"
        else:
            message = f"Integrity constraint violation in {model} during {operation}"
        
        return DatabaseIntegrityException(
            service_name="database",
            message=message,
            details=integrity_context
        )
    
    def _handle_operational_error(self, exception: OperationalError, context: Dict[str, Any]) -> Exception:
        """Handle database operational errors with pattern matching"""
        error_str = str(exception).lower()
        operation = context.get('operation', 'unknown')
        model = context.get('model', 'unknown')
        
        # Enhanced context
        operational_context = {
            **context,
            'error_category': self._categorize_operational_error(error_str),
            'suggested_action': self._suggest_remediation(error_str)
        }
        
        # Connection errors
        if self._is_connection_error(error_str):
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database connection error during {operation} on {model}",
                details=operational_context
            )
        
        # Timeout errors
        elif self._is_timeout_error(error_str):
            timeout_value = self._extract_timeout(error_str)
            operational_context['timeout_seconds'] = timeout_value
            
            return DatabaseTimeoutException(
                service_name="database",
                message=f"Database timeout during {operation}",
                details=operational_context
            )
        
        # Deadlock errors
        elif self._is_deadlock_error(error_str):
            return BusinessRuleException(
                rule_name="database_deadlock",
                message=f"Database deadlock detected during {operation}",
                details=operational_context
            )
        
        # Resource exhaustion
        elif self._is_resource_error(error_str):
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database resource exhaustion during {operation}",
                details=operational_context
            )
        
        else:
            return DatabaseConnectionException(
                service_name="database",
                message=f"Database operational error during {operation}",
                details=operational_context
            )
    
    def _handle_generic_database_error(self, exception: DatabaseError, context: Dict[str, Any]) -> Exception:
        """Handle generic database errors"""
        return DatabaseConnectionException(
            service_name="database",
            message=f"Database error during {context.get('operation', 'unknown')}",
            details=context
        )
    
    def is_retryable_error(self, error: Exception) -> bool:
        """Enhanced retryable error detection with pattern matching"""
        if not isinstance(error, (OperationalError, DatabaseError)):
            return False
        
        error_str = str(error).lower()
        
        # Check all retryable patterns
        for pattern_name, pattern in self._compiled_patterns.items():
            if pattern_name.startswith('retryable_') and pattern.search(error_str):
                return True
        
        return False
    
    def _extract_constraint_info(self, error_msg: str) -> Dict[str, Any]:
        """Extract comprehensive constraint information from error message"""
        constraint_type = 'UNKNOWN'
        constraint_name = None
        details = {}
        
        # Determine constraint type
        for const_type, pattern in self.INTEGRITY_ERROR_PATTERNS.items():
            if any(p in error_msg for p in pattern):
                constraint_type = const_type.upper()
                break
        
        # Extract constraint name using multiple patterns
        name_patterns = [
            r"constraint ['\"]([^'\"]+)['\"]",
            r"key ['\"]([^'\"]+)['\"]",
            r"for key ['\"]([^'\"]+)['\"]",
            r"constraint (`[^`]+`|'[^']+'|\"[^\"]+\")",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                constraint_name = match.group(1).strip('`\'"')
                break
        
        # Extract additional details for specific constraint types
        if constraint_type == 'FOREIGN_KEY':
            # Try to extract referenced table and column
            ref_match = re.search(r"REFERENCES [`'\"]([^`'\"]+)[`'\"]", error_msg, re.IGNORECASE)
            if ref_match:
                details['referenced_table'] = ref_match.group(1)
        
        return {
            'type': constraint_type,
            'name': constraint_name,
            'details': details
        }
    
    def _categorize_operational_error(self, error_msg: str) -> str:
        """Categorize operational error for better handling"""
        if self._is_connection_error(error_msg):
            return 'CONNECTION'
        elif self._is_timeout_error(error_msg):
            return 'TIMEOUT'
        elif self._is_deadlock_error(error_msg):
            return 'DEADLOCK'
        elif self._is_resource_error(error_msg):
            return 'RESOURCE'
        else:
            return 'GENERIC'
    
    def _suggest_remediation(self, error_msg: str) -> str:
        """Provide suggested remediation based on error type"""
        if self._is_connection_error(error_msg):
            return "Check database server status and network connectivity"
        elif self._is_timeout_error(error_msg):
            return "Consider increasing timeout or optimizing query"
        elif self._is_deadlock_error(error_msg):
            return "Retry operation with exponential backoff"
        elif self._is_resource_error(error_msg):
            return "Check database resource limits and connection pool"
        else:
            return "Review database logs for detailed error information"
    
    def _is_connection_error(self, error_msg: str) -> bool:
        """Check if error is a connection error"""
        return any(
            pattern.search(error_msg) 
            for pattern_name, pattern in self._compiled_patterns.items()
            if pattern_name.startswith('connection_')
        )
    
    def _is_timeout_error(self, error_msg: str) -> bool:
        """Check if error is a timeout error"""
        return any(phrase in error_msg for phrase in ['timeout', 'lock wait', 'waiting for lock'])
    
    def _is_deadlock_error(self, error_msg: str) -> bool:
        """Check if error is a deadlock error"""
        return 'deadlock' in error_msg
    
    def _is_resource_error(self, error_msg: str) -> bool:
        """Check if error is a resource error"""
        return any(phrase in error_msg for phrase in [
            'too many connections', 'out of memory', 'disk full', 
            'no space left', 'max_connections'
        ])
    
    @staticmethod
    def _extract_timeout(error_msg: str) -> int:
        """Extract timeout value from error message with improved patterns"""
        patterns = [
            r"wait timeout.*?(\d+)",
            r"timeout.*?(\d+)", 
            r"(\d+)\s*second",
            r"(\d+)\s*ms",
            r"(\d+)\s*milliseconds",
            r"lock wait timeout.*?(\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
                    
        return 30  # Default timeout in seconds


# Global instance
db_exception_mapper = DatabaseExceptionMapper()