import logging
from typing import Callable, Any, Dict, Optional, TypeVar
from functools import wraps
from django.db import DatabaseError, IntegrityError, OperationalError
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from core_exceptions.base_exception import BaseApplicationException
from core_exceptions.django_exceptions import (
    ObjectNotFoundException, ObjectValidationException,
    BulkOperationException, DatabaseConnectionException,
    DatabaseTimeoutException, QueryExecutionException
)
from core_exceptions.error_codes import ErrorCode
from .db_mapper import DatabaseExceptionMapper

T = TypeVar('T')
logger = logging.getLogger('db.handler')


class DatabaseErrorHandler:
    """
    Main database error handler for Django ORM operations
    """
    
    def __init__(self):
        self.mapper = DatabaseExceptionMapper(logger)
        self.retry_config = {
            'max_attempts': 3,
            'base_delay': 0.1,
            'max_delay': 2.0
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
                raise ObjectNotFoundException(
                    model=context.get('model', 'unknown'),
                    lookup_params=context.get('lookup_params', {}),
                    cause=e
                )
                
            except ValidationError as e:
                logger.warning(
                    f"Validation failed in {operation_name}",
                    extra={'context': context, 'errors': e.message_dict}
                )
                raise ObjectValidationException(
                    model=context.get('model', 'unknown'),
                    validation_errors=e.message_dict,
                    cause=e
                )
                
            except (DatabaseError, IntegrityError, OperationalError) as e:
                logger.error(
                    f"Database error in {operation_name}",
                    extra={'context': context, 'error': str(e)},
                    exc_info=True
                )
                # Map Django database errors to custom exceptions
                mapped_exception = self.mapper.map_django_exception(e, context)
                raise mapped_exception
                
            except Exception as e:
                logger.error(
                    f"Unexpected error in {operation_name}",
                    extra={'context': context, 'error': str(e)},
                    exc_info=True
                )
                raise QueryExecutionException(
                    model=context.get('model', 'unknown'),
                    operation=operation_name,
                    sql=None,
                    cause=e
                )
                
        return wrapper
    
    def execute_with_retry(
        self, 
        operation: Callable[..., T],
        max_attempts: int = None,
        context: Dict[str, Any] = None
    ) -> T:
        """
        Execute operation with retry logic for transient errors
        """
        import time
        from django.db import transaction
        
        max_attempts = max_attempts or self.retry_config['max_attempts']
        context = context or {}
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    return operation()
                    
            except (DatabaseError, OperationalError) as e:
                last_exception = e
                
                if not self.mapper.is_retryable_error(e):
                    raise
                    
                if attempt == max_attempts - 1:
                    logger.warning(
                        f"Max retries exceeded for {operation.__name__}",
                        extra={
                            'attempt': attempt + 1,
                            'max_attempts': max_attempts,
                            'context': context
                        }
                    )
                    mapped_exception = self.mapper.map_django_exception(e, context)
                    raise mapped_exception
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.retry_config['base_delay'] * (2 ** attempt),
                    self.retry_config['max_delay']
                )
                
                logger.info(
                    f"Retrying operation {operation.__name__} after {delay}s",
                    extra={
                        'attempt': attempt + 1,
                        'max_attempts': max_attempts,
                        'delay': delay,
                        'context': context
                    }
                )
                time.sleep(delay)
        
        raise last_exception
    
    def _build_context(self, operation: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Build context information for error handling"""
        context = {
            'operation': operation.__name__,
            'module': operation.__module__,
            'args_count': len(args),
            'kwargs_keys': list(kwargs.keys()),
        }
        
        # Try to extract model information from args
        for arg in args:
            if hasattr(arg, '_meta') and hasattr(arg._meta, 'model_name'):
                context['model'] = arg._meta.model_name
                break
            elif hasattr(arg, '__class__') and hasattr(arg.__class__, '_meta'):
                context['model'] = arg.__class__._meta.model_name
                break
        
        # Extract lookup parameters from kwargs
        if 'kwargs' in kwargs:
            context['lookup_params'] = kwargs['kwargs']
        elif args and len(args) > 1 and isinstance(args[1], dict):
            context['lookup_params'] = args[1]
        
        return context
    
    def check_connection_health(self) -> Dict[str, Any]:
        """
        Check database connection health
        """
        from django.db import connection
        import time
        
        health_info = {
            'healthy': False,
            'response_time_ms': None,
            'database': connection.vendor,
            'error': None
        }
        
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            health_info['response_time_ms'] = (time.time() - start_time) * 1000
            health_info['healthy'] = result[0] == 1
            
        except Exception as e:
            health_info['error'] = str(e)
            health_info['healthy'] = False
        
        return health_info


# Global instance
db_error_handler = DatabaseErrorHandler()