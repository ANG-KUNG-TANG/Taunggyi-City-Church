from .async_cache import AsyncRedisCache, async_cache, AsyncCache, async_redis_cache
from .cache_keys import CacheKeyBuilder, CacheNamespace
from .serializer import CacheSerializer, SerializationType

__all__ = [
    'AsyncRedisCache',
    'async_cache', 
    'AsyncCache',
    'async_redis_cache',
    'CacheKeyBuilder',
    'CacheNamespace', 
    'CacheSerializer',
    'SerializationType'
]

import logging
from django.core.cache import cache as django_cache

logger = logging.getLogger(__name__)

def get_cache_client():
    """
    Get cache client for JWT services
    Returns Django cache instance that can be adapted for async use
    """
    return django_cache