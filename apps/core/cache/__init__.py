from .async_cache import AsyncRedisCache, async_cache
from .decorator import cached, cache_key, invalidate_cache
from .cache_keys import CacheKeyGenerator, key_generator

__all__ = [
    'BaseCache',
    'AsyncBaseCache',
    'SyncRedisCache',
    'AsyncRedisCache',
    'sync_cache',
    'async_cache',
    'cached',
    'cache_key',
    'invalidate_cache',
    'CacheKeyGenerator',
    'key_generator',
]

# Default cache instance
cache = async_cache