# from typing import Any, Optional, List
# import asyncio
# import logging

# from apps.core.jwt_auth.infrastructure.redis_client import AsyncRedisClient

# logger = logging.getLogger(__name__)

# class CacheManager:
#     def __init__(self, redis_client: AsyncRedisClient, namespace: str = "app"):
#         self.redis = redis_client
#         self.namespace = namespace
#         self.default_ttl = 3600  # 1 hour

#     def _build_key(self, key: str) -> str:
#         """Build namespaced cache key"""
#         return f"{self.namespace}:{key}"

#     async def get(self, key: str) -> Optional[Any]:
#         """Get value from cache"""
#         built_key = self._build_key(key)
#         return await self.redis.get(built_key)

#     async def set(self, key: str, value: Any, ttl: int = None) -> bool:
#         """Set value in cache"""
#         built_key = self._build_key(key)
#         expire = ttl if ttl is not None else self.default_ttl
#         return await self.redis.set(built_key, value, expire)

#     async def delete(self, key: str) -> bool:
#         """Delete key from cache"""
#         built_key = self._build_key(key)
#         return await self.redis.delete(built_key)

#     async def delete_pattern(self, pattern: str) -> int:
#         """Delete keys matching pattern"""
#         built_pattern = self._build_key(pattern)
#         keys = await self.redis.scan_iter(built_pattern)
        
#         if not keys:
#             return 0
        
#         deleted = 0
#         for key in keys:
#             if await self.redis.delete(key):
#                 deleted += 1
        
#         logger.info(f"Deleted {deleted} keys matching pattern {pattern}")
#         return deleted

#     async def get_or_set(self, key: str, factory, ttl: int = None) -> Any:
#         """Get value or set from factory if not exists"""
#         value = await self.get(key)
#         if value is not None:
#             return value
        
#         # Get value from factory
#         if asyncio.iscoroutinefunction(factory):
#             value = await factory()
#         else:
#             value = factory()
        
#         if value is not None:
#             await self.set(key, value, ttl)
        
#         return value

#     async def increment(self, key: str, amount: int = 1, ttl: int = None) -> Optional[int]:
#         """Increment counter"""
#         try:
#             built_key = self._build_key(key)
#             client = self.redis.get_client()
#             result = await client.incrby(built_key, amount)
            
#             if ttl and await self.redis.ttl(built_key) == -1:
#                 await self.redis.expire(built_key, ttl)
            
#             return result
#         except Exception as e:
#             logger.error(f"Failed to increment key {key}: {e}")
#             return None

#     async def get_many(self, keys: List[str]) -> dict:
#         """Get multiple values"""
#         try:
#             built_keys = [self._build_key(key) for key in keys]
#             client = self.redis.get_client()
#             values = await client.mget(built_keys)
            
#             result = {}
#             for i, key in enumerate(keys):
#                 if values[i] is not None:
#                     result[key] = values[i]
            
#             return result
#         except Exception as e:
#             logger.error(f"Failed to get multiple keys: {e}")
#             return {}

#     async def clear_namespace(self) -> int:
#         """Clear all keys in namespace"""
#         pattern = f"{self.namespace}:*"
#         return await self.delete_pattern(pattern)

#     async def get_stats(self) -> dict:
#         """Get cache statistics"""
#         try:
#             health = await self.redis.health_check()
#             pattern = f"{self.namespace}:*"
#             keys = await self.redis.scan_iter(pattern, count=1000)
            
#             return {
#                 'namespace': self.namespace,
#                 'key_count': len(keys),
#                 'redis_health': health,
#                 'default_ttl': self.default_ttl
#             }
#         except Exception as e:
#             logger.error(f"Failed to get cache stats: {e}")
#             return {}