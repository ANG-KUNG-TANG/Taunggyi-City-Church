import asyncio
import functools
import random
import time
from typing import Callable, TypeVar, Any, Optional, Union, Coroutine
from django.db import transaction
from django.utils.decorators import sync_and_async_mixin

from .db_handler import db_error_handler

T = TypeVar('T')


@sync_and_async_mixin
class AsyncDatabaseDecorator:
    """Base class for async-aware database decorators"""
    
    def __init__(self, func: Callable = None):
        self.func = func
        if func:
            functools.update_wrapper(self, func)
    
    def __call__(self, *args, **kwargs):
        if asyncio.iscoroutinefunction(self.func):
            return self._async_wrapper(*args, **kwargs)
        else:
            return self._sync_wrapper(*args, **kwargs)
    
    def _sync_wrapper(self, *args, **kwargs):
        raise NotImplementedError("Sync wrapper must be implemented")
    
    async def _async_wrapper(self, *args, **kwargs):
        raise NotImplementedError("Async wrapper must be implemented")
    
    def __get__(self, obj, objtype):
        """Support instance methods"""
        return functools.partial(self.__call__, obj)


def with_db_error_handling(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for database operations with comprehensive error handling
    Supports both sync and async functions
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await db_error_handler.handle_async_operation(func)(*args, **kwargs)
        return async_wrapper
    else:
        return db_error_handler.handle_operation(func)


class with_retry:
    """
    Decorator factory for retry logic with async support
    """
    
    def __init__(self, max_retries: int = 3, use_transaction: bool = True):
        self.max_retries = max_retries
        self.use_transaction = use_transaction
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                operation = lambda: func(*args, **kwargs)
                context = {
                    'operation': func.__name__,
                    'module': func.__module__,
                    'max_retries': self.max_retries
                }
                
                if self.use_transaction:
                    return await db_error_handler.execute_with_retry_async(
                        operation,
                        max_attempts=self.max_retries,
                        context=context
                    )
                else:
                    return await operation()
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                operation = lambda: func(*args, **kwargs)
                context = {
                    'operation': func.__name__,
                    'module': func.__module__,
                    'max_retries': self.max_retries
                }
                
                if self.use_transaction:
                    return db_error_handler.execute_with_retry(
                        operation,
                        max_attempts=self.max_retries,
                        context=context
                    )
                else:
                    return operation()
            return sync_wrapper


def atomic_operation(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for atomic database operations with error handling
    Supports both sync and async functions
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        @with_db_error_handling
        async def async_wrapper(*args, **kwargs):
            async with transaction.atomic():
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        @with_db_error_handling
        def sync_wrapper(*args, **kwargs):
            with transaction.atomic():
                return func(*args, **kwargs)
        return sync_wrapper


class atomic_with_retry:
    """
    Decorator for atomic operations with retry capability and async support
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            @with_db_error_handling
            async def async_wrapper(*args, **kwargs):
                operation = lambda: func(*args, **kwargs)
                context = {
                    'operation': func.__name__,
                    'module': func.__module__,
                    'max_retries': self.max_retries
                }
                return await db_error_handler.execute_with_retry_async(
                    operation,
                    max_attempts=self.max_retries,
                    context=context
                )
            return async_wrapper
        else:
            @functools.wraps(func)
            @with_db_error_handling
            def sync_wrapper(*args, **kwargs):
                operation = lambda: func(*args, **kwargs)
                context = {
                    'operation': func.__name__,
                    'module': func.__module__,
                    'max_retries': self.max_retries
                }
                return db_error_handler.execute_with_retry(
                    operation,
                    max_attempts=self.max_retries,
                    context=context
                )
            return sync_wrapper


def read_operation(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for read-only database operations with optimized error handling
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        @with_db_error_handling
        async def async_wrapper(*args, **kwargs):
            # For async read operations, we might want to use a read replica if available
            return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        @with_db_error_handling
        def sync_wrapper(*args, **kwargs):
            # For sync read operations
            return func(*args, **kwargs)
        return sync_wrapper


def write_operation(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for write database operations with transaction and error handling
    """
    return atomic_operation(func)


def async_db_operation(func: Callable[..., Coroutine[T, Any, Any]]) -> Callable[..., Coroutine[T, Any, Any]]:
    """
    Specialized decorator for async database operations with enhanced error handling
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
            # Execute the async operation
            return await func(*args, **kwargs)
        except Exception as e:
            # Log async operation failure
            import logging
            logger = logging.getLogger('core.db.async')
            logger.error(
                f"Async database operation failed: {operation_name}",
                extra={'context': context, 'error': str(e)},
                exc_info=True
            )
            # Re-raise for the global handler to catch
            raise
    
    return async_wrapper


def with_timeout(timeout_seconds: float = 30.0):
    """
    Decorator to add timeout to database operations
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
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
                            'timeout_seconds': timeout_seconds
                        }
                    )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we can't easily add timeout in Python
                # This is a placeholder for future implementation
                # Could use threading with timeout, but that's complex
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exceptions: tuple = (Exception,)
):
    """
    Circuit breaker decorator for database operations
    Prevents repeated calls to failing operations
    """
    class CircuitBreaker:
        def __init__(self):
            self.failure_count = 0
            self.last_failure_time = 0
            self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        def can_execute(self):
            if self.state == "OPEN":
                current_time = time.time()
                if current_time - self.last_failure_time > recovery_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            return True
        
        def on_success(self):
            self.state = "CLOSED"
            self.failure_count = 0
        
        def on_failure(self):
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= failure_threshold:
                self.state = "OPEN"
    
    circuit_breaker_instance = CircuitBreaker()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not circuit_breaker_instance.can_execute():
                    from core.core_exceptions.integration import DatabaseConnectionException
                    raise DatabaseConnectionException(
                        service_name="database",
                        message="Circuit breaker is OPEN - operation blocked",
                        details={
                            'operation': func.__name__,
                            'failure_count': circuit_breaker_instance.failure_count,
                            'state': circuit_breaker_instance.state
                        }
                    )
                
                try:
                    result = await func(*args, **kwargs)
                    circuit_breaker_instance.on_success()
                    return result
                except expected_exceptions as e:
                    circuit_breaker_instance.on_failure()
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not circuit_breaker_instance.can_execute():
                    from core.core_exceptions.integration import DatabaseConnectionException
                    raise DatabaseConnectionException(
                        service_name="database",
                        message="Circuit breaker is OPEN - operation blocked",
                        details={
                            'operation': func.__name__,
                            'failure_count': circuit_breaker_instance.failure_count,
                            'state': circuit_breaker_instance.state
                        }
                    )
                
                try:
                    result = func(*args, **kwargs)
                    circuit_breaker_instance.on_success()
                    return result
                except expected_exceptions as e:
                    circuit_breaker_instance.on_failure()
                    raise
            
            return sync_wrapper
    
    return decorator