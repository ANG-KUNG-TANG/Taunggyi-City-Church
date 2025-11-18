"""
Production Cache Manager with Namespacing and Versioning
Reliability Level: HIGH
"""
from datetime import datetime
import time
from typing import Any, Optional, Dict, List
import logging
from core.cache.async_cache import AsyncCache
from apps.core.cache.cache_keys import CacheKeyBuilder, CacheNamespace

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Production-grade Cache Management
    Reliability Level: HIGH
    Responsibilities: Cache operations, invalidation, monitoring
    """
    
    def __init__(self, cache: AsyncCache, default_ttl: int = 300):
        self.cache = cache
        self.default_ttl = default_ttl
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }

    # User cache methods
    async def get_user(self, user_id: str, version: str = "1") -> Optional[Any]:
        """Get user from cache"""
        key = CacheKeyBuilder.user_profile(user_id, version)
        try:
            result = await self.cache.get(key)
            if result is not None:
                self._metrics["hits"] += 1
            else:
                self._metrics["misses"] += 1
            return result
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Get user cache failed for {user_id}: {e}")
            return None

    async def set_user(self, user_id: str, user_data: Any, ttl: int = None, version: str = "1") -> bool:
        """Set user in cache"""
        key = CacheKeyBuilder.user_profile(user_id, version)
        try:
            success = await self.cache.set(key, user_data, ttl or self.default_ttl)
            if success:
                self._metrics["sets"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Set user cache failed for {user_id}: {e}")
            return False

    async def delete_user(self, user_id: str, version: str = "1") -> bool:
        """Delete user from cache"""
        key = CacheKeyBuilder.user_profile(user_id, version)
        try:
            success = await self.cache.delete(key)
            if success:
                self._metrics["deletes"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Delete user cache failed for {user_id}: {e}")
            return False

    async def get_user_by_email(self, email: str, version: str = "1") -> Optional[Any]:
        """Get user by email from cache"""
        key = CacheKeyBuilder.user_by_email(email, version)
        try:
            result = await self.cache.get(key)
            if result is not None:
                self._metrics["hits"] += 1
            else:
                self._metrics["misses"] += 1
            return result
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Get user by email cache failed for {email}: {e}")
            return None

    async def set_user_by_email(self, email: str, user_data: Any, ttl: int = None, version: str = "1") -> bool:
        """Set user by email in cache"""
        key = CacheKeyBuilder.user_by_email(email, version)
        try:
            success = await self.cache.set(key, user_data, ttl or self.default_ttl)
            if success:
                self._metrics["sets"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Set user by email cache failed for {email}: {e}")
            return False

    # Session management
    async def get_session(self, session_id: str, version: str = "1") -> Optional[Any]:
        """Get session from cache"""
        key = CacheKeyBuilder.session_token(session_id, version)
        try:
            result = await self.cache.get(key)
            if result is not None:
                self._metrics["hits"] += 1
            return result
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Get session cache failed for {session_id}: {e}")
            return None

    async def set_session(self, session_id: str, session_data: Any, ttl: int = None, version: str = "1") -> bool:
        """Set session in cache"""
        key = CacheKeyBuilder.session_token(session_id, version)
        try:
            success = await self.cache.set(key, session_data, ttl or self.default_ttl)
            if success:
                self._metrics["sets"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Set session cache failed for {session_id}: {e}")
            return False

    async def delete_session(self, session_id: str, version: str = "1") -> bool:
        """Delete session from cache"""
        key = CacheKeyBuilder.session_token(session_id, version)
        try:
            success = await self.cache.delete(key)
            if success:
                self._metrics["deletes"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Delete session cache failed for {session_id}: {e}")
            return False

    # Bulk operations
    async def invalidate_user_caches(self, user_id: str, version: str = "1") -> bool:
        """
        Invalidate all caches for a user
        Reliability Level: HIGH
        """
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
        """
        Get multiple users from cache efficiently
        Reliability Level: HIGH
        """
        keys = [CacheKeyBuilder.user_profile(user_id, version) for user_id in user_ids]
        try:
            results = await self.cache.get_many(keys)
            
            # Map back to user_ids
            user_results = {}
            for user_id, key in zip(user_ids, keys):
                if key in results:
                    user_results[user_id] = results[key]
                    self._metrics["hits"] += 1
                else:
                    self._metrics["misses"] += 1
            
            return user_results
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Get many users cache failed: {e}")
            return {}

    async def clear_namespace(self, namespace: CacheNamespace, version: str = "1") -> int:
        """
        Clear all keys in a namespace (use with caution)
        Reliability Level: HIGH
        """
        try:
            # This is a dangerous operation - should be used carefully
            pattern = f"{namespace.value}:*:v{version}" if version else f"{namespace.value}:*"
            deleted_count = await self.cache.flush_pattern(pattern)
            logger.warning(f"Cleared namespace {namespace.value}, deleted {deleted_count} keys")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear namespace {namespace.value}: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        Reliability Level: LOW
        """
        hit_ratio = 0
        total_operations = self._metrics["hits"] + self._metrics["misses"]
        if total_operations > 0:
            hit_ratio = self._metrics["hits"] / total_operations
        
        return {
            **self._metrics,
            "hit_ratio": hit_ratio,
            "default_ttl": self.default_ttl,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for cache manager
        Reliability Level: LOW
        """
        try:
            # Test basic operations
            test_key = "health_check"
            test_data = {"test": True, "timestamp": time.time()}
            
            set_success = await self.cache.set(test_key, test_data, 10)
            retrieved = await self.cache.get(test_key)
            delete_success = await self.cache.delete(test_key)
            
            return {
                "status": "healthy" if all([set_success, retrieved, delete_success]) else "degraded",
                "operations_test": {
                    "set": set_success,
                    "get": retrieved is not None,
                    "delete": delete_success
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Cache manager health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }