import functools
import inspect
from typing import Any, Optional, Callable
from .keys import key_generator
from .sync_cache import sync_cache
from .async_cache import async_cache


def cached(
    timeout: Optional[int] = None,
    key_prefix: str = None,
    cache_instance = None
):
    """
    Decorator to cache function results
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Custom key prefix
        cache_instance: Cache instance to use (sync or async)
    """
    def decorator(func):
        if cache_instance is None:
            # Auto-detect sync/async and use appropriate cache
            _cache = async_cache if inspect.iscoroutinefunction(func) else sync_cache
        else:
            _cache = cache_instance
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or f"func:{func.__module__}:{func.__name__}"
            key = key_generator.function_key(prefix, args, kwargs)
            
            # Try to get from cache
            cached_result = await _cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await _cache.set(key, result, timeout)
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or f"func:{func.__module__}:{func.__name__}"
            key = key_generator.function_key(prefix, args, kwargs)
            
            # Try to get from cache
            cached_result = _cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache.set(key, result, timeout)
            return result
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def cache_key(pattern: str):
    """
    Decorator to specify custom cache key pattern
    """
    def decorator(func):
        func.cache_key_pattern = pattern
        return func
    return decorator


def invalidate_cache(key_pattern: str, cache_instance = None):
    """
    Decorator to invalidate cache after function execution
    """
    def decorator(func):
        if cache_instance is None:
            _cache = async_cache if inspect.iscoroutinefunction(func) else sync_cache
        else:
            _cache = cache_instance
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache based on pattern
            # This is a simple implementation - you might want to use Redis SCAN for pattern matching
            await _cache.delete(key_pattern)
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache based on pattern
            _cache.delete(key_pattern)
            return result
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    
    return decorator