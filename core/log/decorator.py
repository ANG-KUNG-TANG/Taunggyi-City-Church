import asyncio
import logging
import time
import inspect
from typing import Any, Callable, Dict, Optional, Union, TypeVar
from functools import wraps
from enum import Enum
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LogLevel(Enum):
    """Standardized log levels for the system."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogContext:
    """Context manager for logging with additional context."""
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.old_context = {}
    
    def __enter__(self):
        # Store thread/context local context if needed
        # Can be extended for distributed tracing
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def log_call(
    level: LogLevel = LogLevel.INFO,
    log_args: bool = True,
    log_result: bool = False,
    log_exceptions: bool = True,
    log_execution_time: bool = True,
    include_module: bool = True,
    include_lineno: bool = False,
    sensitive_fields: Optional[list] = None
):
    """
    Universal decorator for logging ANY callable (functions, methods, classmethods, staticmethods).
    
    Args:
        level: Log level
        log_args: Whether to log arguments
        log_result: Whether to log return value
        log_exceptions: Whether to log exceptions
        log_execution_time: Whether to log execution time
        include_module: Include module name in log
        include_lineno: Include line number
        sensitive_fields: List of argument names to mask (e.g., ['password', 'token'])
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get function metadata
        func_module = inspect.getmodule(func).__name__ if inspect.getmodule(func) else 'unknown'
        func_name = func.__name__
        lineno = func.__code__.co_firstlineno if hasattr(func, '__code__') else None
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _log_execution(
                func, args, kwargs, func_module, func_name, lineno,
                level, log_args, log_result, log_exceptions, 
                log_execution_time, include_module, include_lineno,
                sensitive_fields, is_async=True
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _log_execution(
                func, args, kwargs, func_module, func_name, lineno,
                level, log_args, log_result, log_exceptions,
                log_execution_time, include_module, include_lineno,
                sensitive_fields, is_async=False
            )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_method(
    level: LogLevel = LogLevel.INFO,
    log_args: bool = True,
    log_result: bool = False,
    log_exceptions: bool = True,
    log_execution_time: bool = True,
    include_class: bool = True,
    sensitive_fields: Optional[list] = None
):
    """
    Specialized decorator for class methods that includes class context.
    Automatically handles instance methods, class methods, and static methods.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _log_method_execution(
                func, args, kwargs, level, log_args, log_result,
                log_exceptions, log_execution_time, include_class,
                sensitive_fields, is_async=True
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _log_method_execution(
                func, args, kwargs, level, log_args, log_result,
                log_exceptions, log_execution_time, include_class,
                sensitive_fields, is_async=False
            )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_transaction(
    operation: Optional[str] = None,
    level: LogLevel = LogLevel.INFO
):
    """
    Decorator for transactional operations (database, external API calls).
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            class_name = _get_class_name(args) if args else None
            
            logger.log(level.value, 
                      f"🚀 Starting transaction: {op_name}" + 
                      (f" in {class_name}" if class_name else ""))
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.log(level.value,
                          f"✅ Transaction completed: {op_name}" +
                          (f" in {class_name}" if class_name else "") +
                          f" [duration={elapsed:.3f}s]")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ Transaction failed: {op_name} - {type(e).__name__}: {str(e)} " +
                            f"[duration={elapsed:.3f}s]")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            class_name = _get_class_name(args) if args else None
            
            logger.log(level.value,
                      f"🚀 Starting transaction: {op_name}" +
                      (f" in {class_name}" if class_name else ""))
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.log(level.value,
                          f"✅ Transaction completed: {op_name}" +
                          (f" in {class_name}" if class_name else "") +
                          f" [duration={elapsed:.3f}s]")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ Transaction failed: {op_name} - {type(e).__name__}: {str(e)} " +
                            f"[duration={elapsed:.3f}s]")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_performance(
    threshold_seconds: float = 1.0,
    level: LogLevel = LogLevel.WARNING
):
    """
    Decorator to log performance warnings for slow operations.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            if elapsed > threshold_seconds:
                logger.log(level.value,
                          f"⚠️ Performance warning: {func.__name__} took {elapsed:.3f}s " +
                          f"(threshold: {threshold_seconds}s)")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            if elapsed > threshold_seconds:
                logger.log(level.value,
                          f"⚠️ Performance warning: {func.__name__} took {elapsed:.3f}s " +
                          f"(threshold: {threshold_seconds}s)")
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_validation_error(func: Callable[..., T]) -> Callable[..., T]:
    """
    Specialized decorator for validation methods.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            class_name = _get_class_name(args) if args else None
            func_name = func.__name__
            
            logger.error(f"❌ Validation failed in {class_name + '.' if class_name else ''}{func_name}: "
                        f"{type(e).__name__}: {str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            class_name = _get_class_name(args) if args else None
            func_name = func.__name__
            
            logger.error(f"❌ Validation failed in {class_name + '.' if class_name else ''}{func_name}: "
                        f"{type(e).__name__}: {str(e)}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


# Helper Functions
def _get_class_name(args: tuple) -> Optional[str]:
    """Extract class name from method arguments."""
    if not args:
        return None
    
    # First argument could be self (instance method) or cls (class method)
    first_arg = args[0]
    
    if hasattr(first_arg, '__class__'):
        # Instance method
        return first_arg.__class__.__name__
    elif isinstance(first_arg, type):
        # Class method
        return first_arg.__name__
    
    return None


def _mask_sensitive_data(data: Any, sensitive_fields: list) -> Any:
    """Mask sensitive data in logs."""
    if isinstance(data, dict):
        masked = data.copy()
        for field in sensitive_fields:
            if field in masked:
                masked[field] = '***MASKED***'
        return masked
    elif isinstance(data, str) and any(field in data for field in sensitive_fields):
        return '***MASKED***'
    return data


async def _log_execution(
    func: Callable,
    args: tuple,
    kwargs: Dict[str, Any],
    func_module: str,
    func_name: str,
    lineno: Optional[int],
    level: LogLevel,
    log_args: bool,
    log_result: bool,
    log_exceptions: bool,
    log_execution_time: bool,
    include_module: bool,
    include_lineno: bool,
    sensitive_fields: Optional[list],
    is_async: bool
):
    """Core logging execution logic."""
    # Prepare log message
    log_parts = []
    if include_module:
        log_parts.append(func_module)
    if include_lineno and lineno:
        log_parts.append(f"L{lineno}")
    
    log_prefix = f"{'::'.join(log_parts)}::" if log_parts else ""
    log_msg = f"{log_prefix}{func_name}"
    
    # Log arguments
    if log_args and (args or kwargs):
        args_list = []
        
        # Mask sensitive data
        if sensitive_fields:
            masked_args = [_mask_sensitive_data(arg, sensitive_fields) for arg in args]
            masked_kwargs = {k: _mask_sensitive_data(v, sensitive_fields) 
                           for k, v in kwargs.items()}
        else:
            masked_args = args
            masked_kwargs = kwargs
        
        # Format arguments
        if masked_args:
            args_list.extend([repr(arg) for arg in masked_args])
        if masked_kwargs:
            args_list.extend([f"{k}={repr(v)}" for k, v in masked_kwargs.items()])
        
        if args_list:
            log_msg += f"({', '.join(args_list)})"
    
    start_time = time.time() if log_execution_time else None
    
    try:
        # Execute function
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        # Add execution time
        if log_execution_time and start_time:
            elapsed = time.time() - start_time
            log_msg += f" [⏱️{elapsed:.3f}s]"
        
        # Log result
        if log_result and result is not None:
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            logger.log(level.value, f"{log_msg} → {result_str}")
        else:
            logger.log(level.value, log_msg)
        
        return result
        
    except Exception as e:
        if log_exceptions:
            error_msg = f"{log_msg} ❌ failed: {type(e).__name__}: {str(e)}"
            if log_execution_time and start_time:
                elapsed = time.time() - start_time
                error_msg += f" [⏱️{elapsed:.3f}s]"
            logger.error(error_msg, exc_info=True)
        raise


def _log_method_execution(
    func: Callable,
    args: tuple,
    kwargs: Dict[str, Any],
    level: LogLevel,
    log_args: bool,
    log_result: bool,
    log_exceptions: bool,
    log_execution_time: bool,
    include_class: bool,
    sensitive_fields: Optional[list],
    is_async: bool
):
    """Logging execution for methods with class context."""
    class_name = _get_class_name(args)
    func_name = func.__name__
    
    # Build log message with class context
    if include_class and class_name:
        log_msg = f"{class_name}.{func_name}"
    else:
        log_msg = func_name
    
    # Handle arguments
    if log_args and (args or kwargs):
        # Skip self/cls for instance/class methods
        method_args = args[1:] if args and (hasattr(args[0], '__class__') or isinstance(args[0], type)) else args
        
        if sensitive_fields:
            masked_args = [_mask_sensitive_data(arg, sensitive_fields) for arg in method_args]
            masked_kwargs = {k: _mask_sensitive_data(v, sensitive_fields) 
                           for k, v in kwargs.items()}
        else:
            masked_args = method_args
            masked_kwargs = kwargs
        
        args_list = []
        if masked_args:
            args_list.extend([repr(arg) for arg in masked_args])
        if masked_kwargs:
            args_list.extend([f"{k}={repr(v)}" for k, v in masked_kwargs.items()])
        
        if args_list:
            log_msg += f"({', '.join(args_list)})"
    
    start_time = time.time() if log_execution_time else None
    
    try:
        # Execute function
        if is_async:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
        else:
            result = func(*args, **kwargs)
        
        # Add execution time
        if log_execution_time and start_time:
            elapsed = time.time() - start_time
            log_msg += f" [⏱️{elapsed:.3f}s]"
        
        # Log result
        if log_result and result is not None:
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            logger.log(level.value, f"{log_msg} → {result_str}")
        else:
            logger.log(level.value, log_msg)
        
        return result
        
    except Exception as e:
        if log_exceptions:
            error_msg = f"{log_msg} ❌ failed: {type(e).__name__}: {str(e)}"
            if log_execution_time and start_time:
                elapsed = time.time() - start_time
                error_msg += f" [⏱️{elapsed:.3f}s]"
            logger.error(error_msg, exc_info=True)
        raise