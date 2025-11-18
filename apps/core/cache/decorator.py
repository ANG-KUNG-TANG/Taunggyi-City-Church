import functools
import inspect
from typing import Any, Callable, Optional
import logging
from .cache_keys import CacheKeyBuilder
from .async_cache import AsyncCache

logger = logging.getLogger(__name__)

def cached(
    key_template: str = None,
    ttl: int = 300,
    namespace: str = "default",
    version: str = "1"
):
    """
    Decorator for caching async function results
    
    Args:
        key_template: String template for cache key (uses function args)
        ttl: Time to live in seconds
        namespace: Cache namespace
        version: Cache version
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get cache instance (assuming it's the first arg after self)
            cache = None
            if args and hasattr(args[0], 'cache'):
                cache = args[0].cache
            elif 'cache' in kwargs:
                cache = kwargs['cache']
            
            if not cache or not isinstance(cache, AsyncCache):
                logger.warning("Cache not available, skipping cache")
                return await func(*args, **kwargs)
            
            # Build cache key
            cache_key = _build_cache_key(
                func, args, kwargs, key_template, namespace, version
            )
            
            # Try to get from cache
            try:
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            try:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key}")
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")
            
            return result
        
        return wrapper
    return decorator

def cache_invalidate(
    key_templates: list[str],
    namespace: str = "default",
    version: str = "1"
):
    """
    Decorator to invalidate cache entries after function execution
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            
            # Get cache instance
            cache = None
            if args and hasattr(args[0], 'cache'):
                cache = args[0].cache
            elif 'cache' in kwargs:
                cache = kwargs['cache']
            
            if not cache or not isinstance(cache, AsyncCache):
                return result
            
            # Build and delete cache keys
            for key_template in key_templates:
                cache_key = _build_cache_key(
                    func, args, kwargs, key_template, namespace, version
                )
                try:
                    await cache.delete(cache_key)
                    logger.debug(f"Invalidated cache key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache deletion failed: {e}")
            
            return result
        
        return wrapper
    return decorator

def _build_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_template: Optional[str],
    namespace: str,
    version: str
) -> str:
    """Build cache key from template and function arguments"""
    if not key_template:
        # Default key: function_name:args:kwargs
        key_template = f"{func.__name__}:{args}:{kwargs}"
    
    # Get function signature
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    # Format key template with arguments
    try:
        formatted_key = key_template.format(**bound_args.arguments)
    except KeyError as e:
        logger.warning(f"Key template error: {e}, using default")
        formatted_key = f"{func.__name__}:{str(bound_args.arguments)}"
    
    return CacheKeyBuilder.build_key(
        namespace, 
        formatted_key, 
        version=version
    )