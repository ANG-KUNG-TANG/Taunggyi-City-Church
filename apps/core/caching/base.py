from abc import ABC, abstractmethod
from typing import Any, Optional, Union, Dict, List
import pickle
import hashlib
import asyncio
from functools import wraps
import time


class BaseCache(ABC):
    """Abstract base class for cache implementations"""
    
    @abstractmethod
    def get(self, key: str) -> Any:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        pass
    
    @abstractmethod
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        pass


class AsyncBaseCache(ABC):
    """Abstract base class for async cache implementations"""
    
    @abstractmethod
    async def get(self, key: str) -> Any:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        pass
    
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        pass