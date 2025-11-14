import logging
import time
from typing import Callable, Any, Dict, Optional, TypeVar, Union
from functools import wraps
from django.db import DatabaseError, IntegrityError, OperationalError, transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned

from core.core_exceptions.domain import (
    EntityNotFoundException, 
    ValidationException as DomainValidationException,
    BusinessRuleException
)
from core.core_exceptions.integration import (
    DatabaseConnectionException,
    DatabaseTimeoutException,
    DatabaseIntegrityException
)
from .db_mapper import DatabaseExceptionMapper

T = TypeVar('T')
logger = logging.getLogger('core.db.handler')


class DatabaseErrorHandler:
    """
    Comprehensive database error handler for Django ORM operations
    with integration with the new exception structure
    """
    
    def __init__(self):
        self.mapper = DatabaseExceptionMapper()
        self.retry_config = {
            'max_attempts': 3,
            'base_delay': 0.1,
            'max_delay': 2.0,
            'jitter': 0.1
        }
    
    def handle_operation(self, operation: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to handle database operations with comprehensive error handling
        """
        @wraps(operation)
        def wrapper(*args, **kwargs) -> T:
            operation_name = operation.__name__
            context = self._build_context(operation, args, kwargs)
            
            try:
                return operation(*args, **kwargs)
                
            except ObjectDoesNotExist as e:
                logger.warning(
                    f"Object not found in {operation_name}",
                    extra={'context': context, 'error': str(e)}
                )
                model_name = context.get('model', 'unknown')
                raise EntityNotFoundException(
                    entity_name=model_name,
                    entity_id=context.get('lookup_params', {}).get('id'),
                    details={
                        'lookup_params': context.get('lookup_params', {}),
                        'operation': operation_name
                    }
                ) from e
                
            except ValidationError as e:
                logger.warning(
                    f"Validation failed in {operation_name}",
                    extra={'context': context, 'errors': e.message_dict}
                )
                model_name = context.get('model', 'unknown')
                raise DomainValidationException(
                    message=f"Validation failed for {model_name}",
                    field_errors=e.message_dict,
                    details={
                        'model': model_name,
                        'operation': operation_name
                    }
                ) from e
                
            except MultipleObjectsReturned as e:
                logger.warning(
                    f"Multiple objects returned in {operation_name}",
                    extra={'context': context, 'error': str(e)}
                )
                model_name = context.get('model', 'unknown')
                raise BusinessRuleException(
                    rule_name="unique_object_retrieval",
                    message=f"Multiple {model_name} objects found with the same criteria",
                    details={
                        'model': model_name,
                        'lookup_params': context.get('lookup_params', {}),
                        'operation': operation_name
                    }
                ) from e
                
            except (DatabaseError, IntegrityError, OperationalError) as e:
                logger.error(
                    f"Database error in {operation_name}",
                    extra={'context': context, 'error': str(e)},
                    exc_info=True
                )
                # Map Django database errors to custom exceptions
                mapped_exception = self.mapper.map_django_exception(e, context)
                raise mapped_exception from e
                
            except Exception as e:
                logger.error(
                    f"Unexpected error in {operation_name}",
                    extra={'context': context, 'error': str(e)},
                    exc_info=True
                )
                raise DatabaseConnectionException(
                    service_name="database",
                    message=f"Unexpected database error in {operation_name}",
                    details={
                        'operation': operation_name,
                        'model': context.get('model', 'unknown'),
                        'context': context
                    }
                ) from e
                
        return wrapper
    
    def execute_with_retry(
        self, 
        operation: Callable[..., T],
        max_attempts: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Execute operation with retry logic for transient errors
        """
        import random
        
        max_attempts = max_attempts or self.retry_config['max_attempts']
        context = context or {}
        operation_name = getattr(operation, '__name__', 'unknown_operation')
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                # Use atomic transaction for each attempt
                with transaction.atomic():
                    return operation()
                    
            except (DatabaseError, OperationalError) as e:
                last_exception = e
                
                # Check if this error is retryable
                if not self.mapper.is_retryable_error(e):
                    logger.warning(
                        f"Non-retryable error in {operation_name}",
                        extra={
                            'attempt': attempt + 1,
                            'error': str(e),
                            'context': context
                        }
                    )
                    raise self.mapper.map_django_exception(e, context) from e
                    
                if attempt == max_attempts - 1:
                    logger.warning(
                        f"Max retries exceeded for {operation_name}",
                        extra={
                            'attempt': attempt + 1,
                            'max_attempts': max_attempts,
                            'context': context
                        }
                    )
                    mapped_exception = self.mapper.map_django_exception(e, context)
                    raise mapped_exception from e
                
                # Calculate delay with exponential backoff and jitter
                base_delay = self.retry_config['base_delay'] * (2 ** attempt)
                jitter = random.uniform(0, self.retry_config['jitter'])
                delay = min(base_delay + jitter, self.retry_config['max_delay'])
                
                logger.info(
                    f"Retrying operation {operation_name} after {delay:.2f}s",
                    extra={
                        'attempt': attempt + 1,
                        'max_attempts': max_attempts,
                        'delay': delay,
                        'context': context
                    }
                )
                time.sleep(delay)
        
        # This should never be reached, but for type safety
        if last_exception:
            raise self.mapper.map_django_exception(last_exception, context) from last_exception
        else:
            raise DatabaseConnectionException(
                service_name="database",
                message=f"Operation {operation_name} failed after {max_attempts} attempts",
                details=context
            )
    
    def _build_context(self, operation: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Build context information for error handling and logging"""
        context = {
            'operation': operation.__name__,
            'module': operation.__module__,
            'args_count': len(args),
            'kwargs_keys': list(kwargs.keys()),
            'timestamp': time.time()
        }
        
        # Try to extract model information from args or self
        model_name = self._extract_model_name(operation, args)
        if model_name:
            context['model'] = model_name
        
        # Extract lookup parameters from kwargs
        lookup_params = self._extract_lookup_params(kwargs, args)
        if lookup_params:
            context['lookup_params'] = lookup_params
        
        return context
    
    def _extract_model_name(self, operation: Callable, args: tuple) -> Optional[str]:
        """Extract model name from operation arguments"""
        # Check if first argument is a model instance or queryset
        if args and hasattr(args[0], '_meta'):
            return args[0]._meta.model_name
        
        # Check for self in bound methods
        if hasattr(operation, '__self__'):
            obj = operation.__self__
            if hasattr(obj, 'model'):
                return obj.model._meta.model_name
        
        return None
    
    def _extract_lookup_params(self, kwargs: dict, args: tuple) -> Dict[str, Any]:
        """Extract lookup parameters from arguments"""
        lookup_params = {}
        
        # Direct kwargs (like get(id=1))
        if kwargs:
            lookup_params.update(kwargs)
        
        # kwargs in 'kwargs' parameter (like get(**filters))
        if 'kwargs' in kwargs and isinstance(kwargs['kwargs'], dict):
            lookup_params.update(kwargs['kwargs'])
        
        # Look for dict in args (usually the second argument)
        if len(args) > 1 and isinstance(args[1], dict):
            lookup_params.update(args[1])
        
        return lookup_params
    
    def check_connection_health(self) -> Dict[str, Any]:
        """
        Check database connection health with detailed diagnostics
        """
        from django.db import connection
        import time
        
        health_info = {
            'healthy': False,
            'response_time_ms': None,
            'database': connection.vendor,
            'database_version': None,
            'error': None,
            'timestamp': time.time()
        }
        
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                # Simple query to test connection
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                # Get database version
                if connection.vendor == 'postgresql':
                    cursor.execute("SELECT version()")
                    version_info = cursor.fetchone()
                    health_info['database_version'] = version_info[0] if version_info else None
                elif connection.vendor == 'mysql':
                    cursor.execute("SELECT VERSION()")
                    version_info = cursor.fetchone()
                    health_info['database_version'] = version_info[0] if version_info else None
                elif connection.vendor == 'sqlite':
                    cursor.execute("SELECT sqlite_version()")
                    version_info = cursor.fetchone()
                    health_info['database_version'] = version_info[0] if version_info else None
            
            health_info['response_time_ms'] = (time.time() - start_time) * 1000
            health_info['healthy'] = result[0] == 1
            
            # Check connection settings
            health_info.update({
                'connection_parameters': {
                    'host': getattr(connection.settings_dict, 'get', lambda x: None)('HOST'),
                    'port': getattr(connection.settings_dict, 'get', lambda x: None)('PORT'),
                    'name': getattr(connection.settings_dict, 'get', lambda x: None)('NAME'),
                    'user': getattr(connection.settings_dict, 'get', lambda x: None)('USER'),
                }
            })
            
        except Exception as e:
            health_info['error'] = str(e)
            health_info['healthy'] = False
        
        return health_info
    
    def bulk_operation_handler(self, operations: list) -> Dict[str, Any]:
        """
        Handle bulk database operations with comprehensive error handling
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'total': len(operations)
        }
        
        for i, operation in enumerate(operations):
            try:
                operation()
                results['successful'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'index': i,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'operation': getattr(operation, '__name__', 'anonymous')
                })
                logger.warning(
                    f"Bulk operation failed at index {i}",
                    extra={'error': str(e)}
                )
        
        return results


# Global instance for easy access
db_error_handler = DatabaseErrorHandler()