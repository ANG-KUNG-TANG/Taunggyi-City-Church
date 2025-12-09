import asyncio
import functools
import random
import threading
import time
import logging
from typing import Callable, Dict, TypeVar, Any, Optional, Union, Coroutine
from django.db import transaction, DatabaseError, OperationalError
from asgiref.sync import sync_to_async  

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
    Simplified decorator that actually works
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # Just call the original async function
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Database error in {func.__name__}: {e}",
                    exc_info=True
                )
                raise
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                # Just call the original sync function
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Database error in {func.__name__}: {e}",
                    exc_info=True
                )
                raise
        return sync_wrapper

def with_retry(
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: int = 2,
    retryable_exceptions: tuple = (DatabaseError, OperationalError)
):
    """
    Retry decorator for database operations with proper Django 5.2 MySQL support
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        # For Django 5.2 with MySQL, we need to use sync_to_async for transactions
                        # Create a sync function that wraps the transaction
                        def sync_transaction_operation():
                            with transaction.atomic():
                                # We can't call async func directly, so we need to handle this differently
                                # If func is async, we need to run it in the event loop
                                return asyncio.run(func(*args, **kwargs))
                        
                        # Run the sync transaction operation asynchronously
                        return await sync_to_async(sync_transaction_operation)()
                            
                    except retryable_exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            raise
                        
                        # Calculate backoff delay
                        sleep_time = delay * (backoff ** attempt)
                        logger.info(
                            f"Retrying {func.__name__} after {sleep_time:.2f}s (attempt {attempt + 1}/{max_attempts})",
                            extra={'error': str(e)}
                        )
                        await asyncio.sleep(sleep_time)
                    
                    except Exception as e:
                        # Non-retryable exceptions
                        raise
                
                if last_exception:
                    raise last_exception
                
            return async_wrapper
            
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        with transaction.atomic():
                            return func(*args, **kwargs)
                            
                    except retryable_exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            raise
                        
                        # Calculate backoff delay
                        sleep_time = delay * (backoff ** attempt)
                        logger.info(
                            f"Retrying {func.__name__} after {sleep_time:.2f}s (attempt {attempt + 1}/{max_attempts})",
                            extra={'error': str(e)}
                        )
                        time.sleep(sleep_time)
                    
                    except Exception as e:
                        # Non-retryable exceptions
                        raise
                
                if last_exception:
                    raise last_exception
                
            return sync_wrapper
    
    return decorator


# Combined operation decorators
def atomic_operation(func: Callable[..., T]) -> Callable[..., T]:
    """
    Combined atomic operation with error handling for Django 5.2
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For async functions in Django 5.2, use sync_to_async
            def sync_wrapped():
                with transaction.atomic():
                    # Run the async function in the event loop
                    return asyncio.run(func(*args, **kwargs))
            
            return await sync_to_async(sync_wrapped)()
        
        return with_db_error_handling(async_wrapper)
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with transaction.atomic():
                return func(*args, **kwargs)
        
        return with_db_error_handling(sync_wrapper)


# Simplified async operation without transaction (for simple queries)
def async_atomic_operation(func: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., Coroutine[T, Any, Any]]:
    """
    Async atomic operation using sync_to_async wrapper
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        def sync_transaction():
            with transaction.atomic():
                # Run the async function in the current event loop
                loop = asyncio.get_event_loop()
                future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
                return future.result(timeout=30)
        
        return await sync_to_async(sync_transaction)()
    
    return async_wrapper


# Simplified operation type decorators
def read_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for read-only database operations"""
    return with_db_error_handling(func)


def write_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for write database operations with transaction"""
    return atomic_operation(func)


# Better approach for async operations in Django 5.2
def async_db_operation(func: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., Coroutine[T, Any, Any]]:
    """
    Specialized decorator for async database operations in Django 5.2
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        operation_name = func.__name__
        context = {
            'operation': operation_name,
            'module': func.__module__,
            'is_async': True,
            'django_version': '5.2'
        }
        
        try:
            # For simple async queries without transactions
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
        self._lock = threading.Lock()
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
        """
        Make the circuit breaker instance callable as a decorator
        """
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._execute_async(func, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._execute_sync(func, *args, **kwargs)
        
        # Return the appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with circuit breaker"""
        with self._lock:
            self.metrics['total_requests'] += 1
            
            if not self._can_execute():
                from core.core_exceptions.integration import DatabaseConnectionException
                raise DatabaseConnectionException(
                    service_name="database",
                    message="Circuit breaker is OPEN - operation blocked",
                    details=self._get_circuit_details()
                )
        
        try:
            # Call async function
            result = await func(*args, **kwargs)
            
            with self._lock:
                self._on_success()
            return result
            
        except self.expected_exceptions as e:
            with self._lock:
                self._on_failure()
            raise
    
    def _execute_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute sync function with circuit breaker"""
        with self._lock:
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
            
            with self._lock:
                self._on_success()
            return result
            
        except self.expected_exceptions as e:
            with self._lock:
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
        with self._lock:
            return self.metrics.copy()
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self._lock:
            self.failure_count = 0
            self.last_failure_time = 0
            self.state = "CLOSED"
            self.metrics = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'circuit_opened_count': 0
            }