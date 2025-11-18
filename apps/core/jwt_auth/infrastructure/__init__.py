from infrastructure.cache.redis_cache import AsyncRedisCacheFactory, AsyncRedisCache
from core.security.blacklist_service import TokenBlacklistService
from config import settings

def get_redis_cache() -> AsyncRedisCache:
    """Get Redis cache instance with application settings"""
    return AsyncRedisCacheFactory.get_instance(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD
    )

def get_blacklist_service() -> TokenBlacklistService:
    """Get token blacklist service instance"""
    redis_cache = get_redis_cache()
    return TokenBlacklistService(redis_cache)