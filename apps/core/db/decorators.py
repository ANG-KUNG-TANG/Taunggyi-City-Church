import asyncio
import functools
import random
import time
import logging
from typing import Callable, Dict, TypeVar, Any, Optional, Union, Coroutine
from django.db import transaction, DatabaseError, OperationalError

from .db_handler import db_error_handler
from .db_mapper import db_exception_mapper

T = TypeVar('T')
logger = logging.getLogger('core.db.decorators')


class DatabaseDecoratorBase:
    """Base class for database decorators with common functionality"""
    
    def __init__(self, func: Callable = None):
        self.func = func
        if func:
            functools.update_wrapper(self, func)
    
    def __get__(self, obj, objtype):
        """Support instance methods"""
        return functools.partial(self.__call__, obj)


def with_db_error_handling(func: Callable[..., T]) -> Callable[..., T]:
    """
    Unified decorator for database operations with comprehensive error handling
    Supports both sync and async functions
    """
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        return db_error_handler.handle_operation(func)(*args, **kwargs)
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        return await db_error_handler.handle_async_operation(func)(*args, **kwargs)
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


class with_retry:
    """
    Enhanced retry decorator with improved async support and configuration
    """
    
    def __init__(
        self, 
        max_retries: int = 3, 
        base_delay: float = 0.1,
        max_delay: float = 2.0,
        use_transaction: bool = True,
        retry_on: tuple = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.use_transaction = use_transaction
        self.retry_on = retry_on or (DatabaseError, OperationalError)
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            operation = lambda: func(*args, **kwargs)
            context = self._build_context(func, args, kwargs)
            
            if self.use_transaction:
                return await self._execute_with_retry_async(
                    operation, 
                    context=context
                )
            else:
                return await operation()
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            operation = lambda: func(*args, **kwargs)
            context = self._build_context(func, args, kwargs)
            
            if self.use_transaction:
                return db_error_handler.execute_with_retry(
                    operation,
                    max_attempts=self.max_retries,
                    context=context
                )
            else:
                return operation()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def _build_context(self, func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Build context for error handling and logging"""
        return {
            'operation': func.__name__,
            'module': func.__module__,
            'max_retries': self.max_retries,
            'is_async': asyncio.iscoroutinefunction(func)
        }
    
    async def _execute_with_retry_async(
        self, 
        operation: Callable[..., T],
        context: Dict[str, Any]
    ) -> T:
        """Execute async operation with enhanced retry logic"""
        last_exception = None
        operation_name = context['operation']
        
        for attempt in range(self.max_retries):
            try:
                async with transaction.atomic():
                    return await operation()
                    
            except self.retry_on as e:
                last_exception = e
                
                # Check if this error is retryable
                if not db_exception_mapper.is_retryable_error(e):
                    logger.warning(
                        f"Non-retryable error in {operation_name}",
                        extra={
                            'attempt': attempt + 1,
                            'error': str(e),
                            'context': context
                        }
                    )
                    raise db_exception_mapper.map_django_exception(e, context) from e
                    
                if attempt == self.max_retries - 1:
                    logger.warning(
                        f"Max retries exceeded for {operation_name}",
                        extra={
                            'attempt': attempt + 1,
                            'max_attempts': self.max_retries,
                            'context': context
                        }
                    )
                    mapped_exception = db_exception_mapper.map_django_exception(e, context)
                    raise mapped_exception from e
                
                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt)
                
                logger.info(
                    f"Retrying operation {operation_name} after {delay:.2f}s",
                    extra={
                        'attempt': attempt + 1,
                        'max_attempts': self.max_retries,
                        'delay': delay,
                        'context': context
                    }
                )
                await asyncio.sleep(delay)
        
        # Final fallback
        if last_exception:
            raise db_exception_mapper.map_django_exception(last_exception, context)
        else:
            from core.core_exceptions.integration import DatabaseConnectionException
            raise DatabaseConnectionException(
                service_name="database",
                message=f"Operation {operation_name} failed after {self.max_retries} attempts",
                details=context
            )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter"""
        base_delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, self.base_delay * 0.1)  # 10% jitter
        return min(base_delay + jitter, self.max_delay)


# Combined operation decorators
def atomic_operation(func: Callable[..., T]) -> Callable[..., T]:
    """
    Combined atomic operation with error handling
    """
    return with_db_error_handling(_atomic_wrapper(func))


def _atomic_wrapper(func: Callable[..., T]) -> Callable[..., T]:
    """Internal atomic wrapper"""
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with transaction.atomic():
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with transaction.atomic():
                return func(*args, **kwargs)
        return sync_wrapper


class atomic_with_retry:
    """
    Combined atomic operation with retry capability
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        retry_decorator = with_retry(max_retries=self.max_retries, use_transaction=True)
        return retry_decorator(func)


# Simplified operation type decorators
def read_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for read-only database operations"""
    return with_db_error_handling(func)


def write_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for write database operations with transaction"""
    return atomic_operation(func)


def async_db_operation(func: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., Coroutine[T, Any, Any]]:
    """
    Specialized decorator for async database operations
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        operation_name = func.__name__
        context = {
            'operation': operation_name,
            'module': func.__module__,
            'is_async': True
        }
        
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Async database operation failed: {operation_name}",
                extra={'context': context, 'error': str(e)},
                exc_info=True
            )
            raise
    
    return async_wrapper


# Advanced decorators
def with_timeout(timeout_seconds: float = 30.0):
    """
    Enhanced timeout decorator with better async support
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), 
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                from core.core_exceptions.integration import DatabaseTimeoutException
                raise DatabaseTimeoutException(
                    service_name="database",
                    message=f"Async operation timed out after {timeout_seconds} seconds",
                    details={
                        'operation': func.__name__,
                        'timeout_seconds': timeout_seconds,
                        'module': func.__module__
                    }
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use threading-based timeout (simplified)
            import threading
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FutureTimeoutError:
                    from core.core_exceptions.integration import DatabaseTimeoutException
                    raise DatabaseTimeoutException(
                        service_name="database",
                        message=f"Sync operation timed out after {timeout_seconds} seconds",
                        details={
                            'operation': func.__name__,
                            'timeout_seconds': timeout_seconds,
                            'module': func.__module__
                        }
                    )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class circuit_breaker:
    """
    Enhanced circuit breaker with state management and metrics
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'circuit_opened_count': 0
        }
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._execute_async(func, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._execute_sync(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def _execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with circuit breaker"""
        self.metrics['total_requests'] += 1
        
        if not self._can_execute():
            from core.core_exceptions.integration import DatabaseConnectionException
            raise DatabaseConnectionException(
                service_name="database",
                message="Circuit breaker is OPEN - operation blocked",
                details=self._get_circuit_details()
            )
        
        try:
            result = asyncio.run(func(*args, **kwargs))
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise
    
    def _execute_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute sync function with circuit breaker"""
        self.metrics['total_requests'] += 1
        
        if not self._can_execute():
            from core.core_exceptions.integration import DatabaseConnectionException
            raise DatabaseConnectionException(
                service_name="database",
                message="Circuit breaker is OPEN - operation blocked",
                details=self._get_circuit_details()
            )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise
    
    def _can_execute(self) -> bool:
        """Check if operation can be executed based on circuit state"""
        if self.state == "OPEN":
            current_time = time.time()
            if current_time - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True
    
    def _on_success(self):
        """Handle successful operation"""
        self.metrics['successful_requests'] += 1
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation"""
        self.metrics['failed_requests'] += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.metrics['circuit_opened_count'] += 1
    
    def _get_circuit_details(self) -> Dict[str, Any]:
        """Get circuit breaker details for error context"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
            'recovery_timeout': self.recovery_timeout,
            'metrics': self.metrics.copy()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return self.metrics.copy()
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'circuit_opened_count': 0
        }