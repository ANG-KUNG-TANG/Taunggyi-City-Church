from functools import wraps
from typing import Callable, TypeVar, Any
from helpers.exceptions.db.db_handler import db_error_handler

T = TypeVar('T')


def with_db_error_handling(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for database operations with error handling
    """
    return db_error_handler.handle_operation(func)


def with_retry(max_retries: int = 3):
    """
    Decorator factory for retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation = lambda: func(*args, **kwargs)
            context = {
                'operation': func.__name__,
                'module': func.__module__
            }
            return db_error_handler.execute_with_retry(
                operation, 
                max_attempts=max_retries,
                context=context
            )
        return wrapper
    return decorator