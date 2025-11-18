"""
Abstract Cache Interface for Production
Reliability Level: HIGH
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class AsyncCache(ABC):
    """
    Production-grade abstract cache interface
    Reliability Level: HIGH
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache with optional expiry"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass
    
    @abstractmethod
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiry"""
        pass
    
    @abstractmethod
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        pass
    
    @abstractmethod
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value"""
        pass
    
    @abstractmethod
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value"""
        pass
    
    @abstractmethod
    async def flush_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        pass
    
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        pass
    
    @abstractmethod
    async def set_many(self, data: Dict[str, Any], expire: int = None) -> bool:
        """Set multiple values"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health check for cache service"""
        pass
    
    def get_pipeline(self):
        """Get pipeline for batch operations (optional)"""
        raise NotImplementedError("Pipeline not supported")