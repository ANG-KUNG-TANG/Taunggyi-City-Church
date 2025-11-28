"""
Production Cache Manager - Business Logic Layer
Reliability Level: HIGH
"""
from typing import Any, Optional, Dict, List
import logging
from .async_cache import AsyncRedisCache
from .cache_keys import CacheKeyBuilder, CacheNamespace

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Business logic layer for cache operations
    Uses AsyncRedisCache for underlying operations
    """
    
    def __init__(self, cache: AsyncRedisCache = None, default_ttl: int = 300):
        self.cache = cache or AsyncRedisCache()
        self.default_ttl = default_ttl

    # User Management
    async def get_user(self, user_id: str, version: str = "1") -> Optional[Any]:
        """Get user from cache"""
        key = CacheKeyBuilder.user_profile(user_id, version)
        return await self.cache.get(key)

    async def set_user(self, user_id: str, user_data: Any, ttl: int = None, version: str = "1") -> bool:
        """Set user in cache"""
        key = CacheKeyBuilder.user_profile(user_id, version)
        return await self.cache.set(key, user_data, ttl or self.default_ttl)

    async def delete_user(self, user_id: str, version: str = "1") -> bool:
        """Delete user from cache"""
        key = CacheKeyBuilder.user_profile(user_id, version)
        return await self.cache.delete(key)

    async def get_user_by_email(self, email: str, version: str = "1") -> Optional[Any]:
        """Get user by email from cache"""
        key = CacheKeyBuilder.user_by_email(email, version)
        return await self.cache.get(key)

    async def set_user_by_email(self, email: str, user_data: Any, ttl: int = None, version: str = "1") -> bool:
        """Set user by email in cache"""
        key = CacheKeyBuilder.user_by_email(email, version)
        return await self.cache.set(key, user_data, ttl or self.default_ttl)

    # Session Management
    async def get_session(self, session_id: str, version: str = "1") -> Optional[Any]:
        """Get session from cache"""
        key = CacheKeyBuilder.session_token(session_id, version)
        return await self.cache.get(key)

    async def set_session(self, session_id: str, session_data: Any, ttl: int = None, version: str = "1") -> bool:
        """Set session in cache"""
        key = CacheKeyBuilder.session_token(session_id, version)
        return await self.cache.set(key, session_data, ttl or self.default_ttl)

    async def delete_session(self, session_id: str, version: str = "1") -> bool:
        """Delete session from cache"""
        key = CacheKeyBuilder.session_token(session_id, version)
        return await self.cache.delete(key)

    # Advanced Operations
    async def invalidate_user_caches(self, user_id: str, version: str = "1") -> bool:
        """Invalidate all caches for a user"""
        try:
            # Delete user profile cache
            await self.delete_user(user_id, version)
            
            # Delete user sessions cache
            sessions_key = CacheKeyBuilder.user_sessions(user_id, version)
            await self.cache.delete(sessions_key)
            
            logger.info(f"Invalidated all caches for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate user caches for {user_id}: {e}")
            return False

    async def get_many_users(self, user_ids: List[str], version: str = "1") -> Dict[str, Any]:
        """Get multiple users from cache efficiently"""
        keys = [CacheKeyBuilder.user_profile(user_id, version) for user_id in user_ids]
        results = await self.cache.get_many(keys)
        
        # Map back to user_ids
        user_results = {}
        for user_id, key in zip(user_ids, keys):
            if key in results:
                user_results[user_id] = results[key]
        
        return user_results

    async def clear_namespace(self, namespace: CacheNamespace, version: str = "1") -> int:
        """Clear all keys in a namespace"""
        try:
            pattern = f"{namespace.value}:*:v{version}" if version else f"{namespace.value}:*"
            deleted_count = await self.cache.flush_pattern(pattern)
            logger.warning(f"Cleared namespace {namespace.value}, deleted {deleted_count} keys")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear namespace {namespace.value}: {e}")
            return 0

    # Health & Monitoring
    async def health_check(self) -> Dict[str, Any]:
        """Health check for cache manager"""
        return await self.cache.health_check()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return await self.cache.get_stats()