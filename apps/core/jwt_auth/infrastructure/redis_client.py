# import redis.asyncio as redis
# from redis.asyncio.connection import ConnectionPool
# from typing import Any, Optional, List, Tuple
# import pickle
# import zlib
# import logging
# from django.conf import settings

# logger = logging.getLogger(__name__)

# class AsyncRedisClient:
#     def __init__(self):
#         self.pool = None
#         self.connected = False
#         self._connect()

#     def _connect(self):
#         """Establish Redis connection pool"""
#         try:
#             self.pool = ConnectionPool(
#                 host=getattr(settings, 'REDIS_HOST', 'localhost'),
#                 port=getattr(settings, 'REDIS_PORT', 6379),
#                 db=getattr(settings, 'REDIS_DB', 0),
#                 password=getattr(settings, 'REDIS_PASSWORD', None),
#                 max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 20),
#                 socket_connect_timeout=5,
#                 socket_timeout=5,
#                 retry_on_timeout=True,
#                 health_check_interval=30,
#                 decode_responses=False
#             )
#             self.connected = True
#             logger.info("Redis connection pool created successfully")
#         except Exception as e:
#             logger.error(f"Failed to create Redis connection pool: {e}")
#             self.connected = False

#     def get_client(self) -> redis.Redis:
#         """Get Redis client from pool"""
#         if not self.connected or not self.pool:
#             raise ConnectionError("Redis is not connected")
#         return redis.Redis(connection_pool=self.pool)

#     async def get(self, key: str) -> Optional[Any]:
#         """Get value with compression and pickle support"""
#         try:
#             client = self.get_client()
#             value = await client.get(key)
            
#             if value is None:
#                 return None

#             # Decompress if needed
#             try:
#                 if value.startswith(b'compressed:'):
#                     value = zlib.decompress(value[11:])
#                 return pickle.loads(value)
#             except (pickle.PickleError, zlib.error) as e:
#                 logger.warning(f"Failed to deserialize Redis key {key}: {e}")
#                 return None

#         except Exception as e:
#             logger.error(f"Redis GET failed for key {key}: {e}")
#             return None

#     async def set(self, key: str, value: Any, expire: int = None, compress: bool = False) -> bool:
#         """Set value with optional compression and expiration"""
#         try:
#             client = self.get_client()
            
#             # Serialize data
#             serialized = pickle.dumps(value)
            
#             # Compress if requested and beneficial
#             if compress and len(serialized) > 100:
#                 serialized = b'compressed:' + zlib.compress(serialized)
            
#             if expire:
#                 await client.setex(key, expire, serialized)
#             else:
#                 await client.set(key, serialized)
            
#             return True
#         except Exception as e:
#             logger.error(f"Redis SET failed for key {key}: {e}")
#             return False

#     async def setex(self, key: str, expire: int, value: Any) -> bool:
#         """Set value with expiration"""
#         return await self.set(key, value, expire)

#     async def delete(self, key: str) -> bool:
#         """Delete key"""
#         try:
#             client = self.get_client()
#             result = await client.delete(key)
#             return result > 0
#         except Exception as e:
#             logger.error(f"Redis DELETE failed for key {key}: {e}")
#             return False

#     async def exists(self, key: str) -> bool:
#         """Check if key exists"""
#         try:
#             client = self.get_client()
#             result = await client.exists(key)
#             return result > 0
#         except Exception as e:
#             logger.error(f"Redis EXISTS failed for key {key}: {e}")
#             return False

#     async def expire(self, key: str, expire: int) -> bool:
#         """Set key expiration"""
#         try:
#             client = self.get_client()
#             return await client.expire(key, expire)
#         except Exception as e:
#             logger.error(f"Redis EXPIRE failed for key {key}: {e}")
#             return False

#     async def ttl(self, key: str) -> int:
#         """Get key TTL"""
#         try:
#             client = self.get_client()
#             return await client.ttl(key)
#         except Exception as e:
#             logger.error(f"Redis TTL failed for key {key}: {e}")
#             return -2

#     async def pipeline(self):
#         """Get pipeline for batch operations"""
#         client = self.get_client()
#         return client.pipeline()

#     async def scan_iter(self, pattern: str, count: int = 100) -> List[str]:
#         """Iterate over keys matching pattern"""
#         try:
#             client = self.get_client()
#             keys = []
#             async for key in client.scan_iter(match=pattern, count=count):
#                 keys.append(key.decode('utf-8'))
#             return keys
#         except Exception as e:
#             logger.error(f"Redis SCAN failed for pattern {pattern}: {e}")
#             return []

#     async def health_check(self) -> dict:
#         """Perform health check on Redis connection"""
#         try:
#             client = self.get_client()
#             info = await client.info()
#             ping = await client.ping()
            
#             return {
#                 'status': 'healthy' if ping else 'unhealthy',
#                 'version': info.get('redis_version', 'unknown'),
#                 'connected_clients': info.get('connected_clients', 0),
#                 'used_memory': info.get('used_memory_human', 'unknown'),
#                 'keyspace_hits': info.get('keyspace_hits', 0),
#                 'keyspace_misses': info.get('keyspace_misses', 0)
#             }
#         except Exception as e:
#             logger.error(f"Redis health check failed: {e}")
#             return {'status': 'unhealthy', 'error': str(e)}

#     async def close(self):
#         """Close connection pool"""
#         if self.pool:
#             await self.pool.disconnect()
#             self.connected = False

# # Singleton instance
# _redis_client = None

# def get_redis_client() -> AsyncRedisClient:
#     global _redis_client
#     if _redis_client is None:
#         _redis_client = AsyncRedisClient()
#     return _redis_client