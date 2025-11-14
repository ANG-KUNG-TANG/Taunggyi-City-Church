import logging
import traceback
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from core.core_exceptions.base import BaseAppException, ErrorContext

logger = logging.getLogger(__name__)


class BackgroundTaskExceptionHandler:
    """
    Comprehensive exception handler for background tasks and async operations.
    Provides proper logging, retry logic, and monitoring for background jobs.
    """
    
    @staticmethod
    def handle_task_exception(
        task_name: str,
        exception: Exception,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle exceptions in background tasks and log appropriately.
        
        Args:
            task_name: Name of the background task
            exception: The exception that occurred
            task_id: Optional task identifier
            context: Additional context information
            
        Returns:
            Dict containing error details for task result
        """
        error_context = ErrorContext()
        error_context.additional_info = context or {}
        error_context.additional_info.update({
            'task_name': task_name,
            'task_id': task_id,
            'failed_at': datetime.utcnow().isoformat()
        })
        
        # Handle custom application exceptions
        if isinstance(exception, BaseAppException):
            logger.warning(
                f"Background task '{task_name}' failed with application exception",
                extra={
                    'exception_details': exception.to_dict(),
                    'context': error_context.__dict__
                }
            )
            return {
                'success': False,
                'error': exception.to_dict(),
                'task_name': task_name,
                'task_id': task_id
            }
        
        # Handle generic exceptions
        else:
            logger.error(
                f"Background task '{task_name}' failed with unexpected exception",
                exc_info=True,
                extra={
                    'exception_message': str(exception),
                    'traceback': traceback.format_exc(),
                    'context': error_context.__dict__
                }
            )
            
            from core.core_exceptions.base import CriticalException
            critical_exception = CriticalException(
                message=f"Background task '{task_name}' failed",
                context=error_context,
                cause=exception
            )
            
            return {
                'success': False,
                'error': critical_exception.to_dict(),
                'task_name': task_name,
                'task_id': task_id
            }
    
    @staticmethod
    async def handle_async_task_exception(
        task_name: str,
        exception: Exception,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle exceptions in async background tasks.
        
        Args:
            task_name: Name of the background task
            exception: The exception that occurred
            task_id: Optional task identifier
            context: Additional context information
            
        Returns:
            Dict containing error details for task result
        """
        return BackgroundTaskExceptionHandler.handle_task_exception(
            task_name, exception, task_id, context
        )
    
    @staticmethod
    def handle_retryable_exception(
        task_name: str,
        exception: Exception,
        retry_count: int,
        max_retries: int,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if a task should be retried based on the exception type.
        
        Args:
            task_name: Name of the background task
            exception: The exception that occurred
            retry_count: Current retry attempt
            max_retries: Maximum number of retries allowed
            context: Additional context information
            
        Returns:
            bool: True if task should be retried, False otherwise
        """
        # Don't retry if we've exceeded max retries
        if retry_count >= max_retries:
            logger.error(
                f"Background task '{task_name}' exceeded maximum retry attempts",
                extra={
                    'retry_count': retry_count,
                    'max_retries': max_retries,
                    'context': context
                }
            )
            return False
        
        # Don't retry for certain exception types
        non_retryable_exceptions = [
            # Add exception types that should not be retried
            # e.g., AuthenticationError, AuthorizationError
        ]
        
        for exc_type in non_retryable_exceptions:
            if isinstance(exception, exc_type):
                logger.warning(
                    f"Background task '{task_name}' failed with non-retryable exception",
                    extra={
                        'exception_type': type(exception).__name__,
                        'retry_count': retry_count,
                        'context': context
                    }
                )
                return False
        
        # For integration exceptions, only retry transient errors
        from core.core_exceptions.integration import IntegrationException
        if isinstance(exception, IntegrationException):
            # Implement logic to determine if it's a transient error
            # For example, network timeouts might be retryable, but
            # authentication errors probably shouldn't be retried
            transient_errors = ["timeout", "connection", "rate_limit", "deadlock"]
            error_message = str(exception).lower()
            
            if any(transient_error in error_message for transient_error in transient_errors):
                logger.info(
                    f"Retrying background task '{task_name}' after transient error",
                    extra={
                        'retry_count': retry_count,
                        'exception_type': type(exception).__name__,
                        'context': context
                    }
                )
                return True
            else:
                return False
        
        # Default: retry for most exceptions
        logger.info(
            f"Retrying background task '{task_name}'",
            extra={
                'retry_count': retry_count,
                'exception_type': type(exception).__name__,
                'context': context
            }
        )
        return True
    
    @staticmethod
    def with_task_error_handling(task_func: Callable) -> Callable:
        """
        Decorator for background tasks with comprehensive error handling.
        
        Args:
            task_func: The task function to wrap
            
        Returns:
            Wrapped function with error handling
        """
        def wrapper(*args, **kwargs):
            task_name = task_func.__name__
            task_id = kwargs.get('task_id')
            context = kwargs.get('context', {})
            
            try:
                return task_func(*args, **kwargs)
            except Exception as e:
                return BackgroundTaskExceptionHandler.handle_task_exception(
                    task_name, e, task_id, context
                )
        
        return wrapper
    
    @staticmethod
    def with_async_task_error_handling(task_func: Callable) -> Callable:
        """
        Decorator for async background tasks with comprehensive error handling.
        
        Args:
            task_func: The async task function to wrap
            
        Returns:
            Wrapped async function with error handling
        """
        async def wrapper(*args, **kwargs):
            task_name = task_func.__name__
            task_id = kwargs.get('task_id')
            context = kwargs.get('context', {})
            
            try:
                return await task_func(*args, **kwargs)
            except Exception as e:
                return await BackgroundTaskExceptionHandler.handle_async_task_exception(
                    task_name, e, task_id, context
                )
        
        return wrapper