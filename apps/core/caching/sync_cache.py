import pickle
from typing import Any, Optional, Dict, List
from django.core.cache import cache as django_cache
from django.conf import settings
from .base import BaseCache
from .keys import key_generator


class SyncRedisCache(BaseCache):
    """Synchronous Redis cache using django-redis"""
    
    def __init__(self, alias: str = 'default'):
        self.client = django_cache
        self.default_timeout = getattr(settings, 'CACHE_TIMEOUT', 300)
    
    def get(self, key: str) -> Any:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            if value is not None:
                return pickle.loads(value)
            return None
        except (pickle.PickleError, TypeError):
            # Fallback to direct value if not pickled
            return self.client.get(key)
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
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
            
            return self.client.set(key, value, timeout)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return self.client.delete(key) > 0
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self.client.has_key(key)
        except Exception:
            return False
    
    def clear(self) -> bool:
        """Clear all cache"""
        try:
            self.client.clear()
            return True
        except Exception:
            return False
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        try:
            values = self.client.get_many(keys)
            result = {}
            for key, value in values.items():
                try:
                    result[key] = pickle.loads(value)
                except (pickle.PickleError, TypeError):
                    result[key] = value
            return result
        except Exception:
            return {}
    
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """Set multiple values"""
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            # Pickle values
            pickled_data = {}
            for key, value in data.items():
                try:
                    pickled_data[key] = pickle.dumps(value)
                except (pickle.PickleError, TypeError):
                    pickled_data[key] = value
            
            self.client.set_many(pickled_data, timeout)
            return True
        except Exception:
            return False
    
    def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment value"""
        try:
            return self.client.incr(key, delta)
        except Exception:
            return None
    
    def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement value"""
        try:
            return self.client.decr(key, delta)
        except Exception:
            return None
    
    def get_or_set(self, key: str, default_func, timeout: Optional[int] = None) -> Any:
        """Get value or set from function if not exists"""
        value = self.get(key)
        if value is None:
            value = default_func()
            self.set(key, value, timeout)
        return value


# Global sync cache instance
sync_cache = SyncRedisCache()