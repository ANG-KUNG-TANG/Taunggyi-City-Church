import pickle
import asyncio
from typing import Any, Optional, Dict, List
from redis.asyncio import Redis
from django.conf import settings
from .base import AsyncBaseCache
from .keys import key_generator


class AsyncRedisCache(AsyncBaseCache):
    """Asynchronous Redis cache using redis.asyncio"""
    
    def __init__(self):
        self.client: Optional[Redis] = None
        self.default_timeout = getattr(settings, 'CACHE_TIMEOUT', 300)
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        redis_url = getattr(settings, 'ASYNC_REDIS_URL', 'redis://localhost:6379/1')
        self.client = Redis.from_url(redis_url, decode_responses=False)
    
    async def get(self, key: str) -> Any:
        """Get value from cache"""
        try:
            value = await self.client.get(key)
            if value is not None:
                return pickle.loads(value)
            return None
        except (pickle.PickleError, TypeError):
            # Fallback to direct value if not pickled
            return await self.client.get(key)
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            # Try to pickle the value
            try:
                value = pickle.dumps(value)
            except (pickle.PickleError, TypeError):
                # If not picklable, store as is
                pass
            
            return await self.client.setex(key, timeout, value)
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return await self.client.delete(key) > 0
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False
    
    async def clear(self) -> bool:
        """Clear all cache"""
        try:
            await self.client.flushdb()
            return True
        except Exception:
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        try:
            pipeline = self.client.pipeline()
            for key in keys:
                pipeline.get(key)
            values = await pipeline.execute()
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = pickle.loads(value)
                    except (pickle.PickleError, TypeError):
                        result[key] = value
            return result
        except Exception:
            return {}
    
    async def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """Set multiple values"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            pipeline = self.client.pipeline()
            for key, value in data.items():
                # Try to pickle the value
                try:
                    value = pickle.dumps(value)
                except (pickle.PickleError, TypeError):
                    pass
                
                pipeline.setex(key, timeout, value)
            
            await pipeline.execute()
            return True
        except Exception:
            return False
    
    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment value"""
        try:
            return await self.client.incrby(key, delta)
        except Exception:
            return None
    
    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement value"""
        try:
            return await self.client.decrby(key, delta)
        except Exception:
            return None
    
    async def get_or_set(self, key: str, default_func, timeout: Optional[int] = None) -> Any:
        """Get value or set from function if not exists"""
        value = await self.get(key)
        if value is None:
            value = default_func() if not asyncio.iscoroutinefunction(default_func) else await default_func()
            await self.set(key, value, timeout)
        return value
    
    async def close(self):
        """Close connection"""
        if self.client:
            await self.client.close()


# Global async cache instance
async_cache = AsyncRedisCache()