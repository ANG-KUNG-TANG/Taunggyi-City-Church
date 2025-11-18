"""
Production Cache Serialization Utilities
Reliability Level: HIGH
"""
import json
import pickle
from typing import Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SerializationType(Enum):
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"

class CacheSerializer:
    """
    Production-grade cache serialization
    Reliability Level: HIGH
    """
    
    @staticmethod
    def serialize(value: Any, method: SerializationType = SerializationType.JSON) -> str:
        """
        Serialize value for cache storage
        Reliability Level: HIGH
        """
        try:
            if method == SerializationType.JSON:
                return json.dumps(value, default=str, separators=(',', ':'))
            elif method == SerializationType.PICKLE:
                return pickle.dumps(value).hex()
            elif method == SerializationType.STRING:
                return str(value)
            else:
                raise ValueError(f"Unsupported serialization method: {method}")
        except Exception as e:
            logger.error(f"Serialization failed for type {type(value)}: {e}")
            raise
    
    @staticmethod
    def deserialize(value: str, method: SerializationType = SerializationType.JSON) -> Any:
        """
        Deserialize value from cache
        Reliability Level: HIGH
        """
        if value is None:
            return None
            
        try:
            if method == SerializationType.JSON:
                return json.loads(value)
            elif method == SerializationType.PICKLE:
                return pickle.loads(bytes.fromhex(value))
            elif method == SerializationType.STRING:
                return value
            else:
                raise ValueError(f"Unsupported deserialization method: {method}")
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise
    
    @staticmethod
    def detect_serialization_method(value: Any) -> SerializationType:
        """
        Detect appropriate serialization method for value
        Reliability Level: MEDIUM
        """
        if isinstance(value, (str, int, float, bool, type(None))):
            return SerializationType.JSON
        elif isinstance(value, (list, dict)):
            try:
                json.dumps(value)
                return SerializationType.JSON
            except (TypeError, ValueError):
                return SerializationType.PICKLE
        else:
            return SerializationType.PICKLE
    
    @staticmethod
    def safe_serialize(value: Any, default_method: SerializationType = None) -> tuple[str, SerializationType]:
        """
        Safely serialize with fallback
        Reliability Level: HIGH
        """
        try:
            method = default_method or CacheSerializer.detect_serialization_method(value)
            return CacheSerializer.serialize(value, method), method
        except Exception as e:
            logger.warning(f"Primary serialization failed, using string fallback: {e}")
            return str(value), SerializationType.STRING
    
    @staticmethod
    def safe_deserialize(value: str, method: SerializationType) -> Any:
        """
        Safely deserialize with error handling
        Reliability Level: HIGH
        """
        try:
            return CacheSerializer.deserialize(value, method)
        except Exception as e:
            logger.error(f"Deserialization failed for method {method}: {e}")
            return None