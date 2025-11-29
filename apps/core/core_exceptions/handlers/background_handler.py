import logging
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from core.core_exceptions.base import BaseAppException
from core.core_exceptions.logging.context import context_manager

logger = logging.getLogger(__name__)


class BackgroundTaskExceptionHandler:
    """
    Comprehensive exception handler for background tasks and async operations.
    Uses unified context system.
    """
    
    @staticmethod
    def handle_task_exception(
        task_name: str,
        exception: Exception,
        task_id: Optional[str] = None,
        context_updates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle exceptions in background tasks using unified context.
        """
        # Update context for this task
        updates = {
            'task_name': task_name,
            'task_id': task_id,
            'failed_at': datetime.utcnow().isoformat()
        }
        if context_updates:
            updates.update(context_updates)
        
        context_manager.set_context(**updates)
        current_context = context_manager.get_context()
        
        # Handle custom application exceptions
        if isinstance(exception, BaseAppException):
            logger.warning(
                f"Background task '{task_name}' failed with application exception",
                extra={
                    'exception_details': exception.to_dict(),
                    'context': current_context.to_dict()
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
                    'context': current_context.to_dict()
                }
            )
            
            from core.core_exceptions.base import CriticalException
            critical_exception = CriticalException(
                message=f"Background task '{task_name}' failed",
                context=current_context,
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
        context_updates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle exceptions in async background tasks.
        """
        return BackgroundTaskExceptionHandler.handle_task_exception(
            task_name, exception, task_id, context_updates
        )
    
    @staticmethod
    def should_retry_exception(
        exception: Exception,
        retry_count: int,
        max_retries: int
    ) -> bool:
        """
        Determine if a task should be retried based on the exception type.
        """
        # Don't retry if we've exceeded max retries
        if retry_count >= max_retries:
            logger.error(
                f"Task exceeded maximum retry attempts",
                extra={
                    'retry_count': retry_count,
                    'max_retries': max_retries,
                }
            )
            return False
        
        # Don't retry for certain exception types
        non_retryable_exceptions = [
            # Add exception types that should not be retried
        ]
        
        for exc_type in non_retryable_exceptions:
            if isinstance(exception, exc_type):
                logger.warning(
                    f"Task failed with non-retryable exception",
                    extra={
                        'exception_type': type(exception).__name__,
                        'retry_count': retry_count,
                    }
                )
                return False
        
        # For integration exceptions, only retry transient errors
        from core.core_exceptions.integration import IntegrationException
        if isinstance(exception, IntegrationException):
            transient_errors = ["timeout", "connection", "rate_limit", "deadlock"]
            error_message = str(exception).lower()
            
            if any(transient_error in error_message for transient_error in transient_errors):
                logger.info(
                    f"Retrying task after transient error",
                    extra={
                        'retry_count': retry_count,
                        'exception_type': type(exception).__name__,
                    }
                )
                return True
            else:
                return False
        
        # Default: retry for most exceptions
        logger.info(
            f"Retrying task",
            extra={
                'retry_count': retry_count,
                'exception_type': type(exception).__name__,
            }
        )
        return True
    
    @staticmethod
    def with_task_error_handling(task_func: Callable) -> Callable:
        """
        Decorator for background tasks with comprehensive error handling.
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