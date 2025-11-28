import logging
import random
import time
import asyncio
from typing import Callable, Any, Dict, Optional, TypeVar, Union, Coroutine
from functools import wraps
from django.db import DatabaseError, IntegrityError, OperationalError, transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned

from core.core_exceptions.domain import (
    EntityNotFoundException, 
    DomainValidationException,  
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
    Enhanced database error handler with async support and improved context building
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
        Main decorator for sync database operations
        """
        @wraps(operation)
        def wrapper(*args, **kwargs) -> T:
            operation_name = operation.__name__
            context = self._build_context(operation, args, kwargs)
            
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                return self._handle_exception(e, context)
        
        return wrapper
    
    async def handle_async_operation(self, operation: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., Coroutine[T, Any, Any]]:
        """
        Async version of the operation handler
        """
        @wraps(operation)
        async def async_wrapper(*args, **kwargs) -> T:
            operation_name = operation.__name__
            context = self._build_context(operation, args, kwargs)
            
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                return self._handle_exception(e, context)
        
        return async_wrapper
    
    def _handle_exception(self, exception: Exception, context: Dict[str, Any]) -> None:
        """
        Unified exception handling for both sync and async operations
        """
        operation_name = context.get('operation', 'unknown')
        
        if isinstance(exception, ObjectDoesNotExist):
            logger.warning(
                f"Object not found in {operation_name}",
                extra={'context': context, 'error': str(exception)}
            )
            model_name = context.get('model', 'unknown')
            raise EntityNotFoundException(
                entity_name=model_name,
                entity_id=context.get('lookup_params', {}).get('id'),
                details={
                    'lookup_params': context.get('lookup_params', {}),
                    'operation': operation_name
                }
            ) from exception
            
        elif isinstance(exception, ValidationError):
            logger.warning(
                f"Validation failed in {operation_name}",
                extra={'context': context, 'errors': getattr(exception, 'message_dict', {})}
            )
            model_name = context.get('model', 'unknown')
            raise DomainValidationException(
                message=f"Validation failed for {model_name}",
                field_errors=getattr(exception, 'message_dict', {}),
                details={
                    'model': model_name,
                    'operation': operation_name
                }
            ) from exception
            
        elif isinstance(exception, MultipleObjectsReturned):
            logger.warning(
                f"Multiple objects returned in {operation_name}",
                extra={'context': context, 'error': str(exception)}
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
            ) from exception
            
        elif isinstance(exception, (DatabaseError, IntegrityError, OperationalError)):
            logger.error(
                f"Database error in {operation_name}",
                extra={'context': context, 'error': str(exception)},
                exc_info=True
            )
            mapped_exception = self.mapper.map_django_exception(exception, context)
            raise mapped_exception from exception
            
        else:
            logger.error(
                f"Unexpected error in {operation_name}",
                extra={'context': context, 'error': str(exception)},
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
            ) from exception
    
    def execute_with_retry(
        self, 
        operation: Callable[..., T],
        max_attempts: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Enhanced retry logic with better context and error handling
        """
        import random
        
        max_attempts = max_attempts or self.retry_config['max_attempts']
        context = context or {}
        operation_name = getattr(operation, '__name__', 'unknown_operation')
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    return operation()
                    
            except (DatabaseError, OperationalError) as e:
                last_exception = e
                
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
                
                delay = self._calculate_retry_delay(attempt)
                
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
        
        if last_exception:
            raise self.mapper.map_django_exception(last_exception, context) from last_exception
        else:
            raise DatabaseConnectionException(
                service_name="database",
                message=f"Operation {operation_name} failed after {max_attempts} attempts",
                details=context
            )
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter"""
        base_delay = self.retry_config['base_delay'] * (2 ** attempt)
        jitter = random.uniform(0, self.retry_config['jitter'])
        return min(base_delay + jitter, self.retry_config['max_delay'])
    
    def _build_context(self, operation: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Enhanced context building with more detailed information"""
        context = {
            'operation': operation.__name__,
            'module': operation.__module__,
            'args_count': len(args),
            'kwargs_keys': list(kwargs.keys()),
            'timestamp': time.time(),
            'caller_info': self._get_caller_info()
        }
        
        # Extract model information
        model_info = self._extract_model_info(operation, args)
        if model_info:
            context.update(model_info)
        
        # Extract lookup parameters
        lookup_params = self._extract_lookup_params(kwargs, args)
        if lookup_params:
            context['lookup_params'] = lookup_params
        
        return context
    
    def _extract_model_info(self, operation: Callable, args: tuple) -> Optional[Dict[str, Any]]:
        """Extract model information from operation arguments"""
        model_info = {}
        
        # Check if first argument is a model instance or queryset
        if args and hasattr(args[0], '_meta'):
            model = args[0]
            model_info = {
                'model': model._meta.model_name,
                'app_label': model._meta.app_label,
                'model_verbose_name': model._meta.verbose_name
            }
        
        # Check for self in bound methods (managers)
        elif hasattr(operation, '__self__'):
            obj = operation.__self__
            if hasattr(obj, 'model'):
                model = obj.model
                model_info = {
                    'model': model._meta.model_name,
                    'app_label': model._meta.app_label,
                    'model_verbose_name': model._meta.verbose_name
                }
        
        return model_info if model_info else None
    
    def _extract_lookup_params(self, kwargs: dict, args: tuple) -> Dict[str, Any]:
        """Enhanced lookup parameter extraction"""
        lookup_params = {}
        
        # Direct kwargs
        if kwargs:
            lookup_params.update(kwargs)
        
        # kwargs in 'kwargs' parameter
        if 'kwargs' in kwargs and isinstance(kwargs['kwargs'], dict):
            lookup_params.update(kwargs['kwargs'])
        
        # Look for dict in args
        for arg in args:
            if isinstance(arg, dict):
                lookup_params.update(arg)
                break
        
        # Filter out non-lookup parameters
        excluded_params = {'self', 'cls', 'using', 'hints'}
        lookup_params = {
            k: v for k, v in lookup_params.items() 
            if k not in excluded_params and not k.startswith('_')
        }
        
        return lookup_params
    
    def _get_caller_info(self) -> Dict[str, Any]:
        """Get information about the function caller"""
        import inspect
        
        try:
            frame = inspect.currentframe()
            # Go back 3 frames: current -> _build_context -> handle_operation -> caller
            for _ in range(3):
                if frame:
                    frame = frame.f_back
            
            if frame:
                caller_frame_info = inspect.getframeinfo(frame)
                return {
                    'filename': caller_frame_info.filename,
                    'function': caller_frame_info.function,
                    'lineno': caller_frame_info.lineno
                }
        except (AttributeError, ValueError):
            pass
        
        return {}
    
    def check_connection_health(self) -> Dict[str, Any]:
        """
        Enhanced connection health check with more diagnostics
        """
        from django.db import connection
        import time
        
        health_info = {
            'healthy': False,
            'response_time_ms': None,
            'database': connection.vendor,
            'database_version': None,
            'error': None,
            'timestamp': time.time(),
            'connection_params': self._get_connection_params(connection)
        }
        
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                # Get database version and additional info
                health_info.update(self._get_database_info(cursor, connection.vendor))
            
            health_info['response_time_ms'] = (time.time() - start_time) * 1000
            health_info['healthy'] = result[0] == 1
            
        except Exception as e:
            health_info['error'] = str(e)
            health_info['healthy'] = False
        
        return health_info
    
    def _get_connection_params(self, connection) -> Dict[str, Any]:
        """Get connection parameters without sensitive data"""
        settings = connection.settings_dict
        return {
            'host': settings.get('HOST'),
            'port': settings.get('PORT'),
            'name': settings.get('NAME'),
            'user': settings.get('USER'),
            'engine': settings.get('ENGINE'),
            'timeout': settings.get('OPTIONS', {}).get('connect_timeout')
        }
    
    def _get_database_info(self, cursor, vendor: str) -> Dict[str, Any]:
        """Get database-specific information"""
        info = {}
        
        try:
            if vendor == 'postgresql':
                cursor.execute("SELECT version(), current_database()")
                version_info = cursor.fetchone()
                info['database_version'] = version_info[0] if version_info else None
                info['current_database'] = version_info[1] if version_info else None
                
            elif vendor == 'mysql':
                cursor.execute("SELECT VERSION(), DATABASE()")
                version_info = cursor.fetchone()
                info['database_version'] = version_info[0] if version_info else None
                info['current_database'] = version_info[1] if version_info else None
                
            elif vendor == 'sqlite':
                cursor.execute("SELECT sqlite_version()")
                version_info = cursor.fetchone()
                info['database_version'] = version_info[0] if version_info else None
        except Exception:
            pass
        
        return info
    
    def bulk_operation_handler(self, operations: list, batch_size: int = 100) -> Dict[str, Any]:
        """
        Enhanced bulk operation handler with batching and detailed reporting
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'total': len(operations),
            'batches_processed': 0,
            'execution_time_seconds': None
        }
        
        start_time = time.time()
        
        try:
            # Process operations in batches
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                results['batches_processed'] += 1
                
                for j, operation in enumerate(batch):
                    global_index = i + j
                    try:
                        operation()
                        results['successful'] += 1
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append({
                            'index': global_index,
                            'batch_index': j,
                            'batch_number': results['batches_processed'],
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'operation': getattr(operation, '__name__', 'anonymous')
                        })
                        logger.warning(
                            f"Bulk operation failed at index {global_index}",
                            extra={'error': str(e), 'batch': results['batches_processed']}
                        )
        
        finally:
            results['execution_time_seconds'] = time.time() - start_time
        
        return results


# Global instance for easy access
db_error_handler = DatabaseErrorHandler()